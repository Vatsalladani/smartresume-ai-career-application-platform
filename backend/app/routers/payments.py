from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.responses import success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models import PaymentEvent, User
from app.schemas.payment import (
    CreateOrderRequest,
    PaymentOrderOut,
    SubscriptionOut,
    VerifyPaymentRequest,
)
from app.services.audit_service import write_audit_log
from app.services.payment_service import (
    activate_subscription,
    create_payment_order,
    get_plan_consent_info,
    record_payment_event_if_new,
    verify_and_process_payment,
    verify_razorpay_signature,
)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/subscription")
def subscription(current_user: User = Depends(get_current_user)) -> dict:
    sub = current_user.subscription
    return success_response(
        SubscriptionOut(
            plan_name=sub.plan_name if sub else "FREE",
            status=sub.status if sub else "ACTIVE",
            expires_at=sub.expires_at if sub else None,
        ).model_dump()
    )


@router.get("/pricing")
def get_pricing_tables() -> dict:
    """Returns centralized pricing and currencies (Rule 11 & Rule 14)."""
    settings = get_settings()
    return success_response({
        "default_currency": settings.default_currency,
        "payment_mode": settings.payment_mode,
        "currencies": settings.currency_prices,
        "test_upi_id": settings.test_upi_id if settings.payment_mode == "test" else None,
    })


@router.get("/consent-info")
def get_consent(plan: str = "PRO_MONTHLY", currency: str = "INR") -> dict:
    """Returns explicit mandate terms before user confirms checkout (Rule 16)."""
    info = get_plan_consent_info(plan, currency=currency)
    return success_response(info)


@router.get("/billing-summary")
def get_billing(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    from app.services.quota_service import get_billing_summary
    summary = get_billing_summary(db, current_user.id)
    return success_response(summary)


@router.get("/history")
def get_payment_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Returns history of user transactions / orders."""
    events = (
        db.query(PaymentEvent)
        .filter(PaymentEvent.user_id == current_user.id)
        .order_by(PaymentEvent.created_at.desc())
        .limit(20)
        .all()
    )
    history = [
        {
            "id": e.id,
            "provider": e.provider,
            "event_id": e.event_id,
            "event_type": e.event_type,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "details": e.payload_json or {},
        }
        for e in events
    ]
    return success_response(history)


@router.post("/cancel")
def cancel_subscription(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    sub = current_user.subscription
    if sub and sub.plan_name != "FREE":
        sub.status = "CANCELLED"
        write_audit_log(db, action="payment.cancel_subscription", user_id=current_user.id, metadata={"previous_plan": sub.plan_name})
        db.commit()
        return success_response({
            "plan_name": sub.plan_name,
            "status": "CANCELLED",
            "expires_at": sub.expires_at,
        }, "Subscription cancelled. You will retain Pro access until the end of your billing cycle.")
    return success_response({"plan_name": "FREE", "status": "ACTIVE"}, "Already on Free plan.")


@router.post("/start-trial")
def start_pro_trial(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Activates the 7-Day Pro Trial (₹0) without requiring a credit card."""
    from app.services.payment_service import activate_pro_trial
    result = activate_pro_trial(db, current_user.id)
    write_audit_log(db, action="payment.start_trial", user_id=current_user.id, metadata=result)
    return success_response(result, result["message"])


@router.post("/create-order")
def create_order(
    payload: CreateOrderRequest | None = None,
    plan: str | None = None,
    currency: str = "INR",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    selected_plan = (payload.plan if payload else plan) or "PRO_MONTHLY"
    selected_currency = (payload.currency if payload else currency) or "INR"

    order = create_payment_order(current_user.id, plan_name=selected_plan, currency=selected_currency)
    if order["provider"] == "mock" and selected_plan != "SINGLE_EXPORT":
        from app.services.payment_service import activate_subscription, record_payment_event_if_new
        activate_subscription(db, current_user.id, plan_name=selected_plan, payment_id=order["order_id"])
        record_payment_event_if_new(
            db,
            provider="mock",
            event_id=order["order_id"],
            event_type="payment.captured",
            user_id=current_user.id,
            payload_json={"order_id": order["order_id"], "plan": selected_plan, "auto_activated": True},
        )
    write_audit_log(
        db,
        action="payment.create_order",
        user_id=current_user.id,
        metadata={"provider": order["provider"], "plan": selected_plan, "currency": selected_currency},
    )
    db.commit()
    return success_response(PaymentOrderOut(**order).model_dump(), "Payment order created.")


@router.post("/verify")
def verify_payment_endpoint(
    payload: VerifyPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Verifies payment signature / test simulator and activates plan or export credit."""
    result = verify_and_process_payment(
        db=db,
        user_id=current_user.id,
        order_id=payload.order_id,
        payment_id=payload.payment_id,
        signature=payload.signature,
        plan_name=payload.plan,
    )
    write_audit_log(
        db,
        action="payment.verify",
        user_id=current_user.id,
        metadata={"order_id": payload.order_id, "payment_id": payload.payment_id, "plan": payload.plan},
    )
    db.commit()
    return success_response(result, result.get("message", "Payment verified successfully."))


@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    raw_body = await request.body()
    if not verify_razorpay_signature(raw_body, x_razorpay_signature):
        raise AppError("Invalid webhook signature.", status.HTTP_400_BAD_REQUEST)

    payload = await request.json()
    event_type = payload.get("event")

    if event_type == "payment.captured":
        payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
        event_id = payload.get("id") or payment.get("id")
        user_id = payment.get("notes", {}).get("user_id")
        plan_name = payment.get("notes", {}).get("plan", "PRO_MONTHLY")

        if not event_id:
            raise AppError("Missing event/payment ID in webhook payload.", status.HTTP_400_BAD_REQUEST)

        is_new = record_payment_event_if_new(
            db=db,
            provider="razorpay",
            event_id=event_id,
            event_type=event_type,
            user_id=int(user_id) if user_id else None,
            payload_json=payload,
        )
        if not is_new:
            return success_response({"status": "duplicate_acknowledged"}, "Duplicate webhook acknowledged.")

        if user_id:
            user_id_int = int(user_id)
            from app.services.payment_service import activate_subscription
            activate_subscription(db, user_id_int, payment_id=event_id, plan_name=plan_name)
            write_audit_log(db, action="payment.webhook_captured", user_id=user_id_int, metadata={"payment_id": event_id, "plan": plan_name})
            db.commit()

        return success_response({"status": "processed"}, "Webhook processed successfully.")

    return success_response({"status": "processed"}, "Webhook processed successfully.")

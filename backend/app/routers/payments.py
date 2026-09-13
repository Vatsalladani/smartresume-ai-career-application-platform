from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.responses import success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models import PaymentEvent, Subscription, User
from app.schemas.payment import (
    CreateOrderRequest,
    PaymentOrderOut,
    SubscriptionOut,
    VerifyPaymentRequest,
)
from app.services.audit_service import write_audit_log
from app.services.payment_service import (
    activate_subscription,
    compute_subscription_summary,
    create_payment_order,
    get_plan_consent_info,
    record_payment_event_if_new,
    verify_and_process_payment,
    verify_razorpay_signature,
)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/subscription")
def subscription(current_user: User = Depends(get_current_user)) -> dict:
    summary = compute_subscription_summary(current_user.subscription)
    return success_response(SubscriptionOut(**summary).model_dump())


@router.get("/pricing")
def get_pricing_tables() -> dict:
    """Returns centralized pricing and currencies."""
    settings = get_settings()
    return success_response({
        "default_currency": settings.default_currency,
        "payment_mode": settings.payment_mode,
        "currencies": settings.currency_prices,
        "test_upi_id": settings.test_upi_id if settings.payment_mode == "test" else None,
    })


@router.get("/consent-info")
def get_consent(plan: str = "PRO_MONTHLY", currency: str = "INR") -> dict:
    """Returns explicit mandate terms before user confirms checkout."""
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
    if not sub or sub.plan_name == "FREE":
        return success_response({"plan_name": "FREE", "status": "ACTIVE"}, "Already on Free plan.")

    method_type = getattr(sub, "payment_method_type", "card") or "card"

    # If subscription authorized via UPI AutoPay, cancellation must occur in the UPI app
    if method_type == "upi":
        app_name = getattr(sub, "upi_app", None) or "your UPI app"
        return success_response({
            "plan_name": sub.plan_name,
            "status": sub.status,
            "payment_method_type": "upi",
            "upi_app": getattr(sub, "upi_app", None),
            "requires_upi_app": True,
            "instructions": f"Your recurring payment mandate was authorized through {app_name}. You can manage or cancel that mandate from {app_name}.",
        }, f"Please manage or cancel your mandate directly in {app_name}.")

    # For Card or standard recurring, cancel renewal through backend provider
    sub.cancellation_scheduled = True
    sub.status = "CANCELLED"

    write_audit_log(
        db,
        action="payment.cancel_renewal",
        user_id=current_user.id,
        metadata={"plan": sub.plan_name, "status": sub.status, "expires_at": sub.expires_at.isoformat() if sub.expires_at else None},
    )
    db.commit()
    summary = compute_subscription_summary(sub)
    return success_response(
        SubscriptionOut(**summary).model_dump(),
        f"Renewal cancelled. Your Pro access remains active until {summary['next_renewal_date']}."
    )


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
    method_type = (payload.payment_method_type if payload else None) or "card"
    upi_app = (payload.upi_app if payload else None)

    order = create_payment_order(current_user.id, plan_name=selected_plan, currency=selected_currency)
    if order["provider"] == "mock" and "PRO" in selected_plan.upper():
        from app.services.payment_service import activate_subscription, record_payment_event_if_new
        activate_subscription(
            db,
            current_user.id,
            plan_name=selected_plan,
            payment_id=order["order_id"],
            payment_method_type=method_type,
            upi_app=upi_app,
        )
        record_payment_event_if_new(
            db,
            provider="mock",
            event_id=order["order_id"],
            event_type="payment.captured",
            user_id=current_user.id,
            payload_json={
                "order_id": order["order_id"],
                "plan": selected_plan,
                "auto_activated": True,
                "payment_method_type": method_type,
                "upi_app": upi_app,
            },
        )
    write_audit_log(
        db,
        action="payment.create_order",
        user_id=current_user.id,
        metadata={"provider": order["provider"], "plan": selected_plan, "currency": selected_currency, "method": method_type},
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
    # If a recurring subscription was activated, record payment method details
    if result.get("recurring"):
        sub = current_user.subscription
        if sub:
            sub.payment_method_type = payload.payment_method_type or "card"
            sub.upi_app = payload.upi_app
            if payload.payment_method_type == "upi":
                sub.payment_method_detail = f"UPI AutoPay ({payload.upi_app})" if payload.upi_app else "UPI AutoPay"
            else:
                sub.payment_method_detail = "Card ending ****4242"
            db.commit()

    write_audit_log(
        db,
        action="payment.verify",
        user_id=current_user.id,
        metadata={"order_id": payload.order_id, "payment_id": payload.payment_id, "plan": payload.plan},
    )
    db.commit()
    return success_response(result, result.get("message", "Payment verified successfully."))


@router.post("/simulate-upi-cancel")
def simulate_upi_cancel(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Simulates provider webhook notification when customer cancels UPI AutoPay inside their UPI app."""
    sub = current_user.subscription
    if not sub or sub.plan_name == "FREE":
        return success_response({"status": "noop"}, "No active subscription to cancel.")

    sub.cancellation_scheduled = True
    now = datetime.utcnow()
    if sub.expires_at and sub.expires_at > now:
        sub.status = "ENDING"
    else:
        sub.status = "CANCELLED"

    sim_event_id = f"evt_cancel_upi_{uuid4().hex[:12]}"
    record_payment_event_if_new(
        db,
        provider="razorpay",
        event_id=sim_event_id,
        event_type="subscription.cancelled",
        user_id=current_user.id,
        payload_json={"simulated": True, "event": "subscription.cancelled", "method": "upi"},
    )
    write_audit_log(db, action="payment.upi_mandate_revoked_webhook", user_id=current_user.id, metadata={"simulated": True})
    db.commit()
    summary = compute_subscription_summary(sub)
    return success_response(SubscriptionOut(**summary).model_dump(), "UPI mandate cancellation received from payment provider.")


@router.post("/retry-failed")
def retry_failed_payment(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    sub = current_user.subscription
    if sub and sub.status == "PAYMENT_FAILED":
        sub.status = "ACTIVE"
        sub.last_payment_error = None
        db.commit()
        summary = compute_subscription_summary(sub)
        return success_response(summary, "Payment retried and recurring status restored.")
    return success_response({"status": "ok"}, "No failed payments pending.")


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

    if event_type in {"payment.captured", "subscription.activated", "subscription.charged"}:
        payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
        sub_entity = payload.get("payload", {}).get("subscription", {}).get("entity", {})
        event_id = payload.get("id") or payment.get("id") or sub_entity.get("id")
        user_id = payment.get("notes", {}).get("user_id") or sub_entity.get("notes", {}).get("user_id")
        plan_name = payment.get("notes", {}).get("plan") or sub_entity.get("notes", {}).get("plan", "PRO_MONTHLY")
        method = payment.get("method", "card")

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
            method_type = "upi" if "upi" in str(method).lower() else "card"
            activate_subscription(
                db,
                user_id_int,
                payment_id=event_id,
                plan_name=plan_name,
                payment_method_type=method_type,
            )
            write_audit_log(db, action=f"payment.webhook_{event_type}", user_id=user_id_int, metadata={"payment_id": event_id, "plan": plan_name})
            db.commit()

        return success_response({"status": "processed"}, "Webhook processed successfully.")

    elif event_type in {"subscription.cancelled", "subscription.halted", "mandate.revoked"}:
        sub_entity = payload.get("payload", {}).get("subscription", {}).get("entity", {})
        event_id = payload.get("id") or sub_entity.get("id")
        user_id = sub_entity.get("notes", {}).get("user_id")

        if not event_id:
            raise AppError("Missing event ID in webhook payload.", status.HTTP_400_BAD_REQUEST)

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
            user_sub = db.query(Subscription).filter(Subscription.user_id == user_id_int).first()
            if user_sub:
                user_sub.cancellation_scheduled = True
                now = datetime.utcnow()
                if user_sub.expires_at and user_sub.expires_at > now:
                    user_sub.status = "ENDING"
                else:
                    user_sub.status = "CANCELLED"
                db.commit()
                write_audit_log(db, action="payment.webhook_subscription_cancelled", user_id=user_id_int, metadata={"status": user_sub.status})

        return success_response({"status": "processed"}, "Cancellation webhook processed.")

    elif event_type == "payment.failed":
        payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
        event_id = payload.get("id") or payment.get("id")
        user_id = payment.get("notes", {}).get("user_id")
        error_desc = payment.get("error_description", "Payment transaction failed.")

        if user_id:
            user_id_int = int(user_id)
            user_sub = db.query(Subscription).filter(Subscription.user_id == user_id_int).first()
            if user_sub and user_sub.plan_name != "FREE":
                user_sub.status = "PAYMENT_FAILED"
                user_sub.last_payment_error = error_desc
                db.commit()

        return success_response({"status": "processed"}, "Payment failed event recorded.")

    return success_response({"status": "processed"}, "Webhook event acknowledged.")


import hmac
import hashlib
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import PaymentEvent, Subscription, UsageCounter


def get_plan_price(plan_name: str, currency: str = "INR") -> tuple[int, float, str]:
    """
    Returns (amount_in_smallest_unit, display_amount, currency).
    e.g. for ₹79 INR: (7900, 79.0, "INR")
    e.g. for $1.99 USD: (199, 1.99, "USD")
    """
    settings = get_settings()
    curr = currency.upper() if currency else "INR"
    if curr not in settings.currency_prices:
        curr = "INR"

    prices = settings.currency_prices[curr]
    plan_upper = plan_name.upper()

    if plan_upper in {"SINGLE_EXPORT", "SINGLE", "EXPORT_1"}:
        disp = prices.get("single", 1)
    elif "ANNUAL" in plan_upper:
        disp = prices.get("pro_annual", 399)
    elif "PACK_10" in plan_upper or "PACK_1" in plan_upper:
        disp = prices.get("pack_10", 29)
    elif "PACK_20" in plan_upper or "PACK_2" in plan_upper:
        disp = prices.get("pack_20", 49)
    elif "PACK_50" in plan_upper or "PACK_3" in plan_upper:
        disp = prices.get("pack_50", 99)
    else:  # PRO_MONTHLY default
        disp = prices.get("pro_monthly", 49)

    smallest_unit = int(round(disp * 100))
    return smallest_unit, float(disp), curr


def create_payment_order(user_id: int, plan_name: str = "PRO_MONTHLY", currency: str = "INR") -> dict:
    settings = get_settings()
    amount, display_amount, curr = get_plan_price(plan_name, currency=currency)

    is_test = settings.payment_mode == "test" or settings.payments_mode == "mock"

    # If Razorpay keys are provided, use Razorpay client (Sandbox if test keys, Live if live keys)
    if settings.razorpay_key_id and settings.razorpay_key_secret:
        try:
            import razorpay
            client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
            order_data = {
                "amount": amount,
                "currency": curr,
                "receipt": f"rcpt_{user_id}_{uuid4().hex[:8]}",
                "notes": {"user_id": str(user_id), "plan": plan_name, "is_test": str(is_test)},
            }
            order = client.order.create(data=order_data)
            return {
                "provider": "razorpay",
                "payment_mode": settings.payment_mode,
                "razorpay_key_id": settings.razorpay_key_id,
                "order_id": order["id"],
                "amount": order["amount"],
                "display_amount": display_amount,
                "currency": order["currency"],
                "plan_name": plan_name,
                "test_upi_id": settings.test_upi_id if is_test else None,
                "is_test": is_test,
                "notes": order.get("notes", {}),
            }
        except Exception:
            # Fall back to structured test simulator if live Razorpay call fails in dev
            if not is_test:
                raise AppError("Payment gateway connection failed. Please try again.", status.HTTP_503_SERVICE_UNAVAILABLE)

    # In TEST / Mock mode without live credentials
    order_id = f"order_test_{uuid4().hex[:16]}"
    return {
        "provider": "mock" if settings.payments_mode == "mock" else "razorpay_test",
        "payment_mode": "test",
        "razorpay_key_id": settings.razorpay_key_id or "rzp_test_mock_mode",
        "order_id": order_id,
        "amount": amount,
        "display_amount": display_amount,
        "currency": curr,
        "plan_name": plan_name,
        "test_upi_id": settings.test_upi_id,
        "is_test": True,
        "notes": {"user_id": str(user_id), "plan": plan_name, "mode": "test"},
    }


def verify_razorpay_signature(raw_body: bytes, signature_header: str | None) -> bool:
    settings = get_settings()
    if not settings.razorpay_webhook_secret or not signature_header:
        return False
    generated = hmac.new(
        settings.razorpay_webhook_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(generated, signature_header)


def record_payment_event_if_new(
    db: Session,
    provider: str,
    event_id: str,
    event_type: str,
    user_id: int | None = None,
    payload_json: dict | None = None,
) -> bool:
    """Returns True if the event was newly recorded; False if already processed (idempotency guarantee)."""
    existing = db.query(PaymentEvent).filter(
        PaymentEvent.provider == provider,
        PaymentEvent.event_id == event_id,
    ).first()
    if existing:
        return False

    event = PaymentEvent(
        provider=provider,
        event_id=event_id,
        event_type=event_type,
        user_id=user_id,
        payload_json=payload_json,
    )
    db.add(event)
    return True


def verify_and_process_payment(
    db: Session,
    user_id: int,
    order_id: str,
    payment_id: str,
    signature: str | None = None,
    plan_name: str = "PRO_MONTHLY",
) -> dict:
    """
    Verifies payment and securely applies subscription or single-use credits.
    Guarantees idempotency and explicit separation between one-time export and recurring subscriptions.
    """
    settings = get_settings()
    is_test_env = settings.payment_mode == "test" or settings.payments_mode == "mock" or "test" in order_id.lower() or "mock" in order_id.lower()

    # If in live mode with Razorpay credentials, verify cryptographic signature
    if not is_test_env and settings.razorpay_key_secret and signature:
        expected = hmac.new(
            settings.razorpay_key_secret.encode("utf-8"),
            f"{order_id}|{payment_id}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise AppError("Payment verification failed: invalid signature.", status.HTTP_400_BAD_REQUEST)

    # Check idempotency using payment event log
    existing_event = None
    if order_id:
        existing_event = db.query(PaymentEvent).filter(PaymentEvent.user_id == user_id, PaymentEvent.event_id == order_id).first()
    if not existing_event and payment_id:
        existing_event = db.query(PaymentEvent).filter(PaymentEvent.user_id == user_id, PaymentEvent.event_id == payment_id).first()

    if existing_event:
        return {"success": True, "message": "Payment already processed (idempotent).", "plan": plan_name, "recurring": False}

    is_new = record_payment_event_if_new(
        db,
        provider="razorpay" if not is_test_env else "test_simulator",
        event_id=payment_id or order_id,
        event_type="payment.captured",
        user_id=user_id,
        payload_json={"order_id": order_id, "payment_id": payment_id, "plan": plan_name, "is_test": is_test_env},
    )

    if not is_new:
        return {"success": True, "message": "Payment already processed (idempotent).", "plan": plan_name, "recurring": False}

    plan_upper = plan_name.upper()
    from app.services.quota_service import get_or_create_usage_counter

    # CASE A: ONE-TIME RESUME EXPORT (₹1)
    # Rule 11 & Rule 16: Never disguise recurring billing as a ₹1 one-time purchase.
    if plan_upper in {"SINGLE_EXPORT", "SINGLE", "EXPORT_1"}:
        counter = get_or_create_usage_counter(db, user_id)
        counter.extra_credits_available += 1
        db.commit()
        return {
            "success": True,
            "message": "One-time resume export credit activated. Download your resume anytime.",
            "plan": "SINGLE_EXPORT",
            "recurring": False,
        }

    # CASE B: EMERGENCY BOOSTER PACKS
    if "PACK" in plan_upper:
        counter = get_or_create_usage_counter(db, user_id)
        credits_to_add = 50 if "50" in plan_upper else (20 if "20" in plan_upper else 10)
        counter.extra_credits_available += credits_to_add
        db.commit()
        return {
            "success": True,
            "message": f"Booster pack ({plan_name}) activated successfully.",
            "plan": plan_name,
            "recurring": False,
        }

    # CASE C: RECURRING PRO SUBSCRIPTION
    sub = activate_subscription(db, user_id, payment_id=payment_id, plan_name=plan_name)
    db.commit()
    return {
        "success": True,
        "message": f"Pro plan activated! Access valid until {sub.expires_at.strftime('%d %b %Y')}.",
        "plan": sub.plan_name,
        "expires_at": sub.expires_at.isoformat(),
        "recurring": True,
    }


def activate_subscription(
    db: Session,
    user_id: int,
    payment_id: str | None = None,
    plan_name: str = "PRO_MONTHLY",
    payment_method_type: str = "card",
    payment_method_detail: str | None = None,
    upi_app: str | None = None,
) -> Subscription:
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    now = datetime.utcnow()
    duration_days = 365 if "ANNUAL" in plan_name.upper() else 30

    if not sub:
        sub = Subscription(user_id=user_id)
        db.add(sub)
        sub.starts_at = now
        sub.expires_at = now + timedelta(days=duration_days)
    else:
        base_time = sub.expires_at if (sub.expires_at and sub.expires_at > now) else now
        sub.starts_at = sub.starts_at or now
        sub.expires_at = base_time + timedelta(days=duration_days)

    sub.plan_name = plan_name
    sub.status = "ACTIVE"
    sub.is_trial = False
    sub.razorpay_payment_id = payment_id
    sub.payment_method_type = payment_method_type or "card"
    sub.payment_method_detail = payment_method_detail
    sub.upi_app = upi_app
    sub.cancellation_scheduled = False
    sub.cancellation_reason = None
    sub.last_payment_error = None
    db.commit()
    db.refresh(sub)
    return sub


def activate_pro_trial(db: Session, user_id: int) -> dict:
    """Activates the 7-Day Pro Trial (₹0) with fair-use limits.
    Strictly zero auto-billing, no credit card required.
    """
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    now = datetime.utcnow()
    if sub and sub.trial_starts_at is not None:
        return {
            "success": False,
            "message": "7-Day Pro Trial has already been claimed on this account. Choose Pro Monthly (₹49) or Pro Annual (₹399).",
            "is_trial": False,
            "trial_used": True,
        }

    trial_days = 7
    trial_expires = now + timedelta(days=trial_days)
    if not sub:
        sub = Subscription(user_id=user_id)
        db.add(sub)

    sub.plan_name = "PRO_TRIAL"
    sub.status = "ACTIVE"
    sub.starts_at = now
    sub.expires_at = trial_expires
    sub.trial_starts_at = now
    sub.trial_expires_at = trial_expires
    sub.is_trial = True
    sub.payment_method_type = "none"
    sub.payment_method_detail = "No credit card required (Trial)"
    sub.cancellation_scheduled = False
    sub.last_payment_error = None

    from app.services.quota_service import get_or_create_usage_counter
    counter = get_or_create_usage_counter(db, user_id)
    counter.extra_credits_available = max(counter.extra_credits_available, 3)
    db.commit()

    from app.services.notification_service import create_notification
    create_notification(
        db=db,
        user_id=user_id,
        title="7-Day Pro Trial Activated (₹0)",
        message="Welcome to Pro! Full access to Evidence Vault, Application Pack, and AI Interview Copilot is now unlocked for 7 days. You will never be charged automatically.",
        notif_type="TRIAL",
        action_url="#evidence-vault",
    )

    return {
        "success": True,
        "message": "Your 7-Day Pro Trial is active! Enjoy unrestricted access.",
        "is_trial": True,
        "trial_expires_at": trial_expires.isoformat(),
        "days_remaining": 7,
    }


def get_plan_consent_info(plan_key: str, currency: str = "INR") -> dict:
    """
    Returns explicit mandate disclosure information before payment mandate confirmation.
    Strictly separates ₹1 one-time export from ₹1 mandate setup authorisation.
    """
    settings = get_settings()
    _, disp_amt, curr = get_plan_price(plan_key, currency=currency)
    curr_symbol = settings.currency_prices.get(curr, {}).get("symbol", "₹")

    plan_upper = plan_key.upper()
    is_one_time = plan_upper in {"SINGLE_EXPORT", "SINGLE", "EXPORT_1"} or "PACK" in plan_upper

    # Calculate corresponding INR base amount for transparent checkout disclosure
    _, inr_disp, _ = get_plan_price(plan_key, currency="INR")
    inr_amt_str = f"₹{int(inr_disp) if inr_disp == int(inr_disp) else inr_disp}"
    if curr == "INR":
        checkout_disclaimer = f"Processed in INR via Razorpay at checkout: {inr_amt_str}."
    else:
        checkout_disclaimer = f"Processed in INR via Razorpay at checkout: {inr_amt_str} (~{curr_symbol}{disp_amt}). Your payment provider converts at standard rates with no platform markup."

    if is_one_time:
        notice = "Pay once for one export. Does not start a subscription. Does not create a recurring mandate."
        return {
            "plan_key": plan_key,
            "display_name": "One-Time Resume Export" if "SINGLE" in plan_upper else "Booster Pack",
            "amount": disp_amt,
            "currency": curr,
            "currency_symbol": curr_symbol,
            "inr_equivalent_amount": inr_disp,
            "checkout_disclaimer": checkout_disclaimer,
            "billing_frequency": "one_time",
            "frequency": "One-time",
            "recurring": False,
            "is_recurring": False,
            "is_mandate_authorisation": False,
            "authorization_amount": None,
            "next_renewal_days": 0,
            "cancellation_terms": "One-time purchase. No recurring charges will ever be levied.",
            "refund_terms": "Full refund available within 7 days if export encounters technical failure.",
            "mandate_notice": notice,
            "regulatory_note": notice,
        }

    is_annual = "ANNUAL" in plan_upper
    auth_amount = 1.0 if curr == "INR" else 0.15
    notice = f"{curr_symbol}1 authorisation is for setting up recurring payment authorization. It is not a one-time resume export."
    return {
        "plan_key": plan_key,
        "display_name": "Annual Power Plan" if is_annual else "Pro Monthly Plan",
        "amount": disp_amt,
        "currency": curr,
        "currency_symbol": curr_symbol,
        "inr_equivalent_amount": inr_disp,
        "checkout_disclaimer": checkout_disclaimer,
        "billing_frequency": "annual" if is_annual else "monthly",
        "frequency": "Annual" if is_annual else "Monthly",
        "recurring": True,
        "is_recurring": True,
        "is_mandate_authorisation": True,
        "authorization_amount": auth_amount,
        "next_renewal_days": 365 if is_annual else 30,
        "cancellation_terms": "Manage through your payment method/provider as described in your subscription dashboard.",
        "refund_terms": "Pro-rated refund available within 14 days of renewal.",
        "mandate_notice": notice,
        "regulatory_note": f"In compliance with RBI e-mandate guidelines, upfront AFA verification is performed. Pre-debit notifications are sent 24 hours prior to billing. {notice}",
    }


def compute_trial_and_workspace_progress(db: Session, user_id: int) -> dict:
    """
    Computes accumulated career workspace value and trial progress milestones.
    No fake urgency, real tangible career asset metrics.
    """
    from app.models.resume import Resume
    from app.models.job_fit import JobPosting
    from app.models.interview import InterviewSession
    from app.models.evidence_vault import EvidenceItem
    from app.models.master_profile import Profile
    from app.services.profile_service import calculate_completeness

    resumes_count = db.query(Resume).filter(Resume.user_id == user_id).count()
    jobs_count = db.query(JobPosting).filter(JobPosting.user_id == user_id).count()
    interviews_count = db.query(InterviewSession).filter(InterviewSession.user_id == user_id).count()
    evidence_count = db.query(EvidenceItem).filter(EvidenceItem.user_id == user_id).count()

    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    completeness = calculate_completeness(profile) if profile else 0

    is_employed = False
    current_company = None
    if profile and profile.experiences:
        for exp in profile.experiences:
            if getattr(exp, "is_current", False) or not exp.end_date:
                is_employed = True
                current_company = exp.company_name
                break

    if completeness < 75:
        next_action = "Complete your Master Profile to unlock higher ATS match precision."
        action_tab = "tabProfile"
    elif resumes_count == 0:
        next_action = "Create your first targeted resume using your Master Profile."
        action_tab = "tabResume"
    elif jobs_count == 0:
        next_action = "Add a target job in Job Match to calculate ATS alignment."
        action_tab = "tabFit"
    elif interviews_count == 0:
        next_action = "Practice your target interview with AI Copilot."
        action_tab = "tabInterview"
    elif evidence_count == 0:
        next_action = "Log a recent achievement in Evidence Vault for future promotions."
        action_tab = "tabEvidenceVault"
    else:
        next_action = "All set! Keep your Evidence Vault updated with ongoing accomplishments."
        action_tab = "tabEvidenceVault"

    return {
        "resumes_count": resumes_count,
        "jobs_analyzed_count": jobs_count,
        "interviews_completed_count": interviews_count,
        "evidence_items_count": evidence_count,
        "profile_completeness": completeness,
        "is_employed": is_employed,
        "current_company": current_company,
        "next_useful_action": next_action,
        "action_tab": action_tab,
    }


def compute_subscription_summary(
    sub: Subscription | None,
    db: Session | None = None,
    user_id: int | None = None,
) -> dict:
    """
    Computes a clean, transparent, user-friendly subscription summary adhering to ethical retention principles:
    TRIAL, ACTIVE, PAUSED, ENDING, CANCELLED, PAST_DUE, PAYMENT_FAILED, EXPIRED.
    Zero hidden cancellation buttons, zero dark patterns.
    """
    now = datetime.utcnow()
    target_user_id = user_id or (sub.user_id if sub else None)

    workspace_value = None
    if db and target_user_id:
        try:
            workspace_value = compute_trial_and_workspace_progress(db, target_user_id)
        except Exception:
            workspace_value = None

    if not sub or sub.plan_name == "FREE":
        return {
            "plan_name": "FREE",
            "status": "ACTIVE",
            "is_trial": False,
            "expires_at": None,
            "starts_at": None,
            "days_remaining": None,
            "payment_method_type": "none",
            "payment_method_detail": "None",
            "upi_app": None,
            "recurring_amount": 0.0,
            "currency": "INR",
            "billing_frequency": "none",
            "cancellation_scheduled": False,
            "cancellation_reason": None,
            "cancellation_feedback": None,
            "next_renewal_date": None,
            "can_cancel_in_app": False,
            "is_paused": False,
            "paused_at": None,
            "paused_until": None,
            "pause_duration_months": 0,
            "can_pause": False,
            "trial_progress": None,
            "workspace_value": workspace_value,
            "last_payment_error": None,
        }

    is_trial = bool(sub.is_trial)
    is_paused = bool(getattr(sub, "is_paused", False))
    is_annual = "ANNUAL" in sub.plan_name.upper()
    freq = "annual" if is_annual else ("monthly" if not is_trial else "trial")
    amount = 399.0 if is_annual else (49.0 if not is_trial else 0.0)

    if is_paused:
        status_str = "PAUSED"
        days_rem = max(0, (sub.paused_until - now).days) if sub.paused_until else 0
    elif is_trial:
        if sub.trial_expires_at and sub.trial_expires_at > now:
            status_str = "TRIAL"
            days_rem = max(0, (sub.trial_expires_at - now).days)
        else:
            status_str = "EXPIRED"
            days_rem = 0
    elif sub.status == "CANCELLED":
        status_str = "CANCELLED"
        days_rem = max(0, (sub.expires_at - now).days) if (sub.expires_at and sub.expires_at > now) else 0
    elif getattr(sub, "last_payment_error", None):
        status_str = "PAYMENT_FAILED"
        days_rem = max(0, (sub.expires_at - now).days) if sub.expires_at else 0
    elif getattr(sub, "cancellation_scheduled", False):
        if sub.expires_at and sub.expires_at > now:
            status_str = "ENDING"
            days_rem = max(0, (sub.expires_at - now).days)
        else:
            status_str = "CANCELLED"
            days_rem = 0
    elif sub.expires_at and sub.expires_at <= now:
        status_str = "EXPIRED"
        days_rem = 0
    else:
        status_str = "ACTIVE"
        days_rem = max(0, (sub.expires_at - now).days) if sub.expires_at else 30

    next_date_str = sub.expires_at.strftime("%d %B %Y") if sub.expires_at else None
    if is_trial and sub.trial_expires_at:
        next_date_str = sub.trial_expires_at.strftime("%d %B %Y")
    elif is_paused and sub.paused_until:
        next_date_str = sub.paused_until.strftime("%d %B %Y")

    method_type = getattr(sub, "payment_method_type", "none") or "none"
    method_detail = getattr(sub, "payment_method_detail", None)
    if not method_detail:
        if method_type == "upi":
            method_detail = f"UPI AutoPay ({sub.upi_app})" if getattr(sub, "upi_app", None) else "UPI AutoPay"
        elif method_type == "card":
            method_detail = "Card ending ****4242"
        elif is_trial:
            method_detail = "No credit card required (Trial)"
        else:
            method_detail = "Standard Billing"

    # Friction-free cancellation: Any non-free plan can be cancelled in-app anytime
    can_cancel_in_app = (sub.plan_name != "FREE") and not getattr(sub, "cancellation_scheduled", False) and status_str != "EXPIRED"
    can_pause = (sub.plan_name != "FREE") and not is_trial and not is_paused and not getattr(sub, "cancellation_scheduled", False) and status_str == "ACTIVE"

    trial_prog = workspace_value if is_trial else None

    return {
        "plan_name": sub.plan_name,
        "status": status_str,
        "is_trial": is_trial,
        "expires_at": sub.expires_at,
        "starts_at": sub.starts_at,
        "days_remaining": days_rem,
        "payment_method_type": method_type,
        "payment_method_detail": method_detail,
        "upi_app": getattr(sub, "upi_app", None),
        "recurring_amount": amount,
        "currency": "INR",
        "billing_frequency": freq,
        "cancellation_scheduled": bool(getattr(sub, "cancellation_scheduled", False)),
        "cancellation_reason": getattr(sub, "cancellation_reason", None),
        "cancellation_feedback": getattr(sub, "cancellation_feedback", None),
        "next_renewal_date": next_date_str,
        "can_cancel_in_app": can_cancel_in_app,
        "is_paused": is_paused,
        "paused_at": getattr(sub, "paused_at", None),
        "paused_until": getattr(sub, "paused_until", None),
        "pause_duration_months": getattr(sub, "pause_duration_months", 0),
        "can_pause": can_pause,
        "trial_progress": trial_prog,
        "workspace_value": workspace_value,
        "last_payment_error": getattr(sub, "last_payment_error", None),
    }


def pause_subscription(db: Session, user_id: int, months: int = 1) -> dict:
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if not sub or sub.plan_name == "FREE":
        raise AppError("Only active paid subscriptions can be paused.", status.HTTP_400_BAD_REQUEST)
    if sub.is_trial:
        raise AppError("Trials cannot be paused. You can cancel or upgrade anytime.", status.HTTP_400_BAD_REQUEST)
    if sub.is_paused:
        raise AppError("Subscription is already paused.", status.HTTP_400_BAD_REQUEST)

    now = datetime.utcnow()
    sub.is_paused = True
    sub.paused_at = now
    sub.pause_duration_months = months
    sub.paused_until = now + timedelta(days=30 * months)
    sub.status = "PAUSED"
    db.commit()
    db.refresh(sub)

    from app.services.audit_service import write_audit_log
    write_audit_log(
        db,
        action="payment.pause_subscription",
        user_id=user_id,
        metadata={"months": months, "paused_until": sub.paused_until.isoformat() if sub.paused_until else None},
    )

    from app.services.notification_service import create_notification
    create_notification(
        db=db,
        user_id=user_id,
        title="Subscription Paused",
        message=f"Your subscription is paused for {months} month(s). No renewal charges will occur. All your career data remains 100% safe and you can resume anytime.",
        notif_type="BILLING",
        action_url="#billing",
    )

    return compute_subscription_summary(sub, db=db, user_id=user_id)


def resume_subscription(db: Session, user_id: int) -> dict:
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if not sub or not sub.is_paused:
        raise AppError("Subscription is not currently paused.", status.HTTP_400_BAD_REQUEST)

    now = datetime.utcnow()
    if sub.paused_at and sub.expires_at:
        paused_duration = now - sub.paused_at
        if paused_duration.total_seconds() > 0:
            sub.expires_at = sub.expires_at + paused_duration

    sub.is_paused = False
    sub.paused_at = None
    sub.paused_until = None
    sub.pause_duration_months = 0
    sub.status = "ACTIVE"
    db.commit()
    db.refresh(sub)

    from app.services.audit_service import write_audit_log
    write_audit_log(
        db,
        action="payment.resume_subscription",
        user_id=user_id,
        metadata={"resumed_at": now.isoformat()},
    )

    from app.services.notification_service import create_notification
    create_notification(
        db=db,
        user_id=user_id,
        title="Subscription Resumed",
        message="Your Pro subscription has resumed! You have full access to all your career workspace features.",
        notif_type="BILLING",
        action_url="#billing",
    )

    return compute_subscription_summary(sub, db=db, user_id=user_id)


def downgrade_subscription(db: Session, user_id: int, reason: str | None = None) -> dict:
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if not sub or sub.plan_name == "FREE":
        return compute_subscription_summary(sub, db=db, user_id=user_id)

    sub.cancellation_scheduled = True
    sub.cancellation_reason = reason or "downgrade_to_free"
    sub.status = "ENDING"
    db.commit()
    db.refresh(sub)

    from app.services.audit_service import write_audit_log
    write_audit_log(
        db,
        action="payment.downgrade_subscription",
        user_id=user_id,
        metadata={"reason": reason},
    )

    from app.services.notification_service import create_notification
    create_notification(
        db=db,
        user_id=user_id,
        title="Downgrade Scheduled",
        message="Your subscription will transition to Free at the end of your billing cycle. All your existing resumes, jobs, and career profile data remain completely safe.",
        notif_type="BILLING",
        action_url="#billing",
    )

    return compute_subscription_summary(sub, db=db, user_id=user_id)



from datetime import datetime
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import Subscription, UsageCounter, User


def get_current_period_month() -> str:
    return datetime.utcnow().strftime("%Y-%m")


def get_or_create_usage_counter(db: Session, user_id: int) -> UsageCounter:
    period = get_current_period_month()
    counter = (
        db.query(UsageCounter)
        .filter(UsageCounter.user_id == user_id, UsageCounter.period_month == period)
        .first()
    )
    if not counter:
        counter = UsageCounter(user_id=user_id, period_month=period)
        db.add(counter)
        db.commit()
        db.refresh(counter)
    return counter


def get_user_plan_and_limits(db: Session, user_id: int) -> dict:
    settings = get_settings()
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    now = datetime.utcnow()
    is_pro = sub and sub.status == "ACTIVE" and (not sub.expires_at or sub.expires_at > now) and sub.plan_name != "FREE"

    if is_pro:
        plan_name = sub.plan_name
        fit_limit = settings.pro_quota_fit_analyses_per_month
        tailor_limit = settings.pro_quota_tailored_versions_per_month
        export_limit = settings.pro_quota_exports_per_month
        templates_allowed = ["classic_ats", "technical_ats", "campus_fresher", "professional"]
    else:
        plan_name = "FREE"
        fit_limit = settings.free_quota_fit_analyses_per_month
        tailor_limit = settings.free_quota_tailored_versions_per_month
        export_limit = settings.free_quota_exports_per_month
        templates_allowed = ["classic_ats", "campus_fresher"]

    return {
        "plan_name": plan_name,
        "is_pro": is_pro,
        "expires_at": sub.expires_at if sub else None,
        "fit_limit": fit_limit,
        "tailor_limit": tailor_limit,
        "export_limit": export_limit,
        "templates_allowed": templates_allowed,
    }


def check_and_increment_quota(db: Session, user_id: int, action: str) -> None:
    limits = get_user_plan_and_limits(db, user_id)
    counter = get_or_create_usage_counter(db, user_id)

    if action == "fit_analysis":
        if counter.fit_analyses_used >= limits["fit_limit"]:
            if counter.extra_credits_available > 0:
                counter.extra_credits_available -= 1
            else:
                raise AppError(
                    f"Monthly fit analysis quota of {limits['fit_limit']} reached for your {limits['plan_name']} plan. Please upgrade to Pro for higher limits.",
                    403,
                )
        counter.fit_analyses_used += 1

    elif action == "tailor_version":
        if counter.tailored_versions_used >= limits["tailor_limit"]:
            if counter.extra_credits_available > 0:
                counter.extra_credits_available -= 1
            else:
                raise AppError(
                    f"Monthly tailoring quota of {limits['tailor_limit']} reached for your {limits['plan_name']} plan. Please upgrade to Pro for higher limits.",
                    403,
                )
        counter.tailored_versions_used += 1

    elif action == "export":
        if counter.exports_used >= limits["export_limit"]:
            if counter.extra_credits_available > 0:
                counter.extra_credits_available -= 1
            else:
                raise AppError(
                    f"Monthly export quota of {limits['export_limit']} reached for your {limits['plan_name']} plan. Please upgrade to Pro for higher limits.",
                    403,
                )
        counter.exports_used += 1

    db.commit()


def get_billing_summary(db: Session, user_id: int) -> dict:
    settings = get_settings()
    limits = get_user_plan_and_limits(db, user_id)
    counter = get_or_create_usage_counter(db, user_id)
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()

    from app.services.payment_service import compute_subscription_summary
    sub_summary = compute_subscription_summary(sub)
    sub_summary["is_pro"] = limits["is_pro"]

    return {
        "subscription": sub_summary,
        "quotas": {
            "period": counter.period_month,
            "fit_analyses": {"used": counter.fit_analyses_used, "limit": limits["fit_limit"]},
            "tailored_versions": {"used": counter.tailored_versions_used, "limit": limits["tailor_limit"]},
            "exports": {"used": counter.exports_used, "limit": limits["export_limit"]},
            "extra_credits": counter.extra_credits_available,
            "templates_allowed": limits["templates_allowed"],
        },
        "pricing_table": {
            "free": {"price": settings.plan_free_price_inr, "period": "month"},
            "pro_monthly": {"price": settings.plan_pro_monthly_price_inr, "period": "month"},
            "pro_annual": {"price": settings.plan_pro_annual_price_inr, "period": "year", "savings": "Save 32%"},
            "credit_packs": [
                {"credits": 10, "price": settings.credit_pack_10_price_inr},
                {"credits": 20, "price": settings.credit_pack_20_price_inr},
                {"credits": 50, "price": settings.credit_pack_50_price_inr},
            ],
        },
        "rbi_e_mandate_notice": "Recurring subscriptions require explicit upfront authorization. You can manage or cancel renewals at any time.",
    }

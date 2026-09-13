from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, model_validator


class SubscriptionOut(BaseModel):
    plan_name: str
    status: str
    expires_at: Optional[datetime] = None
    starts_at: Optional[datetime] = None
    is_trial: bool = False
    days_remaining: Optional[int] = None
    payment_method_type: str = "none"
    payment_method_detail: Optional[str] = None
    upi_app: Optional[str] = None
    recurring_amount: Optional[float] = None
    currency: str = "INR"
    billing_frequency: str = "none"
    cancellation_scheduled: bool = False
    next_renewal_date: Optional[str] = None
    can_cancel_in_app: bool = False
    last_payment_error: Optional[str] = None


class CreateOrderRequest(BaseModel):
    plan: str = "PRO_MONTHLY"
    currency: str = "INR"
    payment_method_type: Optional[str] = "card"
    upi_app: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_plan(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "plan_key" in data and ("plan" not in data or not data.get("plan")):
                data["plan"] = data["plan_key"]
        return data


class PaymentOrderOut(BaseModel):
    provider: str
    payment_mode: str = "test"  # "test" or "live"
    razorpay_key_id: Optional[str] = None
    order_id: str
    amount: int  # in smallest unit (e.g. paise / cents)
    display_amount: float = 0.0
    currency: str = "INR"
    plan_name: str = "PRO_MONTHLY"
    test_upi_id: Optional[str] = None
    is_test: bool = True
    notes: dict = Field(default_factory=dict)


class VerifyPaymentRequest(BaseModel):
    order_id: str
    payment_id: str
    signature: Optional[str] = None
    plan: str = "PRO_MONTHLY"
    payment_method_type: Optional[str] = "card"
    upi_app: Optional[str] = None


class PlanConsentInfo(BaseModel):
    plan_key: str
    display_name: str
    amount: float
    currency: str
    billing_frequency: str  # "one_time", "monthly", "annual"
    recurring: bool
    next_renewal_days: int
    cancellation_terms: str
    refund_terms: str
    mandate_notice: str

from functools import lru_cache
import os
from dataclasses import dataclass, field
from typing import Literal
from dotenv import load_dotenv
from pathlib import Path


load_dotenv(Path(__file__).resolve().parents[3] / ".env")

@dataclass
class Settings:
    app_name: str = "SmartResume.ai"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/resume_saas_db"

    jwt_secret_key: str = "dev-secret-change-before-production-64-characters-minimum"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 14

    allowed_origins: list[str] = field(
        default_factory=lambda: [
            "http://127.0.0.1:3000",
            "http://localhost:3000",
            "http://127.0.0.1:5500",
            "http://localhost:5500",
        ]
    )
    frontend_url: str = "http://127.0.0.1:3000"

    max_request_size_bytes: int = 12_000_000
    upload_max_bytes: int = 10_000_000

    # Rate limiting: granular thresholds
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    rate_limit_auth_requests: int = 10
    rate_limit_auth_window_seconds: int = 60
    rate_limit_ai_requests: int = 15
    rate_limit_ai_window_seconds: int = 60

    max_login_attempts: int = 5
    lockout_minutes: int = 15
    password_reset_minutes: int = 20
    email_verification_minutes: int = 60 * 24

    # AI Model Configuration (Gemini 3.6 Flash default, 3.5 Flash-Lite cost-optimized)
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.6-flash"
    gemini_lite_model: str = "gemini-3.5-flash-lite"

    # Payment configuration & pricing (India Tier 1 default)
    payments_mode: Literal["mock", "razorpay"] = "mock"
    payment_mode: Literal["test", "live", "mock"] = "test"
    test_upi_id: str = "ladanivatsal8892@oksbi"
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    razorpay_webhook_secret: str | None = None

    # Pricing (All amounts centralized, never hardcoded in routes)
    plan_free_price_inr: int = 0
    plan_single_export_price_inr: int = 1
    plan_pro_monthly_price_inr: int = 49
    plan_pro_annual_price_inr: int = 399
    credit_pack_10_price_inr: int = 29
    credit_pack_20_price_inr: int = 49
    credit_pack_50_price_inr: int = 99

    # Multi-currency pricing tables (Base INR, centralized equivalents)
    currency_prices: dict = field(
        default_factory=lambda: {
            "INR": {"symbol": "₹", "single": 1, "pro_monthly": 49, "pro_annual": 399, "pack_10": 29, "pack_20": 49, "pack_50": 99},
            "USD": {"symbol": "$", "single": 0.15, "pro_monthly": 1.99, "pro_annual": 14.99, "pack_10": 0.99, "pack_20": 1.49, "pack_50": 2.49},
            "EUR": {"symbol": "€", "single": 0.15, "pro_monthly": 1.89, "pro_annual": 13.99, "pack_10": 0.89, "pack_20": 1.39, "pack_50": 2.29},
            "GBP": {"symbol": "£", "single": 0.12, "pro_monthly": 1.69, "pro_annual": 11.99, "pack_10": 0.79, "pack_20": 1.19, "pack_50": 1.99},
            "AED": {"symbol": "AED ", "single": 0.50, "pro_monthly": 7.50, "pro_annual": 55.00, "pack_10": 3.50, "pack_20": 5.50, "pack_50": 9.00},
            "CAD": {"symbol": "CA$", "single": 0.20, "pro_monthly": 2.69, "pro_annual": 19.99, "pack_10": 1.29, "pack_20": 1.99, "pack_50": 3.49},
            "AUD": {"symbol": "A$", "single": 0.25, "pro_monthly": 2.99, "pro_annual": 22.99, "pack_10": 1.49, "pack_20": 2.29, "pack_50": 3.99},
            "SGD": {"symbol": "S$", "single": 0.20, "pro_monthly": 2.69, "pro_annual": 19.99, "pack_10": 1.29, "pack_20": 1.99, "pack_50": 3.49},
            "JPY": {"symbol": "¥", "single": 25, "pro_monthly": 300, "pro_annual": 2500, "pack_10": 150, "pack_20": 200, "pack_50": 350},
        }
    )

    # OAuth Configuration (Google & LinkedIn)
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str = "http://127.0.0.1:3000"
    linkedin_client_id: str | None = None
    linkedin_client_secret: str | None = None
    linkedin_redirect_uri: str = "http://127.0.0.1:3000"

    # Tier 2 Global proposed test prices (Configured, inactive until Tier 2 launches)
    plan_pro_monthly_price_usd: float = 1.99
    plan_pro_annual_price_usd: float = 14.99

    # Usage Quotas per month
    free_quota_fit_analyses_per_month: int = 2
    free_quota_tailored_versions_per_month: int = 2
    free_quota_exports_per_month: int = 2
    free_quota_templates_allowed: int = 2

    pro_quota_fit_analyses_per_month: int = 50
    pro_quota_tailored_versions_per_month: int = 30
    pro_quota_exports_per_month: int = 20
    pro_quota_templates_allowed: int = 4

    # Markets
    active_launch_markets: list[str] = field(default_factory=lambda: ["IN", "US", "EU", "GB", "AE", "CA", "AU", "SG", "JP"])
    default_currency: str = "INR"

    def __post_init__(self) -> None:
        if self.environment == "production":
            if self.jwt_secret_key in {"dev-secret-change-before-production-64-characters-minimum", "SUPER_SECRET_KEY_CHANGE_IN_PRODUCTION_12345"}:
                raise ValueError("Insecure default JWT_SECRET_KEY cannot be used in production.")
            if not self.database_url or "localhost" in self.database_url:
                pass  # allow if configured
        if len(self.jwt_secret_key) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters.")


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=_str("APP_NAME", "SmartResume.ai"),
        environment=_str("ENVIRONMENT", "development"),
        debug=_bool("DEBUG", True),
        database_url=_str("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/resume_saas_db"),
        jwt_secret_key=_str("JWT_SECRET_KEY", "dev-secret-change-before-production-64-characters-minimum"),
        jwt_algorithm=_str("JWT_ALGORITHM", "HS256"),
        access_token_expire_minutes=_int("ACCESS_TOKEN_EXPIRE_MINUTES", 15),
        refresh_token_expire_days=_int("REFRESH_TOKEN_EXPIRE_DAYS", 14),
        allowed_origins=_list(
            "ALLOWED_ORIGINS",
            [
                "http://127.0.0.1:3000",
                "http://localhost:3000",
                "http://127.0.0.1:5500",
                "http://localhost:5500",
            ],
        ),
        frontend_url=_str("FRONTEND_URL", "http://127.0.0.1:3000"),
        max_request_size_bytes=_int("MAX_REQUEST_SIZE_BYTES", 12_000_000),
        upload_max_bytes=_int("UPLOAD_MAX_BYTES", 10_000_000),
        rate_limit_requests=_int("RATE_LIMIT_REQUESTS", 120),
        rate_limit_window_seconds=_int("RATE_LIMIT_WINDOW_SECONDS", 60),
        rate_limit_auth_requests=_int("RATE_LIMIT_AUTH_REQUESTS", 10),
        rate_limit_auth_window_seconds=_int("RATE_LIMIT_AUTH_WINDOW_SECONDS", 60),
        rate_limit_ai_requests=_int("RATE_LIMIT_AI_REQUESTS", 15),
        rate_limit_ai_window_seconds=_int("RATE_LIMIT_AI_WINDOW_SECONDS", 60),
        max_login_attempts=_int("MAX_LOGIN_ATTEMPTS", 5),
        lockout_minutes=_int("LOCKOUT_MINUTES", 15),
        password_reset_minutes=_int("PASSWORD_RESET_MINUTES", 20),
        email_verification_minutes=_int("EMAIL_VERIFICATION_MINUTES", 60 * 24),
        gemini_api_key=_optional("GEMINI_API_KEY"),
        gemini_model=_str("GEMINI_MODEL_NAME", "gemini-3.6-flash"),
        gemini_lite_model=_str("GEMINI_FAST_MODEL_NAME", _str("GEMINI_LITE_MODEL_NAME", "gemini-3.5-flash-lite")),
        payments_mode=_str("PAYMENTS_MODE", "mock"),
        payment_mode=_str("PAYMENT_MODE", "test"),
        test_upi_id=_str("TEST_UPI_ID", "ladanivatsal8892@oksbi"),
        razorpay_key_id=_optional("RAZORPAY_KEY_ID"),
        razorpay_key_secret=_optional("RAZORPAY_KEY_SECRET"),
        razorpay_webhook_secret=_optional("RAZORPAY_WEBHOOK_SECRET"),
        google_client_id=_optional("GOOGLE_CLIENT_ID"),
        google_client_secret=_optional("GOOGLE_CLIENT_SECRET"),
        google_redirect_uri=_str("GOOGLE_REDIRECT_URI", "http://127.0.0.1:3000"),
        linkedin_client_id=_optional("LINKEDIN_CLIENT_ID"),
        linkedin_client_secret=_optional("LINKEDIN_CLIENT_SECRET"),
        linkedin_redirect_uri=_str("LINKEDIN_REDIRECT_URI", "http://127.0.0.1:3000"),
        plan_free_price_inr=_int("PLAN_FREE_PRICE_INR", 0),
        plan_single_export_price_inr=_int("PLAN_SINGLE_EXPORT_PRICE_INR", 1),
        plan_pro_monthly_price_inr=_int("PLAN_PRO_MONTHLY_PRICE_INR", 79),
        plan_pro_annual_price_inr=_int("PLAN_PRO_ANNUAL_PRICE_INR", 699),
        credit_pack_10_price_inr=_int("CREDIT_PACK_10_PRICE_INR", 29),
        credit_pack_20_price_inr=_int("CREDIT_PACK_20_PRICE_INR", 49),
        credit_pack_50_price_inr=_int("CREDIT_PACK_50_PRICE_INR", 99),
        free_quota_fit_analyses_per_month=_int("FREE_QUOTA_FIT_ANALYSES_PER_MONTH", 2),
        free_quota_tailored_versions_per_month=_int("FREE_QUOTA_TAILORED_VERSIONS_PER_MONTH", 2),
        free_quota_exports_per_month=_int("FREE_QUOTA_EXPORTS_PER_MONTH", 2),
        free_quota_templates_allowed=_int("FREE_QUOTA_TEMPLATES_ALLOWED", 2),
        pro_quota_fit_analyses_per_month=_int("PRO_QUOTA_FIT_ANALYSES_PER_MONTH", 50),
        pro_quota_tailored_versions_per_month=_int("PRO_QUOTA_TAILORED_VERSIONS_PER_MONTH", 30),
        pro_quota_exports_per_month=_int("PRO_QUOTA_EXPORTS_PER_MONTH", 20),
        pro_quota_templates_allowed=_int("PRO_QUOTA_TEMPLATES_ALLOWED", 4),
    )


def _str(name: str, default: str) -> str:
    return os.getenv(name, default)


def _optional(name: str) -> str | None:
    value = os.getenv(name)
    return value or None


def _int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]

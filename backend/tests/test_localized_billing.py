import pytest
from app.core.config import get_settings
from app.services.payment_service import get_plan_price, get_plan_consent_info
from app.routers.payments import get_pricing_tables


def test_nzd_pricing_configuration():
    settings = get_settings()
    assert "NZD" in settings.currency_prices
    nzd = settings.currency_prices["NZD"]
    assert nzd["symbol"] == "NZ$"
    assert nzd["pro_monthly"] == 3.29
    assert nzd["pro_annual"] == 24.99
    assert nzd["single"] == 0.25


def test_get_plan_price_multi_currency():
    # INR
    smallest_inr, disp_inr, curr_inr = get_plan_price("PRO_MONTHLY", currency="INR")
    assert curr_inr == "INR"
    assert disp_inr == 49.0
    assert smallest_inr == 4900

    # NZD
    smallest_nzd, disp_nzd, curr_nzd = get_plan_price("PRO_MONTHLY", currency="NZD")
    assert curr_nzd == "NZD"
    assert disp_nzd == 3.29
    assert smallest_nzd == 329

    # USD
    smallest_usd, disp_usd, curr_usd = get_plan_price("PRO_ANNUAL", currency="USD")
    assert curr_usd == "USD"
    assert disp_usd == 14.99
    assert smallest_usd == 1499


def test_get_plan_consent_info_localized_disclaimer():
    # 1. NZD Consent
    nzd_consent = get_plan_consent_info("PRO_MONTHLY", currency="NZD")
    assert nzd_consent["currency"] == "NZD"
    assert nzd_consent["amount"] == 3.29
    assert nzd_consent["currency_symbol"] == "NZ$"
    assert nzd_consent["inr_equivalent_amount"] == 49.0
    assert "Processed in INR via Razorpay at checkout: ₹49" in nzd_consent["checkout_disclaimer"]
    assert "NZ$3.29" in nzd_consent["checkout_disclaimer"]

    # 2. INR Consent
    inr_consent = get_plan_consent_info("PRO_MONTHLY", currency="INR")
    assert inr_consent["currency"] == "INR"
    assert inr_consent["amount"] == 49.0
    assert inr_consent["currency_symbol"] == "₹"
    assert "Processed in INR via Razorpay at checkout: ₹49" in inr_consent["checkout_disclaimer"]


def test_pricing_endpoint_transparent_entitlements():
    res = get_pricing_tables()
    data = res["data"]

    assert data["checkout_currency"] == "INR"
    assert "Processed in INR via Razorpay at checkout" in data["checkout_disclaimer"]
    assert "NZD" in data["currencies"]

    # Entitlements verification
    entitlements = data["plan_entitlements"]
    assert "FREE" in entitlements
    assert "PRO" in entitlements
    assert any("Active Resume Workspace" in e for e in entitlements["FREE"])
    assert any("Unlimited Independent Resumes" in e for e in entitlements["PRO"])
    assert any("Market Guidance" in e for e in entitlements["PRO"])
    assert any("Interview Simulator" in e for e in entitlements["PRO"])

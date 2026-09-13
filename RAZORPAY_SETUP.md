# Razorpay Payment Gateway & Billing Integration Guide — SmartResume.ai

This guide details the complete configuration for Razorpay payments, UPI AutoPay, Card recurring mandates, webhook processing, subscription lifecycle states, and RBI e-mandate compliance in SmartResume.ai.

---

## 1. Overview of Pricing & Products

SmartResume.ai provides transparent, user-first pricing with strict separation between recurring subscriptions, one-time credits, and risk-free trials:

| Plan / Product | Price | Duration | Recurring? | Credit Card Required? | Mandate Setup? | Features |
|---|---|---|---|---|---|---|
| **Free Plan** | **₹0** | Lifetime | No | No | No | 2 Job Fits/mo, 2 Tailored Resumes/mo, 2 Exports/mo, Classic ATS template |
| **7-Day Pro Trial** | **₹0** | 7 Days | No | No | No | 10 Job Fits, 5 Tailored Resumes, 3 Exports, all templates, STAR AI synthesizer, AI Mock Interviews |
| **One-Time Resume Export** | **₹1** | One-time | No | No | No | 1 High-res PDF/DOCX export credit, chosen template, **never recurs** |
| **Pro Monthly** | **₹49** / mo | Monthly | Yes | UPI AutoPay / Card | Yes (₹1 auth) | 50 Job Fits/mo, 30 Tailored Resumes/mo, 20 Exports/mo, all templates, SmartApply |
| **Pro Annual** | **₹399** / yr | Annual | Yes | UPI AutoPay / Card | Yes (₹1 auth) | 1,000 Job Fits/yr, 500 Tailored Resumes/yr, 500 Exports/yr (~32% savings) |
| **Booster Packs** | **₹29 / ₹49 / ₹99** | One-time | No | No | No | Extra non-expiring credits (10, 20, 50) without altering subscription plan |

> [!IMPORTANT]
> **Strict Separation Rule**: The ₹1 one-time resume export credit is a standalone purchase that **never** creates a recurring mandate or charges recurring fees. The ₹1 recurring mandate authorization is a regulatory setup verification disclosed explicitly in the recurring consent modal for ₹49/month or ₹399/year plans. They are never combined.

---

## 2. Standardized Subscription Status Model

SmartResume.ai normalizes subscription states across gateways and internal databases into 7 clean, human-readable lifecycle states:

```
                  ┌──────────────┐
                  │    TRIAL     │ ──(7 days pass without upgrade)──► EXPIRED
                  └──────┬───────┘
                         │ (User upgrades)
                         ▼
┌──────────────┐  (Upgrade)   ┌──────────────┐  (AutoPay / Card Charged)  ┌──────────────┐
│     FREE     │ ────────────►│    ACTIVE    │ ◄───────────────────────── │    ACTIVE    │
└──────────────┘              └──────┬───────┘                            └──────────────┘
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          │ (UPI / Card Cancel)      │ (Debit failed)           │ (Cycle ends without renewal)
          ▼                          ▼                          ▼
   ┌──────────────┐           ┌──────────────┐           ┌──────────────┐
   │    ENDING    │           │PAYMENT_FAILED│           │   EXPIRED    │
   │ (Access till │           │  / PAST_DUE  │           │ (Reverts to  │
   │  cycle end)  │           └──────┬───────┘           │    FREE)     │
   └──────┬───────┘                  │ (Retry/Recovery)  └──────────────┘
          │ (Cycle end date reached) ▼
          ▼                   ┌──────────────┐
   ┌──────────────┐           │    ACTIVE    │
   │  CANCELLED   │           └──────────────┘
   └──────────────┘
```

| Status | Meaning | Pro Access Active? | Renewal Active? |
|---|---|---|---|
| `TRIAL` | 7-Day Pro Trial active (₹0 upfront, no card needed) | **Yes** | No |
| `ACTIVE` | Paid Pro subscription in good standing | **Yes** | **Yes** |
| `ENDING` | Cancellation requested / mandate revoked; access retained until paid cycle ends | **Yes** | No |
| `CANCELLED` | Access expired after cancellation | No (Free tier) | No |
| `PAYMENT_FAILED` | Gateway reported payment failure / insufficient funds; retry available | **Yes (grace)** | Retrying |
| `PAST_DUE` | Renewal charge failed after retry grace period | No (Free tier) | Retrying |
| `EXPIRED` | Paid period ended without active renewal | No (Free tier) | No |

---

## 3. Payment-Method-Aware Subscription Management

Subscription management reflects the payment method used during mandate authorization:

### 3.1 UPI AutoPay Subscriptions
- **Mandate Authority**: Under NPCI & RBI rules, a UPI AutoPay mandate is legally authorized and maintained inside the user's UPI application (PhonePe, Google Pay, Paytm, BHIM).
- **In-App Experience**: Clicking `[Manage AutoPay]` opens the contextual UPI management guide with clear steps for:
  - **PhonePe**: Profile → Autopay / Mandates → SmartResume → Cancel
  - **Google Pay**: Profile → Autopay → SmartResume → Cancel
  - **Paytm**: Profile → Automatic Payments → SmartResume → Cancel
  - **Generic UPI**: Mandates / Recurring Payments → SmartResume → Cancel
- **Webhook Synchronization**: SmartResume never fakes immediate cancellation for UPI. When the user revokes the mandate in their UPI app, Razorpay emits a `mandate.revoked` or `subscription.cancelled` webhook. SmartResume receives the webhook, marks `cancellation_scheduled = True`, transitions status to `ENDING`, and preserves Pro access until `expires_at`.

### 3.2 Card Recurring Subscriptions
- **Mandate Authority**: Managed directly through the payment gateway tokenized card API.
- **In-App Experience**: Clicking `[Cancel Renewal]` calls `POST /api/v1/payments/cancel`.
- **Immediate Confirmation**: Renewal is turned off instantly, status updates to `ENDING` (or `CANCELLED`), and Pro features remain active until `expires_at`.

---

## 4. Razorpay Dashboard Configuration

### 4.1 Generating API Keys
1. Log in to the [Razorpay Dashboard](https://dashboard.razorpay.com/).
2. Navigate to **Settings** → **API Keys**.
3. Generate **Test Keys** (for sandbox verification) or **Live Keys** (for production).
4. Save `Key Id` and `Key Secret`.

### 4.2 Enabling Payment Methods
1. Go to **Settings** → **Payment Methods**.
2. Enable **UPI** (Google Pay, PhonePe, Paytm, BHIM) and **UPI AutoPay / Subscriptions**.
3. Set Primary Settlement UPI ID: `ladanivatsal8892@oksbi`.
4. Enable **Cards** (Visa, Mastercard, RuPay with recurring mandate support), NetBanking, and Wallets.

---

## 5. Webhook Setup & Security

Webhooks guarantee that subscription lifecycle transitions, renewals, mandate cancellations, and payment failures synchronize reliably even if the client disconnects.

### 5.1 Endpoint Details
- **Production URL**: `https://<your-domain>/api/v1/payments/webhooks/razorpay`
- **Local Dev / Sandbox URL**: `https://<tunnel-id>.ngrok-free.app/api/v1/payments/webhooks/razorpay`
- **Secret**: Configure a secure random token in both Razorpay Dashboard and `RAZORPAY_WEBHOOK_SECRET`.

### 5.2 Subscribed Events
Select the following events in the Razorpay Webhook configuration:
- `payment.captured` — One-time purchases, export credits, and booster packs
- `payment.failed` — Payment debit failures (triggers `PAYMENT_FAILED` state with customer alert)
- `subscription.activated` — Initial subscription activation upon authorization
- `subscription.charged` — Successful recurring monthly/annual renewal
- `subscription.cancelled` — Cancellation of recurring mandate
- `mandate.revoked` — UPI AutoPay or e-mandate revocation by customer inside UPI app or bank portal

### 5.3 Cryptographic Verification
Every incoming webhook is cryptographically verified using HMAC SHA-256 against `X-Razorpay-Signature`. Requests with missing or invalid signatures are rejected with `400 Bad Request`. Replayed or duplicate webhooks are acknowledged idempotently with `duplicate_acknowledged` without double-crediting.

---

## 6. Backend Environment Configuration

Add the following to `backend/.env`:

```env
# Payment Gateway Configuration
PAYMENTS_MODE=razorpay
PAYMENT_MODE=live
RAZORPAY_KEY_ID=rzp_live_your_key_id_here
RAZORPAY_KEY_SECRET=your_razorpay_secret_key_here
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret_here
TEST_UPI_ID=ladanivatsal8892@oksbi

# Indian Tier 1 Base Pricing (INR)
PLAN_FREE_PRICE_INR=0
PLAN_SINGLE_EXPORT_PRICE_INR=1
PLAN_PRO_MONTHLY_PRICE_INR=49
PLAN_PRO_ANNUAL_PRICE_INR=399
CREDIT_PACK_10_PRICE_INR=29
CREDIT_PACK_20_PRICE_INR=49
CREDIT_PACK_50_PRICE_INR=99

# Global Pricing Equivalents (Multi-Currency)
PLAN_PRO_MONTHLY_PRICE_USD=1.99
PLAN_PRO_ANNUAL_PRICE_USD=14.99
```

---

## 7. RBI E-Mandate Compliance Checklist

1. **Explicit Pre-Consent Modal**: Before opening checkout for recurring plans, the customer must review and explicitly accept recurring terms in the Subscription Authorization & Consent modal.
2. **AFA (Additional Factor of Authentication)**: Initial mandate registration executes two-factor authentication (OTP/PIN).
3. **Pre-Debit Notifications**: Razorpay automatically dispatches pre-debit SMS/email notifications 24 hours prior to recurring debit.
4. **Transparent Cancellation**: Clear guidance on how to pause, modify, or revoke mandates directly within UPI apps or through the subscription dashboard.
5. **No Negative-Option Billing**: The 7-Day Pro Trial (₹0) requires no credit card, no mandate, and expires safely into the Free plan without automatic charges.

---

## 8. Verification & QA Matrix

Run the automated test suite covering all 20 lifecycle cases:

```bash
cd backend
pytest tests/test_subscription_lifecycle_and_ux.py -v
```

All 20 test cases pass:
- [x] Free tier default status (`ACTIVE`, `none`, ₹0)
- [x] 7-Day Pro Trial activation (`TRIAL`, 7-day expiry, 3 credits)
- [x] 7-Day Pro Trial single-claim enforcement
- [x] ₹1 One-Time export purchase isolation (does not start subscription)
- [x] UPI AutoPay mandate authorization (`method=upi`, ₹49/mo)
- [x] UPI AutoPay cancellation returns app instructions (does not fake cancellation)
- [x] UPI mandate revocation webhook sets `cancellation_scheduled=True`, status `ENDING`
- [x] Card recurring activation (`method=card`, Card ending ****4242)
- [x] Card renewal cancellation in app (`cancellation_scheduled=True`)
- [x] Subscription expiration transition when `expires_at` is past (`EXPIRED`)
- [x] Webhook `payment.failed` records error and sets `PAYMENT_FAILED`
- [x] Endpoint `POST /payments/retry-failed` restores `ACTIVE` status
- [x] Multi-currency pricing endpoint (`INR`, `USD`, `EUR`, `GBP`, etc.)
- [x] Mandate consent disclosures for `PRO_MONTHLY`
- [x] Non-recurring consent disclosures for `SINGLE_EXPORT`
- [x] Quota counters and extra credit preservation
- [x] Pro Annual upgrade (₹399/yr, 365 days)
- [x] Emergency booster pack (+10 credits, Free tier preserved)
- [x] Webhook idempotency (duplicate deliveries acknowledged)
- [x] Webhook `mandate.revoked` transitions to `ENDING` state

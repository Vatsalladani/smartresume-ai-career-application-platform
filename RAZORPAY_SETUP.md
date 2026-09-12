# Razorpay Payment Gateway & Billing Integration Guide — SmartResume.ai

This guide details the complete configuration for Razorpay payments, UPI settlements, webhook handling, and RBI compliance in SmartResume.ai.

---

## 1. Overview of Pricing & Products

SmartResume.ai offers clear, user-first pricing without deceptive traps:

| Plan / Product | Price | Duration | Recurring? | Credit Card Required? | Features |
|---|---|---|---|---|---|
| **7-Day Pro Trial** | **₹0** | 7 Days | No | No | Complete Pro access, Evidence Vault, STAR Synthesizer, 3 tailored resumes, 2 AI Mock Interviews |
| **First Export Offer** | **₹1** | One-time | No | No | 1 Premium Export Credit (PDF/DOCX), full ATS validation |
| **Pro Monthly** | **₹49** / mo | Monthly | Yes | Card / UPI AutoPay | Unlimited ATS tailored resumes, unlimited mock interviews, full Application Pack generator |
| **Pro Annual** | **₹399** / yr | Annual | Yes | Card / UPI AutoPay | Full Pro access with ~32% annual discount |

---

## 2. Razorpay Dashboard Configuration

### 2.1 Generating API Keys
1. Log in to the [Razorpay Dashboard](https://dashboard.razorpay.com/).
2. In the left sidebar, navigate to **Settings** → **API Keys**.
3. Click **Generate Test Key** (or **Generate Live Key** for production).
4. Note down your `Key Id` and `Key Secret`.

### 2.2 Configuring UPI & Settlement
1. Go to **Settings** → **Payment Methods**.
2. Enable **UPI** (Google Pay, PhonePe, Paytm, BHIM).
3. Under settlements and bank accounts, ensure the merchant settlement account or UPI ID is verified:
   - Primary UPI VPA: `ladanivatsal8892@oksbi`
4. Enable Cards (Visa, Mastercard, RuPay), NetBanking, and Wallets.

---

## 3. Webhook Setup

Razorpay webhooks guarantee that user subscriptions and export credits update reliably even if the user closes their browser before redirection.

### 3.1 Webhook URL Configuration
1. In Razorpay Dashboard, go to **Settings** → **Webhooks**.
2. Click **+ Add New Webhook**.
3. **Webhook URL**:
   - Production: `https://your-domain.com/api/v1/payments/webhook`
   - Local testing: Use ngrok/localtunnel: `https://<subdomain>.ngrok-free.app/api/v1/payments/webhook`
4. **Secret**: Enter a secure random string (e.g. `rzp_whsec_9948274aef1284`).
5. **Active Events**: Select the following events:
   - `order.paid`
   - `payment.captured`
   - `payment.failed`
   - `subscription.charged`
   - `subscription.cancelled`
6. Click **Save**.

---

## 4. Backend Environment Configuration

Add the credentials into `backend/.env`:

```env
# Razorpay Configuration
RAZORPAY_KEY_ID=rzp_test_51X9abc...
RAZORPAY_KEY_SECRET=xYz123SecretKeyHere...
RAZORPAY_WEBHOOK_SECRET=rzp_whsec_9948274aef1284
UPI_VPA=ladanivatsal8892@oksbi

# Plan Amounts (in INR)
PRO_MONTHLY_PRICE=49
PRO_ANNUAL_PRICE=399
FIRST_EXPORT_PRICE=1
```

---

## 5. RBI Compliance & E-Mandate Architecture

For recurring Indian payments, the Reserve Bank of India (RBI) mandates strict consumer protections:
1. **Additional Factor of Authentication (AFA)**:
   - The initial recurring registration requires an OTP / 3D-Secure transaction.
2. **Pre-Debit Notifications**:
   - For recurring debits above ₹15,000, e-mandates require pre-transaction notification SMS/email 24 hours prior. SmartResume.ai plans are well under this threshold (₹49/mo, ₹399/yr), but Razorpay handles the mandatory notification automatically.
3. **No Automatic Surprises**:
   - The 7-Day Pro Trial (₹0) does **NOT** collect credit card details upfront and will **never** automatically charge the user upon expiration. When the trial ends, the account safely reverts to the FREE tier with full read access to past resumes.
4. **Immediate Cancellation**:
   - Users can cancel recurring subscriptions anytime directly from the **Billing** tab or Razorpay mandate portal with a single click.

---

## 6. Testing & Verification

### 6.1 Testing ₹1 One-Time Purchase
1. Open the application at `http://localhost:8000`.
2. Navigate to **Billing & Plan**.
3. Click **Buy 1 Export Credit for ₹1**.
4. In test mode, Razorpay modal opens. Select **UPI** or **Test Cards**:
   - Success Card: `4111 1111 1111 1111`, any future expiry, OTP `123456`.
5. Verify that your balance increases by `+1` export credit and the transaction log reflects status `COMPLETED`.

### 6.2 Testing 7-Day Pro Trial Activation
1. Create a fresh account on `http://localhost:8000`.
2. Go to **Billing & Plan**.
3. Click **Start 7-Day Pro Trial (₹0)**.
4. Verify the trial is activated instantly without asking for card details.
5. Attempt to claim it a second time — verify the system displays "Trial has already been claimed for this account".

# SmartResume.ai — Dedicated Admin Console

This directory contains the standalone, independent **Admin Console Application** for SmartResume.ai.

## Architecture & Security Separation

1. **Isolation from Public User App**:
   - The public website (`frontend/`) contains **zero** administrative routes, navigation buttons, or admin JavaScript bundles.
   - The Admin Portal is a completely separate Single-Page Application (SPA) located exclusively in `admin-panel/`.
2. **Backend Authentication & Server-Side RBAC**:
   - Connects to the backend REST API (`/api/v1/admin/*`).
   - Every API request is checked by the server (`require_admin`).
   - Unauthenticated requests return `401 Unauthorized`.
   - Standard user accounts (`role="USER"`) return `403 Forbidden` and are barred from accessing the console.
   - Zero frontend tokens or client flags can bypass backend authorization.

---

## Launching the Admin Console Locally

Run the standalone development server on port **4174**:

```powershell
python admin-panel/server.py
```

### Local Admin URL:
👉 **`http://127.0.0.1:4174`** or **`http://localhost:4174`**

---

## API Endpoints Used

| Endpoint | Method | Purpose |
| :--- | :--- | :--- |
| `/api/v1/auth/login` | `POST` | Authenticate admin credentials and retrieve JWT |
| `/api/v1/admin/overview` | `GET` | Platform health KPIs, user/resume counts, and AI ops summary |
| `/api/v1/admin/users` | `GET` | Paginated registered user directory with role indicators |
| `/api/v1/admin/users/{id}/role` | `POST` | Safely elevate or demote user roles with audit trail |
| `/api/v1/admin/ai-ops` | `GET` | AI latency distribution ($p50/p90/p99$), model telemetry & breakdown |
| `/api/v1/admin/feature-flags` | `GET` | Retrieve active system feature flags |
| `/api/v1/admin/feature-flags` | `PUT` | Toggle system feature flags with audit logging |
| `/api/v1/admin/audit-logs` | `GET` | Retrieve immutable security and administrative audit event trail |

---

## Secure Administrator Provisioning

To securely designate an administrator account without exposing database credentials or creating public signup forms:

### Method 1: Server-Side Database Provisioning (Initial Admin)
```sql
UPDATE users SET role = 'ADMIN' WHERE email = 'your-admin-email@example.com';
```

### Method 2: Existing Administrator Promotion
An authenticated administrator can promote another user in the **User Directory** tab of the Admin Console (`http://localhost:4174/#/users`) by clicking **"Make Admin"**.

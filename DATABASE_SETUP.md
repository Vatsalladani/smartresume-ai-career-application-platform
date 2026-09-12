# PostgreSQL Database Setup Guide — SmartResume.ai

This document provides complete instructions for setting up, configuring, migrating, and maintaining the PostgreSQL database for SmartResume.ai.

---

## 1. Prerequisites
- **PostgreSQL 14+** (PostgreSQL 16 recommended)
- **Python 3.11+**
- Active virtual environment with dependencies installed (`pip install -r requirements.txt`)

---

## 2. Database Creation & User Provisioning

Open your PostgreSQL interactive terminal (`psql`) as superuser:

```bash
psql -U postgres
```

Execute the database provisioning commands:

```sql
-- Create database user
CREATE USER resume_user WITH PASSWORD 'your_secure_password';

-- Create database
CREATE DATABASE resume_saas_db OWNER resume_user;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE resume_saas_db TO resume_user;

-- Connect to the database
\c resume_saas_db

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO resume_user;
```

---

## 3. Environment Configuration

In `backend/.env`, configure the connection string:

```env
DATABASE_URL=postgresql://resume_user:your_secure_password@localhost:5432/resume_saas_db
```

For SSL connections in production (e.g. Supabase, AWS RDS, Neon):

```env
DATABASE_URL=postgresql://resume_user:your_secure_password@db.provider.com:5432/resume_saas_db?sslmode=require
```

---

## 4. Running Database Migrations

SmartResume.ai uses **Alembic** for schema migrations.

### Check Current Migration Status
```bash
cd backend
alembic current
```

### Apply All Migrations (Up to Head)
```bash
cd backend
alembic upgrade head
```

### Complete Migration History:
1. `0001_initial_schema.py`: Base tables (`users`, `profiles`, `resumes`, `job_applications`, `subscriptions`, etc.)
2. `0002_production_hardening.py`: Granular security tokens, password validators, audit logs
3. `0003_application_links.py`: Direct foreign key relationships between job postings, resumes, and versions
4. `0004_product_intelligence_v2.py`: Career levels, target domains, consistency graph, and readiness reports
5. `0005_career_and_application_os.py`: Career Evidence Vault (`evidence_items`), AI Interview Copilot (`interview_sessions`, `interview_messages`, `interview_evaluations`), In-App Notifications (`notifications`), Application Pack JSON, and 7-Day Pro Trial attributes.

---

## 5. Verifying Database Health

You can verify database connectivity and table creation using Python:

```bash
python -c "from app.database import engine; from sqlalchemy import inspect; insp = inspect(engine); print('Tables:', sorted(insp.get_table_names()))"
```

Expected tables:
- `application_versions`
- `ats_analyses`
- `ats_checks`
- `audit_logs`
- `certifications`
- `education`
- `evidence_items`
- `evidence_links`
- `experiences`
- `interview_evaluations`
- `interview_messages`
- `interview_sessions`
- `job_applications`
- `job_postings`
- `job_requirements`
- `notifications`
- `payment_events`
- `profiles`
- `projects`
- `refresh_tokens`
- `resumes`
- `skills`
- `subscriptions`
- `token_blacklist`
- `usage_counters`
- `users`

---

## 6. Backups and Recovery

### Taking a Database Dump
```bash
pg_dump -U resume_user -h localhost -d resume_saas_db -F c -b -v -f resume_saas_backup.dump
```

### Restoring a Dump
```bash
pg_restore -U resume_user -h localhost -d resume_saas_db -v resume_saas_backup.dump
```

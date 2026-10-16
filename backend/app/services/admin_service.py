"""Admin Management and AI Telemetry Service for SmartResume.ai.

Provides administrative insights, user RBAC management, AI ops metrics,
feature flag controls, resume and template management, subscription control,
and security audit logs with strict access control and real PostgreSQL persistence.
"""

from __future__ import annotations

import datetime
import math
from typing import Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.core.errors import AppError
from app.models import (
    AdminAccount,
    AIOperationLog,
    AuditLog,
    InterviewEvaluation,
    InterviewSession,
    JobApplication,
    JobPosting,
    Resume,
    ResumeVersion,
    Subscription,
    User,
)
from app.services import platform_config_service
from app.services.audit_service import write_audit_log


def get_actor_email(admin_actor: Any) -> str:
    """Extracts email string safely from either AdminAccount, User, or str."""
    if hasattr(admin_actor, "email"):
        return getattr(admin_actor, "email")
    return str(admin_actor) if admin_actor else "admin"


def log_admin_action(*args: Any, **kwargs: Any) -> None:
    """Persists an administrative action entry directly to the PostgreSQL audit_logs table.
    Accepts both (actor_email, action, details) and (db, actor_email, action, details) signatures.
    """
    from app.database import get_session
    db: Optional[Session] = None
    actor_email: str = "system"
    action: str = "ACTION"
    details: str = ""
    severity: str = "INFO"
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None

    if args:
        if isinstance(args[0], Session):
            db = args[0]
            if len(args) > 1: actor_email = str(args[1])
            if len(args) > 2: action = str(args[2])
            if len(args) > 3: details = str(args[3])
            if len(args) > 4: severity = str(args[4])
        else:
            actor_email = str(args[0])
            if len(args) > 1: action = str(args[1])
            if len(args) > 2: details = str(args[2])
            if len(args) > 3: severity = str(args[3])

    if "db" in kwargs and kwargs["db"] is not None: db = kwargs["db"]
    if "actor_email" in kwargs: actor_email = str(kwargs["actor_email"])
    if "action" in kwargs: action = str(kwargs["action"])
    if "details" in kwargs: details = str(kwargs["details"])
    if "severity" in kwargs: severity = str(kwargs["severity"])
    if "entity_type" in kwargs: entity_type = kwargs["entity_type"]
    if "entity_id" in kwargs: entity_id = kwargs["entity_id"]

    def _write(s: Session):
        write_audit_log(
            s,
            action=action,
            entity_type=entity_type or "admin_action",
            entity_id=entity_id,
            metadata={
                "actor": actor_email,
                "details": details,
                "severity": severity,
                "timestamp": datetime.datetime.utcnow().isoformat(),
            },
        )
        s.commit()

    if db is not None:
        _write(db)
    else:
        with get_session() as s:
            _write(s)



def get_admin_overview(db: Session) -> dict[str, Any]:
    """Compiles high-level platform health, user engagement, subscription breakdown, and real AI telemetry."""
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0
    total_resumes = db.query(func.count(Resume.id)).filter(Resume.is_archived.is_(False)).scalar() or 0
    total_versions = db.query(func.count(ResumeVersion.id)).scalar() or 0
    total_jobs = db.query(func.count(JobPosting.id)).scalar() or 0
    total_applications = db.query(func.count(JobApplication.id)).scalar() or 0
    active_applications = db.query(func.count(JobApplication.id)).filter(
        JobApplication.is_archived.is_(False),
        ~JobApplication.status.in_(["REJECTED", "WITHDRAWN"]),
    ).scalar() or 0
    offers_extended = db.query(func.count(JobApplication.id)).filter(
        JobApplication.status == "OFFER"
    ).scalar() or 0
    total_interviews = db.query(func.count(InterviewSession.id)).scalar() or 0
    completed_interviews = db.query(func.count(InterviewSession.id)).filter(InterviewSession.status == "COMPLETED").scalar() or 0

    # Subscription breakdown
    free_subs = db.query(func.count(Subscription.id)).filter(Subscription.plan_name == "FREE").scalar() or 0
    pro_subs = db.query(func.count(Subscription.id)).filter(Subscription.plan_name == "PRO").scalar() or 0
    exec_subs = db.query(func.count(Subscription.id)).filter(Subscription.plan_name == "EXECUTIVE").scalar() or 0

    # Real AI operational summary from ai_operation_logs in last 24h
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    total_ai_requests = db.query(func.count(AIOperationLog.id)).filter(AIOperationLog.created_at >= cutoff).scalar() or 0
    fallback_ai_requests = db.query(func.count(AIOperationLog.id)).filter(
        AIOperationLog.created_at >= cutoff, AIOperationLog.is_fallback.is_(True)
    ).scalar() or 0
    avg_latency = db.query(func.avg(AIOperationLog.latency_ms)).filter(AIOperationLog.created_at >= cutoff).scalar() or 0

    fallback_rate = round((fallback_ai_requests / total_ai_requests * 100), 2) if total_ai_requests > 0 else 0.0

    # Active system feature flags
    all_settings = platform_config_service.get_all_settings(db)
    flags = {k: v["value"] for k, v in all_settings.items() if v.get("type") == "boolean"}

    return {
        "platform_status": "HEALTHY",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "user_metrics": {
            "total_users": total_users,
            "active_users": active_users,
        },
        "document_metrics": {
            "total_resumes": total_resumes,
            "total_versions": total_versions,
            "total_jobs_tracked": total_applications or total_jobs,
            "total_applications": total_applications,
        },
        "application_metrics": {
            "total_applications": total_applications,
            "active_applications": active_applications,
            "offers_extended": offers_extended,
        },
        "interview_metrics": {
            "total_sessions": total_interviews,
            "completed_sessions": completed_interviews,
        },
        "subscription_metrics": {
            "free_count": free_subs,
            "pro_count": pro_subs,
            "executive_count": exec_subs,
            "total_active": free_subs + pro_subs + exec_subs,
        },
        "ai_ops_summary": {
            "active_provider": platform_config_service.get_setting("gemini_primary_model", "gemini-2.5-flash", db=db),
            "force_fallback_enabled": platform_config_service.get_setting("gemini_force_deterministic_fallback", False, db=db),
            "total_requests_24h": total_ai_requests,
            "fallback_rate_pct": fallback_rate,
            "avg_latency_ms": int(avg_latency),
            "healthy": True,
        },
        "feature_flags": flags,
    }


def list_admin_users(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    search: str = "",
) -> dict[str, Any]:
    """Retrieves paginated user directory with role indicators, plan name, and resume counts."""
    query = db.query(User)
    if search:
        s = f"%{search.strip().lower()}%"
        query = query.filter(User.email.ilike(s) | User.full_name.ilike(s))

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    user_list = []
    for u in users:
        r_count = db.query(func.count(Resume.id)).filter(Resume.user_id == u.id, Resume.is_archived.is_(False)).scalar() or 0
        plan = u.subscription.plan_name if u.subscription else "FREE"
        user_list.append({
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "plan_name": plan,
            "is_active": u.is_active,
            "is_verified": u.is_verified,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "resume_count": r_count,
        })

    return {
        "users": user_list,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


def update_user_role(
    db: Session,
    user_id: int | None = None,
    target_user_id: int | None = None,
    new_role: str = "USER",
    admin_actor: Any = None,
) -> dict[str, Any]:
    """Updates a user's role (ADMIN or USER) with security audit logging."""
    target_id = user_id or target_user_id
    if not target_id:
        raise AppError("Target user ID is required.", 400)
    target_user = db.get(User, target_id)
    if not target_user:
        raise AppError("User not found.", 404)

    role_clean = new_role.strip().upper()
    if role_clean not in ("ADMIN", "USER"):
        raise AppError("Invalid role. Must be 'ADMIN' or 'USER'.", 400)

    old_role = target_user.role
    target_user.role = role_clean
    db.commit()
    db.refresh(target_user)

    actor_email = get_actor_email(admin_actor)
    log_admin_action(
        db,
        actor_email=actor_email,
        action="USER_ROLE_CHANGED",
        details=f"User #{target_user.id} ({target_user.email}) role changed from {old_role} to {role_clean}.",
        severity="WARNING" if role_clean == "ADMIN" else "INFO",
        entity_type="user",
        entity_id=str(target_user.id),
    )

    return {
        "id": target_user.id,
        "email": target_user.email,
        "role": target_user.role,
        "message": f"User role updated to {role_clean}.",
    }


def update_user_status(
    db: Session,
    user_id: int,
    is_active: Optional[bool] = None,
    is_verified: Optional[bool] = None,
    admin_actor: Any = None,
) -> dict[str, Any]:
    """Updates a user's operational status (active/suspended, email verified)."""
    user = db.get(User, user_id)
    if not user:
        raise AppError("User not found.", 404)

    changes = []
    if is_active is not None and user.is_active != is_active:
        user.is_active = is_active
        changes.append(f"is_active={is_active}")
    if is_verified is not None and user.is_verified != is_verified:
        user.is_verified = is_verified
        changes.append(f"is_verified={is_verified}")

    if changes:
        db.commit()
        db.refresh(user)
        actor_email = get_actor_email(admin_actor)
        log_admin_action(
            db,
            actor_email=actor_email,
            action="USER_STATUS_UPDATED",
            details=f"User #{user.id} ({user.email}) status modified: {', '.join(changes)}",
            severity="WARNING" if is_active is False else "INFO",
            entity_type="user",
            entity_id=str(user.id),
        )

    return {
        "id": user.id,
        "email": user.email,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "message": f"User status updated successfully ({', '.join(changes) if changes else 'no change'}).",
    }


def update_user_plan(
    db: Session,
    user_id: int,
    new_plan: str,
    admin_actor: Any = None,
) -> dict[str, Any]:
    """Updates a user's subscription plan directly from admin."""
    user = db.get(User, user_id)
    if not user:
        raise AppError("User not found.", 404)

    clean_plan = new_plan.strip().upper()
    if clean_plan not in ("FREE", "PRO", "EXECUTIVE"):
        raise AppError("Invalid plan name. Must be FREE, PRO, or EXECUTIVE.", 400)

    sub = user.subscription
    if not sub:
        sub = Subscription(
            user_id=user.id,
            plan_name=clean_plan,
            status="ACTIVE",
            starts_at=datetime.datetime.utcnow(),
        )
        db.add(sub)
    else:
        old_plan = sub.plan_name
        sub.plan_name = clean_plan
        sub.status = "ACTIVE"
        sub.updated_at = datetime.datetime.utcnow()

    db.commit()
    db.refresh(user)

    actor_email = get_actor_email(admin_actor)
    log_admin_action(
        db,
        actor_email=actor_email,
        action="USER_PLAN_UPDATED",
        details=f"User #{user.id} ({user.email}) subscription plan set to {clean_plan}.",
        severity="INFO",
        entity_type="user",
        entity_id=str(user.id),
    )

    return {
        "id": user.id,
        "email": user.email,
        "plan_name": clean_plan,
        "message": f"User plan successfully changed to {clean_plan}.",
    }


def list_admin_resumes(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    search: str = "",
) -> dict[str, Any]:
    """Retrieves paginated resumes across all users."""
    query = db.query(Resume).join(User, Resume.user_id == User.id)
    if search:
        s = f"%{search.strip().lower()}%"
        query = query.filter(Resume.title.ilike(s) | Resume.target_role.ilike(s) | User.email.ilike(s))

    total = query.count()
    resumes = query.order_by(Resume.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for r in resumes:
        v_count = db.query(func.count(ResumeVersion.id)).filter(ResumeVersion.resume_id == r.id).scalar() or 0
        items.append({
            "id": r.id,
            "user_id": r.user_id,
            "user_email": r.user.email if r.user else "unknown",
            "title": r.title,
            "status": r.status,
            "target_role": r.target_role or "Unspecified",
            "ats_score": r.ats_score,
            "completeness_score": r.completeness_score,
            "version_count": v_count,
            "is_archived": r.is_archived,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        })

    return {
        "resumes": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


def get_admin_resume_detail(db: Session, resume_id: int) -> dict[str, Any]:
    """Retrieves full details and versions of a specific resume for administrative inspection."""
    resume = db.get(Resume, resume_id)
    if not resume:
        raise AppError("Resume not found.", 404)

    versions = [
        {
            "id": v.id,
            "version_number": v.version_number,
            "changelog": v.changelog,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in resume.versions
    ]

    return {
        "id": resume.id,
        "user_id": resume.user_id,
        "user_email": resume.user.email if resume.user else None,
        "title": resume.title,
        "status": resume.status,
        "target_role": resume.target_role,
        "target_company": resume.target_company,
        "ats_score": resume.ats_score,
        "completeness_score": resume.completeness_score,
        "parsed_content": resume.parsed_content,
        "is_archived": resume.is_archived,
        "created_at": resume.created_at.isoformat() if resume.created_at else None,
        "updated_at": resume.updated_at.isoformat() if resume.updated_at else None,
        "versions": versions,
    }


def get_templates_status(db: Session) -> dict[str, Any]:
    """Retrieves template catalog and enabled status."""
    catalog = platform_config_service.get_setting("template_catalog", {}, db=db)
    return {
        "templates": [
            {"id": "classic_ats", "name": "Classic ATS", "description": "Single-column high-parse rate standard layout", "enabled": catalog.get("classic_ats", True)},
            {"id": "modern_clean", "name": "Modern Clean", "description": "Crisp borders, subtle headers, structured sections", "enabled": catalog.get("modern_clean", True)},
            {"id": "executive_brief", "name": "Executive Brief", "description": "Dense layout for senior leaders with executive summary", "enabled": catalog.get("executive_brief", True)},
            {"id": "tech_minimal", "name": "Tech Minimal", "description": "Compact monospaced layout with skills taxonomy", "enabled": catalog.get("tech_minimal", True)},
        ]
    }


def update_template_status(
    db: Session,
    template_id: str,
    enabled: bool,
    admin_actor: Any = None,
) -> dict[str, Any]:
    """Enables or disables a resume template globally."""
    catalog = dict(platform_config_service.get_setting("template_catalog", {}, db=db))
    catalog[template_id] = bool(enabled)
    platform_config_service.set_setting(
        db,
        key="template_catalog",
        value=catalog,
        actor_email=get_actor_email(admin_actor),
    )
    return {"template_id": template_id, "enabled": enabled, "message": f"Template {template_id} enabled status set to {enabled}."}


def get_ai_ops_telemetry(db: Session) -> dict[str, Any]:
    """Returns real AI operational telemetry calculated directly from PostgreSQL ai_operation_logs."""
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    logs = db.query(AIOperationLog).filter(AIOperationLog.created_at >= cutoff).all()

    total_requests = len(logs)
    fallback_requests = sum(1 for log in logs if log.is_fallback)
    successful_gemini = total_requests - fallback_requests

    fallback_rate = round((fallback_requests / total_requests * 100), 2) if total_requests > 0 else 0.0

    # Percentiles
    latencies = sorted([log.latency_ms for log in logs if log.latency_ms > 0])
    if latencies:
        p50 = latencies[int(len(latencies) * 0.50)]
        p90 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.90))]
        p99 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.99))]
    else:
        p50, p90, p99 = 0, 0, 0

    # Breakdown by feature
    features = {}
    for log in logs:
        fname = log.feature_name or "general"
        if fname not in features:
            features[fname] = {"calls": 0, "fallback_calls": 0}
        features[fname]["calls"] += 1
        if log.is_fallback:
            features[fname]["fallback_calls"] += 1

    feature_breakdown = {}
    for fname, data in features.items():
        fb_pct = round((data["fallback_calls"] / data["calls"] * 100), 1) if data["calls"] > 0 else 0.0
        feature_breakdown[fname] = {
            "calls": data["calls"],
            "fallback_rate": f"{fb_pct}%",
        }

    return {
        "status": "OPERATIONAL",
        "primary_model": platform_config_service.get_setting("gemini_primary_model", "gemini-2.5-flash", db=db),
        "force_fallback_enabled": platform_config_service.get_setting("gemini_force_deterministic_fallback", False, db=db),
        "total_requests_24h": total_requests,
        "successful_gemini_calls": successful_gemini,
        "fallback_calls": fallback_requests,
        "fallback_rate_pct": fallback_rate,
        "latency_percentiles_ms": {
            "p50": p50,
            "p90": p90,
            "p99": p99,
        },
        "breakdown_by_feature": feature_breakdown,
    }


def get_ai_config(db: Session) -> dict[str, Any]:
    """Retrieves AI model controls and configuration."""
    return {
        "gemini_primary_model": platform_config_service.get_setting("gemini_primary_model", "gemini-2.5-flash", db=db),
        "gemini_force_deterministic_fallback": platform_config_service.get_setting("gemini_force_deterministic_fallback", False, db=db),
        "gemini_temperature": platform_config_service.get_setting("gemini_temperature", 0.2, db=db),
        "gemini_timeout_seconds": platform_config_service.get_setting("gemini_timeout_seconds", 15, db=db),
    }


def update_ai_config(db: Session, config_data: dict[str, Any], admin_actor: Any = None) -> dict[str, Any]:
    """Updates AI model controls with immediate cache invalidation and audit logging."""
    actor_email = get_actor_email(admin_actor)
    allowed_keys = {
        "gemini_primary_model",
        "gemini_force_deterministic_fallback",
        "gemini_temperature",
        "gemini_timeout_seconds",
    }
    updated = {}
    for k, v in config_data.items():
        if k in allowed_keys:
            updated[k] = platform_config_service.set_setting(db, key=k, value=v, actor_email=actor_email)
    return updated


def get_feature_flags(db: Optional[Session] = None) -> dict[str, bool]:
    """Retrieves current boolean system feature flags from database."""
    if db is not None:
        all_s = platform_config_service.get_all_settings(db)
    else:
        with get_session() as s:
            all_s = platform_config_service.get_all_settings(s)
    return {k: v["value"] for k, v in all_s.items() if v.get("type") == "boolean"}


def update_feature_flags(flags: dict[str, bool], admin_actor: Any, db: Optional[Session] = None) -> dict[str, bool]:
    """Updates system feature flags with database persistence and audit logging."""
    actor_email = get_actor_email(admin_actor)
    if db is not None:
        for k, v in flags.items():
            platform_config_service.set_setting(db, key=k, value=bool(v), actor_email=actor_email)
        log_admin_action(
            db=db,
            actor_email=actor_email,
            action="FEATURE_FLAGS_UPDATED",
            details=f"Updated flags: {flags}",
            severity="INFO",
        )
        return get_feature_flags(db)
    else:
        with get_session() as s:
            for k, v in flags.items():
                platform_config_service.set_setting(s, key=k, value=bool(v), actor_email=actor_email)
            log_admin_action(
                db=s,
                actor_email=actor_email,
                action="FEATURE_FLAGS_UPDATED",
                details=f"Updated flags: {flags}",
                severity="INFO",
            )
            return get_feature_flags(s)



def list_admin_subscriptions(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    search: str = "",
) -> dict[str, Any]:
    """Retrieves paginated user subscriptions."""
    query = db.query(Subscription).join(User, Subscription.user_id == User.id)
    if search:
        s = f"%{search.strip().lower()}%"
        query = query.filter(User.email.ilike(s) | Subscription.plan_name.ilike(s))

    total = query.count()
    subs = query.order_by(Subscription.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for sub in subs:
        items.append({
            "id": sub.id,
            "user_id": sub.user_id,
            "user_email": sub.user.email if sub.user else "unknown",
            "plan_name": sub.plan_name,
            "status": sub.status,
            "starts_at": sub.starts_at.isoformat() if sub.starts_at else None,
            "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
            "is_trial": sub.is_trial,
            "razorpay_payment_id": sub.razorpay_payment_id,
            "updated_at": sub.updated_at.isoformat() if sub.updated_at else None,
        })

    return {
        "subscriptions": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


def get_quotas_config(db: Session) -> dict[str, Any]:
    """Retrieves default quotas per plan."""
    return {
        "quota_free_resumes": platform_config_service.get_setting("quota_free_resumes", 1, db=db),
        "quota_free_tailors": platform_config_service.get_setting("quota_free_tailors", 3, db=db),
        "quota_free_exports": platform_config_service.get_setting("quota_free_exports", 5, db=db),
        "quota_free_analyses": platform_config_service.get_setting("quota_free_analyses", 5, db=db),
        "quota_pro_tailors": platform_config_service.get_setting("quota_pro_tailors", 50, db=db),
        "quota_pro_exports": platform_config_service.get_setting("quota_pro_exports", 100, db=db),
    }


def update_quotas_config(db: Session, quotas_data: dict[str, Any], admin_actor: Any = None) -> dict[str, Any]:
    """Updates default plan quotas."""
    actor_email = get_actor_email(admin_actor)
    updated = {}
    for k, v in quotas_data.items():
        if k.startswith("quota_"):
            updated[k] = platform_config_service.set_setting(db, key=k, value=int(v), actor_email=actor_email)
    return updated


def get_audit_logs(
    db: Optional[Session] = None,
    limit: int = 50,
    search: str = "",
) -> list[dict[str, Any]]:
    """Retrieves real administrative and security audit events directly from PostgreSQL audit_logs table."""
    def _fetch(session: Session) -> list[dict[str, Any]]:
        query = session.query(AuditLog)
        if search:
            s = f"%{search.strip().lower()}%"
            query = query.filter(AuditLog.action.ilike(s) | AuditLog.entity_type.ilike(s))
        logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()

        formatted = []
        for l in logs:
            meta = l.metadata_json or {}
            actor = meta.get("actor")
            if not actor:
                u = session.get(User, l.user_id) if l.user_id else None
                actor = u.email if u else "system"
            details = meta.get("details") or (f"Entity: {l.entity_type} #{l.entity_id}" if l.entity_type else "No details recorded")
            severity = meta.get("severity") or "INFO"

            formatted.append({
                "id": l.id,
                "timestamp": l.created_at.isoformat() if l.created_at else None,
                "actor": actor,
                "action": l.action,
                "details": details,
                "severity": severity,
                "entity_type": l.entity_type,
                "entity_id": l.entity_id,
            })
        return formatted

    if db is not None:
        return _fetch(db)
    else:
        with get_session() as s:
            return _fetch(s)

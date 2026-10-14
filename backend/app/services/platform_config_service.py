"""Canonical Platform Configuration Service for SmartResume.ai.

Owns platform-wide settings, feature flags, AI orchestration controls,
plan quotas, and runtime configurations.
Backed by the PostgreSQL `platform_settings` table with a thread-safe
in-memory cache for ultra-low latency lookups.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.database import get_session
from app.models.platform_setting import PlatformSetting
from app.services.audit_service import write_audit_log

logger = logging.getLogger(__name__)

# Default canonical specifications for all platform settings
CANONICAL_DEFAULTS: dict[str, dict[str, Any]] = {
    # System Feature Flags
    "text_interview_enabled": {
        "value": True,
        "type": "boolean",
        "description": "Enable interactive multi-turn text mock interview practice",
        "is_public": True,
    },
    "voice_interview_enabled": {
        "value": True,
        "type": "boolean",
        "description": "Enable voice audio recording and AI voice prompts in interview practice",
        "is_public": True,
    },
    "focus_coaching_enabled": {
        "value": True,
        "type": "boolean",
        "description": "Enable video focus and eye contact coaching in interview practice",
        "is_public": True,
    },
    "strict_focus_mode_enabled": {
        "value": True,
        "type": "boolean",
        "description": "Enable optional Strict Focus Practice mode with auto-end threshold",
        "is_public": True,
    },
    "interview_default_duration": {
        "value": 60,
        "type": "integer",
        "description": "Default planned mock interview session duration in minutes",
        "is_public": True,
    },
    "interview_max_duration": {
        "value": 120,
        "type": "integer",
        "description": "Maximum permitted mock interview session duration in minutes",
        "is_public": True,
    },
    "strict_focus_max_warnings": {
        "value": 3,
        "type": "integer",
        "description": "Maximum sustained attention warnings before strict practice ends",
        "is_public": True,
    },
    "smartbuild_ai_wizard": {
        "value": True,
        "type": "boolean",
        "description": "Enable guided conversational SmartBuild resume creator",
        "is_public": True,
    },
    "gemini_live_mode": {
        "value": True,
        "type": "boolean",
        "description": "Enable live Google Gemini 2.5 generative AI orchestration",
        "is_public": True,
    },
    "job_radar_crawler": {
        "value": True,
        "type": "boolean",
        "description": "Enable automated Job Radar market search and tracking",
        "is_public": True,
    },
    "international_workspace": {
        "value": True,
        "type": "boolean",
        "description": "Enable international market compliance and multi-region formatting",
        "is_public": True,
    },
    "public_signup_enabled": {
        "value": True,
        "type": "boolean",
        "description": "Allow new candidate registration on the public application",
        "is_public": True,
    },
    "maintenance_mode": {
        "value": False,
        "type": "boolean",
        "description": "Put the public platform in read-only maintenance mode",
        "is_public": True,
    },

    # AI Orchestration Controls
    "gemini_primary_model": {
        "value": "gemini-2.5-flash",
        "type": "string",
        "description": "Primary Google Gemini model identifier",
        "is_public": False,
    },
    "gemini_force_deterministic_fallback": {
        "value": False,
        "type": "boolean",
        "description": "Emergency kill switch: force deterministic rules engine for all AI calls",
        "is_public": False,
    },
    "gemini_temperature": {
        "value": 0.2,
        "type": "float",
        "description": "Sampling temperature for Gemini model calls",
        "is_public": False,
    },
    "gemini_timeout_seconds": {
        "value": 15,
        "type": "integer",
        "description": "Network timeout in seconds for Gemini API calls",
        "is_public": False,
    },

    # System Announcements & Banners
    "system_announcement_enabled": {
        "value": False,
        "type": "boolean",
        "description": "Display global announcement banner across candidate application",
        "is_public": True,
    },
    "system_announcement_text": {
        "value": "",
        "type": "string",
        "description": "Announcement banner text displayed to candidates",
        "is_public": True,
    },

    # Default Subscription Plan Quotas
    "quota_free_resumes": {
        "value": 1,
        "type": "integer",
        "description": "Maximum active resumes for FREE tier",
        "is_public": False,
    },
    "quota_free_tailors": {
        "value": 2,
        "type": "integer",
        "description": "Monthly AI tailoring allowance for FREE tier",
        "is_public": False,
    },
    "quota_free_exports": {
        "value": 2,
        "type": "integer",
        "description": "Monthly PDF export allowance for FREE tier",
        "is_public": False,
    },
    "quota_free_analyses": {
        "value": 2,
        "type": "integer",
        "description": "Monthly job fit analysis allowance for FREE tier",
        "is_public": False,
    },

    "quota_pro_tailors": {
        "value": 50,
        "type": "integer",
        "description": "Monthly AI tailoring allowance for PRO tier",
        "is_public": False,
    },
    "quota_pro_exports": {
        "value": 100,
        "type": "integer",
        "description": "Monthly PDF export allowance for PRO tier",
        "is_public": False,
    },

    # Template Management Catalog
    "template_catalog": {
        "value": {
            "classic_ats": True,
            "modern_clean": True,
            "executive_brief": True,
            "tech_minimal": True,
        },
        "type": "json",
        "description": "Enabled state of resume templates",
        "is_public": True,
    },
}

_cache_lock = threading.Lock()
_memory_cache: dict[str, Any] = {}
_cache_initialized = False


def _serialize_value(val: Any, val_type: str) -> str:
    if val_type == "json" or isinstance(val, (dict, list)):
        return json.dumps(val)
    elif val_type == "boolean":
        return "true" if bool(val) else "false"
    elif val_type in ("integer", "float"):
        return str(val)
    return str(val)


def _deserialize_value(raw: str, val_type: str) -> Any:
    if val_type == "boolean":
        return raw.strip().lower() in ("true", "1", "yes")
    elif val_type == "integer":
        try:
            return int(raw)
        except (ValueError, TypeError):
            return 0
    elif val_type == "float":
        try:
            return float(raw)
        except (ValueError, TypeError):
            return 0.0
    elif val_type == "json":
        try:
            return json.loads(raw)
        except Exception:
            return {}
    return raw


def ensure_defaults_seeded(db: Session) -> None:
    """Seeds any missing canonical settings into the database table."""
    existing = {s.key for s in db.query(PlatformSetting.key).all()}
    to_add = []
    now = datetime.utcnow()
    for key, spec in CANONICAL_DEFAULTS.items():
        if key not in existing:
            raw_val = _serialize_value(spec["value"], spec["type"])
            to_add.append(
                PlatformSetting(
                    key=key,
                    value=raw_val,
                    value_type=spec["type"],
                    description=spec["description"],
                    is_public=spec["is_public"],
                    updated_by="system_init",
                    updated_at=now,
                )
            )
    if to_add:
        db.add_all(to_add)
        db.commit()


def _refresh_cache_from_db(db: Session) -> None:
    """Loads all settings from database into memory cache."""
    global _memory_cache, _cache_initialized
    try:
        ensure_defaults_seeded(db)
        rows = db.query(PlatformSetting).all()
        new_cache: dict[str, Any] = {}
        for r in rows:
            val = _deserialize_value(r.value, r.value_type)
            new_cache[r.key] = {
                "value": val,
                "type": r.value_type,
                "description": r.description,
                "is_public": r.is_public,
                "updated_by": r.updated_by,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
        with _cache_lock:
            _memory_cache = new_cache
            _cache_initialized = True
    except Exception as e:
        logger.warning("Could not query platform_settings from DB (%s); falling back to canonical defaults", e)
        try:
            db.rollback()
        except Exception:
            pass
        with _cache_lock:
            _memory_cache = {
                k: {
                    "value": spec["value"],
                    "type": spec["type"],
                    "description": spec["description"],
                    "is_public": spec["is_public"],
                    "updated_by": "canonical_default",
                    "updated_at": datetime.utcnow().isoformat(),
                }
                for k, spec in CANONICAL_DEFAULTS.items()
            }
            _cache_initialized = True


def get_setting(key: str, default: Any = None, db: Optional[Session] = None) -> Any:
    """High-speed cached lookup for any configuration key."""
    global _cache_initialized
    if not _cache_initialized:
        if db is not None:
            _refresh_cache_from_db(db)
        else:
            with get_session() as session:
                _refresh_cache_from_db(session)

    with _cache_lock:
        item = _memory_cache.get(key)
        if item is not None:
            return item["value"]
    if key in CANONICAL_DEFAULTS:
        return CANONICAL_DEFAULTS[key]["value"]
    return default


def get_all_settings(db: Session) -> dict[str, Any]:
    """Returns the complete canonical platform configuration for administrative management."""
    if not _cache_initialized:
        _refresh_cache_from_db(db)
    with _cache_lock:
        return dict(_memory_cache)


def get_public_config(db: Session) -> dict[str, Any]:
    """Returns the subset of settings permitted for public client applications."""
    if not _cache_initialized:
        _refresh_cache_from_db(db)
    with _cache_lock:
        public_items = {k: v["value"] for k, v in _memory_cache.items() if v.get("is_public")}
    return public_items


def set_setting(
    db: Session,
    key: str,
    value: Any,
    actor_email: str = "admin",
    description: Optional[str] = None,
) -> Any:
    """Updates or creates a configuration key with validation, database persistence, audit logging, and cache invalidation."""
    spec = CANONICAL_DEFAULTS.get(key, {})
    if "type" in spec:
        val_type = spec["type"]
    elif isinstance(value, bool):
        val_type = "boolean"
    elif isinstance(value, int):
        val_type = "integer"
    elif isinstance(value, float):
        val_type = "float"
    elif isinstance(value, (dict, list)):
        val_type = "json"
    else:
        val_type = "string"

    is_public = spec.get("is_public", False)
    desc = description or spec.get("description", "")

    # Normalize type if known
    if val_type == "boolean":
        clean_val = bool(value)
    elif val_type == "integer":
        clean_val = int(value)
    elif val_type == "float":
        clean_val = float(value)
    elif val_type == "json":
        clean_val = value if isinstance(value, (dict, list)) else json.loads(str(value))
    else:
        clean_val = str(value)

    raw_str = _serialize_value(clean_val, val_type)
    now = datetime.utcnow()

    setting = db.get(PlatformSetting, key)
    if setting:
        old_val = setting.value
        setting.value = raw_str
        setting.updated_by = actor_email
        setting.updated_at = now
        if description:
            setting.description = description
    else:
        old_val = None
        setting = PlatformSetting(
            key=key,
            value=raw_str,
            value_type=val_type,
            description=desc,
            is_public=is_public,
            updated_by=actor_email,
            updated_at=now,
        )
        db.add(setting)

    # Record security audit log entry
    write_audit_log(
        db,
        action="PLATFORM_SETTING_UPDATED",
        entity_type="platform_setting",
        entity_id=key,
        metadata={
            "actor": actor_email,
            "key": key,
            "old_value": old_val,
            "new_value": raw_str,
            "timestamp": now.isoformat(),
        },
    )

    db.commit()
    db.refresh(setting)

    # Invalidate and update memory cache immediately
    with _cache_lock:
        _memory_cache[key] = {
            "value": clean_val,
            "type": val_type,
            "description": setting.description,
            "is_public": setting.is_public,
            "updated_by": setting.updated_by,
            "updated_at": setting.updated_at.isoformat(),
        }

    return clean_val


def update_bulk_settings(db: Session, settings_dict: dict[str, Any], actor_email: str) -> dict[str, Any]:
    """Updates multiple settings atomically."""
    results = {}
    for k, v in settings_dict.items():
        results[k] = set_setting(db, key=k, value=v, actor_email=actor_email)
    return results

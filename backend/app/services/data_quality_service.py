"""Data Quality Audit Service for SmartResume.ai.

Audits resumes for structural anomalies, data duplications, misplaced contact details,
name-as-headline mistakes, malformed skill entries, and profile discrepancies.
Provides structured diagnostic issues with clear remediation proposals rather than
silently mutating candidate data.
"""

from __future__ import annotations

import re
from typing import Any


def audit_resume_data_quality(
    parsed_content: dict[str, Any] | None,
    profile_data: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Audits a parsed resume dictionary and returns a list of detected data quality issues."""
    issues: list[dict[str, Any]] = []
    if not parsed_content or not isinstance(parsed_content, dict):
        return [
            {
                "id": "dq_empty_content",
                "category": "document",
                "severity": "warning",
                "field": "parsed_content",
                "message": "Resume content is empty or unparsed.",
                "current_value": None,
                "suggested_fix": "Add sections or import an existing document.",
                "can_auto_fix": False,
            }
        ]

    header = parsed_content.get("header") or {}
    full_name = str(header.get("full_name") or "").strip()
    headline = str(header.get("headline") or "").strip()
    email = str(header.get("email") or "").strip()
    phone = str(header.get("phone") or "").strip()
    location = str(header.get("location") or "").strip()
    summary = str(parsed_content.get("summary") or "").strip()
    experiences = parsed_content.get("experiences") or []
    education = parsed_content.get("education") or []
    skills = parsed_content.get("skills") or []

    # 1. Check: Name mistakenly copied as Headline
    if full_name and headline and full_name.lower() == headline.lower():
        issues.append({
            "id": "dq_name_as_headline",
            "category": "headline",
            "severity": "warning",
            "field": "header.headline",
            "message": "Your candidate name is repeated as your professional headline.",
            "current_value": headline,
            "suggested_fix": "Replace with your target role title (e.g., 'Senior Software Engineer' or 'Full Stack Developer').",
            "can_auto_fix": True,
            "fix_action": {"type": "clear_or_replace_headline", "suggested_value": ""},
        })

    # 2. Check: Contact information or dates mistakenly placed in header location or phone
    if location and re.search(r"\b(engineer|developer|manager|specialist|analyst)\b", location, re.I):
        issues.append({
            "id": "dq_role_in_location",
            "category": "contact",
            "severity": "warning",
            "field": "header.location",
            "message": "Your location field appears to contain a job title rather than a geographic location.",
            "current_value": location,
            "suggested_fix": "Enter your City, State / Country (e.g., 'Bengaluru, India' or 'San Francisco, CA').",
            "can_auto_fix": False,
        })

    # 3. Check: Summary with embedded contact info or duplicate headings
    if summary:
        if re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", summary):
            issues.append({
                "id": "dq_summary_email",
                "category": "summary",
                "severity": "warning",
                "field": "summary",
                "message": "Summary contains an email address. Contact information belongs in the header to avoid recruiter ATS confusion.",
                "current_value": summary[:60] + "...",
                "suggested_fix": "Remove email from summary and keep it in the dedicated Contact section.",
                "can_auto_fix": True,
            })
        if re.search(r"(?:\+?\d[\d\s().-]{8,}\d)", summary):
            issues.append({
                "id": "dq_summary_phone",
                "category": "summary",
                "severity": "warning",
                "field": "summary",
                "message": "Summary contains a phone number. Contact information belongs in the header.",
                "current_value": summary[:60] + "...",
                "suggested_fix": "Remove phone number from summary statement.",
                "can_auto_fix": True,
            })
        if re.search(r"^(summary|professional summary|about me)[\s:–-]+", summary, re.I):
            clean_s = re.sub(r"^(summary|professional summary|about me)[\s:–-]+", "", summary, flags=re.I).strip()
            issues.append({
                "id": "dq_summary_redundant_heading",
                "category": "summary",
                "severity": "info",
                "field": "summary",
                "message": "Summary starts with redundant heading label ('Summary:' or 'Professional Summary:').",
                "current_value": summary[:40] + "...",
                "suggested_fix": "Remove the prefix so your statement begins directly.",
                "can_auto_fix": True,
                "fix_action": {"type": "replace_summary", "suggested_value": clean_s},
            })

    # 4. Check: Duplicate experience records & repeated employer names/dates
    seen_exp_fingerprints: dict[str, int] = {}
    seen_company_dates: dict[str, int] = {}
    for idx, exp in enumerate(experiences):
        if not isinstance(exp, dict):
            continue
        comp = str(exp.get("company") or "").strip().lower()
        title = str(exp.get("title") or exp.get("role_title") or "").strip().lower()
        start = str(exp.get("start_date") or "").strip().lower()
        end = str(exp.get("end_date") or "").strip().lower()

        # Check empty required experience fields
        if not comp and not title:
            issues.append({
                "id": f"dq_exp_empty_{idx}",
                "category": "experience",
                "severity": "error",
                "field": f"experiences[{idx}]",
                "message": f"Experience entry #{idx+1} has no company name or job title.",
                "current_value": "",
                "suggested_fix": "Fill in the company name and role title or remove the empty entry.",
                "can_auto_fix": False,
            })
            continue

        if comp and title:
            fp = f"{comp}::{title}"
            if fp in seen_exp_fingerprints:
                first_idx = seen_exp_fingerprints[fp]
                issues.append({
                    "id": f"dq_duplicate_exp_{idx}",
                    "category": "experience",
                    "severity": "warning",
                    "field": f"experiences[{idx}]",
                    "message": f"Duplicate experience record: '{exp.get('title')}' at '{exp.get('company')}' appears multiple times (entries #{first_idx+1} and #{idx+1}).",
                    "current_value": f"{exp.get('title')} at {exp.get('company')}",
                    "suggested_fix": "Consolidate into a single experience record with cumulative bullets.",
                    "can_auto_fix": False,
                })
            else:
                seen_exp_fingerprints[fp] = idx

        if comp and (start or end):
            cd_fp = f"{comp}::{start}::{end}"
            if cd_fp in seen_company_dates:
                first_idx = seen_company_dates[cd_fp]
                issues.append({
                    "id": f"dq_repeated_employer_dates_{idx}",
                    "category": "experience",
                    "severity": "warning",
                    "field": f"experiences[{idx}]",
                    "message": f"Identical employer and date range repeated in entries #{first_idx+1} and #{idx+1} ({exp.get('company')}, {start}–{end}).",
                    "current_value": f"{exp.get('company')} ({start}–{end})",
                    "suggested_fix": "Verify whether these represent separate promotions within the same company or accidental duplication.",
                    "can_auto_fix": False,
                })
            else:
                seen_company_dates[cd_fp] = idx

    # 5. Check: Duplicate and malformed skills
    seen_skills: set[str] = set()
    dup_skills: list[str] = []
    malformed_skills: list[str] = []
    for s in skills:
        s_str = (s if isinstance(s, str) else str((s or {}).get("name") or "")).strip()
        if not s_str:
            continue
        lower_s = s_str.lower()
        if lower_s in seen_skills:
            dup_skills.append(s_str)
        else:
            seen_skills.add(lower_s)

        # Malformed: e.g. length 1, or contains commas indicating comma-separated clump
        if len(s_str) == 1 and s_str not in {"c", "r"}:
            malformed_skills.append(s_str)
        elif "," in s_str:
            malformed_skills.append(s_str)
        elif lower_s in {"skills", "technical skills", "competencies"}:
            malformed_skills.append(s_str)

    if dup_skills:
        unique_dups = list(dict.fromkeys(dup_skills))
        issues.append({
            "id": "dq_duplicate_skills",
            "category": "skills",
            "severity": "info",
            "field": "skills",
            "message": f"Duplicate skills detected: {', '.join(unique_dups[:5])}.",
            "current_value": unique_dups,
            "suggested_fix": "Deduplicate skills list to keep your skills section concise and clean.",
            "can_auto_fix": True,
            "fix_action": {
                "type": "deduplicate_skills",
                "suggested_value": list(dict.fromkeys([
                    (s if isinstance(s, str) else str((s or {}).get("name") or "")).strip()
                    for s in skills
                    if (s if isinstance(s, str) else str((s or {}).get("name") or "")).strip()
                ]))
            }
        })

    if malformed_skills:
        issues.append({
            "id": "dq_malformed_skills",
            "category": "skills",
            "severity": "warning",
            "field": "skills",
            "message": f"Malformed skill entries found ({len(malformed_skills)} items, e.g. '{malformed_skills[0]}'). Items with commas should be split into individual tags.",
            "current_value": malformed_skills[:5],
            "suggested_fix": "Split comma-separated skill lists into distinct standalone skills.",
            "can_auto_fix": True,
        })

    # 6. Check: Empty Education entries
    for idx, edu in enumerate(education):
        if not isinstance(edu, dict):
            continue
        inst = str(edu.get("institution") or edu.get("school") or "").strip()
        deg = str(edu.get("degree") or "").strip()
        if not inst and not deg:
            issues.append({
                "id": f"dq_edu_empty_{idx}",
                "category": "education",
                "severity": "error",
                "field": f"education[{idx}]",
                "message": f"Education entry #{idx+1} has no institution or degree.",
                "current_value": "",
                "suggested_fix": "Specify the institution and degree or delete the blank entry.",
                "can_auto_fix": False,
            })

    # 7. Check: Profile vs Resume Conflicts (if profile_data provided)
    if profile_data and isinstance(profile_data, dict):
        p_email = str(profile_data.get("email") or "").strip().lower()
        if email and p_email and email.lower() != p_email:
            issues.append({
                "id": "dq_profile_conflict_email",
                "category": "conflict",
                "severity": "info",
                "field": "header.email",
                "message": f"Resume email ('{email}') differs from Master Profile email ('{p_email}').",
                "current_value": email,
                "suggested_fix": "Confirm whether you intentionally want a different email on this resume.",
                "can_auto_fix": False,
            })

        p_headline = str(profile_data.get("headline") or "").strip()
        if headline and p_headline and headline.lower() != p_headline.lower():
            issues.append({
                "id": "dq_profile_conflict_headline",
                "category": "conflict",
                "severity": "info",
                "field": "header.headline",
                "message": f"Resume headline ('{headline}') differs from Master Profile headline ('{p_headline}').",
                "current_value": headline,
                "suggested_fix": "Confirm whether you intentionally want a different headline on this resume.",
                "can_auto_fix": False,
            })

    return issues

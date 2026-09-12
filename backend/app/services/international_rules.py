"""International Resume & CV Rules Engine
Supports country-specific conventions:
- United States (US)
- India (IN)
- United Kingdom (UK)
- Canada (CA)
- Australia (AU)
- Europe / DACH (DE, AT, CH, EU)
- Middle East / UAE (AE, SA, QA)
"""
from typing import Any


COUNTRY_RULES: dict[str, dict[str, Any]] = {
    "US": {
        "name": "United States",
        "photo_allowed": False,
        "photo_guidance": "DO NOT include a photo. In the US, resumes with photos are often rejected to comply with anti-discrimination employment laws.",
        "dob_allowed": False,
        "marital_status_allowed": False,
        "gender_allowed": False,
        "recommended_pages": "1 page for <10 years of experience, max 2 pages for senior/executives",
        "spelling": "US English (e.g., 'optimized', 'analyzed', 'color')",
        "must_have_sections": ["Summary or Objective", "Experience", "Skills", "Education"],
        "disallowed_fields": ["photo", "dob", "birth_date", "marital_status", "gender", "nationality", "religion", "social_security_number"]
    },
    "IN": {
        "name": "India",
        "photo_allowed": True,
        "photo_guidance": "Photo optional. Clean, professional headshots are accepted on corporate and consulting resumes, but optional for tech roles.",
        "dob_allowed": True,
        "marital_status_allowed": False,
        "gender_allowed": False,
        "recommended_pages": "1 to 2 pages",
        "spelling": "UK / Indian English (e.g., 'optimised', 'analysed')",
        "must_have_sections": ["Experience", "Skills", "Education", "Projects"],
        "disallowed_fields": ["aadhaar", "pan_number", "religion", "caste"]
    },
    "UK": {
        "name": "United Kingdom",
        "photo_allowed": False,
        "photo_guidance": "Standard UK CVs do NOT include photos, age, or marital status to prevent unconscious bias (Equality Act 2010).",
        "dob_allowed": False,
        "marital_status_allowed": False,
        "gender_allowed": False,
        "recommended_pages": "2 pages is the standard UK professional CV length",
        "spelling": "British English (e.g., 'optimised', 'organised', 'specialise')",
        "must_have_sections": ["Personal Statement", "Employment History", "Skills", "Education & Qualifications"],
        "disallowed_fields": ["photo", "dob", "marital_status", "national_insurance_number"]
    },
    "CA": {
        "name": "Canada",
        "photo_allowed": False,
        "photo_guidance": "Strictly NO photos or personal demographic information (Human Rights Code compliance).",
        "dob_allowed": False,
        "marital_status_allowed": False,
        "gender_allowed": False,
        "recommended_pages": "1 to 2 pages",
        "spelling": "Canadian English / US English",
        "must_have_sections": ["Professional Summary", "Experience", "Technical Skills", "Education"],
        "disallowed_fields": ["photo", "dob", "sin_number", "marital_status", "immigration_status"]
    },
    "AU": {
        "name": "Australia",
        "photo_allowed": False,
        "photo_guidance": "Australian resumes typically do not contain photos or personal details like age or relationship status.",
        "dob_allowed": False,
        "marital_status_allowed": False,
        "gender_allowed": False,
        "recommended_pages": "2 to 3 pages is standard in Australia",
        "spelling": "Australian English (similar to UK English)",
        "must_have_sections": ["Career Summary", "Key Skills", "Professional Experience", "Education"],
        "disallowed_fields": ["photo", "dob", "marital_status", "tax_file_number"]
    },
    "DE": {
        "name": "Germany (DACH)",
        "photo_allowed": True,
        "photo_guidance": "Professional application photo (Bewerbungsfoto) is traditional and widely expected in DACH countries.",
        "dob_allowed": True,
        "marital_status_allowed": True,
        "gender_allowed": False,
        "recommended_pages": "1 to 2 pages Lebenslauf",
        "spelling": "Standard English / German",
        "must_have_sections": ["Berufserfahrung", "Ausbildung", "Kenntnisse", "Sprachen (CEFR levels)"],
        "disallowed_fields": []
    },
    "AE": {
        "name": "Middle East / UAE",
        "photo_allowed": True,
        "photo_guidance": "Professional photo is customary. Current location, visa status, and nationality are commonly included in GCC applications.",
        "dob_allowed": True,
        "marital_status_allowed": True,
        "gender_allowed": True,
        "recommended_pages": "2 pages",
        "spelling": "International / UK / US English",
        "must_have_sections": ["Executive Summary", "Work Experience", "Core Competencies", "Education", "Personal Details"],
        "disallowed_fields": []
    },
}


def normalize_country_code(country: str) -> str:
    c = country.strip().upper()
    if c in COUNTRY_RULES:
        return c
    mapping = {
        "UNITED STATES": "US",
        "USA": "US",
        "AMERICA": "US",
        "INDIA": "IN",
        "BHARAT": "IN",
        "UNITED KINGDOM": "UK",
        "BRITAIN": "UK",
        "ENGLAND": "UK",
        "CANADA": "CA",
        "AUSTRALIA": "AU",
        "GERMANY": "DE",
        "DEUTSCHLAND": "DE",
        "AUSTRIA": "DE",
        "SWITZERLAND": "DE",
        "UNITED ARAB EMIRATES": "AE",
        "UAE": "AE",
        "DUBAI": "AE",
        "SAUDI ARABIA": "AE",
        "QATAR": "AE",
    }
    return mapping.get(c, "IN")  # Default to India if unspecified


def get_country_guidelines(country: str) -> dict[str, Any]:
    code = normalize_country_code(country)
    return COUNTRY_RULES.get(code, COUNTRY_RULES["IN"])


def audit_resume_for_country(profile_data: dict[str, Any], country: str) -> dict[str, Any]:
    """Audits profile/resume content against target country standards."""
    code = normalize_country_code(country)
    rules = COUNTRY_RULES[code]
    warnings: list[str] = []
    recommendations: list[str] = []

    # Check photo
    has_photo = bool(profile_data.get("photo_url") or profile_data.get("avatar_url"))
    if has_photo and not rules["photo_allowed"]:
        warnings.append(f"Photo detected: {rules['photo_guidance']}")
    elif not has_photo and code in ("DE", "AE"):
        recommendations.append(f"Consider adding a high-quality professional photo for {rules['name']} applications.")

    # Check disallowed fields
    for field in rules.get("disallowed_fields", []):
        if profile_data.get(field):
            warnings.append(f"Remove '{field}' from your resume for {rules['name']} to comply with local hiring practices.")

    recommendations.append(f"Target page length: {rules['recommended_pages']}.")
    recommendations.append(f"Preferred spelling style: {rules['spelling']}.")

    return {
        "country": rules["name"],
        "country_code": code,
        "is_compliant": len(warnings) == 0,
        "warnings": warnings,
        "recommendations": recommendations,
        "rules_summary": rules,
    }

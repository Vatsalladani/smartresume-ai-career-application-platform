"""International Resume & CV Rules Engine
Supports country & market-specific conventions:
- Global / International (GLOBAL) - Default
- United States (US)
- Canada (CA)
- United Kingdom (UK)
- Australia (AU)
- New Zealand (NZ)
- Germany / DACH (DE)
- European Union / Europe (EU)
- Singapore (SG)
- United Arab Emirates (AE)
- Saudi Arabia / GCC (SA)
- India (IN)
"""
import re
from typing import Any


COUNTRY_RULES: dict[str, dict[str, Any]] = {
    "GLOBAL": {
        "code": "GLOBAL",
        "name": "Global / International",
        "terminology": "Resume / CV",
        "photo_allowed": False,
        "photo_guidance": "Photo optional. For international applications across varied regions, a clean layout without a photo is universally accepted and minimizes bias.",
        "dob_allowed": False,
        "marital_status_allowed": False,
        "gender_allowed": False,
        "recommended_pages": "1 to 2 pages (concise for early-career; up to 2 pages for experienced candidates)",
        "spelling": "International English (consistent UK or US spelling)",
        "must_have_sections": ["Summary", "Experience", "Skills", "Education"],
        "recommended_sections": ["Summary", "Experience", "Skills", "Education", "Projects", "Certifications", "Languages"],
        "disallowed_fields": ["religion", "caste", "marital_status", "father_name", "national_id", "passport_number"],
        "personal_info_guidance": "Include full name, professional email, phone number with country code, city/country, and LinkedIn/portfolio link. Exclude personal demographic or sensitive attributes.",
        "education_guidance": "List degree, institution, graduation year, and GPA/grade if strong. Do not invent conversion rates between grading scales.",
        "date_format_recommended": "Month Year (e.g., May 2025)",
        "ats_safety_guidance": "ATS-Safe single column layout provides maximum compatibility across global enterprise applicant tracking systems.",
        "recommended_templates": {
            "tech": "classic_ats",
            "business": "modern_professional",
            "executive": "executive_professional",
            "academic": "academic_research",
            "creative": "creative_professional",
            "default": "classic_ats",
        },
    },
    "US": {
        "code": "US",
        "name": "United States",
        "terminology": "Resume",
        "photo_allowed": False,
        "photo_guidance": "DO NOT include a photo. In the United States, resumes with photos are widely rejected to comply with federal and state anti-discrimination employment laws.",
        "dob_allowed": False,
        "marital_status_allowed": False,
        "gender_allowed": False,
        "recommended_pages": "1 page for <5-7 years experience; maximum 2 pages for senior/executives. Academic CVs may be longer.",
        "spelling": "US English (e.g., 'optimized', 'analyzed', 'color', 'program')",
        "must_have_sections": ["Summary or Objective", "Experience", "Skills", "Education"],
        "recommended_sections": ["Summary", "Experience", "Skills", "Projects", "Education", "Certifications"],
        "disallowed_fields": ["photo", "dob", "birth_date", "marital_status", "gender", "nationality", "religion", "social_security_number", "ssn"],
        "personal_info_guidance": "Contact details: Name, Email, Phone, City & State (e.g. San Francisco, CA), LinkedIn URL, GitHub/Portfolio. Never include age, marital status, or SSN.",
        "education_guidance": "List Degree, Major, University, Graduation Year, and GPA (on 4.0 scale if 3.5+). Include Honors (cum laude) and relevant coursework if early career.",
        "date_format_recommended": "Month Year (e.g., May 2025) or MM/YYYY (e.g., 05/2025)",
        "ats_safety_guidance": "Strictly ATS-Safe: single column, clear standard headings, standard bullet points for Workday, Greenhouse, Lever, and Taleo.",
        "recommended_templates": {
            "tech": "classic_ats",
            "business": "modern_professional",
            "executive": "executive_professional",
            "academic": "academic_research",
            "creative": "creative_professional",
            "default": "classic_ats",
        },
    },
    "CA": {
        "code": "CA",
        "name": "Canada",
        "terminology": "Resume",
        "photo_allowed": False,
        "photo_guidance": "Strictly NO photos or personal demographic information (Human Rights Code compliance).",
        "dob_allowed": False,
        "marital_status_allowed": False,
        "gender_allowed": False,
        "recommended_pages": "1 to 2 pages (1 page for early career, 2 pages for experienced candidates)",
        "spelling": "Canadian English / US English (e.g., 'optimized' or 'optimised', 'program')",
        "must_have_sections": ["Professional Summary", "Experience", "Technical Skills", "Education"],
        "recommended_sections": ["Professional Summary", "Work Experience", "Technical Skills", "Education", "Projects"],
        "disallowed_fields": ["photo", "dob", "sin_number", "sin", "marital_status", "immigration_status", "religion", "gender"],
        "personal_info_guidance": "City & Province (e.g. Toronto, ON), Email, Phone, LinkedIn. Work authorization status can be stated neutrally (e.g., 'Legally authorized to work in Canada') if helpful.",
        "education_guidance": "Degree, Institution, Province, Graduation Year. GPA on 4.0 scale if applicable.",
        "date_format_recommended": "Month Year (e.g., May 2025)",
        "ats_safety_guidance": "Single column ATS-Safe structure recommended for Canadian enterprise ATS filters.",
        "recommended_templates": {
            "tech": "classic_ats",
            "business": "modern_professional",
            "executive": "executive_professional",
            "academic": "academic_research",
            "creative": "minimal_professional",
            "default": "classic_ats",
        },
    },
    "UK": {
        "code": "UK",
        "name": "United Kingdom",
        "terminology": "CV",
        "photo_allowed": False,
        "photo_guidance": "Standard UK CVs do NOT include photos, age, or marital status to prevent unconscious bias (Equality Act 2010).",
        "dob_allowed": False,
        "marital_status_allowed": False,
        "gender_allowed": False,
        "recommended_pages": "2 pages is the standard UK professional CV length (1 page for recent school leavers)",
        "spelling": "British English (e.g., 'optimised', 'organised', 'specialise', 'colour')",
        "must_have_sections": ["Personal Statement", "Employment History", "Skills", "Education & Qualifications"],
        "recommended_sections": ["Personal Statement", "Employment History", "Key Skills", "Education & Qualifications", "Key Projects"],
        "disallowed_fields": ["photo", "dob", "marital_status", "national_insurance_number", "ni_number", "religion", "gender"],
        "personal_info_guidance": "Location (Town/City and Postcode area), Email, Phone, LinkedIn. Exclude full residential street address.",
        "education_guidance": "Degree with UK Degree Classification (e.g., 'First-Class Honours (1st)' or 'Upper Second-Class Honours (2:1)').",
        "date_format_recommended": "Month Year (e.g., May 2025) or MM/YYYY",
        "ats_safety_guidance": "Structured layout with clear headings and consistent date format for UK ATS platforms.",
        "recommended_templates": {
            "tech": "classic_ats",
            "business": "modern_professional",
            "executive": "executive_professional",
            "academic": "academic_research",
            "creative": "creative_professional",
            "default": "modern_professional",
        },
    },
    "AU": {
        "code": "AU",
        "name": "Australia",
        "terminology": "Resume / CV",
        "photo_allowed": False,
        "photo_guidance": "Australian resumes typically do not contain photos or personal details like age or relationship status to avoid hiring bias.",
        "dob_allowed": False,
        "marital_status_allowed": False,
        "gender_allowed": False,
        "recommended_pages": "2 to 3 pages is standard and expected in Australia for experienced professionals; 1-2 pages for graduates.",
        "spelling": "Australian English (aligned with UK English: 'optimised', 'analysed')",
        "must_have_sections": ["Career Summary", "Key Skills", "Professional Experience", "Education"],
        "recommended_sections": ["Career Summary", "Key Skills", "Professional Experience", "Education & Training", "Key Achievements"],
        "disallowed_fields": ["photo", "dob", "marital_status", "tax_file_number", "tfn", "religion"],
        "personal_info_guidance": "Suburb & State (e.g. Sydney, NSW), Phone (+61), Email, LinkedIn. Note work rights if relevant (e.g. 'Australian Citizen / Permanent Resident').",
        "education_guidance": "Degree, Institution, State, Year. Honours level or WAM/GPA if relevant.",
        "date_format_recommended": "Month Year (e.g., May 2025)",
        "ats_safety_guidance": "Clean two or three page ATS-balanced formatting with distinct responsibilities and achievements sections.",
        "recommended_templates": {
            "tech": "classic_ats",
            "business": "modern_professional",
            "executive": "executive_professional",
            "academic": "academic_research",
            "creative": "creative_professional",
            "default": "modern_professional",
        },
    },
    "NZ": {
        "code": "NZ",
        "name": "New Zealand",
        "terminology": "CV",
        "photo_allowed": False,
        "photo_guidance": "Photos are generally not recommended in New Zealand CVs to prevent unconscious bias.",
        "dob_allowed": False,
        "marital_status_allowed": False,
        "gender_allowed": False,
        "recommended_pages": "2 pages is standard in New Zealand; concise and focused on evidence.",
        "spelling": "New Zealand English (UK English spelling convention)",
        "must_have_sections": ["Personal Statement", "Work History", "Skills", "Qualifications"],
        "recommended_sections": ["Personal Statement", "Work History", "Skills", "Qualifications", "Key Achievements"],
        "disallowed_fields": ["photo", "dob", "marital_status", "ird_number", "religion"],
        "personal_info_guidance": "City/Region (e.g. Auckland, Wellington), Phone (+64), Email, LinkedIn.",
        "education_guidance": "Qualification, Institution, Completion Year. Grade / Honours if applicable.",
        "date_format_recommended": "Month Year (e.g., May 2025)",
        "ats_safety_guidance": "Balanced professional styling with clear chronological work history.",
        "recommended_templates": {
            "tech": "classic_ats",
            "business": "modern_professional",
            "executive": "executive_professional",
            "academic": "academic_research",
            "creative": "minimal_professional",
            "default": "modern_professional",
        },
    },
    "DE": {
        "code": "DE",
        "name": "Germany (DACH)",
        "terminology": "Lebenslauf / CV",
        "photo_allowed": True,
        "photo_guidance": "Professional application photo (Bewerbungsfoto) is traditional and widely expected in DACH countries, though anti-discrimination laws make it optional.",
        "dob_allowed": True,
        "marital_status_allowed": False,
        "gender_allowed": False,
        "recommended_pages": "1 to 2 pages (Lebenslauf should be concise, structured, and factual)",
        "spelling": "Standard English or German depending on the company / posting language",
        "must_have_sections": ["Berufserfahrung (Work Experience)", "Ausbildung (Education)", "Kenntnisse (Skills)", "Sprachen (Languages)"],
        "recommended_sections": ["Berufserfahrung", "Ausbildung", "Fachliche Kenntnisse", "Sprachkenntnisse (CEFR)", "Zertifikate & Weiterbildung"],
        "disallowed_fields": ["religion", "caste", "political_affiliation"],
        "personal_info_guidance": "Name, City/Country, Email, Phone, LinkedIn. Date of birth is common in traditional applications, but optional. Nationality may be helpful for EU work authorization.",
        "education_guidance": "Degree, Institution, Location, Final Grade (German grading 1.0 best - 4.0 pass). Thesis/Dissertation title is valued.",
        "date_format_recommended": "MM/YYYY (e.g., 05/2025) or Month Year",
        "ats_safety_guidance": "Structured, chronological layout with clear date markers (MM/YYYY - MM/YYYY).",
        "recommended_templates": {
            "tech": "classic_ats",
            "business": "modern_professional",
            "executive": "executive_professional",
            "academic": "academic_research",
            "creative": "minimal_professional",
            "default": "modern_professional",
        },
    },
    "EU": {
        "code": "EU",
        "name": "European Union / Europe",
        "terminology": "CV",
        "photo_allowed": True,
        "photo_guidance": "Photo optional across Europe. Western/Northern Europe tends toward no photo, while Central/Southern Europe often accepts a professional headshot.",
        "dob_allowed": True,
        "marital_status_allowed": False,
        "gender_allowed": False,
        "recommended_pages": "1 to 2 pages for standard roles; Europass-aligned structure.",
        "spelling": "British / International English",
        "must_have_sections": ["Summary", "Work Experience", "Education", "Skills", "Languages"],
        "recommended_sections": ["Summary", "Work Experience", "Education", "Skills", "Languages (CEFR)", "Projects"],
        "disallowed_fields": ["religion", "caste", "marital_status", "national_id"],
        "personal_info_guidance": "City, Country, Email, Phone (+ country code), LinkedIn. Note EU work authorization or citizenship if relevant.",
        "education_guidance": "Degree (BSc, MSc, PhD), University, Country, Completion Date, Grade / Distinction.",
        "date_format_recommended": "Month Year or MM/YYYY",
        "ats_safety_guidance": "Clean chronological layout with CEFR language proficiency levels (A1-C2).",
        "recommended_templates": {
            "tech": "classic_ats",
            "business": "modern_professional",
            "executive": "executive_professional",
            "academic": "academic_research",
            "creative": "minimal_professional",
            "default": "modern_professional",
        },
    },
    "SG": {
        "code": "SG",
        "name": "Singapore",
        "terminology": "Resume / CV",
        "photo_allowed": False,
        "photo_guidance": "Photo optional. Singapore's Tripartite Guidelines on Fair Employment Practices (TAFEP) recommend omitting photo, age, and marital status.",
        "dob_allowed": False,
        "marital_status_allowed": False,
        "gender_allowed": False,
        "recommended_pages": "1 to 2 pages (concise, results-oriented, skills-forward)",
        "spelling": "UK / International English",
        "must_have_sections": ["Executive Summary", "Work Experience", "Skills", "Education"],
        "recommended_sections": ["Executive Summary", "Work Experience", "Core Skills", "Education", "Key Projects", "Certifications"],
        "disallowed_fields": ["nric", "fin_number", "race", "religion", "marital_status", "age", "dob"],
        "personal_info_guidance": "Email, Phone (+65), City/Region, LinkedIn. Exclude NRIC/FIN number, race, and religion per TAFEP guidelines.",
        "education_guidance": "Degree, Institution, Graduation Year, Honours / GPA (CAP) if strong.",
        "date_format_recommended": "Month Year (e.g., May 2025)",
        "ats_safety_guidance": "ATS-Safe single column format optimized for multinational enterprise portals in Singapore.",
        "recommended_templates": {
            "tech": "classic_ats",
            "business": "modern_professional",
            "executive": "executive_professional",
            "academic": "academic_research",
            "creative": "creative_professional",
            "default": "classic_ats",
        },
    },
    "AE": {
        "code": "AE",
        "name": "United Arab Emirates",
        "terminology": "Resume / CV",
        "photo_allowed": True,
        "photo_guidance": "Professional photo is customary in UAE and GCC corporate roles, though optional for global tech firms.",
        "dob_allowed": True,
        "marital_status_allowed": True,
        "gender_allowed": False,
        "recommended_pages": "2 pages is standard in UAE and Middle East markets.",
        "spelling": "International / UK / US English",
        "must_have_sections": ["Professional Summary", "Work Experience", "Core Competencies", "Education", "Languages"],
        "recommended_sections": ["Professional Summary", "Work Experience", "Core Competencies", "Education", "Languages", "Visa & Location"],
        "disallowed_fields": ["religion", "caste", "emirates_id_number"],
        "personal_info_guidance": "Email, Phone (+971), Current Location (e.g. Dubai / Abu Dhabi), LinkedIn. Mentioning current visa status (e.g. 'Employment Visa', 'Golden Visa', 'Visit Visa') is standard practice.",
        "education_guidance": "Degree, University, Country, Year of Graduation.",
        "date_format_recommended": "Month Year (e.g., May 2025)",
        "ats_safety_guidance": "Clean executive structure with clearly highlighted language skills and international experience.",
        "recommended_templates": {
            "tech": "classic_ats",
            "business": "modern_professional",
            "executive": "executive_professional",
            "academic": "academic_research",
            "creative": "two_column_professional",
            "default": "modern_professional",
        },
    },
    "SA": {
        "code": "SA",
        "name": "Saudi Arabia / GCC",
        "terminology": "Resume / CV",
        "photo_allowed": True,
        "photo_guidance": "Professional photo is customary in GCC corporate applications, optional for international tech roles.",
        "dob_allowed": True,
        "marital_status_allowed": False,
        "gender_allowed": False,
        "recommended_pages": "2 pages standard in Saudi Arabia and GCC markets.",
        "spelling": "International / UK / US English",
        "must_have_sections": ["Executive Summary", "Work Experience", "Key Skills", "Education", "Languages"],
        "recommended_sections": ["Executive Summary", "Work Experience", "Key Skills", "Education", "Certifications", "Languages"],
        "disallowed_fields": ["iqama_number", "religion", "caste"],
        "personal_info_guidance": "Location (e.g. Riyadh, Jeddah), Phone (+966), Email, LinkedIn, Transferable Iqama status if expatriate.",
        "education_guidance": "Degree, Institution, Country, Year.",
        "date_format_recommended": "Month Year (e.g., May 2025)",
        "ats_safety_guidance": "Formal, high-contrast, structured layout highlighting domain competencies and regional certifications.",
        "recommended_templates": {
            "tech": "classic_ats",
            "business": "modern_professional",
            "executive": "executive_professional",
            "academic": "academic_research",
            "creative": "minimal_professional",
            "default": "modern_professional",
        },
    },
    "IN": {
        "code": "IN",
        "name": "India",
        "terminology": "Resume / CV",
        "photo_allowed": True,
        "photo_guidance": "Photo optional. Clean, professional headshots are accepted on corporate and consulting resumes, but optional for tech roles.",
        "dob_allowed": True,
        "marital_status_allowed": False,
        "gender_allowed": False,
        "recommended_pages": "1 to 2 pages (1 page for campus freshers; 2 pages for experienced professionals)",
        "spelling": "UK / Indian English (e.g., 'optimised', 'analysed', 'programme')",
        "must_have_sections": ["Experience", "Skills", "Education", "Projects"],
        "recommended_sections": ["Summary", "Experience", "Skills", "Education", "Projects", "Certifications", "Achievements"],
        "disallowed_fields": ["aadhaar", "pan_number", "religion", "caste", "father_name", "marital_status"],
        "personal_info_guidance": "Name, Email, Phone (+91), City & State (e.g. Bengaluru, Karnataka), LinkedIn, GitHub. Never include Aadhaar, PAN, caste, or marital status.",
        "education_guidance": "Degree, College/Institute, Affiliated University, CGPA or Percentage (e.g. '8.6/10 CGPA' or '78%'). Do not force GPA conversions.",
        "date_format_recommended": "Month Year (e.g., May 2025)",
        "ats_safety_guidance": "Standard ATS-Safe single column format for campus portals and IT/product hiring platforms.",
        "recommended_templates": {
            "tech": "classic_ats",
            "business": "modern_professional",
            "executive": "executive_professional",
            "academic": "academic_research",
            "creative": "creative_professional",
            "default": "classic_ats",
        },
    },
}


def normalize_country_code(country: str) -> str:
    """Normalizes country or region string to standard market code."""
    if not country or not isinstance(country, str):
        return "GLOBAL"
    c = country.strip().upper()
    if c in COUNTRY_RULES:
        return c

    mapping = {
        "UNITED STATES": "US",
        "USA": "US",
        "AMERICA": "US",
        "US": "US",
        "INDIA": "IN",
        "BHARAT": "IN",
        "IN": "IN",
        "UNITED KINGDOM": "UK",
        "BRITAIN": "UK",
        "ENGLAND": "UK",
        "SCOTLAND": "UK",
        "WALES": "UK",
        "GB": "UK",
        "UK": "UK",
        "CANADA": "CA",
        "CA": "CA",
        "AUSTRALIA": "AU",
        "AU": "AU",
        "NEW ZEALAND": "NZ",
        "NZ": "NZ",
        "GERMANY": "DE",
        "DEUTSCHLAND": "DE",
        "AUSTRIA": "DE",
        "SWITZERLAND": "DE",
        "DE": "DE",
        "EUROPE": "EU",
        "EUROPEAN UNION": "EU",
        "EU": "EU",
        "FRANCE": "EU",
        "NETHERLANDS": "EU",
        "IRELAND": "EU",
        "SPAIN": "EU",
        "ITALY": "EU",
        "SINGAPORE": "SG",
        "SG": "SG",
        "UNITED ARAB EMIRATES": "AE",
        "UAE": "AE",
        "DUBAI": "AE",
        "ABU DHABI": "AE",
        "AE": "AE",
        "SAUDI ARABIA": "SA",
        "SAUDI": "SA",
        "KSA": "SA",
        "SA": "SA",
        "QATAR": "SA",
        "KUWAIT": "SA",
        "GCC": "SA",
        "GLOBAL": "GLOBAL",
        "INTERNATIONAL": "GLOBAL",
        "WORLDWIDE": "GLOBAL",
    }
    return mapping.get(c, "GLOBAL")


def get_country_guidelines(country: str) -> dict[str, Any]:
    """Retrieves country / market rules for given country."""
    code = normalize_country_code(country)
    return COUNTRY_RULES.get(code, COUNTRY_RULES["GLOBAL"])


def get_all_market_presets() -> list[dict[str, Any]]:
    """Returns list of all active market presets with metadata."""
    presets = []
    # Desired order: Global, US, Canada, UK, Australia, New Zealand, Germany, Europe, Singapore, UAE, Saudi Arabia, India
    ordered_keys = ["GLOBAL", "US", "CA", "UK", "AU", "NZ", "DE", "EU", "SG", "AE", "SA", "IN"]
    for k in ordered_keys:
        if k in COUNTRY_RULES:
            r = COUNTRY_RULES[k]
            presets.append({
                "code": r["code"],
                "name": r["name"],
                "terminology": r["terminology"],
                "photo_allowed": r["photo_allowed"],
                "photo_guidance": r["photo_guidance"],
                "recommended_pages": r["recommended_pages"],
                "spelling": r["spelling"],
                "date_format": r["date_format_recommended"],
            })
    return presets


def detect_market_from_location(location: str | None) -> dict[str, Any]:
    """
    Intelligently identifies the application market from job or company location text.
    Returns recommended market code and actionable guidance message.
    """
    if not location or not location.strip():
        return {
            "detected": False,
            "market_code": "GLOBAL",
            "market_name": "Global / International",
            "message": "No specific location detected. Using Global international guidance.",
        }

    loc = location.strip().lower()

    patterns = [
        (r"\b(canada|toronto|vancouver|montreal|ottawa|calgary|edmonton|ontario|bc|quebec|alberta)\b", "CA"),
        (r"\b(united states|usa|\bus\b|new york|nyc|san francisco|seattle|austin|chicago|los angeles|california|texas|washington|boston|remote, us|us remote)\b", "US"),
        (r"\b(united kingdom|\buk\b|britain|london|manchester|edinburgh|birmingham|glasgow|england|scotland|wales)\b", "UK"),
        (r"\b(germany|deutschland|berlin|munich|münchen|frankfurt|hamburg|cologne|köln|düsseldorf|stuttgart)\b", "DE"),
        (r"\b(australia|sydney|melbourne|brisbane|perth|adelaide|canberra|queensland|victoria|nsw)\b", "AU"),
        (r"\b(new zealand|\bnz\b|auckland|wellington|christchurch|hamilton)\b", "NZ"),
        (r"\b(singapore|\bsg\b)\b", "SG"),
        (r"\b(united arab emirates|uae|dubai|abu dhabi|sharjah)\b", "AE"),
        (r"\b(saudi arabia|saudi|riyadh|jeddah|dammam|khobar|qatar|doha|kuwait|bahrain|oman|gcc)\b", "SA"),
        (r"\b(india|bengaluru|bangalore|hyderabad|mumbai|delhi|gurugram|gurgaon|pune|chennai|noida|kolkata)\b", "IN"),
        (r"\b(europe|\beu\b|amsterdam|netherlands|paris|france|dublin|ireland|madrid|spain|milan|rome|italy|zurich|switzerland|stockholm|sweden)\b", "EU"),
    ]

    for regex, code in patterns:
        if re.search(regex, loc):
            rules = COUNTRY_RULES[code]
            return {
                "detected": True,
                "market_code": code,
                "market_name": rules["name"],
                "terminology": rules["terminology"],
                "message": f"Target location '{location.strip()}' indicates {rules['name']}. Recommended terminology: {rules['terminology']}.",
            }

    return {
        "detected": False,
        "market_code": "GLOBAL",
        "market_name": "Global / International",
        "message": f"Location '{location.strip()}' uses standard Global resume guidance.",
    }


def recommend_template_for_market(market: str, role: str | None = None, career_level: str | None = None) -> str:
    """Recommends an ATS-compliant template based on market, domain role, and career seniority."""
    code = normalize_country_code(market)
    rules = COUNTRY_RULES.get(code, COUNTRY_RULES["GLOBAL"])
    templates_map = rules.get("recommended_templates", {})

    role_str = (role or "").lower()
    lvl = (career_level or "").upper()

    if "academic" in role_str or "research" in role_str or "phd" in role_str or "postdoc" in role_str or "professor" in role_str:
        return templates_map.get("academic", "academic_research")
    if "creative" in role_str or "design" in role_str or "marketing" in role_str or "brand" in role_str:
        return templates_map.get("creative", "creative_professional")
    if "executive" in lvl or "director" in role_str or "vp" in role_str or "head" in role_str or "chief" in role_str:
        return templates_map.get("executive", "executive_professional")
    if "business" in role_str or "finance" in role_str or "consult" in role_str or "analyst" in role_str:
        return templates_map.get("business", "modern_professional")

    # Tech default
    return templates_map.get("tech", "classic_ats")


def audit_resume_for_country(profile_data: dict[str, Any], country: str) -> dict[str, Any]:
    """Audits profile/resume content against target country standards."""
    code = normalize_country_code(country)
    rules = COUNTRY_RULES.get(code, COUNTRY_RULES["GLOBAL"])
    warnings: list[str] = []
    recommendations: list[str] = []

    # Check photo
    has_photo = bool(profile_data.get("photo_url") or profile_data.get("avatar_url"))
    if has_photo and not rules["photo_allowed"]:
        warnings.append(f"Photo detected: {rules['photo_guidance']}")
    elif not has_photo and code in ("DE", "AE", "SA"):
        recommendations.append(f"Consider a professional photo headshot for {rules['name']} applications if appropriate.")

    # Check disallowed fields
    for field in rules.get("disallowed_fields", []):
        if profile_data.get(field):
            warnings.append(f"Remove '{field}' from your resume for {rules['name']} to comply with local hiring practices.")

    recommendations.append(f"Document terminology: {rules['terminology']}.")
    recommendations.append(f"Target page length: {rules['recommended_pages']}.")
    recommendations.append(f"Preferred spelling style: {rules['spelling']}.")
    recommendations.append(f"Recommended date formatting: {rules['date_format_recommended']}.")

    return {
        "country": rules["name"],
        "country_code": code,
        "is_compliant": len(warnings) == 0,
        "warnings": warnings,
        "recommendations": recommendations,
        "rules_summary": rules,
    }

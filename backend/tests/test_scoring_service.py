import pytest
from app.services.scoring_service import calculate_evidence_based_score, detect_career_level

def test_detect_career_level_fresher():
    resume = {
        "header": {"full_name": "Rohan Sharma"},
        "experiences": [],
        "projects": [{"title": "AgroMeds", "technologies": ["Python", "FastAPI"]}]
    }
    assert detect_career_level(resume) == "EARLY_CAREER"

def test_detect_career_level_experienced():
    resume = {
        "header": {"full_name": "Senior Architect"},
        "experiences": [
            {"role_title": "Senior Software Architect", "company": "Global Corp", "is_current": True}
        ],
    }
    assert detect_career_level(resume) == "EXPERIENCED"

def test_fresher_zero_experience_not_penalized():
    """A fresher with solid projects and skills must score well and NOT be penalized for lacking work history."""
    fresher_resume = {
        "header": {
            "full_name": "Vatsal Ladani",
            "headline": "Junior Software Engineer | Python & Cloud Developer",
            "email": "vatsal@example.com",
            "phone": "+91 9876543210",
            "location": "Ahmedabad, India",
            "linkedin": "linkedin.com/in/vatsal",
            "github": "github.com/vatsal"
        },
        "summary": "Motivated computer engineering graduate with hands-on expertise building REST APIs and backend systems with Python, FastAPI, and PostgreSQL.",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Git", "REST APIs", "SQL"],
        "experiences": [], # Zero work experience
        "projects": [
            {
                "title": "SmartResume AI Platform",
                "technologies": ["Python", "FastAPI", "PostgreSQL", "Docker"],
                "description": "Architected resume parsing and scoring backend with automated validation.",
                "bullet_points": [
                    "Engineered modular REST APIs achieving sub-100ms response times for 50+ concurrent requests.",
                    "Implemented PostgreSQL relational schema with foreign key constraints and transactional integrity."
                ]
            },
            {
                "title": "AgroMeds Healthcare System",
                "technologies": ["Python", "SQL", "Git"],
                "description": "Healthcare inventory and order management system.",
                "bullet_points": [
                    "Implemented secure session authentication and role-based access control.",
                    "Designed query optimizations reducing database search latency by 45%."
                ]
            }
        ],
        "education": [
            {
                "institution": "Gujarat Technological University",
                "degree": "M.Sc. Information Technology",
                "field_of_study": "Computer Science & IT",
                "start_date": "2022",
                "end_date": "2024"
            }
        ],
        "certifications": ["Python Core Certified", "PostgreSQL Fundamentals"]
    }

    result = calculate_evidence_based_score(
        resume_data=fresher_resume,
        target_role="Software Engineer",
        career_level="EARLY_CAREER"
    )

    assert result["is_fresher_calibrated"] is True
    assert result["career_level"] == "EARLY_CAREER"
    # Score should be strong (>= 75) despite zero employment history!
    assert result["overall_score"] >= 75
    # Must list what is helping
    assert any("project" in h.lower() for h in result["what_is_helping"])
    assert any("skills" in h.lower() for h in result["what_is_helping"])
    # Must NOT have experience penalty in holding back for freshers
    assert not any("lack of documented professional work experience" in h.lower() for h in result["what_is_holding_back"])

def test_buzzword_detection():
    resume = {
        "header": {"full_name": "Test User", "email": "test@example.com", "phone": "123"},
        "summary": "Hardworking, results-driven dynamic professional and quick learner.",
        "skills": ["Python"],
        "projects": [],
        "education": []
    }
    result = calculate_evidence_based_score(resume, target_role="Software Engineer")
    buzzword_phrases = [b["phrase"] for b in result["buzzwords_detected"]]
    assert "hardworking" in buzzword_phrases
    assert "quick learner" in buzzword_phrases
    assert "results-driven" in buzzword_phrases
    assert any("generic language detected" in h.lower() for h in result["what_is_holding_back"])

def test_unsupported_skills_detection():
    resume = {
        "header": {"full_name": "Test User", "email": "test@example.com", "phone": "123"},
        "summary": "Software developer.",
        "skills": ["Python", "Kubernetes", "AWS", "Rust"],
        "projects": [
            {"title": "Python Web App", "technologies": ["Python"], "bullet_points": ["Built using Python."]}
        ],
        "education": []
    }
    result = calculate_evidence_based_score(resume, target_role="Software Engineer")
    unsupported_names = [s["name"] for s in result["unsupported_skills"]]
    assert "Kubernetes" in unsupported_names
    assert "AWS" in unsupported_names
    assert "Rust" in unsupported_names
    assert "Python" not in unsupported_names

def test_eligibility_gap_vs_writing_defect():
    resume = {
        "header": {"full_name": "Fresher Candidate", "email": "fresher@example.com", "phone": "123"},
        "skills": ["Python", "FastAPI"],
        "projects": [{"title": "API Project", "technologies": ["Python"], "bullet_points": ["Created API."]}],
        "experiences": [],
        "education": [{"institution": "University", "degree": "B.Tech"}]
    }
    jd = "We are seeking a Senior Backend Engineer with 5+ years of experience in distributed systems."
    result = calculate_evidence_based_score(
        resume,
        target_role="Senior Backend Engineer",
        job_description=jd,
        career_level="EARLY_CAREER"
    )
    assert len(result["eligibility_gaps"]) >= 1
    assert result["eligibility_gaps"][0]["nature"] == "JOB_ELIGIBILITY_GAP"
    assert "eligibility gap, not a resume-writing defect" in result["eligibility_gaps"][0]["explanation"]

def test_score_recalculation_delta():
    resume = {
        "header": {"full_name": "Test User", "email": "test@example.com", "phone": "123"},
        "summary": "Software Engineer specializing in Python and FastAPI backend development.",
        "skills": ["Python", "FastAPI"],
        "projects": [{"title": "FastAPI App", "technologies": ["FastAPI", "Python"], "bullet_points": ["Engineered with Python."]}],
        "education": [{"institution": "College", "degree": "B.Sc"}]
    }
    result = calculate_evidence_based_score(
        resume,
        target_role="Software Engineer",
        previous_score=60
    )
    assert result["previous_score"] == 60
    assert result["score_delta"] is not None
    assert result["delta_explanation"] is not None


def test_field_neutral_scoring_finance():
    """A financial analyst must score based on finance evidence, NOT software engineer keywords."""
    finance_resume = {
        "header": {
            "full_name": "Maya Lin",
            "headline": "Financial Analyst | Valuation & FP&A Specialist",
            "email": "maya@example.com",
            "phone": "+1 555-0199",
            "location": "Chicago, IL"
        },
        "summary": "Financial analyst with 3 years of experience in financial modeling, valuation, variance analysis, and annual budgeting.",
        "skills": ["Financial Modeling", "Valuation", "Budgeting", "Forecasting", "Variance Analysis", "Excel", "GAAP"],
        "experiences": [
            {
                "role_title": "Financial Analyst",
                "company": "Horizon Capital",
                "start_date": "2022",
                "end_date": "2025",
                "is_current": True,
                "bullet_points": [
                    "Constructed multi-scenario DCF and LBO financial models evaluating $45M in strategic acquisitions.",
                    "Led quarterly variance analysis and budgeting workflows, reducing budget discrepancy by 18%.",
                    "Prepared executive P&L dashboards and reporting for the board of directors."
                ]
            }
        ],
        "education": [{"institution": "NYU Stern", "degree": "B.S. Finance"}],
        "certifications": ["CFA Level 1 Passed"]
    }

    result = calculate_evidence_based_score(finance_resume, target_role="Financial Analyst")
    assert result["overall_score"] >= 80
    assert result["dimensions"]["target_role_alignment"]["score"] >= 80
    # Verified: NO technical software penalty
    assert not any("software" in h.lower() for h in result["what_is_holding_back"])


def test_field_neutral_scoring_healthcare():
    """A registered nurse must score based on clinical skills and patient care, not tech projects."""
    nurse_resume = {
        "header": {
            "full_name": "Sarah Jenkins",
            "headline": "Registered Nurse (RN) | Emergency & Acute Care",
            "email": "sarah@example.com",
            "phone": "+1 555-4321",
            "location": "Boston, MA"
        },
        "summary": "Compassionate and certified Registered Nurse with 4 years in fast-paced emergency department patient care, triage, and medication administration.",
        "skills": ["Patient Care", "Triage", "EHR", "Medication Administration", "BLS", "ACLS", "Vital Signs"],
        "experiences": [
            {
                "role_title": "Emergency Room Staff Nurse",
                "company": "Boston General Hospital",
                "start_date": "2021",
                "end_date": "2025",
                "is_current": True,
                "bullet_points": [
                    "Delivered clinical care and vital signs monitoring for 25+ acute patients per 12-hour shift.",
                    "Executed triage assessments adhering strictly to HIPAA and patient safety protocols.",
                    "Administered critical medications and maintained 100% compliant EHR records."
                ]
            }
        ],
        "education": [{"institution": "Simmons University", "degree": "B.S. Nursing"}],
        "certifications": ["Registered Nurse (RN)", "BLS Certified", "ACLS Certified"]
    }

    result = calculate_evidence_based_score(nurse_resume, target_role="Registered Nurse")
    assert result["overall_score"] >= 80
    assert result["dimensions"]["target_role_alignment"]["score"] >= 80
    # No tech software penalties
    assert not any("git" in h.lower() or "python" in h.lower() for h in result["what_is_holding_back"])


def test_skill_evidence_grounding_levels():
    """Validates that skills are explicitly categorized into SUPPORTED, PARTIALLY_SUPPORTED, and UNSUPPORTED."""
    resume = {
        "header": {"full_name": "Alex Tech", "email": "alex@example.com", "phone": "123"},
        "summary": "Specialist in Python with familiarity in Docker.",
        "skills": ["Python", "Docker", "UnusedFramework"],
        "experiences": [
            {
                "role_title": "Software Engineer",
                "company": "Tech Inc",
                "bullet_points": ["Engineered distributed services using Python."]
            }
        ],
        "education": []
    }

    result = calculate_evidence_based_score(resume, target_role="Software Engineer")
    grounding = {s["name"]: s["status"] for s in result["skills_grounding"]}

    assert grounding["Python"] == "SUPPORTED"
    assert grounding["Docker"] == "PARTIALLY_SUPPORTED"
    assert grounding["UnusedFramework"] == "UNSUPPORTED"


def test_skill_proficiency_language_and_expert_gating():
    """Expert claim without sufficient evidence triggers gentle gating advisory, not a punitive insult."""
    resume = {
        "header": {"full_name": "Junior Developer", "email": "jd@example.com", "phone": "123"},
        "summary": "Junior developer with 1 year experience.",
        "skills": [
            {"name": "Python", "proficiency": "Expert"},
            {"name": "CSS", "proficiency": "Basic"}
        ],
        "experiences": [
            {
                "role_title": "Junior Developer",
                "company": "Startup",
                "bullet_points": ["Assisted with web bugs."]
            }
        ],
        "education": []
    }

    result = calculate_evidence_based_score(resume, target_role="Software Engineer", career_level="EARLY_CAREER")
    feedback = {f["skill"]: f for f in result["skill_proficiency_feedback"]}

    # Python should be evidence-gated with gentle advice
    assert "Python" in feedback
    assert feedback["Python"]["status"] == "EVIDENCE_GATED"
    assert "reconciliation" not in feedback["Python"]["note"]
    assert "architectural leadership" in feedback["Python"]["note"]

    # CSS should have positive phrasing without 'beginner'
    assert "CSS" in feedback
    assert "beginner" not in feedback["CSS"]["suggested_phrasing"].lower()
    assert "practical application" in feedback["CSS"]["suggested_phrasing"].lower()


def test_headline_seniority_consistency_check():
    """An early career candidate with 'Senior Director' in headline triggers consistency advisory check."""
    resume = {
        "header": {
            "full_name": "Alex Fresher",
            "headline": "Senior Lead Software Architect",
            "email": "alex@example.com",
            "phone": "123"
        },
        "summary": "Recent graduate looking for entry level roles.",
        "skills": ["Python"],
        "experiences": [],
        "projects": [{"title": "Web App", "technologies": ["Python"]}],
        "education": [{"degree": "B.S."}]
    }

    result = calculate_evidence_based_score(resume, target_role="Software Engineer", career_level="EARLY_CAREER")
    assert any("headline specifies senior positioning" in note.lower() for note in result["summary_consistency_notes"])
    assert any(c["check"] == "Headline Seniority vs Experience" for c in result["consistency_checks"])


def test_top_improvements_action_types_and_targets():
    """Top improvements include structured action_type, action_target, and action_label for direct UI navigation."""
    resume = {
        "header": {"full_name": "Test User", "email": "test@example.com", "phone": "123"},
        "summary": "",  # Empty summary
        "skills": ["Python", "FloatingSkill1", "FloatingSkill2"],
        "projects": [{"title": "Demo", "description": "Did work"}],  # No metrics
        "experiences": [],
        "education": []
    }

    result = calculate_evidence_based_score(resume, target_role="Software Engineer")
    imps = result["top_improvements"]
    assert len(imps) >= 1

    action_types = [imp.get("action_type") for imp in imps]
    assert any(t in action_types for t in ["IMPROVE_SUMMARY", "REVIEW_SKILLS", "REWRITE_BULLETS"])
    for imp in imps:
        assert "action_type" in imp
        assert "action_target" in imp
        assert "action_label" in imp


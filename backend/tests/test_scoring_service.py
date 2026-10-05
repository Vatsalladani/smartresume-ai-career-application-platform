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

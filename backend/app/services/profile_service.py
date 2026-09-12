import re
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import (
    Certification,
    Education,
    Experience,
    Profile,
    Project,
    Skill,
    User,
)
from app.schemas.master_profile import (
    CertificationCreate,
    EducationCreate,
    ExperienceCreate,
    ExperienceUpdate,
    ProfileImportDraft,
    ProfileUpdate,
    ProjectCreate,
    ProjectUpdate,
    SkillCreate,
)


def get_or_create_profile(db: Session, user_id: int) -> Profile:
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        profile = Profile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    profile.completeness_score = calculate_completeness(profile)
    return profile


def update_profile(db: Session, user_id: int, payload: ProfileUpdate) -> Profile:
    profile = get_or_create_profile(db, user_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    profile.completeness_score = calculate_completeness(profile)
    db.commit()
    db.refresh(profile)
    return profile


def calculate_completeness(profile: Profile) -> int:
    score = 0
    if profile.headline and len(profile.headline.strip()) > 5:
        score += 15
    if profile.summary and len(profile.summary.strip()) > 30:
        score += 15
    if profile.location or profile.phone:
        score += 10
    if len(profile.experiences) > 0:
        score += 25
    if len(profile.projects) > 0:
        score += 15
    if len(profile.education) > 0:
        score += 10
    if len(profile.skills) >= 3:
        score += 10
    return min(100, score)


# Experience CRUD
def add_experience(db: Session, user_id: int, payload: ExperienceCreate) -> Experience:
    profile = get_or_create_profile(db, user_id)
    exp = Experience(
        profile_id=profile.id,
        company=payload.company,
        role_title=payload.role_title,
        location=payload.location,
        employment_type=payload.employment_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_current=payload.is_current,
        description=payload.description,
        bullet_points=payload.bullet_points,
        technologies_used=payload.technologies_used,
        order_index=payload.order_index,
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    profile.completeness_score = calculate_completeness(profile)
    db.commit()
    return exp


def update_experience(db: Session, user_id: int, experience_id: int, payload: ExperienceUpdate) -> Experience:
    profile = get_or_create_profile(db, user_id)
    exp = db.query(Experience).filter(Experience.id == experience_id, Experience.profile_id == profile.id).first()
    if not exp:
        raise AppError("Experience entry not found.", 404)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(exp, field, value)
    db.commit()
    db.refresh(exp)
    return exp


def delete_experience(db: Session, user_id: int, experience_id: int) -> None:
    profile = get_or_create_profile(db, user_id)
    exp = db.query(Experience).filter(Experience.id == experience_id, Experience.profile_id == profile.id).first()
    if not exp:
        raise AppError("Experience entry not found.", 404)
    db.delete(exp)
    db.commit()


# Project CRUD
def add_project(db: Session, user_id: int, payload: ProjectCreate) -> Project:
    profile = get_or_create_profile(db, user_id)
    proj = Project(
        profile_id=profile.id,
        title=payload.title,
        role_title=payload.role_title,
        url=payload.url,
        repo_url=payload.repo_url,
        start_date=payload.start_date,
        end_date=payload.end_date,
        description=payload.description,
        bullet_points=payload.bullet_points,
        technologies=payload.technologies,
        order_index=payload.order_index,
    )
    db.add(proj)
    db.commit()
    db.refresh(proj)
    profile.completeness_score = calculate_completeness(profile)
    db.commit()
    return proj


def update_project(db: Session, user_id: int, project_id: int, payload: ProjectUpdate) -> Project:
    profile = get_or_create_profile(db, user_id)
    proj = db.query(Project).filter(Project.id == project_id, Project.profile_id == profile.id).first()
    if not proj:
        raise AppError("Project entry not found.", 404)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(proj, field, value)
    db.commit()
    db.refresh(proj)
    return proj


def delete_project(db: Session, user_id: int, project_id: int) -> None:
    profile = get_or_create_profile(db, user_id)
    proj = db.query(Project).filter(Project.id == project_id, Project.profile_id == profile.id).first()
    if not proj:
        raise AppError("Project entry not found.", 404)
    db.delete(proj)
    db.commit()


# Education CRUD
def add_education(db: Session, user_id: int, payload: EducationCreate) -> Education:
    profile = get_or_create_profile(db, user_id)
    edu = Education(
        profile_id=profile.id,
        institution=payload.institution,
        degree=payload.degree,
        field_of_study=payload.field_of_study,
        start_date=payload.start_date,
        end_date=payload.end_date,
        grade=payload.grade,
        activities_societies=payload.activities_societies,
        order_index=payload.order_index,
    )
    db.add(edu)
    db.commit()
    db.refresh(edu)
    profile.completeness_score = calculate_completeness(profile)
    db.commit()
    return edu


def delete_education(db: Session, user_id: int, education_id: int) -> None:
    profile = get_or_create_profile(db, user_id)
    edu = db.query(Education).filter(Education.id == education_id, Education.profile_id == profile.id).first()
    if not edu:
        raise AppError("Education entry not found.", 404)
    db.delete(edu)
    db.commit()


# Skill CRUD
def add_skill(db: Session, user_id: int, payload: SkillCreate) -> Skill:
    profile = get_or_create_profile(db, user_id)
    # Check if skill already exists in profile
    existing = db.query(Skill).filter(Skill.profile_id == profile.id, Skill.name.ilike(payload.name.strip())).first()
    if existing:
        return existing
    skill = Skill(
        profile_id=profile.id,
        name=payload.name.strip(),
        category=payload.category,
        proficiency=payload.proficiency,
        years_of_experience=payload.years_of_experience,
        is_top_skill=payload.is_top_skill,
        order_index=payload.order_index,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


def delete_skill(db: Session, user_id: int, skill_id: int) -> None:
    profile = get_or_create_profile(db, user_id)
    skill = db.query(Skill).filter(Skill.id == skill_id, Skill.profile_id == profile.id).first()
    if not skill:
        raise AppError("Skill not found.", 404)
    db.delete(skill)
    db.commit()


# Certification CRUD
def add_certification(db: Session, user_id: int, payload: CertificationCreate) -> Certification:
    profile = get_or_create_profile(db, user_id)
    cert = Certification(
        profile_id=profile.id,
        name=payload.name.strip(),
        issuer=payload.issuer.strip(),
        issue_date=payload.issue_date,
        expiration_date=payload.expiration_date,
        credential_id=payload.credential_id,
        credential_url=payload.credential_url,
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)
    return cert


def delete_certification(db: Session, user_id: int, cert_id: int) -> None:
    profile = get_or_create_profile(db, user_id)
    cert = db.query(Certification).filter(Certification.id == cert_id, Certification.profile_id == profile.id).first()
    if not cert:
        raise AppError("Certification not found.", 404)
    db.delete(cert)
    db.commit()


# Resume Import & Parsing into Human-Reviewable Draft
def parse_resume_to_draft_profile(raw_text: str) -> ProfileImportDraft:
    draft = ProfileImportDraft(extracted_text_preview=raw_text[:500].strip())

    # Extract Phone
    phone_match = re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", raw_text)
    if phone_match:
        draft.phone = phone_match.group(0).strip()

    # Extract LinkedIn & GitHub
    linkedin_match = re.search(r"(https?://)?(www\.)?linkedin\.com/in/[\w-]+", raw_text, re.IGNORECASE)
    if linkedin_match:
        draft.linkedin_url = linkedin_match.group(0).strip()

    github_match = re.search(r"(https?://)?(www\.)?github\.com/[\w-]+", raw_text, re.IGNORECASE)
    if github_match:
        draft.github_url = github_match.group(0).strip()

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if lines:
        draft.headline = lines[0][:150]

    # Section keyword detection
    sections: dict[str, list[str]] = {"experience": [], "education": [], "skills": [], "projects": []}
    current_sec = "summary"
    summary_lines = []

    for line in lines[1:]:
        lower = line.lower()
        if any(h in lower for h in ["experience", "employment", "work history"]):
            current_sec = "experience"
            continue
        elif any(h in lower for h in ["education", "academic", "qualifications"]):
            current_sec = "education"
            continue
        elif any(h in lower for h in ["skills", "technologies", "tech stack", "competencies"]):
            current_sec = "skills"
            continue
        elif any(h in lower for h in ["projects", "personal projects", "academic projects"]):
            current_sec = "projects"
            continue

        if current_sec == "summary" and len(summary_lines) < 5:
            summary_lines.append(line)
        elif current_sec in sections:
            sections[current_sec].append(line)

    if summary_lines:
        draft.summary = " ".join(summary_lines)[:1000]

    # Parse Skills
    found_skills = set()
    for sline in sections["skills"]:
        parts = re.split(r"[,|•·\n]", sline)
        for part in parts:
            clean = part.strip()
            if 2 <= len(clean) <= 40 and not any(k in clean.lower() for k in ["skill", "proficient", "advanced"]):
                found_skills.add(clean)

    for idx, sk in enumerate(list(found_skills)[:25]):
        draft.skills.append(SkillCreate(name=sk, category="technical", order_index=idx))

    # Parse Experience blocks
    exp_lines = sections["experience"]
    if exp_lines:
        current_exp = None
        for el in exp_lines:
            if el.startswith(("-", "•", "*", "–")):
                bullet = el.lstrip("-•*– ").strip()
                if current_exp and len(bullet) > 10:
                    current_exp.bullet_points.append(bullet)
            else:
                # Treat as potential company/title line
                if not current_exp:
                    current_exp = ExperienceCreate(
                        company=el[:100],
                        role_title="Software Engineer" if "engineer" in el.lower() else el[:100],
                        start_date="2023",
                        end_date="Present",
                    )
                elif len(current_exp.bullet_points) >= 1:
                    draft.experiences.append(current_exp)
                    current_exp = ExperienceCreate(
                        company=el[:100],
                        role_title=el[:100],
                        start_date="2022",
                        end_date="2023",
                    )
        if current_exp:
            draft.experiences.append(current_exp)

    # Parse Education blocks
    edu_lines = sections["education"]
    if edu_lines:
        edu_item = EducationCreate(
            institution=edu_lines[0][:150],
            degree="Bachelor of Technology" if "tech" in " ".join(edu_lines).lower() else "Bachelor's Degree",
            start_date="2020",
            end_date="2024",
        )
        draft.education.append(edu_item)

    return draft


def commit_reviewed_profile(db: Session, user_id: int, draft: ProfileImportDraft) -> Profile:
    profile = get_or_create_profile(db, user_id)
    if draft.headline:
        profile.headline = draft.headline
    if draft.summary:
        profile.summary = draft.summary
    if draft.phone:
        profile.phone = draft.phone
    if draft.location:
        profile.location = draft.location
    if draft.linkedin_url:
        profile.linkedin_url = draft.linkedin_url
    if draft.github_url:
        profile.github_url = draft.github_url

    # Save experiences
    for exp_data in draft.experiences:
        db.add(Experience(
            profile_id=profile.id,
            company=exp_data.company,
            role_title=exp_data.role_title,
            location=exp_data.location,
            employment_type=exp_data.employment_type,
            start_date=exp_data.start_date,
            end_date=exp_data.end_date,
            is_current=exp_data.is_current,
            description=exp_data.description,
            bullet_points=exp_data.bullet_points,
            technologies_used=exp_data.technologies_used,
            order_index=exp_data.order_index,
        ))

    # Save projects
    for proj_data in draft.projects:
        db.add(Project(
            profile_id=profile.id,
            title=proj_data.title,
            role_title=proj_data.role_title,
            url=proj_data.url,
            repo_url=proj_data.repo_url,
            start_date=proj_data.start_date,
            end_date=proj_data.end_date,
            description=proj_data.description,
            bullet_points=proj_data.bullet_points,
            technologies=proj_data.technologies,
            order_index=proj_data.order_index,
        ))

    # Save education
    for edu_data in draft.education:
        db.add(Education(
            profile_id=profile.id,
            institution=edu_data.institution,
            degree=edu_data.degree,
            field_of_study=edu_data.field_of_study,
            start_date=edu_data.start_date,
            end_date=edu_data.end_date,
            grade=edu_data.grade,
            activities_societies=edu_data.activities_societies,
            order_index=edu_data.order_index,
        ))

    # Save skills
    for skill_data in draft.skills:
        existing = db.query(Skill).filter(Skill.profile_id == profile.id, Skill.name.ilike(skill_data.name)).first()
        if not existing:
            db.add(Skill(
                profile_id=profile.id,
                name=skill_data.name,
                category=skill_data.category,
                proficiency=skill_data.proficiency,
                years_of_experience=skill_data.years_of_experience,
                is_top_skill=skill_data.is_top_skill,
                order_index=skill_data.order_index,
            ))

    db.commit()
    db.refresh(profile)
    profile.completeness_score = calculate_completeness(profile)
    db.commit()
    db.refresh(profile)
    return profile

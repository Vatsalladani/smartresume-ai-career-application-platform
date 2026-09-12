"""Add Master Profile, Evidence Mapping, Job Fit, Payment Events, and Usage Counters.

Revision ID: 0002_master_profile_and_evidence
Revises: 0001_initial
Create Date: 2026-09-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_master_profile_and_evidence"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Payment Events for Webhook Idempotency
    op.create_table(
        "payment_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="razorpay"),
        sa.Column("event_id", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("provider", "event_id", name="uq_payment_events_provider_event_id"),
    )
    op.create_index("ix_payment_events_event_id", "payment_events", ["event_id"])

    # 2. Master Profile
    op.create_table(
        "profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("headline", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("phone", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("location", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("website_url", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("linkedin_url", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("github_url", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("completeness_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_profiles_user_id", "profiles", ["user_id"], unique=True)

    # 3. Experiences
    op.create_table(
        "experiences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company", sa.String(length=150), nullable=False),
        sa.Column("role_title", sa.String(length=150), nullable=False),
        sa.Column("location", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("employment_type", sa.String(length=50), nullable=False, server_default="Full-time"),
        sa.Column("start_date", sa.String(length=30), nullable=False),
        sa.Column("end_date", sa.String(length=30), nullable=False, server_default="Present"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("bullet_points", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("technologies_used", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_experiences_profile_id", "experiences", ["profile_id"])

    # 4. Projects
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("role_title", sa.String(length=150), nullable=False, server_default=""),
        sa.Column("url", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("repo_url", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("start_date", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("end_date", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("bullet_points", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("technologies", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_projects_profile_id", "projects", ["profile_id"])

    # 5. Education
    op.create_table(
        "education",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("institution", sa.String(length=200), nullable=False),
        sa.Column("degree", sa.String(length=150), nullable=False),
        sa.Column("field_of_study", sa.String(length=150), nullable=False, server_default=""),
        sa.Column("start_date", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("end_date", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("grade", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("activities_societies", sa.Text(), nullable=False, server_default=""),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_education_profile_id", "education", ["profile_id"])

    # 6. Skills
    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False, server_default="technical"),
        sa.Column("proficiency", sa.String(length=30), nullable=False, server_default="Intermediate"),
        sa.Column("years_of_experience", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_top_skill", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_skills_profile_id", "skills", ["profile_id"])
    op.create_index("ix_skills_name", "skills", ["name"])

    # 7. Certifications
    op.create_table(
        "certifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("issuer", sa.String(length=150), nullable=False),
        sa.Column("issue_date", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("expiration_date", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("credential_id", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("credential_url", sa.String(length=255), nullable=False, server_default=""),
    )
    op.create_index("ix_certifications_profile_id", "certifications", ["profile_id"])

    # 8. Job Postings
    op.create_table(
        "job_postings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("company", sa.String(length=150), nullable=False),
        sa.Column("location", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("job_url", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("raw_description", sa.Text(), nullable=False),
        sa.Column("parsed_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_job_postings_user_id", "job_postings", ["user_id"])

    # 9. Job Requirements
    op.create_table(
        "job_requirements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requirement_text", sa.Text(), nullable=False),
        sa.Column("importance", sa.String(length=20), nullable=False, server_default="MUST_HAVE"),
        sa.Column("category", sa.String(length=50), nullable=False, server_default="skill"),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_job_requirements_job_id", "job_requirements", ["job_id"])

    # 10. Evidence Links
    op.create_table(
        "evidence_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requirement_id", sa.Integer(), sa.ForeignKey("job_requirements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="UNCLEAR"),
        sa.Column("evidence_type", sa.String(length=50), nullable=False, server_default="experience"),
        sa.Column("evidence_id", sa.Integer(), nullable=True),
        sa.Column("evidence_quote", sa.Text(), nullable=False, server_default=""),
        sa.Column("gap_explanation", sa.Text(), nullable=False, server_default=""),
        sa.Column("user_actionable_hint", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_evidence_links_job_id", "evidence_links", ["job_id"])
    op.create_index("ix_evidence_links_requirement_id", "evidence_links", ["requirement_id"])

    # 11. Application Versions
    op.create_table(
        "application_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("template_name", sa.String(length=50), nullable=False, server_default="classic_ats"),
        sa.Column("content_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("diff_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("ats_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_immutable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("changelog", sa.String(length=255), nullable=False, server_default="Initial tailoring"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("job_id", "version_number", name="uq_app_version_job_version"),
    )
    op.create_index("ix_application_versions_job_id", "application_versions", ["job_id"])

    # 12. ATS Checks
    op.create_table(
        "ats_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version_id", sa.Integer(), sa.ForeignKey("application_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("format_health_score", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("keyword_coverage_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("evidence_match_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_quality_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("application_fit_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("readiness_level", sa.String(length=30), nullable=False, server_default="READY"),
        sa.Column("detailed_report", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ats_checks_version_id", "ats_checks", ["version_id"])

    # 13. Usage Counters
    op.create_table(
        "usage_counters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_month", sa.String(length=7), nullable=False),
        sa.Column("fit_analyses_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tailored_versions_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("exports_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("extra_credits_available", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("user_id", "period_month", name="uq_user_usage_period"),
    )
    op.create_index("ix_usage_counters_user_id", "usage_counters", ["user_id"])


def downgrade() -> None:
    op.drop_table("usage_counters")
    op.drop_table("ats_checks")
    op.drop_table("application_versions")
    op.drop_table("evidence_links")
    op.drop_table("job_requirements")
    op.drop_table("job_postings")
    op.drop_table("certifications")
    op.drop_table("skills")
    op.drop_table("education")
    op.drop_table("projects")
    op.drop_table("experiences")
    op.drop_table("profiles")
    op.drop_table("payment_events")

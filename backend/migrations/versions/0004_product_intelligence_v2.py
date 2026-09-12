"""Product Intelligence V2: Career Level, Domains, Evidence Graph, and Readiness Schema

Revision ID: 0004_product_intelligence_v2
Revises: 0003_application_links
Create Date: 2026-09-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_product_intelligence_v2"
down_revision = "0003_application_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Profiles additions
    op.add_column("profiles", sa.Column("target_domain", sa.String(100), nullable=False, server_default="Software Engineering"))
    op.add_column("profiles", sa.Column("career_level", sa.String(50), nullable=False, server_default="DEVELOPING_PROFESSIONAL"))
    op.add_column("profiles", sa.Column("target_geography", sa.String(100), nullable=False, server_default=""))
    op.add_column("profiles", sa.Column("preferred_industries", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("profiles", sa.Column("health_report", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("profiles", sa.Column("consistency_graph", sa.JSON(), nullable=False, server_default="{}"))

    # 2. Skills additions
    op.add_column("skills", sa.Column("evidence_status", sa.String(30), nullable=False, server_default="UNSUPPORTED"))
    op.add_column("skills", sa.Column("evidence_notes", sa.Text(), nullable=False, server_default=""))
    op.add_column("skills", sa.Column("relevance_status", sa.String(30), nullable=False, server_default="KEEP"))
    op.add_column("skills", sa.Column("relevance_reason", sa.Text(), nullable=False, server_default=""))

    # 3. Job postings additions
    op.add_column("job_postings", sa.Column("target_domain", sa.String(100), nullable=False, server_default=""))
    op.add_column("job_postings", sa.Column("career_level", sa.String(50), nullable=False, server_default=""))
    op.add_column("job_postings", sa.Column("parsed_schema", sa.JSON(), nullable=False, server_default="{}"))

    # 4. Evidence links additions
    op.add_column("evidence_links", sa.Column("why_it_matters", sa.Text(), nullable=False, server_default=""))
    op.add_column("evidence_links", sa.Column("learning_suggestion", sa.Text(), nullable=False, server_default=""))
    op.add_column("evidence_links", sa.Column("suggested_project", sa.Text(), nullable=False, server_default=""))

    # 5. Application versions additions
    op.add_column("application_versions", sa.Column("readiness_report", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("application_versions", sa.Column("consistency_warnings", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    op.drop_column("application_versions", "consistency_warnings")
    op.drop_column("application_versions", "readiness_report")

    op.drop_column("evidence_links", "suggested_project")
    op.drop_column("evidence_links", "learning_suggestion")
    op.drop_column("evidence_links", "why_it_matters")

    op.drop_column("job_postings", "parsed_schema")
    op.drop_column("job_postings", "career_level")
    op.drop_column("job_postings", "target_domain")

    op.drop_column("skills", "relevance_reason")
    op.drop_column("skills", "relevance_status")
    op.drop_column("skills", "evidence_notes")
    op.drop_column("skills", "evidence_status")

    op.drop_column("profiles", "consistency_graph")
    op.drop_column("profiles", "health_report")
    op.drop_column("profiles", "preferred_industries")
    op.drop_column("profiles", "target_geography")
    op.drop_column("profiles", "career_level")
    op.drop_column("profiles", "target_domain")

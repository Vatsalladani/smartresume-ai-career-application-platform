CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'USER',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    verification_token_hash VARCHAR(128),
    verification_token_expires TIMESTAMP,
    reset_token_hash VARCHAR(128),
    reset_token_expires TIMESTAMP,
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_name VARCHAR(50) NOT NULL DEFAULT 'FREE',
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    razorpay_payment_id VARCHAR(100),
    starts_at TIMESTAMP,
    expires_at TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS resumes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL DEFAULT 'My Resume',
    raw_text TEXT NOT NULL,
    parsed_content JSONB NOT NULL DEFAULT '{}'::jsonb,
    ats_score INTEGER NOT NULL DEFAULT 0,
    completeness_score INTEGER NOT NULL DEFAULT 0,
    public_share_token VARCHAR(64) UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS resume_versions (
    id SERIAL PRIMARY KEY,
    resume_id INTEGER NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    source_text TEXT NOT NULL,
    content JSONB NOT NULL DEFAULT '{}'::jsonb,
    analysis_snapshot JSONB,
    changelog VARCHAR(255) NOT NULL DEFAULT 'Saved version',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (resume_id, version_number)
);

CREATE TABLE IF NOT EXISTS ats_analyses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resume_id INTEGER REFERENCES resumes(id) ON DELETE SET NULL,
    job_title VARCHAR(150),
    job_description TEXT NOT NULL,
    original_score INTEGER NOT NULL DEFAULT 0,
    predicted_ats_score INTEGER NOT NULL DEFAULT 0,
    confidence_score INTEGER NOT NULL DEFAULT 70,
    keyword_report JSONB NOT NULL DEFAULT '{}'::jsonb,
    suggestions JSONB NOT NULL DEFAULT '{}'::jsonb,
    enhanced_content JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS job_applications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resume_id INTEGER REFERENCES resumes(id) ON DELETE SET NULL,
    job_posting_id INTEGER REFERENCES job_postings(id) ON DELETE SET NULL,
    version_id INTEGER REFERENCES application_versions(id) ON DELETE SET NULL,
    company VARCHAR(150) NOT NULL,
    job_title VARCHAR(150) NOT NULL,
    job_url VARCHAR(500),
    job_description TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'SAVED',
    notes TEXT,
    next_action VARCHAR(150),
    next_action_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    jti VARCHAR(64) UNIQUE NOT NULL,
    token_hash VARCHAR(128) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP,
    replaced_by_jti VARCHAR(64),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS token_blacklist (
    id SERIAL PRIMARY KEY,
    jti VARCHAR(64) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(80) NOT NULL,
    entity_type VARCHAR(80),
    entity_id VARCHAR(80),
    ip_address VARCHAR(80),
    user_agent VARCHAR(300),
    metadata_json JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_status ON subscriptions(user_id, status);
CREATE INDEX IF NOT EXISTS idx_resumes_user_id ON resumes(user_id);
CREATE INDEX IF NOT EXISTS idx_resume_versions_resume_version ON resume_versions(resume_id, version_number);
CREATE INDEX IF NOT EXISTS idx_ats_analyses_user_created ON ats_analyses(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_ats_analyses_resume_id ON ats_analyses(resume_id);
CREATE INDEX IF NOT EXISTS idx_job_applications_user_status ON job_applications(user_id, status);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_jti ON token_blacklist(jti);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_action ON audit_logs(user_id, action);

CREATE TABLE IF NOT EXISTS payment_events (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL DEFAULT 'razorpay',
    event_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(80) NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    payload_json JSONB,
    processed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (provider, event_id)
);

CREATE TABLE IF NOT EXISTS profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    headline VARCHAR(200) NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    phone VARCHAR(50) NOT NULL DEFAULT '',
    location VARCHAR(100) NOT NULL DEFAULT '',
    website_url VARCHAR(255) NOT NULL DEFAULT '',
    linkedin_url VARCHAR(255) NOT NULL DEFAULT '',
    github_url VARCHAR(255) NOT NULL DEFAULT '',
    completeness_score INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS experiences (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    company VARCHAR(150) NOT NULL,
    role_title VARCHAR(150) NOT NULL,
    location VARCHAR(100) NOT NULL DEFAULT '',
    employment_type VARCHAR(50) NOT NULL DEFAULT 'Full-time',
    start_date VARCHAR(30) NOT NULL,
    end_date VARCHAR(30) NOT NULL DEFAULT 'Present',
    is_current BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT NOT NULL DEFAULT '',
    bullet_points JSONB NOT NULL DEFAULT '[]'::jsonb,
    technologies_used JSONB NOT NULL DEFAULT '[]'::jsonb,
    order_index INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    role_title VARCHAR(150) NOT NULL DEFAULT '',
    url VARCHAR(255) NOT NULL DEFAULT '',
    repo_url VARCHAR(255) NOT NULL DEFAULT '',
    start_date VARCHAR(30) NOT NULL DEFAULT '',
    end_date VARCHAR(30) NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    bullet_points JSONB NOT NULL DEFAULT '[]'::jsonb,
    technologies JSONB NOT NULL DEFAULT '[]'::jsonb,
    order_index INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS education (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    institution VARCHAR(200) NOT NULL,
    degree VARCHAR(150) NOT NULL,
    field_of_study VARCHAR(150) NOT NULL DEFAULT '',
    start_date VARCHAR(30) NOT NULL DEFAULT '',
    end_date VARCHAR(30) NOT NULL DEFAULT '',
    grade VARCHAR(50) NOT NULL DEFAULT '',
    activities_societies TEXT NOT NULL DEFAULT '',
    order_index INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS skills (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'technical',
    proficiency VARCHAR(30) NOT NULL DEFAULT 'Intermediate',
    years_of_experience FLOAT NOT NULL DEFAULT 0,
    is_top_skill BOOLEAN NOT NULL DEFAULT FALSE,
    order_index INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS certifications (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    issuer VARCHAR(150) NOT NULL,
    issue_date VARCHAR(30) NOT NULL DEFAULT '',
    expiration_date VARCHAR(30) NOT NULL DEFAULT '',
    credential_id VARCHAR(100) NOT NULL DEFAULT '',
    credential_url VARCHAR(255) NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS job_postings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    company VARCHAR(150) NOT NULL,
    location VARCHAR(100) NOT NULL DEFAULT '',
    job_url VARCHAR(500) NOT NULL DEFAULT '',
    raw_description TEXT NOT NULL,
    parsed_summary TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS job_requirements (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES job_postings(id) ON DELETE CASCADE,
    requirement_text TEXT NOT NULL,
    importance VARCHAR(20) NOT NULL DEFAULT 'MUST_HAVE',
    category VARCHAR(50) NOT NULL DEFAULT 'skill',
    order_index INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS evidence_links (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES job_postings(id) ON DELETE CASCADE,
    requirement_id INTEGER NOT NULL REFERENCES job_requirements(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'UNCLEAR',
    evidence_type VARCHAR(50) NOT NULL DEFAULT 'experience',
    evidence_id INTEGER,
    evidence_quote TEXT NOT NULL DEFAULT '',
    gap_explanation TEXT NOT NULL DEFAULT '',
    user_actionable_hint TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS application_versions (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES job_postings(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    template_name VARCHAR(50) NOT NULL DEFAULT 'classic_ats',
    content_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    diff_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    ats_score INTEGER NOT NULL DEFAULT 0,
    is_immutable BOOLEAN NOT NULL DEFAULT TRUE,
    changelog VARCHAR(255) NOT NULL DEFAULT 'Initial tailoring',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (job_id, version_number)
);

CREATE TABLE IF NOT EXISTS ats_checks (
    id SERIAL PRIMARY KEY,
    version_id INTEGER NOT NULL REFERENCES application_versions(id) ON DELETE CASCADE,
    format_health_score INTEGER NOT NULL DEFAULT 100,
    keyword_coverage_score INTEGER NOT NULL DEFAULT 0,
    evidence_match_score INTEGER NOT NULL DEFAULT 0,
    content_quality_score INTEGER NOT NULL DEFAULT 0,
    application_fit_score INTEGER NOT NULL DEFAULT 0,
    readiness_level VARCHAR(30) NOT NULL DEFAULT 'READY',
    detailed_report JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS usage_counters (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    period_month VARCHAR(7) NOT NULL,
    fit_analyses_used INTEGER NOT NULL DEFAULT 0,
    tailored_versions_used INTEGER NOT NULL DEFAULT 0,
    exports_used INTEGER NOT NULL DEFAULT 0,
    extra_credits_available INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, period_month)
);

CREATE INDEX IF NOT EXISTS idx_payment_events_event_id ON payment_events(event_id);
CREATE INDEX IF NOT EXISTS idx_profiles_user_id ON profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_experiences_profile_id ON experiences(profile_id);
CREATE INDEX IF NOT EXISTS idx_projects_profile_id ON projects(profile_id);
CREATE INDEX IF NOT EXISTS idx_education_profile_id ON education(profile_id);
CREATE INDEX IF NOT EXISTS idx_skills_profile_id ON skills(profile_id);
CREATE INDEX IF NOT EXISTS idx_certifications_profile_id ON certifications(profile_id);
CREATE INDEX IF NOT EXISTS idx_job_postings_user_id ON job_postings(user_id);
CREATE INDEX IF NOT EXISTS idx_job_requirements_job_id ON job_requirements(job_id);
CREATE INDEX IF NOT EXISTS idx_evidence_links_job_id ON evidence_links(job_id);
CREATE INDEX IF NOT EXISTS idx_application_versions_job_id ON application_versions(job_id);
CREATE INDEX IF NOT EXISTS idx_ats_checks_version_id ON ats_checks(version_id);
CREATE INDEX IF NOT EXISTS idx_usage_counters_user_id ON usage_counters(user_id);

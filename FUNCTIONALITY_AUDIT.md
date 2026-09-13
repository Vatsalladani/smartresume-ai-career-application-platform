# SmartResume.ai — Master Functionality Audit Matrix

> **Audit Date:** September 13, 2026  
> **Repository:** `E:\RESUME SaaS ANTIGRAVITY`  
> **Environment Baseline:** FastAPI + PostgreSQL + SQLAlchemy + Alembic + Vanilla JS + HTML + CSS  
> **Total Automated Tests Passing:** 98 / 98 (backend test suite)  
> **Verification Standard:** Zero fake completion, zero ungrounded toasts, real DB persistence, exact configuration disclosures.

---

## 1. Audit Classification Legend

| Status | Definition |
| :--- | :--- |
| **`REAL + CONNECTED`** | Fully connected from UI → API → Database/Service → UI State with real persistence and verification. |
| **`PARTIALLY CONNECTED`** | Connected end-to-end, but has edge-case UI gaps, route parameter naming mismatches, or missing sub-views. |
| **`MOCKED/SIMULATED`** | Uses hardcoded mock/seed data, simulated loading labels, or in-memory stubs without actual persistence. |
| **`FRONTEND ONLY`** | UI exists in `index.html` / `app.js` with no corresponding backend API endpoint or service. |
| **`BACKEND ONLY`** | API endpoint and service exist in backend, but not connected to any UI trigger or handler in frontend. |
| **`CONFIGURATION PENDING`** | Full production code architecture implemented, waiting for real external API credentials (Gemini, Razorpay, Google, LinkedIn, SMTP). |
| **`BROKEN`** | UI trigger calls a mismatched or non-existent endpoint, throwing an HTTP 404/405/500 or uncaught JS error. |

---

## 2. Master Functionality Matrix

| FEATURE | UI ENTRY POINT | FRONTEND HANDLER | API ENDPOINT | BACKEND SERVICE | DATABASE DEPENDENCY | EXTERNAL SERVICE | CURRENT STATUS | MOCK/REAL | CONFIG REQUIRED | TEST STATUS | BROWSER TEST STATUS | BLOCKERS |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **User Registration** | `#authModal` (Register tab) | `handleRegisterSubmit()` in `app.js` | `POST /api/v1/auth/register` | `auth_service.register_user` | `User`, `Subscription` | SMTP (for email verification) | `REAL + CONNECTED` | Real | `SMTP_*` (optional for live email) | PASS (`test_security_phase1.py`) | PASS | None |
| **User Login** | `#authModal` (Login tab) | `handleLoginSubmit()` in `app.js` | `POST /api/v1/auth/login` | `auth_service.authenticate_user`, `create_session` | `User`, `RefreshToken` | None | `REAL + CONNECTED` | Real | None | PASS (`test_security_phase1.py`) | PASS | None |
| **Session Refresh** | Automatic on 401 via `api.js` | `API.request()` interceptor | `POST /api/v1/auth/refresh` | `auth_service.rotate_refresh_token` | `RefreshToken`, `User` | None | `REAL + CONNECTED` | Real | None | PASS (`test_security_phase1.py`) | PASS | None |
| **User Logout** | `#navLogoutBtn`, `#settingsLogoutBtn` | `handleLogout()` in `app.js` | `POST /api/v1/auth/logout` | `auth_service.blacklist_access_token`, `revoke_refresh_token` | `TokenBlacklist`, `RefreshToken`, `AuditLog` | None | `REAL + CONNECTED` | Real | None | PASS (`test_security_phase1.py`) | PASS | None |
| **Forgot Password** | `#authModal` (Forgot view) | `handleForgotSubmit()` in `app.js` | `POST /api/v1/auth/forgot-password` | `auth_service.create_password_reset` | `User` | SMTP | `PARTIALLY CONNECTED` | Real hash, email dispatch pending | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` | PASS | PASS | Real email dispatch pending SMTP service |
| **Reset Password** | `#authModal` (Reset view) | `handleResetSubmit()` in `app.js` | `POST /api/v1/auth/reset-password` | `auth_service.reset_password` | `User` | None | `REAL + CONNECTED` | Real | None | PASS (`test_security_phase1.py`) | PASS | None |
| **Email Verification** | `#authModal` (Verify view) | `handleVerifyEmailSubmit()` in `app.js` | `POST /api/v1/auth/verify-email` | `auth_service.verify_email` | `User`, `AuditLog` | None | `REAL + CONNECTED` | Real | None | PASS (`test_security_phase1.py`) | PASS | None |
| **Google Sign-In URL** | `#googleSignInBtn`, `#googleSignUpBtn` | `initiateOAuth('google')` | `GET /api/v1/auth/oauth/google/url` | `oauth_service.get_google_authorization_url` | None | Google Identity API | `CONFIGURATION PENDING` | Real Architecture | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` | PASS (`test_payments_and_oauth.py`) | Verified pending modal | Google credentials required |
| **Google Sign-In Callback** | URL redirect param `?code=...` | `handleOAuthCallback()` in `app.js` | `POST /api/v1/auth/oauth/google/callback` | `oauth_service.verify_google_oauth_code`, `auth_service.get_or_create_oauth_user` | `User`, `OAuthIdentity`, `AuditLog` | Google Token Endpoint | `CONFIGURATION PENDING` | Real Architecture | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | PASS (`test_payments_and_oauth.py`) | Verified pending modal | Google credentials required |
| **LinkedIn Sign-In URL** | `#linkedinSignInBtn`, `#linkedinSignUpBtn` | `initiateOAuth('linkedin')` | `GET /api/v1/auth/oauth/linkedin/url` | `oauth_service.get_linkedin_authorization_url` | None | LinkedIn OAuth / OIDC | `CONFIGURATION PENDING` | Real Architecture | `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, `LINKEDIN_REDIRECT_URI` | PASS (`test_payments_and_oauth.py`) | Verified pending modal | LinkedIn credentials required |
| **LinkedIn Sign-In Callback** | URL redirect param `?code=...` | `handleOAuthCallback()` in `app.js` | `POST /api/v1/auth/oauth/linkedin/callback` | `oauth_service.verify_linkedin_oauth_code`, `auth_service.get_or_create_oauth_user` | `User`, `OAuthIdentity`, `AuditLog` | LinkedIn Token & UserInfo | `CONFIGURATION PENDING` | Real Architecture | `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET` | PASS (`test_payments_and_oauth.py`) | Verified pending modal | LinkedIn credentials required |
| **OAuth Status Check** | App boot lifecycle | `loadOAuthStatus()` in `app.js` | `GET /api/v1/auth/oauth/config` | `oauth_service.get_oauth_config_status` | None | None | `REAL + CONNECTED` | Real | None | PASS (`test_payments_and_oauth.py`) | PASS | None |
| **User Profile Summary** | `#tabSettings` | `loadSettingsUser()` in `app.js` | `GET /api/v1/users/profile` | `users.py` router | `User` | None | `REAL + CONNECTED` | Real | None | PASS | PASS | None |
| **Update User Profile** | `#profileForm` | `handleUpdateProfileSubmit()` in `app.js` | `PATCH /api/v1/users/profile` | `users.py` router | `User` | None | `REAL + CONNECTED` | Real | None | PASS | PASS | None |
| **Change Password** | `#changePasswordForm` | `handleChangePasswordSubmit()` in `app.js` | `POST /api/v1/users/change-password` | `users.py` router | `User` | None | `REAL + CONNECTED` | Real | None | PASS (`test_password_validator.py`) | PASS | None |
| **Master Profile Load** | `#tabProfile` | `loadMasterProfile()` in `app.js` | `GET /api/v1/profile` | `profile_service.get_or_create_profile` | `Profile`, `Experience`, `Education`, `Skill`, `Project`, `Certification` | None | `REAL + CONNECTED` | Real | None | PASS (`test_master_profile.py`) | PASS | None |
| **Update Master Profile** | `#saveMasterContactBtn` | `handleSaveContact()` in `app.js` | `PUT /api/v1/profile` | `profile_service.update_contact_info` | `Profile` | None | `REAL + CONNECTED` | Real | None | PASS (`test_master_profile.py`) | PASS | None |
| **Add Work Experience** | `#addExperienceForm` | `handleSaveExperience()` in `app.js` | `POST /api/v1/profile/experiences` | `profile_service.create_experience` | `Experience` | None | `REAL + CONNECTED` | Real | None | PASS (`test_master_profile.py`) | PASS | None |
| **Edit Work Experience** | `#experienceItems` (Edit button) | `handleSaveExperience()` (PUT branch) | `PUT /api/v1/profile/experiences/{id}` | `profile_service.update_experience` | `Experience` | None | `REAL + CONNECTED` | Real | None | PASS (`test_master_profile.py`) | PASS | None |
| **Delete Work Experience** | `#experienceItems` (Delete button) | `handleDeleteExperience()` | `DELETE /api/v1/profile/experiences/{id}` | `profile_service.delete_experience` | `Experience` | None | `REAL + CONNECTED` | Real | None | PASS (`test_master_profile.py`) | PASS | None |
| **Add Education** | `#addEducationForm` | `handleSaveEducation()` in `app.js` | `POST /api/v1/profile/education` | `profile_service.create_education` | `Education` | None | `REAL + CONNECTED` | Real | None | PASS (`test_master_profile.py`) | PASS | None |
| **Delete Education** | `#educationItems` (Delete button) | `handleDeleteEducation()` | `DELETE /api/v1/profile/education/{id}` | `profile_service.delete_education` | `Education` | None | `REAL + CONNECTED` | Real | None | PASS (`test_master_profile.py`) | PASS | None |
| **Add Skill** | `#addSkillForm` | `handleSaveSkill()` in `app.js` | `POST /api/v1/profile/skills` | `profile_service.create_skill` | `Skill` | None | `REAL + CONNECTED` | Real | None | PASS (`test_master_profile.py`) | PASS | None |
| **Delete Skill** | `#skillsGrid` (Delete tag) | `handleDeleteSkill()` | `DELETE /api/v1/profile/skills/{id}` | `profile_service.delete_skill` | `Skill` | None | `REAL + CONNECTED` | Real | None | PASS (`test_master_profile.py`) | PASS | None |
| **Add Project** | `#addProjectForm` | `handleSaveProject()` in `app.js` | `POST /api/v1/profile/projects` | `profile_service.create_project` | `Project` | None | `REAL + CONNECTED` | Real | None | PASS (`test_master_profile.py`) | PASS | None |
| **Edit Project** | `#projectItems` (Edit button) | `handleSaveProject()` (PUT branch) | `PUT /api/v1/profile/projects/{id}` | `profile_service.update_project` | `Project` | None | `REAL + CONNECTED` | Real | None | PASS (`test_master_profile.py`) | PASS | None |
| **Delete Project** | `#projectItems` (Delete button) | `handleDeleteProject()` | `DELETE /api/v1/profile/projects/{id}` | `profile_service.delete_project` | `Project` | None | `REAL + CONNECTED` | Real | None | PASS (`test_master_profile.py`) | PASS | None |
| **Add Certification** | `#addCertificationForm` | `handleSaveCertification()` in `app.js` | `POST /api/v1/profile/certifications` | `profile_service.create_certification` | `Certification` | None | `REAL + CONNECTED` | Real | None | PASS (`test_master_profile.py`) | PASS | None |
| **Delete Certification** | `#certificationItems` (Delete button) | `handleDeleteCertification()` | `DELETE /api/v1/profile/certifications/{id}` | `profile_service.delete_certification` | `Certification` | None | `REAL + CONNECTED` | Real | None | PASS (`test_master_profile.py`) | PASS | None |
| **Resume Import (File/Text)** | `#importResumeBtn`, `#resumeImportModal` | `handleImportResume()` in `app.js` | `POST /api/v1/profile/import` (mismatched with `/parse-file`, `/parse-text` in UI) | `profile_service.parse_resume_to_draft_profile` | None | None | `BROKEN` (Endpoint mismatch) | Real parsing | None | PASS on `/import`, fails in UI | Blocked by UI path | Frontend calls `/parse-file`, `/parse-text`; backend has `/import` |
| **Commit Imported Resume** | `#commitImportBtn` | `handleCommitImport()` in `app.js` | `POST /api/v1/profile/import/commit` | `profile_service.commit_imported_draft` | `Profile`, `Experience`, `Skill`, etc. | None | `REAL + CONNECTED` | Real | None | PASS | PASS | Needs import fix |
| **Profile Health Report** | `#tabProfile`, Dashboard health score | `loadProfileHealth()` in `app.js` | `GET /api/v1/profile/health-report` | `intelligence_engine.calculate_resume_health` | `Profile` | None | `REAL + CONNECTED` | Real | None | PASS (`test_intelligence_v2.py`) | PASS | None |
| **Career Level Assessment** | `#assessCareerLevelBtn` | `handleAssessCareerLevel()` | `POST /api/v1/profile/career-level` | `intelligence_engine.assess_career_level` | `Profile` | None | `REAL + CONNECTED` | Real | None | PASS (`test_intelligence_v2.py`) | PASS | None |
| **Evidence Consistency Graph** | `#tabEvidenceVault` | `loadEvidenceConsistencyGraph()` | `GET /api/v1/profile/consistency` | `intelligence_engine.build_evidence_consistency_graph` | `Profile`, `EvidenceItem` | None | `REAL + CONNECTED` | Real | None | PASS (`test_intelligence_v2.py`) | PASS | None |
| **Content Relevance Check** | `#checkRelevanceBtn` | `handleCheckRelevance()` | `POST /api/v1/profile/relevance-check` | `intelligence_engine.evaluate_content_relevance` | `Profile` | None | `REAL + CONNECTED` | Real | None | PASS (`test_intelligence_v2.py`) | PASS | None |
| **Evidence Vault List** | `#tabEvidenceVault` | `loadEvidenceVault()` in `app.js` | `GET /api/v1/evidence-vault` | `evidence_vault_service.list_evidence` | `EvidenceItem` | None | `REAL + CONNECTED` | Real | None | PASS (`test_master_profile.py`) | PASS | None |
| **Add Evidence Item** | `#addEvidenceModal` | `handleSaveEvidenceItem()` | `POST /api/v1/evidence-vault` | `evidence_vault_service.create_evidence` | `EvidenceItem` | None | `REAL + CONNECTED` | Real | None | PASS (`test_master_profile.py`) | PASS | None |
| **Edit Evidence Item** | `#evidenceGrid` (Edit button) | `handleSaveEvidenceItem()` (PUT branch) | `PUT /api/v1/evidence-vault/{id}` | `evidence_vault_service.update_evidence` | `EvidenceItem` | None | `REAL + CONNECTED` | Real | None | PASS (`test_master_profile.py`) | PASS | None |
| **Delete Evidence Item** | `#evidenceGrid` (Delete button) | `handleDeleteEvidenceItem()` | `DELETE /api/v1/evidence-vault/{id}` | `evidence_vault_service.delete_evidence` | `EvidenceItem` | None | `REAL + CONNECTED` | Real | None | PASS (`test_master_profile.py`) | PASS | None |
| **Sync Evidence from Profile** | `#syncEvidenceBtn` | `handleSyncEvidence()` | `POST /api/v1/evidence-vault/sync` | `evidence_vault_service.sync_from_master_profile` | `EvidenceItem`, `Profile` | None | `REAL + CONNECTED` | Real | None | PASS (`test_master_profile.py`) | PASS | None |
| **Audit Statements (Anti-Fabrication)** | `#auditEvidenceBtn` | `handleAuditEvidence()` | `POST /api/v1/evidence-vault/audit` | `evidence_vault_service.audit_unverified_claims` | `EvidenceItem` | Gemini (fallback heuristic) | `REAL + CONNECTED` | Real | `GEMINI_API_KEY` (optional) | PASS | PASS | None |
| **Templates Catalog** | `#tabTemplates` | `loadTemplatesCatalog()` in `app.js` | `GET /api/v1/templates` | `template_service.list_templates` | None | None | `REAL + CONNECTED` | Real catalog (12 templates) | None | PASS (`test_templates_and_guidance.py`) | PASS | None |
| **Template AI Recommendation** | `#recHeroCard`, `#tabTemplates` | `loadTemplateRecommendation()` | `GET /api/v1/templates/recommend` | `template_service.recommend_template_for_user` | `Profile`, `JobPosting` | None | `REAL + CONNECTED` | Real logic | None | PASS (`test_templates_and_guidance.py`) | PASS | None |
| **Template Sample Preview** | `#templatePreviewModal` | `openTemplatePreview()` in `app.js` | `GET /api/v1/templates/{id}/sample` | `template_service.get_sample_data` | None | None | `REAL + CONNECTED` | Real sample data | None | PASS (`test_templates_and_guidance.py`) | PASS | Loading text previously had 'simulated' |
| **Template Pro Access Gate** | `#templateUpgradeModal` | `selectActiveTemplate()` | `GET /api/v1/payments/billing-summary` | `payment_service.get_billing_summary` | `Subscription` | None | `REAL + CONNECTED` | Real entitlement check | None | PASS (`test_templates_and_guidance.py`) | PASS | None |
| **Resume Builder Sync** | `#builderSyncProfileBtn` | `syncBuilderFromProfile()` in `app.js` | Client-side sync from cached `state.profile` | None | None | None | `REAL + CONNECTED` | Real | None | PASS | PASS | None |
| **Resume Builder Live Canvas** | Input fields in `#tabResumeBuilder` | `updateResumePreviewCanvasFromInputs()` | Client-side reactive rendering | None | None | None | `REAL + CONNECTED` | Real live canvas | None | PASS | PASS | None |
| **Resume Builder Save** | `#saveResumeBtn` | `handleSaveResume()` in `app.js` | `POST /api/v1/resumes` or `PATCH /api/v1/resumes/{id}` | `resume_service.save_resume` | `Resume`, `ResumeVersion` | None | `REAL + CONNECTED` | Real | None | PASS (`test_resume_export.py`) | PASS | None |
| **Resume Builder Versions** | `#resumeVersionsList` | `loadResumeVersions()` in `app.js` | `GET /api/v1/resumes/{id}/versions` | `resume_service.list_versions` | `ResumeVersion` | None | `REAL + CONNECTED` | Real | None | PASS (`test_resume_export.py`) | PASS | None |
| **Resume Version Restore** | `#restoreVersionBtn` | `handleRestoreVersion()` | `POST /api/v1/resumes/{id}/versions/{version_id}/restore` | `resume_service.restore_version` | `Resume`, `ResumeVersion` | None | `REAL + CONNECTED` | Real | None | PASS (`test_resume_export.py`) | PASS | None |
| **SmartBuild Bullet Synthesizer** | `#synthesizeBulletBtn` | `handleSynthesizeBullet()` | `POST /api/v1/smartbuild/synthesize-bullet` | `smartbuild_service.synthesize_star_bullet` | None | Gemini (fallback STAR) | `REAL + CONNECTED` | Real | `GEMINI_API_KEY` (optional) | PASS | PASS | None |
| **Country Rules Inspection** | `#countryRulesSelect` | `handleCountryRulesChange()` | `GET /api/v1/smartbuild/country-rules/{country}` | `international_rules.get_country_rules` | None | None | `REAL + CONNECTED` | Real | None | PASS (`test_templates_and_guidance.py`) | PASS | None |
| **Resume PDF Export** | `#builderExportPdfBtn` | `handleExportResume('pdf')` | `GET /api/v1/resumes/{id}/export?format=pdf` | `export_service.export_resume_to_pdf` | `Resume`, `Subscription`, `UsageCounter` | ReportLab | `REAL + CONNECTED` | Real PDF stream | None | PASS (`test_resume_export.py`) | PASS | Quota enforced |
| **Resume DOCX Export** | `#builderExportDocxBtn` | `handleExportResume('docx')` | `GET /api/v1/resumes/{id}/export?format=docx` | `export_service.export_resume_to_docx` | `Resume`, `Subscription`, `UsageCounter` | python-docx | `REAL + CONNECTED` | Real DOCX stream | None | PASS (`test_resume_export.py`) | PASS | Quota enforced |
| **Job Radar Discovery** | `#tabJobRadar`, `#searchRadarBtn` | `loadJobRadar()` in `app.js` | `GET /api/v1/job-radar` | `job_radar_service.search_job_radar` | `JobPosting`, `Profile` | Aggregator / Career pages | `MOCKED/SIMULATED` | Contains hardcoded seeds | Real Job Provider API credentials | PASS | PASS | Contains hardcoded `SEED_OPPORTUNITIES` to remove from normal view |
| **Create Target Job Posting** | `#createJobForm` | `handleCreateJob()` in `app.js` | `POST /api/v1/jobs` | `fit_service.create_job_posting` | `JobPosting`, `JobRequirement` | None | `REAL + CONNECTED` | Real | None | PASS (`test_fit_engine.py`) | PASS | None |
| **List User Jobs** | `#jobsList`, `#tabFit` | `loadJobs()` in `app.js` | `GET /api/v1/jobs` | `jobs.py` router | `JobPosting`, `JobRequirement` | None | `REAL + CONNECTED` | Real | None | PASS (`test_fit_engine.py`) | PASS | None |
| **Delete Target Job** | `#deleteJobBtn` | `handleDeleteJob()` in `app.js` | `DELETE /api/v1/jobs/{id}` | `jobs.py` router | `JobPosting` | None | `REAL + CONNECTED` | Real | None | PASS (`test_fit_engine.py`) | PASS | None |
| **Company Verification** | Job input on blur / verify btn | `verifyCompanyContext()` in `app.js` | `POST /api/v1/company/verify` | `company_verification_service.verify_company` | None | DNS / Web Verification | `REAL + CONNECTED` | Real DNS/domain checks | None | PASS (`test_company_verification.py`) | PASS | None |
| **Run ATS Fit Analysis** | `#runFitAnalysisBtn` | `handleRunFitAnalysis()` | `POST /api/v1/jobs/{id}/fit-analysis` | `fit_service.run_fit_analysis` | `EvidenceLink`, `JobPosting`, `Profile` | None | `REAL + CONNECTED` | Real match breakdown | None | PASS (`test_fit_engine.py`) | PASS | None |
| **Fetch Cached Fit Score** | `selectActiveJob()` in `app.js` | `API.request('/jobs/${id}/fit-score')` | `GET /api/v1/jobs/{id}/fit-score` (missing in backend) | None | `EvidenceLink` | None | `BROKEN` (Missing GET endpoint) | Mismatched | None | Fails in browser | Throws 404 in UI | Backend has no GET `/jobs/{id}/fit-score` |
| **Learning Gap Blueprint** | `#getLearningGapBtn` | `handleGetLearningGap()` | `GET /api/v1/jobs/{id}/learning-gap` | `intelligence_engine.generate_learning_gap_blueprint` | `JobPosting`, `Profile` | None | `REAL + CONNECTED` | Real | None | PASS (`test_intelligence_v2.py`) | PASS | None |
| **Job Readiness Score** | `#getReadinessBtn` | `handleGetJobReadiness()` | `GET /api/v1/jobs/{id}/readiness` | `intelligence_engine.calculate_job_readiness` | `JobPosting`, `Profile` | None | `REAL + CONNECTED` | Real | None | PASS (`test_intelligence_v2.py`) | PASS | None |
| **Generate Tailoring Proposal** | `#generateTailoringBtn` | `handleGenerateTailoring()` | `POST /api/v1/jobs/{id}/tailor-proposal` (mismatched with `/tailor` in backend) | `tailoring_service.generate_tailoring_proposal` | `JobPosting`, `Profile` | Gemini (fallback heuristic) | `BROKEN` (Endpoint mismatch) | Real proposal engine | `GEMINI_API_KEY` (optional) | PASS on `/tailor`, 404 on `/tailor-proposal` | Throws 404 | UI calls `/tailor-proposal`, backend route is `/tailor` |
| **Commit Tailored Version** | `#commitVersionBtn` | `handleCommitVersion()` | `POST /api/v1/jobs/{id}/versions` | `tailoring_service.create_immutable_version` | `ApplicationVersion` | None | `REAL + CONNECTED` | Real immutable snapshot | None | PASS (`test_tailoring_versions.py`) | PASS | None |
| **List Job Versions** | `#versionsList` | `loadJobVersions()` in `app.js` | `GET /api/v1/jobs/{id}/versions` | `tailoring_service.list_versions` | `ApplicationVersion` | None | `REAL + CONNECTED` | Real | None | PASS (`test_tailoring_versions.py`) | PASS | None |
| **Pre-Export Consistency Check** | `#downloadPdfBtn`, `#downloadDocxBtn` | `handleExportWithPreCheck()` | `POST /api/v1/jobs/{id}/versions/{version_id}/pre-export-check` | `intelligence_engine.validate_version_consistency` | `ApplicationVersion` | None | `REAL + CONNECTED` | Real verification | None | PASS (`test_intelligence_v2.py`) | PASS | None |
| **Export Tailored Version** | Export actions in Tailoring Studio | `API.request('/jobs/{id}/versions/{version_id}/export')` | `GET /api/v1/jobs/{id}/versions/{version_id}/export?format=pdf` | `export_service.export_version` | `ApplicationVersion`, `Subscription`, `UsageCounter` | ReportLab / docx | `REAL + CONNECTED` | Real file download | None | PASS (`test_resume_export.py`) | PASS | Quota enforced |
| **Generate Application Pack** | `#generateAppPackBtn` | `handleGenerateAppPack()` | `POST /api/v1/application-pack/generate` | `application_pack_service.generate_full_pack` | `ApplicationVersion` | Gemini (fallback template) | `REAL + CONNECTED` | Real pack synthesis | `GEMINI_API_KEY` (optional) | PASS (`test_career_and_application_os.py`) | PASS | None |
| **View Application Pack** | `#appPackModal` | `openApplicationPackModal()` | `GET /api/v1/application-pack/{version_id}` | `application_pack_service.get_pack` | `ApplicationVersion` | None | `REAL + CONNECTED` | Real | None | PASS (`test_career_and_application_os.py`) | PASS | None |
| **List Applications** | `#tabApplications` | `loadApplications()` in `app.js` | `GET /api/v1/applications` | `applications.py` router | `Application` | None | `REAL + CONNECTED` | Real | None | PASS (`test_applications.py`) | PASS | None |
| **Create Application** | `#addApplicationForm` | `handleCreateApplication()` | `POST /api/v1/applications` | `applications.py` router | `Application` | None | `REAL + CONNECTED` | Real | None | PASS (`test_applications.py`) | PASS | None |
| **Update Application Status** | Status dropdown in `#applicationsTable` | `handleUpdateAppStatus()` | `PATCH /api/v1/applications/{id}` | `applications.py` router | `Application` | None | `REAL + CONNECTED` | Real | None | PASS (`test_applications.py`) | PASS | None |
| **Delete Application** | Delete button in `#applicationsTable` | `handleDeleteApplication()` | `DELETE /api/v1/applications/{id}` | `applications.py` router | `Application` | None | `REAL + CONNECTED` | Real | None | PASS (`test_applications.py`) | PASS | None |
| **SmartApply Detect Job** | Extension on job page | `SmartResumeAPI.detectJob()` | `POST /api/v1/smartapply/detect-job` | `smartapply.py` router | None | None | `REAL + CONNECTED` | Real DOM heuristics | None | PASS | Extension QA | None |
| **SmartApply Field Answers** | Extension autofill trigger | `SmartResumeAPI.getFieldAnswers()` | `POST /api/v1/smartapply/field-answers` | `smartapply.py` router | `Profile`, `EvidenceItem` | None | `REAL + CONNECTED` | Real verified profile facts | None | PASS | Extension QA | None |
| **SmartApply Answer Generation** | Extension freeform question | `SmartResumeAPI.generatePortalAnswer()` | `POST /api/v1/smartapply/answer` | `ai_service.generate_cover_letter` | `Profile` | Gemini | `REAL + CONNECTED` | Real | `GEMINI_API_KEY` (optional) | PASS | Extension QA | None |
| **Claims to Defend Extraction** | `#tabInterview` | `loadClaimsToDefend()` in `app.js` | `GET /api/v1/interview/claims-to-defend` | `interview_service.get_claims_to_defend` | `Profile`, `EvidenceItem` | None | `REAL + CONNECTED` | Real extracted claims | None | PASS (`test_interview_copilot.py`) | PASS | None |
| **Start Text Interview** | `#startTextInterviewBtn` | `handleStartTextInterview()` | `POST /api/v1/interview/sessions` | `interview_service.create_interview_session` | `InterviewSession`, `InterviewTurn` | None | `REAL + CONNECTED` | Real adaptive session | None | PASS (`test_interview_copilot.py`) | PASS | None |
| **Submit Text Interview Turn** | `#interviewTurnForm` | Turn form listener in `app.js` | `POST /api/v1/interview/sessions/{id}/turns` | `interview_service.submit_interview_turn` | `InterviewSession`, `InterviewTurn` | Gemini (fallback STAR) | `REAL + CONNECTED` | Real 6-level progression | `GEMINI_API_KEY` (optional) | PASS (`test_interview_copilot.py`) | PASS | None |
| **Complete Interview & Review** | `#endInterviewBtn` | Complete listener in `app.js` | `POST /api/v1/interview/sessions/{id}/complete` | `interview_service.complete_interview_session` | `InterviewSession` | Gemini (fallback STAR evaluator) | `REAL + CONNECTED` | Real evidence-based scoring | `GEMINI_API_KEY` (optional) | PASS (`test_interview_copilot.py`) | PASS | None |
| **Gemini Live Config Check** | `#startLiveInterviewBtn` | `handleStartLiveInterview()` | `GET /api/v1/interview/live-config` | `interview.py` router | None | Gemini Live API | `CONFIGURATION PENDING` | Real config check | `GEMINI_API_KEY`, `GEMINI_LIVE_MODEL_NAME` | PASS (`test_interview_copilot.py`) | Verified Pending State | Key not supplied in environment |
| **Live Interview Room Media** | `#startLiveInterviewBtn` | `navigator.mediaDevices.getUserMedia` | None (Client hardware) | None | None | WebRTC / Audio-Video API | `REAL + CONNECTED` | Real MediaStream capture | Browser camera/mic permissions | N/A (Hardware) | PASS | Hardware permission dependent |
| **Live Interview Controls** | `#liveMicToggleBtn`, `#liveCameraToggleBtn`, `#liveEndBtn` | Dock button listeners in `app.js` | Client MediaStream + `complete` endpoint | `interview_service.complete_interview_session` | `InterviewSession` | None | `REAL + CONNECTED` | Real track mute/stop | None | PASS | PASS | None |
| **Career Insights Dashboard** | `#tabInsights` | `loadCareerInsights()` in `app.js` | `GET /api/v1/career-insights` | `career_insights_service.get_career_insights` | `Profile`, `JobPosting` | None | `REAL + CONNECTED` | Real skills demand matching | None | PASS (`test_career_and_application_os.py`) | PASS | None |
| **List Notifications** | `#notificationBellBtn`, `#notifFlyout` | `loadNotifications()` in `app.js` | `GET /api/v1/notifications` | `notification_service.list_user_notifications` | `Notification`, `Subscription`, `JobPosting` | None | `REAL + CONNECTED` | Real system events | None | PASS | PASS | None |
| **Mark Notification Read** | Notification item click | `handleMarkNotifRead()` | `POST /api/v1/notifications/{id}/read` | `notification_service.mark_read` | `Notification` | None | `REAL + CONNECTED` | Real | None | PASS | PASS | None |
| **Mark All Notifications Read** | `#markAllNotifsReadBtn` | `handleMarkAllNotifsRead()` | `POST /api/v1/notifications/read-all` | `notification_service.mark_all_read` | `Notification` | None | `REAL + CONNECTED` | Real | None | PASS | PASS | None |
| **Billing Pricing Tables** | `#tabBilling`, `#planCardsGrid` | `loadPricingTables()` in `app.js` | `GET /api/v1/payments/pricing` | `payment_service.get_pricing_tables` | None | None | `REAL + CONNECTED` | Real pricing tables | None | PASS (`test_subscription_lifecycle_and_ux.py`) | PASS | None |
| **Billing Summary** | `#tabBilling` (Pillars 1-6) | `loadBillingSummary()` in `app.js` | `GET /api/v1/payments/billing-summary` | `payment_service.get_billing_summary` | `Subscription`, `UsageCounter`, `PaymentEvent` | None | `REAL + CONNECTED` | Real 7-state lifecycle | None | PASS (`test_subscription_lifecycle_and_ux.py`) | PASS | None |
| **7-Day Pro Trial Start** | `#startTrialBtn` | `handleStartTrial()` in `app.js` | `POST /api/v1/payments/start-trial` | `payment_service.start_pro_trial` | `Subscription`, `AuditLog` | None | `REAL + CONNECTED` | Real trial provisioning | None | PASS (`test_subscription_lifecycle_and_ux.py`) | PASS | None |
| **Create Razorpay Order** | `#paySingleExportBtn`, `#payProMonthlyBtn` | `createRazorpayOrder()` in `app.js` | `POST /api/v1/payments/create-order` | `payment_service.create_order` | `PaymentEvent` | Razorpay Orders API | `REAL + CONNECTED` (Mock/Live switchable) | Real Razorpay SDK client / Mock mode | `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` | PASS (`test_subscription_lifecycle_and_ux.py`) | PASS | Real keys required for live merchant charge |
| **Verify Payment Signature** | Razorpay Checkout callback | `verifyRazorpayPayment()` in `app.js` | `POST /api/v1/payments/verify` | `payment_service.verify_payment` | `Subscription`, `UsageCounter`, `PaymentEvent` | Razorpay Signature Verification | `REAL + CONNECTED` | Real SHA256 HMAC verification | `RAZORPAY_KEY_SECRET` | PASS (`test_subscription_lifecycle_and_ux.py`) | PASS | None |
| **Cancel Subscription** | `#cancelSubscriptionBtn` | `handleCancelSubscription()` | `POST /api/v1/payments/cancel` | `payment_service.cancel_subscription` | `Subscription` | Razorpay Subscriptions API | `REAL + CONNECTED` | Real cancellation & access retention | None | PASS (`test_subscription_lifecycle_and_ux.py`) | PASS | Method-aware (Card vs UPI) |
| **Payment History & Receipts** | `#billingHistoryList` | `loadPaymentHistory()` in `app.js` | `GET /api/v1/payments/history` | `payment_service.get_payment_history` | `PaymentEvent` | None | `REAL + CONNECTED` | Real persisted invoices | None | PASS (`test_subscription_lifecycle_and_ux.py`) | PASS | None |
| **Razorpay Webhooks** | HTTP Webhook Delivery | `main.py` router | `POST /api/v1/payments/webhooks/razorpay` | `payment_service.process_webhook` | `Subscription`, `PaymentEvent`, `Notification` | Razorpay Webhooks | `REAL + CONNECTED` | Real HMAC signature validation | `RAZORPAY_WEBHOOK_SECRET` | PASS (`test_subscription_lifecycle_and_ux.py`) | PASS | None |
| **Public SEO Routes** | URL routing (`/resume-builder`, `/pricing`, etc.) | Backend static HTML route handlers | `GET /about`, `GET /pricing`, `GET /terms`, etc. | `main.py` SEO handlers | None | None | `REAL + CONNECTED` | Real HTML responses | None | PASS | PASS | None |

---

## 3. Summary of Discovered Blockers & Deviations

1. **Profile Resume Import Route Disconnect**:
   - **Frontend:** Calls `POST /profile/import/parse-file` (with FormData) and `POST /profile/import/parse-text` (with JSON).
   - **Backend:** Defines `POST /profile/import` (accepting `raw_text: str = Form("")` and `file: UploadFile = File(None)`).
   - **Fix:** Add route aliases or unify `/profile/import/parse-file` and `/profile/import/parse-text` in `backend/app/routers/profile.py` so both endpoints succeed cleanly.

2. **Job Fit Score Retrieval Route Disconnect**:
   - **Frontend:** When clicking an active job posting, calls `GET /jobs/{id}/fit-score` to retrieve cached fit analysis.
   - **Backend:** Only has `POST /jobs/{id}/fit-analysis`.
   - **Fix:** Add `GET /jobs/{id}/fit-score` in `backend/app/routers/jobs.py` that retrieves existing `requirements` and `evidence_links` to render instant fit status without requiring re-computation.

3. **Tailoring Proposal Route Disconnect**:
   - **Frontend:** Calls `POST /jobs/{id}/tailor-proposal`.
   - **Backend:** Has `POST /jobs/{id}/tailor`.
   - **Fix:** Add alias `@router.post("/{job_id}/tailor-proposal")` in `backend/app/routers/jobs.py` pointing to `tailor_for_job` or update frontend to use `/jobs/{id}/tailor`.

4. **Job Radar Hardcoded Seed Opportunities**:
   - **Current:** `job_radar_service.py` injects `SEED_OPPORTUNITIES` (5 hardcoded tech roles) into normal search results.
   - **Requirement (Section 35):** Remove hardcoded seeds from normal production display. Provide an honest provider abstraction for official job feeds / user-provided postings and clear empty states when external API credentials are pending.

5. **Template Preview Loading Label**:
   - **Current:** Displays "Rendering simulated ATS candidate layout...".
   - **Requirement (Section 15):** Replace with "Loading template preview..." to eliminate developer/simulation wording.

6. **Missing Config Parameters in `.env.example` & `config.py`**:
   - Pricing default mismatch in `config.py`: `PLAN_PRO_MONTHLY_PRICE_INR` defaulted to 79 instead of 49; `PLAN_PRO_ANNUAL_PRICE_INR` defaulted to 699 instead of 399.
   - Missing Razorpay Plan IDs: `RAZORPAY_MONTHLY_PLAN_ID`, `RAZORPAY_ANNUAL_PLAN_ID`.
   - Missing SMTP variables: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_TLS`.
   - Missing Gemini Live Model in `.env.example`: `GEMINI_LIVE_MODEL_NAME`.

---

## 4. Next Phase Action Plan

- **Phase 2:** Database & API Connectivity Hardening (Fix all 3 route mismatches, align `.env.example` and `config.py`).
- **Phase 3:** Authentication & Email Dispatch Service (Add SMTP integration with honest `CONFIGURATION_PENDING` fallback).
- **Phase 4:** Profile & Evidence Vault Completion.
- **Phase 5:** Templates & Resume Builder Polish.
- **Phase 6:** Gemini Standard AI Verification.
- **Phase 7:** Job Radar Real Data & Provider Abstraction (Remove seeds from normal view).
- **Phase 8:** Job Match & Readiness.
- **Phase 9:** Tailoring Studio & Application Pack.
- **Phase 10:** Application Tracker.
- **Phase 11:** Text Interview Engine.
- **Phase 12:** Gemini Live Interview.
- **Phase 13:** SmartApply Extension.
- **Phase 14:** Razorpay One-Time Payment.
- **Phase 15:** Subscriptions & Mandates.
- **Phase 16:** Notifications.
- **Phase 17:** SEO & Public Routes.
- **Phase 18:** Security Audit.
- **Phase 19:** Automated Test Suite.
- **Phase 20:** Browser End-to-End QA.
- **Phase 21:** Final Documentation & Credentials Handoff.

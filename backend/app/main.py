import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.middleware.security import RequestSizeLimitMiddleware, SecurityHeadersMiddleware, SimpleRateLimitMiddleware
from app.routers import (
    ai,
    application_pack,
    applications,
    auth,
    career_insights,
    company,
    evidence_vault,
    interview,
    job_radar,
    jobs,
    notifications,
    payments,
    profile,
    resumes,
    smartapply,
    smartbuild,
    templates,
    users,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

settings = get_settings()

app_title = (getattr(settings, "app_name", None) or "").strip() or "SmartResume.ai"

app = FastAPI(
    title=app_title,
    description="AI-powered ATS resume optimization, Career OS, Application OS, and Interview Copilot API.",
    version="2.0.0",
    debug=settings.debug,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(SimpleRateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(profile.router, prefix=settings.api_prefix)
app.include_router(evidence_vault.router, prefix=settings.api_prefix)
app.include_router(jobs.router, prefix=settings.api_prefix)
app.include_router(company.router, prefix=settings.api_prefix)
app.include_router(job_radar.router, prefix=settings.api_prefix)
app.include_router(resumes.router, prefix=settings.api_prefix)
app.include_router(ai.router, prefix=settings.api_prefix)
app.include_router(smartbuild.router, prefix=settings.api_prefix)
app.include_router(application_pack.router, prefix=settings.api_prefix)
app.include_router(applications.router, prefix=settings.api_prefix)
app.include_router(smartapply.router, prefix=settings.api_prefix)
app.include_router(interview.router, prefix=settings.api_prefix)
app.include_router(career_insights.router, prefix=settings.api_prefix)
app.include_router(notifications.router, prefix=settings.api_prefix)
app.include_router(payments.router, prefix=settings.api_prefix)
app.include_router(templates.router, prefix=settings.api_prefix)


@app.get("/health")
def health() -> dict:
    return {"success": True, "message": "OK", "data": {"service": app_title}}


# Mount frontend static assets and clean SEO routes
from pathlib import Path
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"

if frontend_dir.exists():
    @app.api_route("/robots.txt", methods=["GET", "HEAD"], include_in_schema=False)
    def get_robots_txt():
        robots_file = frontend_dir / "robots.txt"
        if robots_file.exists():
            return FileResponse(str(robots_file), media_type="text/plain")
        return Response("User-agent: *\nAllow: /\nDisallow: /api/\n", media_type="text/plain")

    @app.api_route("/sitemap.xml", methods=["GET", "HEAD"], include_in_schema=False)
    def get_sitemap_xml():
        sitemap_file = frontend_dir / "sitemap.xml"
        if sitemap_file.exists():
            return FileResponse(str(sitemap_file), media_type="application/xml")
        return Response("<urlset></urlset>", media_type="application/xml")

    # Clean SEO-friendly public pages
    seo_routes = {
        "/resume-builder": "resume-builder.html",
        "/resume-templates": "resume-templates.html",
        "/job-match": "job-match.html",
        "/interview-prep": "interview-prep.html",
        "/pricing": "pricing.html",
        "/about": "about.html",
        "/blog": "blog.html",
        "/contact": "contact.html",
        "/privacy": "privacy.html",
        "/terms": "terms.html",
        # Programmatic SEO entry paths
        "/ats-resume-checker": "job-match.html",
        "/resume-builder-for-engineers": "resume-builder.html",
        "/faang-resume-guide": "interview-prep.html",
    }

    for route_path, page_file in seo_routes.items():
        def _make_handler(target_file=page_file):
            def handler():
                fp = frontend_dir / target_file
                if fp.exists():
                    return FileResponse(str(fp), media_type="text/html")
                return FileResponse(str(frontend_dir / "index.html"), media_type="text/html")
            return handler
        app.add_api_route(route_path, _make_handler(page_file), methods=["GET", "HEAD"], include_in_schema=False)

    @app.api_route("/app", methods=["GET", "HEAD"], include_in_schema=False)
    def get_app_view():
        resp = FileResponse(str(frontend_dir / "index.html"), media_type="text/html")
        resp.headers["X-Robots-Tag"] = "noindex, nofollow"
        return resp

    if (frontend_dir / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")



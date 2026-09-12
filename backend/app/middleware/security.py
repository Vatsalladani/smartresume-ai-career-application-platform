import os
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from fastapi import Request, status
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.responses import error_response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        settings = get_settings()
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.max_request_size_bytes:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content=error_response("Request body is too large."),
            )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    _hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        settings = get_settings()
        if settings.environment == "test" or os.environ.get("TESTING") == "1":
            return await call_next(request)
        path = request.url.path
        if path in {"/health", "/docs", "/openapi.json", "/favicon.ico"}:
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        now = time.monotonic()

        # Categorize route for granular limits
        if "/auth/" in path:
            limit = settings.rate_limit_auth_requests
            window = settings.rate_limit_auth_window_seconds
            category = "auth"
        elif "/ai/" in path or "/jobs/" in path:
            limit = settings.rate_limit_ai_requests
            window = settings.rate_limit_ai_window_seconds
            category = "ai"
        else:
            limit = settings.rate_limit_requests
            window = settings.rate_limit_window_seconds
            category = "general"

        key = f"{client_host}:{category}:{path}"
        bucket = self._hits[key]

        while bucket and now - bucket[0] > window:
            bucket.popleft()

        if len(bucket) >= limit:
            retry_after = int(window - (now - bucket[0])) if bucket else window
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=error_response(f"Too many {category} requests. Please wait {max(1, retry_after)} seconds."),
                headers={"Retry-After": str(max(1, retry_after))},
            )

        bucket.append(now)
        return await call_next(request)

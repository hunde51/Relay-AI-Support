import logging
import time
import uuid
from collections import defaultdict
from typing import Callable, Dict

import jwt
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

EXCLUDED_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/metrics"}

logger = logging.getLogger("app.http")

try:
    import aioredis  # type: ignore
    _HAS_AIREDIS = True
except Exception:
    aioredis = None
    _HAS_AIREDIS = False


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        request.state.current_user = None

        auth = request.headers.get("authorization") or request.headers.get("Authorization")
        if auth and auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1]
            try:
                payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
                request.state.current_user = {
                    "auth_method": "jwt",
                    "user_id": payload.get("sub"),
                    "organization_id": payload.get("org"),
                    "role": payload.get("role"),
                }
            except Exception:
                request.state.current_user = None

        return await call_next(request)


class StructuredLogMiddleware(BaseHTTPMiddleware):
    """Structured request logging with request ID, duration, and auth context."""

    async def dispatch(self, request: Request, call_next: Callable):
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        start = time.monotonic()

        try:
            response = await call_next(request)
        except HTTPException as he:
            duration = time.monotonic() - start
            user = getattr(request.state, "current_user", None)
            logger.info(
                "request_id=%s method=%s path=%s status=%d duration=%.3f org=%s user=%s",
                request_id, request.method, request.url.path,
                he.status_code, duration,
                (user or {}).get("organization_id", "-"),
                (user or {}).get("user_id", "-"),
            )
            return JSONResponse(status_code=he.status_code, content={"error": he.detail})
        except Exception:
            duration = time.monotonic() - start
            user = getattr(request.state, "current_user", None)
            logger.exception(
                "request_id=%s method=%s path=%s status=500 duration=%.3f org=%s user=%s",
                request_id, request.method, request.url.path,
                duration,
                (user or {}).get("organization_id", "-"),
                (user or {}).get("user_id", "-"),
            )
            return JSONResponse(status_code=500, content={"error": "internal_server_error"})

        duration = time.monotonic() - start
        user = getattr(request.state, "current_user", None)
        logger.info(
            "request_id=%s method=%s path=%s status=%d duration=%.3f org=%s user=%s",
            request_id, request.method, request.url.path,
            response.status_code, duration,
            (user or {}).get("organization_id", "-"),
            (user or {}).get("user_id", "-"),
        )
        return response


class UsageTrackingMiddleware(BaseHTTPMiddleware):
    """Count API requests per organization for usage accounting.

    Must be registered *after* AuthMiddleware so that
    ``request.state.current_user`` is populated before we inspect it.
    Excludes health checks, docs, metrics, and OpenAPI schema paths.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        if request.url.path in EXCLUDED_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        user = getattr(request.state, "current_user", None)
        org_id = (user or {}).get("organization_id") if user else None
        if not org_id:
            return await call_next(request)

        response = await call_next(request)

        if response.status_code < 500:
            try:
                import asyncio
                from app.db.database import SessionLocal
                from app.services.usage_service import increment_api_requests

                async def _track():
                    async with SessionLocal() as db:
                        await increment_api_requests(db, str(org_id))
                        await db.commit()
                asyncio.create_task(_track())
            except Exception:
                logger.warning("Failed to track API usage for org=%s path=%s", org_id, request.url.path)

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Org-aware rate limiter with Redis-ready placeholder.

    Reads the per-org rate limit from organization_settings or plan defaults.
    Falls back to a global default when the org cannot be resolved.
    Note: In-memory limiter is suitable for single-process development only.
    For production, configure Redis and replace counters with a centralized store.
    """
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.default_max_requests = max_requests
        self.window = window_seconds
        self._buckets: Dict[str, list[float]] = defaultdict(list)
        self._rate_cache: Dict[str, int] = {}  # org_id -> max_requests, TTL 30s
        self._cache_time: Dict[str, float] = {}
        # Redis client if configured
        self._redis = None
        if _HAS_AIREDIS and settings.REDIS_URL:
            try:
                self._redis = aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
            except Exception:
                self._redis = None

    async def _get_org_limit(self, org_id: str) -> int:
        """Fetch the org's rate limit, cached for 30 seconds."""
        now = time.time()
        cached = self._rate_cache.get(org_id)
        cached_at = self._cache_time.get(org_id, 0)
        if cached is not None and now - cached_at < 30:
            return cached
        try:
            from app.db.database import SessionLocal
            from app.services.billing_service import get_org_rate_limit
            async with SessionLocal() as db:
                limit = await get_org_rate_limit(db, org_id)
            self._rate_cache[org_id] = limit
            self._cache_time[org_id] = now
            return limit
        except Exception:
            return self.default_max_requests

    async def dispatch(self, request: Request, call_next: Callable):
        if request.url.path in EXCLUDED_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        user = getattr(request.state, "current_user", None)
        org_id = (user or {}).get("organization_id") if user else None

        # Only rate-limit authenticated requests with an org_id
        if not org_id:
            return await call_next(request)

        ident = org_id
        max_req = await self._get_org_limit(org_id)

        # Redis-backed fixed-window counter
        if self._redis:
            try:
                current_window = int(time.time() // self.window)
                key = f"rl:{ident}:{current_window}"
                cnt = await self._redis.incr(key)
                if cnt == 1:
                    await self._redis.expire(key, int(self.window) + 1)
                if cnt > max_req:
                    return JSONResponse(status_code=429, content={"error": "rate_limit_exceeded", "limit": max_req, "window_seconds": self.window})
            except Exception:
                pass

        # fallback in-memory sliding window
        now = time.time()
        window_start = now - self.window
        bucket = self._buckets[ident]
        while bucket and bucket[0] < window_start:
            bucket.pop(0)
        if len(bucket) >= max_req:
            return JSONResponse(status_code=429, content={"error": "rate_limit_exceeded", "limit": max_req, "window_seconds": self.window})
        bucket.append(now)
        return await call_next(request)

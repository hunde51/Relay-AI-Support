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
    """Simple in-memory rate limiter with Redis-ready placeholder.

    Note: In-memory limiter is suitable for single-process development only.
    For production, configure Redis and replace counters with a centralized store.
    """
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window_seconds
        self._buckets: Dict[str, list[float]] = defaultdict(list)
        # Redis client if configured
        self._redis = None
        if _HAS_AIREDIS and settings.REDIS_URL:
            try:
                self._redis = aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
            except Exception:
                self._redis = None

    async def dispatch(self, request: Request, call_next: Callable):
        ident = request.client.host if request.client else "unknown"

        # Redis-backed fixed-window counter
        if self._redis:
            try:
                current_window = int(time.time() // self.window)
                key = f"rl:{ident}:{current_window}"
                cnt = await self._redis.incr(key)
                if cnt == 1:
                    # set expiry so key auto-expires after window
                    await self._redis.expire(key, int(self.window) + 1)
                if cnt > self.max_requests:
                    return JSONResponse(status_code=429, content={"error": "rate_limited"})
            except Exception:
                # on redis errors, fallback to in-memory
                pass

        # fallback in-memory sliding window
        now = time.time()
        window_start = now - self.window
        bucket = self._buckets[ident]
        # purge old
        while bucket and bucket[0] < window_start:
            bucket.pop(0)
        if len(bucket) >= self.max_requests:
            return JSONResponse(status_code=429, content={"error": "rate_limited"})
        bucket.append(now)
        return await call_next(request)

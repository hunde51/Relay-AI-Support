from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
from app.core.config import settings
import base64
import logging
from fastapi.responses import JSONResponse
from fastapi import HTTPException
import time
from collections import defaultdict
from typing import Dict
try:
    import jwt  # type: ignore
    _HAS_PYJWT = True
except Exception:
    jwt = None
    _HAS_PYJWT = False
try:
    import aioredis  # type: ignore
    _HAS_AIREDIS = True
except Exception:
    aioredis = None
    _HAS_AIREDIS = False


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        request.state.current_user = None

        # JWT auth (API key is resolved via dependency in each route)
        auth = request.headers.get("authorization") or request.headers.get("Authorization")
        if auth and auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1]
            try:
                if _HAS_PYJWT:
                    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
                    request.state.current_user = {
                        "auth_method": "jwt",
                        "user_id": payload.get("sub"),
                        "organization_id": payload.get("org"),
                        "role": payload.get("role"),
                    }
                else:
                    try:
                        raw = base64.urlsafe_b64decode(token.encode()).decode()
                        parts = raw.split(":")
                        request.state.current_user = {
                            "auth_method": "jwt",
                            "user_id": parts[0] if len(parts) > 0 else None,
                            "organization_id": parts[1] if len(parts) > 1 else None,
                            "role": parts[2] if len(parts) > 2 else None,
                        }
                    except Exception:
                        request.state.current_user = None
            except Exception:
                request.state.current_user = None

        return await call_next(request)


class StructuredErrorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        logger = logging.getLogger("app.middleware")
        logger.info("%s %s", request.method, request.url)
        try:
            response = await call_next(request)
            logger.info("%s %s -> %s", request.method, request.url, response.status_code)
            return response
        except HTTPException as he:
            return JSONResponse(status_code=he.status_code, content={"error": he.detail})
        except Exception as e:
            logger.exception("Unhandled exception processing request")
            return JSONResponse(status_code=500, content={"error": "internal_server_error"})


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

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
from app.core.config import settings
import base64
try:
    import jwt  # type: ignore
    _HAS_PYJWT = True
except Exception:
    jwt = None
    _HAS_PYJWT = False


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        # extract bearer token
        auth = request.headers.get("authorization") or request.headers.get("Authorization")
        request.state.current_user = None
        if auth and auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1]
            try:
                if _HAS_PYJWT:
                    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
                    request.state.current_user = {
                        "user_id": payload.get("sub"),
                        "organization_id": payload.get("org"),
                        "role": payload.get("role"),
                    }
                else:
                    # fallback parsing for dev: base64 encoded "user:org:role"
                    try:
                        raw = base64.urlsafe_b64decode(token.encode()).decode()
                        parts = raw.split(":")
                        request.state.current_user = {
                            "user_id": parts[0] if len(parts) > 0 else None,
                            "organization_id": parts[1] if len(parts) > 1 else None,
                            "role": parts[2] if len(parts) > 2 else None,
                        }
                    except Exception:
                        request.state.current_user = None
            except Exception:
                request.state.current_user = None

        response = await call_next(request)
        return response

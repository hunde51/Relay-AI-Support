from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import jwt
from app.core.config import settings


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        # extract bearer token
        auth = request.headers.get("authorization") or request.headers.get("Authorization")
        request.state.current_user = None
        if auth and auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1]
            try:
                payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
                # minimal user object
                request.state.current_user = {
                    "user_id": payload.get("sub"),
                    "organization_id": payload.get("org"),
                    "role": payload.get("role"),
                }
            except Exception:
                request.state.current_user = None

        response = await call_next(request)
        return response

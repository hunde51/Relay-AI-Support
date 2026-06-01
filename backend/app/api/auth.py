from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import base64
from app.core.config import settings

try:
    import jwt  # type: ignore
    _HAS_PYJWT = True
except Exception:
    jwt = None
    _HAS_PYJWT = False


def get_current_user(request: Request):
    user = getattr(request.state, "current_user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user


def optional_current_user(request: Request):
    return getattr(request.state, "current_user", None)


router = APIRouter(prefix="/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    organization_id: str
    role: str


class LoginRequest(BaseModel):
    user_id: str
    organization_id: str
    role: str


@router.post("/token", response_model=TokenResponse)
def issue_token(req: LoginRequest):
    # Issue a token; use PyJWT when available, otherwise use a simple base64 fallback for dev
    if _HAS_PYJWT:
        payload = {
            "sub": req.user_id,
            "org": req.organization_id,
            "role": req.role,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=8),
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    else:
        raw = f"{req.user_id}:{req.organization_id}:{req.role}"
        token = base64.urlsafe_b64encode(raw.encode()).decode()
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": req.user_id,
        "organization_id": req.organization_id,
        "role": req.role,
    }

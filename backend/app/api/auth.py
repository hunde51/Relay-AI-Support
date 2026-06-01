from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt
from app.core.config import settings
from fastapi import Request, Depends, HTTPException


def get_current_user(request: Request):
    user = getattr(request.state, "current_user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    user_id: str
    organization_id: str
    role: str


@router.post("/token", response_model=TokenResponse)
def issue_token(req: LoginRequest):
    # Simple token issuer for dev: signs user id, org id, role
    payload = {
        "sub": req.user_id,
        "org": req.organization_id,
        "role": req.role,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=8),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    return {"access_token": token, "token_type": "bearer"}

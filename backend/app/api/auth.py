from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta, timezone
import base64
import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.database import get_db
from app.models.org import OrganizationORM, UserORM, OrganizationSettingsORM, NotificationSettingsORM

try:
    import jwt  # type: ignore
    _HAS_PYJWT = True
except Exception:
    jwt = None
    _HAS_PYJWT = False

try:
    from passlib.context import CryptContext  # type: ignore
    _pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    _HAS_PASSLIB = True
except Exception:
    _pwd_ctx = None
    _HAS_PASSLIB = False


def _hash_password(password: str) -> str:
    if _HAS_PASSLIB:
        return _pwd_ctx.hash(password)
    # dev fallback — never use in production
    import hashlib
    return "plain:" + hashlib.sha256(password.encode()).hexdigest()


def _verify_password(plain: str, hashed: str) -> bool:
    if _HAS_PASSLIB and not hashed.startswith("plain:"):
        return _pwd_ctx.verify(plain, hashed)
    import hashlib
    return hashed == "plain:" + hashlib.sha256(plain.encode()).hexdigest()


def _make_jwt(user_id: str, org_id: str, role: str) -> str:
    if _HAS_PYJWT:
        payload = {
            "sub": user_id, "org": org_id, "role": role,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=8),
        }
        return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    raw = f"{user_id}:{org_id}:{role}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def get_current_user(request: Request):
    user = getattr(request.state, "current_user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user


def optional_current_user(request: Request):
    return getattr(request.state, "current_user", None)


router = APIRouter(tags=["auth"])


# ── Dev token endpoint (no DB needed) ─────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    organization_id: str
    role: str


class DevTokenRequest(BaseModel):
    user_id: str
    organization_id: str
    role: str


@router.post("/auth/token", response_model=TokenResponse)
def issue_token(req: DevTokenRequest):
    token = _make_jwt(req.user_id, req.organization_id, req.role)
    return {"access_token": token, "token_type": "bearer",
            "user_id": req.user_id, "organization_id": req.organization_id, "role": req.role}


# ── Real login ────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserORM).where(UserORM.email == req.email, UserORM.is_active == True))  # noqa: E712
    user = result.scalar_one_or_none()
    if not user or not user.password_hash or not _verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = _make_jwt(user.id, user.organization_id, user.role)
    return {"access_token": token, "token_type": "bearer",
            "user_id": user.id, "organization_id": user.organization_id, "role": user.role}


# ── Organization signup ───────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    org_name: str
    admin_email: str
    admin_name: str
    password: str


class SignupResponse(BaseModel):
    organization_id: str
    user_id: str
    access_token: str
    token_type: str = "bearer"


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:48] + "-" + base64.urlsafe_b64encode(name.encode())[:6].decode().lower()


@router.post("/organizations", status_code=201, response_model=SignupResponse)
async def signup(req: SignupRequest, db: AsyncSession = Depends(get_db)):
    # check email not already taken
    existing = await db.execute(select(UserORM).where(UserORM.email == req.admin_email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    from app.models.base import make_id
    org = OrganizationORM(name=req.org_name, slug=_slugify(req.org_name))
    db.add(org)
    await db.flush()

    user = UserORM(
        organization_id=org.id,
        name=req.admin_name,
        email=req.admin_email,
        role="admin",
        password_hash=_hash_password(req.password),
    )
    db.add(user)
    db.add(OrganizationSettingsORM(organization_id=org.id))
    db.add(NotificationSettingsORM(organization_id=org.id))
    await db.commit()

    token = _make_jwt(user.id, org.id, "admin")
    return {"organization_id": org.id, "user_id": user.id, "access_token": token, "token_type": "bearer"}

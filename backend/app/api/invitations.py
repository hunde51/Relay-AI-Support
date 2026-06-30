"""Invitation management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, _hash_password, _make_jwt
from app.db.database import get_db
from app.db.models import (
    InvitationORM,
    UserORM,
    OrganizationORM,
    make_id,
)
from app.services import invitation_service
from app.services.email_sender import send_invitation_email
from app.core.config import settings

router = APIRouter(prefix="/invitations", tags=["invitations"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class InviteCreateRequest(BaseModel):
    email: str
    role: str = "agent"


class InviteResponse(BaseModel):
    id: str
    email: str
    role: str
    status: str
    expires_at: str
    created_at: str


class InviteValidateResponse(BaseModel):
    valid: bool
    email: str | None = None
    organization_name: str | None = None
    role: str | None = None
    expires_at: str | None = None
    message: str | None = None


class InviteAcceptRequest(BaseModel):
    token: str
    name: str
    password: str


class InviteAcceptResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    organization_id: str
    role: str


# ── Helpers ────────────────────────────────────────────────────────────────────

def _require_admin(user: dict):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="admin role required")


def _require_admin_or_manager(user: dict):
    if user.get("role") not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="admin or manager role required")


def _invite_response(inv: InvitationORM) -> InviteResponse:
    return InviteResponse(
        id=inv.id,
        email=inv.email,
        role=inv.role,
        status=inv.status,
        expires_at=inv.expires_at.isoformat(),
        created_at=inv.created_at.isoformat(),
    )


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.get("")
async def list_invitations(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List pending invitations for the organization (admin/manager only)."""
    _require_admin_or_manager(current_user)
    org_id = current_user["organization_id"]
    invitations = await invitation_service.list_pending_invitations(db, org_id)
    return [_invite_response(i) for i in invitations]


@router.post("", status_code=201)
async def create_invitation(
    data: InviteCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Send an invitation to join the organization (admin/manager only)."""
    _require_admin_or_manager(current_user)
    org_id = current_user["organization_id"]
    user_id = current_user.get("user_id")

    try:
        invitation, plain_token = await invitation_service.create_invitation(
            db, org_id, data.email, data.role, invited_by_user_id=user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # Send invitation email (fire and forget on failure)
    org_result = await db.execute(select(OrganizationORM).where(OrganizationORM.id == org_id))
    org = org_result.scalar_one_or_none()
    inviter_result = await db.execute(select(UserORM).where(UserORM.id == user_id))
    inviter = inviter_result.scalar_one_or_none()

    org_name = org.name if org else "RelayAI"
    inviter_name = inviter.name if inviter else "An admin"
    send_invitation_email(
        to=data.email,
        org_name=org_name,
        inviter_name=inviter_name,
        role=data.role,
        plain_token=plain_token,
    )

    return _invite_response(invitation)


@router.delete("/{invitation_id}", status_code=204)
async def revoke_invitation(
    invitation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Revoke a pending invitation (admin only)."""
    _require_admin(current_user)
    org_id = current_user["organization_id"]
    ok = await invitation_service.revoke_invitation(db, invitation_id, org_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Invitation not found or already processed")


@router.get("/validate/{token}")
async def validate_invitation(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Validate an invitation token (public)."""
    invitation = await invitation_service.validate_invitation_token(db, token)
    if not invitation:
        return InviteValidateResponse(valid=False, message="Invalid or expired invitation token")

    org_result = await db.execute(
        select(OrganizationORM).where(OrganizationORM.id == invitation.organization_id)
    )
    org = org_result.scalar_one_or_none()

    return InviteValidateResponse(
        valid=True,
        email=invitation.email,
        organization_name=org.name if org else None,
        role=invitation.role,
        expires_at=invitation.expires_at.isoformat(),
        message="Invitation is valid",
    )


@router.post("/accept", response_model=InviteAcceptResponse)
async def accept_invitation(
    data: InviteAcceptRequest,
    db: AsyncSession = Depends(get_db),
):
    """Accept an invitation and create a user account (public)."""
    if len(data.password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters")

    password_hash = _hash_password(data.password)
    result = await invitation_service.accept_invitation(
        db, data.token, data.name.strip(), password_hash
    )
    if not result:
        raise HTTPException(status_code=400, detail="Invalid or expired invitation token")

    user, org_id = result
    token = _make_jwt(user.id, org_id, user.role)
    return InviteAcceptResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        organization_id=org_id,
        role=user.role,
    )


@router.get("/members")
async def list_members(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List organization members (admin/manager only)."""
    _require_admin_or_manager(current_user)
    org_id = current_user["organization_id"]
    members = await invitation_service.list_members(db, org_id)
    return [
        {
            "id": m.id,
            "name": m.name,
            "email": m.email,
            "role": m.role,
            "is_active": m.is_active,
            "created_at": m.created_at.isoformat(),
        }
        for m in members
    ]

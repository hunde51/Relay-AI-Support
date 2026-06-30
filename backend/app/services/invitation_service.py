"""Invitation token generation, verification, and management."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import InvitationORM, UserORM, OrganizationORM, make_id, utc_now

INVITE_TOKEN_BYTES = 32
INVITE_EXPIRY_DAYS = 7
ALLOWED_ROLES = ("admin", "manager", "agent")


def _generate_token() -> tuple[str, str]:
    """Return (plain_token, token_hash)."""
    plain = secrets.token_urlsafe(INVITE_TOKEN_BYTES)
    token_hash = hashlib.sha256(plain.encode()).hexdigest()
    return plain, token_hash


def _hash_token(plain: str) -> str:
    return hashlib.sha256(plain.encode()).hexdigest()


async def create_invitation(
    db: AsyncSession,
    organization_id: str,
    email: str,
    role: str,
    invited_by_user_id: str,
) -> tuple[InvitationORM, str]:
    """Create a pending invitation. Returns (orm, plain_token). plain_token shown once."""
    if role not in ALLOWED_ROLES:
        raise ValueError(f"Invalid role: {role}. Must be one of {ALLOWED_ROLES}")

    email = email.strip().lower()

    existing = await db.execute(
        select(InvitationORM).where(
            InvitationORM.organization_id == organization_id,
            InvitationORM.email == email,
            InvitationORM.status == "pending",
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("A pending invitation already exists for this email")

    existing_user = await db.execute(
        select(UserORM).where(
            UserORM.organization_id == organization_id,
            UserORM.email == email,
        )
    )
    if existing_user.scalar_one_or_none():
        raise ValueError("A user with this email already exists in the organization")

    plain_token, token_hash = _generate_token()
    expires_at = utc_now() + timedelta(days=INVITE_EXPIRY_DAYS)

    invitation = InvitationORM(
        id=make_id("INV"),
        organization_id=organization_id,
        email=email,
        role=role,
        token_hash=token_hash,
        invited_by_user_id=invited_by_user_id,
        status="pending",
        expires_at=expires_at,
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
    return invitation, plain_token


async def validate_invitation_token(db: AsyncSession, plain_token: str) -> InvitationORM | None:
    """Validate a plain invitation token. Returns the InvitationORM if valid, None otherwise."""
    token_hash = _hash_token(plain_token)
    now = utc_now()

    result = await db.execute(
        select(InvitationORM).where(
            InvitationORM.token_hash == token_hash,
            InvitationORM.status == "pending",
        )
    )
    invitation = result.scalar_one_or_none()
    if not invitation:
        return None
    if invitation.expires_at < now:
        invitation.status = "expired"
        await db.commit()
        return None
    return invitation


async def get_invitation_by_id(
    db: AsyncSession, invitation_id: str, organization_id: str
) -> InvitationORM | None:
    result = await db.execute(
        select(InvitationORM).where(
            InvitationORM.id == invitation_id,
            InvitationORM.organization_id == organization_id,
        )
    )
    return result.scalar_one_or_none()


async def list_pending_invitations(
    db: AsyncSession, organization_id: str
) -> list[InvitationORM]:
    now = utc_now()
    # Mark expired invitations lazily
    expired = await db.execute(
        select(InvitationORM).where(
            InvitationORM.organization_id == organization_id,
            InvitationORM.status == "pending",
            InvitationORM.expires_at < now,
        )
    )
    for inv in expired.scalars().all():
        inv.status = "expired"
    if expired.scalars().all():
        await db.commit()

    result = await db.execute(
        select(InvitationORM)
        .where(
            InvitationORM.organization_id == organization_id,
            or_(InvitationORM.status == "pending", InvitationORM.status == "revoked"),
        )
        .order_by(InvitationORM.created_at.desc())
    )
    return list(result.scalars().all())


async def list_members(db: AsyncSession, organization_id: str) -> list[UserORM]:
    result = await db.execute(
        select(UserORM)
        .where(
            UserORM.organization_id == organization_id,
            UserORM.is_active == True,  # noqa: E712
        )
        .order_by(UserORM.created_at.desc())
    )
    return list(result.scalars().all())


async def revoke_invitation(db: AsyncSession, invitation_id: str, organization_id: str) -> bool:
    invitation = await get_invitation_by_id(db, invitation_id, organization_id)
    if not invitation:
        return False
    if invitation.status != "pending":
        return False
    invitation.status = "revoked"
    await db.commit()
    return True


async def accept_invitation(
    db: AsyncSession,
    plain_token: str,
    name: str,
    password_hash: str,
) -> tuple[UserORM, str] | None:
    """Accept an invitation. Returns (user, organization_id) if successful, None otherwise.

    Caller must hash the password before calling this function.
    """
    invitation = await validate_invitation_token(db, plain_token)
    if not invitation:
        return None

    # Check for duplicate user in org
    existing = await db.execute(
        select(UserORM).where(
            UserORM.organization_id == invitation.organization_id,
            UserORM.email == invitation.email,
        )
    )
    if existing.scalar_one_or_none():
        invitation.status = "revoked"
        await db.commit()
        return None

    user = UserORM(
        id=make_id("USR"),
        organization_id=invitation.organization_id,
        email=invitation.email,
        name=name,
        role=invitation.role,
        is_active=True,
        password_hash=password_hash,
    )
    db.add(user)
    invitation.status = "accepted"
    invitation.accepted_at = utc_now()
    await db.commit()
    await db.refresh(user)
    return user, invitation.organization_id

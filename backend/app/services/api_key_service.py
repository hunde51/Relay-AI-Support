"""API key generation, verification, and rotation."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ApiKeyORM, make_id, utc_now

DEFAULT_SCOPES = ["tickets:write", "tickets:read", "customers:write"]


def _generate_raw_key(prefix: str) -> tuple[str, str, str]:
    """Return (full_key, key_prefix, key_hash)."""
    secret = secrets.token_urlsafe(32)[:32]
    full_key = f"relay_{prefix}_{secret}"
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, prefix, key_hash


async def create_api_key(
    db: AsyncSession,
    organization_id: str,
    name: str,
    scopes: list[str] | None = None,
    created_by_user_id: str | None = None,
    expires_at: datetime | None = None,
) -> tuple[ApiKeyORM, str]:
    """Create a new API key. Returns (orm, full_key). full_key is shown once only."""
    prefix = secrets.token_hex(4)  # 8 hex chars
    full_key, key_prefix, key_hash = _generate_raw_key(prefix)

    key = ApiKeyORM(
        id=make_id("AK"),
        organization_id=organization_id,
        name=name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        scopes=scopes or DEFAULT_SCOPES,
        is_active=True,
        expires_at=expires_at,
        created_by_user_id=created_by_user_id,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return key, full_key


async def verify_api_key(db: AsyncSession, full_key: str) -> ApiKeyORM | None:
    """Look up and verify an API key. Returns the ORM if valid, None otherwise."""
    # Key format: relay_<8-char-prefix>_<secret>
    parts = full_key.split("_", 2)
    if len(parts) != 3 or parts[0] != "relay":
        return None
    prefix = parts[1]
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()

    result = await db.execute(
        select(ApiKeyORM).where(
            ApiKeyORM.key_prefix == prefix,
            ApiKeyORM.key_hash == key_hash,
            ApiKeyORM.is_active == True,  # noqa: E712
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        return None
    if key.expires_at and key.expires_at < utc_now():
        return None
    # update last_used_at async (fire and forget — best effort)
    await db.execute(
        update(ApiKeyORM).where(ApiKeyORM.id == key.id).values(last_used_at=utc_now())
    )
    await db.commit()
    return key


async def list_api_keys(db: AsyncSession, organization_id: str) -> list[ApiKeyORM]:
    result = await db.execute(
        select(ApiKeyORM)
        .where(ApiKeyORM.organization_id == organization_id)
        .order_by(ApiKeyORM.created_at.desc())
    )
    return list(result.scalars().all())


async def revoke_api_key(db: AsyncSession, key_id: str, organization_id: str) -> bool:
    result = await db.execute(
        select(ApiKeyORM).where(ApiKeyORM.id == key_id, ApiKeyORM.organization_id == organization_id)
    )
    key = result.scalar_one_or_none()
    if not key:
        return False
    key.is_active = False
    await db.commit()
    return True


async def rotate_api_key(
    db: AsyncSession, key_id: str, organization_id: str
) -> tuple[ApiKeyORM, str] | None:
    """Revoke old key and issue a new one with the same name/scopes."""
    result = await db.execute(
        select(ApiKeyORM).where(ApiKeyORM.id == key_id, ApiKeyORM.organization_id == organization_id)
    )
    old = result.scalar_one_or_none()
    if not old:
        return None
    old.is_active = False
    await db.flush()
    return await create_api_key(
        db, organization_id, old.name, scopes=old.scopes,
        created_by_user_id=old.created_by_user_id,
    )

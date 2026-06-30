"""Widget key generation, verification, and management."""
from __future__ import annotations

import hashlib
import secrets

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.widget import WidgetKeyORM
from app.models.base import make_id, utc_now


def _generate_raw_key(prefix: str) -> tuple[str, str, str]:
    """Return (full_key, key_prefix, key_hash)."""
    secret = secrets.token_urlsafe(32)[:32]
    full_key = f"widget_{prefix}_{secret}"
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, prefix, key_hash


async def create_widget_key(
    db: AsyncSession,
    organization_id: str,
    name: str,
    allowed_origins: list[str] | None = None,
) -> tuple[WidgetKeyORM, str]:
    """Create a new widget key. Returns (orm, full_key). full_key is shown once only."""
    prefix = secrets.token_hex(4)
    full_key, key_prefix, key_hash = _generate_raw_key(prefix)

    key = WidgetKeyORM(
        id=make_id("WKEY"),
        organization_id=organization_id,
        name=name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        allowed_origins=allowed_origins or [],
        is_active=True,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return key, full_key


async def verify_widget_key(db: AsyncSession, full_key: str) -> WidgetKeyORM | None:
    """Look up and verify a widget key. Returns the ORM if valid, None otherwise."""
    parts = full_key.split("_", 2)
    if len(parts) != 3 or parts[0] != "widget":
        return None
    prefix = parts[1]
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()

    result = await db.execute(
        select(WidgetKeyORM).where(
            WidgetKeyORM.key_prefix == prefix,
            WidgetKeyORM.key_hash == key_hash,
            WidgetKeyORM.is_active == True,  # noqa: E712
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        return None

    # update last_used_at
    await db.execute(
        update(WidgetKeyORM).where(WidgetKeyORM.id == key.id).values(last_used_at=utc_now())
    )
    await db.commit()
    return key


async def list_widget_keys(db: AsyncSession, organization_id: str) -> list[WidgetKeyORM]:
    result = await db.execute(
        select(WidgetKeyORM)
        .where(WidgetKeyORM.organization_id == organization_id)
        .order_by(WidgetKeyORM.created_at.desc())
    )
    return list(result.scalars().all())


async def revoke_widget_key(db: AsyncSession, key_id: str, organization_id: str) -> bool:
    result = await db.execute(
        select(WidgetKeyORM).where(
            WidgetKeyORM.id == key_id,
            WidgetKeyORM.organization_id == organization_id,
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        return False
    key.is_active = False
    await db.commit()
    return True


async def update_widget_key(
    db: AsyncSession,
    key_id: str,
    organization_id: str,
    name: str | None = None,
    allowed_origins: list[str] | None = None,
    is_active: bool | None = None,
) -> WidgetKeyORM | None:
    result = await db.execute(
        select(WidgetKeyORM).where(
            WidgetKeyORM.id == key_id,
            WidgetKeyORM.organization_id == organization_id,
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        return None
    if name is not None:
        key.name = name
    if allowed_origins is not None:
        key.allowed_origins = allowed_origins
    if is_active is not None:
        key.is_active = is_active
    await db.commit()
    await db.refresh(key)
    return key

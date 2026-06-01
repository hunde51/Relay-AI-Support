from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import optional_current_user
from app.core.tenant import resolve_org_id, assert_org_access
from app.db.database import get_db
from app.db.models import NotificationORM


router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(optional_current_user),
):
    org_id = resolve_org_id(current_user)
    result = await db.execute(
        select(NotificationORM)
        .where(NotificationORM.organization_id == org_id)
        .order_by(NotificationORM.created_at.desc())
    )
    return [
        {
            "id": n.id,
            "organization_id": n.organization_id,
            "user_id": n.user_id,
            "type": n.type,
            "title": n.title,
            "body": n.body,
            "read_at": n.read_at,
            "created_at": n.created_at,
        }
        for n in result.scalars().all()
    ]


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(optional_current_user),
):
    result = await db.execute(select(NotificationORM).where(NotificationORM.id == notification_id))
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    try:
        assert_org_access(notification.organization_id, current_user)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")

    from datetime import UTC, datetime

    notification.read_at = datetime.now(UTC).replace(tzinfo=None)
    await db.commit()
    await db.refresh(notification)
    return {
        "id": notification.id,
        "read_at": notification.read_at,
    }

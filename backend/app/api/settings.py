from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.database import get_db
from app.db.models import OrganizationORM, OrganizationSettingsORM, NotificationSettingsORM
from app.db.seed import DEFAULT_ORG_ID

router = APIRouter(prefix="/settings", tags=["settings"])


class WorkspacePatch(BaseModel):
    name: Optional[str] = None
    plan: Optional[str] = None
    region: Optional[str] = None


class AIPatch(BaseModel):
    ai_enabled: Optional[bool] = None
    auto_resolve_enabled: Optional[bool] = None
    human_approval_threshold: Optional[str] = None


class NotificationPatch(BaseModel):
    email_digest_enabled: Optional[bool] = None
    slack_alerts_enabled: Optional[bool] = None
    sms_incidents_enabled: Optional[bool] = None


@router.get("/workspace")
async def get_workspace(db: AsyncSession = Depends(get_db)):
    org = await _get_org(db)
    return {"id": org.id, "name": org.name, "plan": org.plan, "region": org.region}


@router.patch("/workspace")
async def patch_workspace(data: WorkspacePatch, db: AsyncSession = Depends(get_db)):
    org = await _get_org(db)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(org, field, value)
    await db.commit()
    await db.refresh(org)
    return {"id": org.id, "name": org.name, "plan": org.plan, "region": org.region}


@router.get("/ai")
async def get_ai_settings(db: AsyncSession = Depends(get_db)):
    s = await _get_ai_settings(db)
    return {
        "ai_enabled": s.ai_enabled,
        "auto_resolve_enabled": s.auto_resolve_enabled,
        "human_approval_threshold": s.human_approval_threshold,
    }


@router.patch("/ai")
async def patch_ai_settings(data: AIPatch, db: AsyncSession = Depends(get_db)):
    s = await _get_ai_settings(db)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(s, field, value)
    await db.commit()
    await db.refresh(s)
    return {
        "ai_enabled": s.ai_enabled,
        "auto_resolve_enabled": s.auto_resolve_enabled,
        "human_approval_threshold": s.human_approval_threshold,
    }


@router.get("/notifications")
async def get_notification_settings(db: AsyncSession = Depends(get_db)):
    s = await _get_notification_settings(db)
    return {
        "email_digest_enabled": s.email_digest_enabled,
        "slack_alerts_enabled": s.slack_alerts_enabled,
        "sms_incidents_enabled": s.sms_incidents_enabled,
    }


@router.patch("/notifications")
async def patch_notification_settings(data: NotificationPatch, db: AsyncSession = Depends(get_db)):
    s = await _get_notification_settings(db)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(s, field, value)
    await db.commit()
    await db.refresh(s)
    return {
        "email_digest_enabled": s.email_digest_enabled,
        "slack_alerts_enabled": s.slack_alerts_enabled,
        "sms_incidents_enabled": s.sms_incidents_enabled,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_org(db: AsyncSession) -> OrganizationORM:
    result = await db.execute(select(OrganizationORM).where(OrganizationORM.id == DEFAULT_ORG_ID))
    return result.scalar_one()


async def _get_ai_settings(db: AsyncSession) -> OrganizationSettingsORM:
    result = await db.execute(
        select(OrganizationSettingsORM).where(OrganizationSettingsORM.organization_id == DEFAULT_ORG_ID)
    )
    return result.scalar_one()


async def _get_notification_settings(db: AsyncSession) -> NotificationSettingsORM:
    result = await db.execute(
        select(NotificationSettingsORM).where(NotificationSettingsORM.organization_id == DEFAULT_ORG_ID)
    )
    return result.scalar_one()

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.database import get_db
from app.db.models import OrganizationORM, OrganizationSettingsORM, NotificationSettingsORM, IntegrationORM
from app.api.auth import optional_current_user
from app.core.tenant import resolve_org_id, assert_org_access

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
async def get_workspace(db: AsyncSession = Depends(get_db), current_user: dict | None = Depends(optional_current_user)):
    org = await _get_org(db, resolve_org_id(current_user))
    return {"id": org.id, "name": org.name, "plan": org.plan, "region": org.region}


@router.patch("/workspace")
async def patch_workspace(data: WorkspacePatch, db: AsyncSession = Depends(get_db), current_user: dict | None = Depends(optional_current_user)):
    org = await _get_org(db, resolve_org_id(current_user))
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(org, field, value)
    await db.commit()
    await db.refresh(org)
    return {"id": org.id, "name": org.name, "plan": org.plan, "region": org.region}


@router.get("/ai")
async def get_ai_settings(db: AsyncSession = Depends(get_db), current_user: dict | None = Depends(optional_current_user)):
    s = await _get_ai_settings(db, resolve_org_id(current_user))
    return {
        "ai_enabled": s.ai_enabled,
        "auto_resolve_enabled": s.auto_resolve_enabled,
        "human_approval_threshold": s.human_approval_threshold,
    }


@router.patch("/ai")
async def patch_ai_settings(data: AIPatch, db: AsyncSession = Depends(get_db), current_user: dict | None = Depends(optional_current_user)):
    s = await _get_ai_settings(db, resolve_org_id(current_user))
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
async def get_notification_settings(db: AsyncSession = Depends(get_db), current_user: dict | None = Depends(optional_current_user)):
    s = await _get_notification_settings(db, resolve_org_id(current_user))
    return {
        "email_digest_enabled": s.email_digest_enabled,
        "slack_alerts_enabled": s.slack_alerts_enabled,
        "sms_incidents_enabled": s.sms_incidents_enabled,
    }


@router.patch("/notifications")
async def patch_notification_settings(data: NotificationPatch, db: AsyncSession = Depends(get_db), current_user: dict | None = Depends(optional_current_user)):
    s = await _get_notification_settings(db, resolve_org_id(current_user))
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(s, field, value)
    await db.commit()
    await db.refresh(s)
    return {
        "email_digest_enabled": s.email_digest_enabled,
        "slack_alerts_enabled": s.slack_alerts_enabled,
        "sms_incidents_enabled": s.sms_incidents_enabled,
    }


class IntegrationPatch(BaseModel):
    status: Optional[str] = None
    config: Optional[dict] = None


@router.get("/integrations")
async def get_integrations(db: AsyncSession = Depends(get_db), current_user: dict | None = Depends(optional_current_user)):
    org_id = resolve_org_id(current_user)
    result = await db.execute(
        select(IntegrationORM).where(IntegrationORM.organization_id == org_id)
    )
    integrations = result.scalars().all()
    return [
        {"id": i.id, "provider": i.provider, "status": i.status, "config": i.config}
        for i in integrations
    ]


@router.patch("/integrations/{integration_id}")
async def patch_integration(
    integration_id: str, data: IntegrationPatch, db: AsyncSession = Depends(get_db), current_user: dict | None = Depends(optional_current_user)
):
    result = await db.execute(select(IntegrationORM).where(IntegrationORM.id == integration_id))
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    try:
        assert_org_access(integration.organization_id, current_user)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(integration, field, value)
    await db.commit()
    await db.refresh(integration)
    return {"id": integration.id, "provider": integration.provider, "status": integration.status, "config": integration.config}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_org(db: AsyncSession, org_id: str) -> OrganizationORM:
    result = await db.execute(select(OrganizationORM).where(OrganizationORM.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        org = OrganizationORM(id=org_id, name="RelayAI Support", slug="default" if org_id == "ORG-DEFAULT000000" else org_id.lower().replace("ORG-", "org-").replace("_", "-"))
        db.add(org)
        await db.commit()
        await db.refresh(org)
    return org


async def _get_ai_settings(db: AsyncSession, org_id: str) -> OrganizationSettingsORM:
    result = await db.execute(
        select(OrganizationSettingsORM).where(OrganizationSettingsORM.organization_id == org_id)
    )
    s = result.scalar_one_or_none()
    if not s:
        await _get_org(db, org_id)
        s = OrganizationSettingsORM(organization_id=org_id)
        db.add(s)
        await db.commit()
        await db.refresh(s)
    return s


async def _get_notification_settings(db: AsyncSession, org_id: str) -> NotificationSettingsORM:
    result = await db.execute(
        select(NotificationSettingsORM).where(NotificationSettingsORM.organization_id == org_id)
    )
    s = result.scalar_one_or_none()
    if not s:
        await _get_org(db, org_id)
        s = NotificationSettingsORM(organization_id=org_id)
        db.add(s)
        await db.commit()
        await db.refresh(s)
    return s

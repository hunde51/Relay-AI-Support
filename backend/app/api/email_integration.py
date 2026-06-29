"""Email integration API — OAuth flows, listing, disconnect, test poll."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import optional_current_user
from app.core.tenant import assert_org_access, resolve_org_id
from app.db.database import get_db
from app.db.models import EmailIntegrationORM
from app.services import email_service

router = APIRouter(prefix="/settings/email", tags=["email"])


class IntegrationResponse(BaseModel):
    id: str
    provider: str
    email_address: str
    is_active: bool
    last_polled_at: str | None = None
    last_error: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


class OAuthUrlResponse(BaseModel):
    url: str


class ConnectRequest(BaseModel):
    code: str
    state: str


# ── List connected inboxes ────────────────────────────────────────────────────


@router.get("/integrations")
async def list_integrations(
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(optional_current_user),
):
    org_id = resolve_org_id(current_user)
    integrations = await email_service.get_integrations_for_org(db, org_id)
    return [
        IntegrationResponse(
            id=i.id,
            provider=i.provider,
            email_address=i.email_address,
            is_active=i.is_active,
            last_polled_at=i.last_polled_at.isoformat() if i.last_polled_at else None,
            last_error=i.last_error,
            created_at=i.created_at.isoformat(),
        )
        for i in integrations
    ]


# ── Gmail OAuth ───────────────────────────────────────────────────────────────


@router.get("/gmail/auth")
async def gmail_auth_url(
    current_user: dict | None = Depends(optional_current_user),
):
    org_id = resolve_org_id(current_user)
    url = email_service.build_gmail_auth_url(state=org_id)
    return OAuthUrlResponse(url=url)


@router.post("/gmail/callback")
async def gmail_callback(
    data: ConnectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(optional_current_user),
):
    org_id = resolve_org_id(current_user)
    if data.state != org_id:
        raise HTTPException(status_code=403, detail="State mismatch")

    # Check no existing Gmail integration
    existing = await db.execute(
        select(EmailIntegrationORM).where(
            EmailIntegrationORM.organization_id == org_id,
            EmailIntegrationORM.provider == "gmail",
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Gmail already connected")

    try:
        token_data = await email_service.exchange_gmail_code(data.code)
        email_addr = await email_service.get_gmail_email(token_data["access_token"])
        integration = await email_service.store_integration(db, org_id, "gmail", email_addr, token_data)
        return IntegrationResponse(
            id=integration.id,
            provider=integration.provider,
            email_address=integration.email_address,
            is_active=integration.is_active,
            last_polled_at=integration.last_polled_at.isoformat() if integration.last_polled_at else None,
            last_error=integration.last_error,
            created_at=integration.created_at.isoformat(),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gmail OAuth failed: {exc}")


# ── Outlook OAuth ─────────────────────────────────────────────────────────────


@router.get("/outlook/auth")
async def outlook_auth_url(
    current_user: dict | None = Depends(optional_current_user),
):
    org_id = resolve_org_id(current_user)
    url = email_service.build_outlook_auth_url(state=org_id)
    return OAuthUrlResponse(url=url)


@router.post("/outlook/callback")
async def outlook_callback(
    data: ConnectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(optional_current_user),
):
    org_id = resolve_org_id(current_user)
    if data.state != org_id:
        raise HTTPException(status_code=403, detail="State mismatch")

    existing = await db.execute(
        select(EmailIntegrationORM).where(
            EmailIntegrationORM.organization_id == org_id,
            EmailIntegrationORM.provider == "outlook",
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Outlook already connected")

    try:
        token_data = await email_service.exchange_outlook_code(data.code)
        email_addr = token_data.get("email", "outlook-connected@unknown")
        integration = await email_service.store_integration(db, org_id, "outlook", email_addr, token_data)
        return IntegrationResponse(
            id=integration.id,
            provider=integration.provider,
            email_address=integration.email_address,
            is_active=integration.is_active,
            last_polled_at=integration.last_polled_at.isoformat() if integration.last_polled_at else None,
            last_error=integration.last_error,
            created_at=integration.created_at.isoformat(),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Outlook OAuth failed: {exc}")


# ── Get single integration ────────────────────────────────────────────────────


@router.get("/integrations/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(optional_current_user),
):
    org_id = resolve_org_id(current_user)
    integration = await email_service.get_integration(db, integration_id, org_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    return IntegrationResponse(
        id=integration.id,
        provider=integration.provider,
        email_address=integration.email_address,
        is_active=integration.is_active,
        last_polled_at=integration.last_polled_at.isoformat() if integration.last_polled_at else None,
        last_error=integration.last_error,
        created_at=integration.created_at.isoformat(),
    )


class UpdateIntegrationRequest(BaseModel):
    is_active: bool | None = None


@router.patch("/integrations/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    integration_id: str,
    data: UpdateIntegrationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(optional_current_user),
):
    org_id = resolve_org_id(current_user)
    integration = await email_service.update_integration(db, integration_id, org_id, is_active=data.is_active)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    return IntegrationResponse(
        id=integration.id,
        provider=integration.provider,
        email_address=integration.email_address,
        is_active=integration.is_active,
        last_polled_at=integration.last_polled_at.isoformat() if integration.last_polled_at else None,
        last_error=integration.last_error,
        created_at=integration.created_at.isoformat(),
    )


# ── Disconnect ────────────────────────────────────────────────────────────────


@router.delete("/integrations/{integration_id}", status_code=204)
async def disconnect_integration(
    integration_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(optional_current_user),
):
    org_id = resolve_org_id(current_user)
    ok = await email_service.disconnect_integration(db, integration_id, org_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Integration not found")


# ── Test poll ─────────────────────────────────────────────────────────────────


class PollResult(BaseModel):
    provider: str
    new_messages: int


@router.post("/integrations/{integration_id}/poll")
async def poll_integration(
    integration_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(optional_current_user),
):
    org_id = resolve_org_id(current_user)
    result = await db.execute(
        select(EmailIntegrationORM).where(
            EmailIntegrationORM.id == integration_id,
            EmailIntegrationORM.organization_id == org_id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    if not integration.is_active:
        raise HTTPException(status_code=400, detail="Integration is inactive")

    try:
        if integration.provider == "gmail":
            cnt = await email_service.poll_gmail(db, integration)
        else:
            cnt = await email_service.poll_outlook(db, integration)
        return PollResult(provider=integration.provider, new_messages=cnt)
    except Exception as exc:
        integration.last_error = str(exc)
        await db.commit()
        raise HTTPException(status_code=502, detail=f"Poll failed: {exc}")

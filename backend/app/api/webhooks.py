import secrets
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.webhook import WebhookDeliveryORM, WebhookEndpointORM
from app.models.base import make_id, utc_now

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _require_admin(user: dict):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="admin role required")


class EndpointCreate(BaseModel):
    url: str
    events: list[str]


def _ep_out(ep: WebhookEndpointORM) -> dict:
    return {
        "id": ep.id,
        "url": ep.url,
        "events": ep.events,
        "is_active": ep.is_active,
        "created_at": ep.created_at.isoformat(),
    }


@router.get("/endpoints")
async def list_endpoints(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _require_admin(current_user)
    result = await db.execute(
        select(WebhookEndpointORM)
        .where(WebhookEndpointORM.organization_id == current_user["organization_id"])
        .order_by(WebhookEndpointORM.created_at.desc())
    )
    return [_ep_out(e) for e in result.scalars().all()]


@router.post("/endpoints", status_code=201)
async def create_endpoint(
    data: EndpointCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _require_admin(current_user)
    ep = WebhookEndpointORM(
        organization_id=current_user["organization_id"],
        url=data.url,
        secret=secrets.token_hex(32),
        events=data.events,
    )
    db.add(ep)
    await db.commit()
    await db.refresh(ep)
    r = _ep_out(ep)
    r["secret"] = ep.secret  # shown once
    return r


@router.delete("/endpoints/{endpoint_id}", status_code=204)
async def delete_endpoint(
    endpoint_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _require_admin(current_user)
    result = await db.execute(
        select(WebhookEndpointORM).where(
            WebhookEndpointORM.id == endpoint_id,
            WebhookEndpointORM.organization_id == current_user["organization_id"],
        )
    )
    ep = result.scalar_one_or_none()
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    await db.delete(ep)
    await db.commit()


@router.get("/deliveries")
async def list_deliveries(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _require_admin(current_user)
    # Join through endpoint to scope by org
    ep_result = await db.execute(
        select(WebhookEndpointORM.id).where(
            WebhookEndpointORM.organization_id == current_user["organization_id"]
        )
    )
    ep_ids = [r[0] for r in ep_result.all()]
    if not ep_ids:
        return []
    result = await db.execute(
        select(WebhookDeliveryORM)
        .where(WebhookDeliveryORM.endpoint_id.in_(ep_ids))
        .order_by(WebhookDeliveryORM.created_at.desc())
        .limit(100)
    )
    return [
        {
            "id": d.id,
            "endpoint_id": d.endpoint_id,
            "event_type": d.event_type,
            "status": d.status,
            "attempts": d.attempts,
            "response_status": d.response_status,
            "created_at": d.created_at.isoformat(),
        }
        for d in result.scalars().all()
    ]


@router.post("/endpoints/{endpoint_id}/test", status_code=202)
async def test_endpoint(
    endpoint_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _require_admin(current_user)
    result = await db.execute(
        select(WebhookEndpointORM).where(
            WebhookEndpointORM.id == endpoint_id,
            WebhookEndpointORM.organization_id == current_user["organization_id"],
        )
    )
    ep = result.scalar_one_or_none()
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    from app.services.webhook_service import create_delivery, deliver_webhook
    delivery = await create_delivery(
        db, ep.id, "webhook.test",
        {"event": "webhook.test", "organization_id": current_user["organization_id"]}
    )
    await deliver_webhook(db, delivery.id)
    return {"delivery_id": delivery.id, "status": delivery.status}

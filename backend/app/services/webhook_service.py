"""Webhook delivery — HMAC-SHA256 signed, with retry logic."""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import utc_now
from app.models.webhook import WebhookDeliveryORM, WebhookEndpointORM


def _sign_payload(secret: str, payload_bytes: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


async def get_endpoints_for_event(
    db: AsyncSession, organization_id: str, event_type: str
) -> list[WebhookEndpointORM]:
    result = await db.execute(
        select(WebhookEndpointORM).where(
            WebhookEndpointORM.organization_id == organization_id,
            WebhookEndpointORM.is_active == True,  # noqa: E712
        )
    )
    return [e for e in result.scalars().all() if event_type in (e.events or [])]


async def create_delivery(
    db: AsyncSession, endpoint_id: str, event_type: str, payload: dict
) -> WebhookDeliveryORM:
    delivery = WebhookDeliveryORM(
        endpoint_id=endpoint_id,
        event_type=event_type,
        payload=payload,
        status="pending",
        created_at=utc_now(),
    )
    db.add(delivery)
    await db.commit()
    await db.refresh(delivery)
    return delivery


async def deliver_webhook(db: AsyncSession, delivery_id: str) -> bool:
    """Attempt delivery. Returns True on success. Caller handles retries."""
    result = await db.execute(
        select(WebhookDeliveryORM).where(WebhookDeliveryORM.id == delivery_id)
    )
    delivery = result.scalar_one_or_none()
    if not delivery:
        return False

    ep_result = await db.execute(
        select(WebhookEndpointORM).where(WebhookEndpointORM.id == delivery.endpoint_id)
    )
    endpoint = ep_result.scalar_one_or_none()
    if not endpoint:
        delivery.status = "failed"
        await db.commit()
        return False

    payload_bytes = json.dumps(delivery.payload).encode()
    signature = _sign_payload(endpoint.secret, payload_bytes)

    delivery.attempts += 1
    delivery.last_attempt_at = utc_now()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                endpoint.url,
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-RelayAI-Signature": signature,
                    "X-RelayAI-Event": delivery.event_type,
                },
            )
        delivery.response_status = resp.status_code
        delivery.response_body = resp.text[:500]
        delivery.status = "delivered" if resp.status_code < 300 else "failed"
    except Exception as e:
        delivery.response_body = str(e)[:500]
        delivery.status = "failed"

    await db.commit()
    return delivery.status == "delivered"


async def trigger_webhook(
    db: AsyncSession, organization_id: str, event_type: str, payload: dict
) -> None:
    """Find matching endpoints, create delivery records, queue Celery tasks."""
    endpoints = await get_endpoints_for_event(db, organization_id, event_type)
    for endpoint in endpoints:
        delivery = await create_delivery(db, endpoint.id, event_type, payload)
        # Queue async delivery task
        try:
            from app.background.tasks import deliver_webhook_task
            deliver_webhook_task.delay(delivery.id)
        except Exception:
            # Celery not running (dev/test) — attempt inline delivery
            await deliver_webhook(db, delivery.id)

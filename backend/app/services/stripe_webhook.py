"""Optional Stripe webhook handler for subscription plan changes.

This module is kept isolated — Stripe is never required.
If STRIPE_WEBHOOK_SECRET is not configured, the webhook endpoint returns 501.
"""

from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.db.models import OrganizationORM, OrganizationSettingsORM
from app.services.billing_service import validate_plan

logger = logging.getLogger("app.stripe")


# ── Plan mapping: Stripe price IDs → RelayAI plan names ──────────────────────
STRIPE_PRICE_TO_PLAN: dict[str, str] = {}

_price_map_raw = (settings.STRIPE_PRICE_TO_PLAN or "").strip()
if _price_map_raw:
    for pair in _price_map_raw.split(","):
        if ":" in pair:
            price_id, plan = pair.split(":", 1)
            STRIPE_PRICE_TO_PLAN[price_id.strip()] = plan.strip()


async def verify_webhook_signature(payload: bytes, sig_header: str | None) -> bool:
    """Verify Stripe webhook signature using the configured secret.

    Returns True if signature is valid or if Stripe is not configured.
    Returns False on mismatch.
    """
    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.warning("STRIPE_WEBHOOK_SECRET not configured — skipping signature verification")
        return True

    if not sig_header:
        logger.error("Missing Stripe signature header")
        return False

    try:
        import stripe
        stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        return True
    except Exception as exc:
        logger.error("Stripe webhook signature verification failed: %s", exc)
        return False


async def extract_event(payload: bytes, sig_header: str | None) -> dict | None:
    """Parse and verify a Stripe event. Returns None if unverifiable."""
    if not await verify_webhook_signature(payload, sig_header):
        return None

    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        logger.error("Invalid Stripe webhook payload JSON")
        return None


async def handle_checkout_session_completed(event: dict, db: AsyncSession) -> bool:
    """Handle checkout.session.completed — set org plan from the purchased price."""
    data = event.get("data", {}).get("object", {})
    client_ref = data.get("client_reference_id")
    if not client_ref:
        logger.warning("checkout.session.completed has no client_reference_id")
        return False

    price_id = _resolve_price_id(event)
    if not price_id:
        return False

    plan = STRIPE_PRICE_TO_PLAN.get(price_id)
    if not plan:
        logger.warning("Unknown Stripe price ID: %s", price_id)
        return False

    try:
        validate_plan(plan)
    except ValueError:
        logger.error("Stripe price %s maps to invalid plan '%s'", price_id, plan)
        return False

    return await _set_org_plan(db, client_ref, plan)


async def handle_subscription_updated(event: dict, db: AsyncSession) -> bool:
    """Handle customer.subscription.updated — update org plan."""
    data = event.get("data", {}).get("object", {})
    metadata = data.get("metadata", {}) or {}
    org_id = metadata.get("organization_id")
    if not org_id:
        logger.warning("subscription.updated has no organization_id metadata")
        return False

    price_id = _resolve_price_id(event)
    if not price_id:
        return False

    plan = STRIPE_PRICE_TO_PLAN.get(price_id)
    if not plan:
        logger.warning("Unknown Stripe price ID in subscription update: %s", price_id)
        return False

    try:
        validate_plan(plan)
    except ValueError:
        return False

    return await _set_org_plan(db, org_id, plan)


async def handle_subscription_deleted(event: dict, db: AsyncSession) -> bool:
    """Handle customer.subscription.deleted — downgrade to starter."""
    data = event.get("data", {}).get("object", {})
    metadata = data.get("metadata", {}) or {}
    org_id = metadata.get("organization_id")
    if not org_id:
        logger.warning("subscription.deleted has no organization_id metadata")
        return False

    return await _set_org_plan(db, org_id, "starter")


def _resolve_price_id(event: dict) -> str | None:
    """Extract the first price ID from a Stripe event."""
    data = event.get("data", {}).get("object", {})
    items = data.get("lines", {}).get("data", []) if "lines" in data else data.get("items", {}).get("data", [])
    if items:
        price = items[0].get("price", {})
        return price.get("id")

    return data.get("metadata", {}).get("price_id")


async def _set_org_plan(db: AsyncSession, org_id: str, plan: str) -> bool:
    """Update an org's plan tier and reset overridden limits to plan defaults."""
    result = await db.execute(select(OrganizationORM).where(OrganizationORM.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        logger.error("Organization %s not found for Stripe plan update", org_id)
        return False

    org.plan = plan

    settings_result = await db.execute(
        select(OrganizationSettingsORM).where(OrganizationSettingsORM.organization_id == org_id)
    )
    s = settings_result.scalar_one_or_none()
    if s:
        s.monthly_ticket_limit = None
        s.api_rate_limit = None
        s.max_knowledge_docs = None

    await db.commit()
    logger.info("Organization %s plan updated to %s via Stripe webhook", org_id, plan)
    return True

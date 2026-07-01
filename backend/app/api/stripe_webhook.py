"""Stripe webhook endpoint — routes events to stripe_webhook service handlers."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.services import stripe_webhook as sw

logger = logging.getLogger("app.stripe")
router = APIRouter(prefix="/stripe", tags=["stripe"])

EVENT_HANDLERS = {
    "checkout.session.completed": sw.handle_checkout_session_completed,
    "customer.subscription.updated": sw.handle_subscription_updated,
    "customer.subscription.deleted": sw.handle_subscription_deleted,
}


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=501, detail="Stripe webhook not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    event = await sw.extract_event(payload, sig_header)
    if not event:
        raise HTTPException(status_code=400, detail="Invalid webhook signature or payload")

    event_type = event.get("type", "")
    handler = EVENT_HANDLERS.get(event_type)
    if not handler:
        logger.debug("Unhandled Stripe event type: %s", event_type)
        return {"received": True, "event_type": event_type, "handled": False}

    success = await handler(event, db)
    return {"received": True, "event_type": event_type, "handled": success}

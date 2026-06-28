from sqlalchemy.ext.asyncio import AsyncSession


async def _fire_webhook(db: AsyncSession, ticket, event_type: str, extra: dict | None = None):
    if not ticket or not ticket.organization_id:
        return
    try:
        from app.services.webhook_service import trigger_webhook
        payload = {"event": event_type, "ticket_id": ticket.id, **(extra or {})}
        await trigger_webhook(db, ticket.organization_id, event_type, payload)
    except Exception:
        pass

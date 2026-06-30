"""Widget-specific business logic — ticket creation, customer upsert, origin enforcement."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import CustomerORM
from app.models.base import make_id
from app.services.ticket_service import create_ticket, add_message
from app.services.ai_service import run_ai_on_ticket
from app.schemas.ticket import TicketCreate, MessageCreate
from app.services.widget_session import create_session


async def upsert_customer(
    db: AsyncSession, organization_id: str, name: str, email: str
) -> CustomerORM:
    """Find existing customer by email in org, or create a new one."""
    result = await db.execute(
        select(CustomerORM).where(
            CustomerORM.organization_id == organization_id,
            CustomerORM.email == email,
        )
    )
    customer = result.scalar_one_or_none()
    if customer:
        return customer

    customer = CustomerORM(
        id=make_id("CUS"),
        organization_id=organization_id,
        name=name,
        email=email,
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer


async def create_widget_ticket(
    db: AsyncSession,
    organization_id: str,
    visitor_name: str,
    visitor_email: str,
    message: str,
    page_url: str | None = None,
    browser_context: dict | None = None,
) -> dict:
    """Create a ticket from a widget submission. Returns ticket info + session token."""
    _ = browser_context  # available for future metadata use

    customer = await upsert_customer(db, organization_id, visitor_name, visitor_email)

    ticket_data = TicketCreate(
        title=f"Support request from {visitor_name}",
        message=message,
        priority="medium",
        category="general",
    )
    ticket = await create_ticket(
        db,
        ticket_data,
        source="widget",
        customer_id=customer.id,
        organization_id=organization_id,
    )

    # Create the initial message from this customer
    await add_message(
        db,
        ticket.id,
        MessageCreate(body=message, is_internal=False, sender_type="customer"),
    )

    # Generate session token for the visitor
    session_token = create_session(ticket.id, organization_id)

    # Queue AI run (fire and forget)
    await run_ai_on_ticket(db, ticket.id)

    return {
        "ticket_id": ticket.id,
        "session_token": session_token,
        "status": ticket.status,
        "created_at": ticket.created_at.isoformat() if hasattr(ticket.created_at, "isoformat") else str(ticket.created_at),
    }


async def add_widget_message(
    db: AsyncSession,
    ticket_id: str,
    organization_id: str,
    body: str,
) -> dict:
    """Add a follow-up message from the widget visitor."""
    msg = await add_message(
        db,
        ticket_id,
        MessageCreate(body=body, is_internal=False, sender_type="customer"),
    )
    if msg:
        # Queue a new AI run on the follow-up
        await run_ai_on_ticket(db, ticket_id)
    return {
        "message_id": msg.id if msg else None,
        "body": body,
        "created_at": msg.created_at.isoformat() if msg and hasattr(msg.created_at, "isoformat") else "",
    }


def check_widget_origin(widget_key: WidgetKeyORM, origin: str | None) -> bool:
    """Validate that the request origin is allowed for this widget key.

    If allowed_origins is empty, all origins are accepted (careful!).
    If '*' is in allowed_origins, all origins are accepted.
    """
    if not widget_key.allowed_origins:
        return True
    if "*" in widget_key.allowed_origins:
        return True
    if not origin:
        return False
    return origin in widget_key.allowed_origins

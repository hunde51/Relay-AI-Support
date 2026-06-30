import math
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TicketEventORM, TicketORM
from app.core.tenant import resolve_org_id
from app.schemas.ticket import TicketCreate, TicketFilters, TicketUpdate


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def create(
    db: AsyncSession,
    data: TicketCreate,
    current_user: dict | None = None,
    source: str | None = None,
    customer_id: str | None = None,
    organization_id: str | None = None,
) -> TicketORM:
    ticket = TicketORM(
        id=f"TKT-{uuid4().hex[:6].upper()}",
        organization_id=organization_id or resolve_org_id(current_user),
        title=data.title,
        message=data.message,
        priority=data.priority,
        category=data.category,
        source=source or (current_user.get("source", "manual") if current_user else "manual"),
        customer_id=customer_id,
        created_at=_utc_now(),
        updated_at=_utc_now(),
    )
    db.add(ticket)
    await db.flush()

    event = TicketEventORM(
        ticket_id=ticket.id,
        actor_type="system",
        event_type="ticket_created",
        new_value=ticket.status,
    )
    db.add(event)
    await db.commit()
    await db.refresh(ticket)
    return ticket


async def get_all(db: AsyncSession, filters: TicketFilters, current_user: dict | None = None):
    q = select(TicketORM).where(TicketORM.organization_id == resolve_org_id(current_user))
    if filters.status:
        q = q.where(TicketORM.status == filters.status)
    if filters.priority:
        q = q.where(TicketORM.priority == filters.priority)
    if filters.category:
        q = q.where(TicketORM.category == filters.category)
    if filters.assignee_id:
        q = q.where(TicketORM.assignee_id == filters.assignee_id)
    if filters.customer_id:
        q = q.where(TicketORM.customer_id == filters.customer_id)
    if filters.created_from:
        q = q.where(TicketORM.created_at >= filters.created_from)
    if filters.created_to:
        q = q.where(TicketORM.created_at <= filters.created_to)
    if filters.search:
        term = f"%{filters.search}%"
        q = q.where(TicketORM.title.ilike(term) | TicketORM.message.ilike(term))

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar_one()

    if filters.sort == "created_at_asc":
        q = q.order_by(TicketORM.created_at.asc())
    elif filters.sort == "updated_at_desc":
        q = q.order_by(TicketORM.updated_at.desc())
    else:
        q = q.order_by(TicketORM.created_at.desc())

    offset = (filters.page - 1) * filters.page_size
    q = q.offset(offset).limit(filters.page_size)
    result = await db.execute(q)
    items = result.scalars().all()

    return items, total, math.ceil(total / filters.page_size) if total else 0


async def get_by_id(db: AsyncSession, ticket_id: str) -> TicketORM | None:
    result = await db.execute(select(TicketORM).where(TicketORM.id == ticket_id))
    return result.scalar_one_or_none()


async def update(db: AsyncSession, ticket_id: str, data: TicketUpdate) -> TicketORM | None:
    ticket = await get_by_id(db, ticket_id)
    if not ticket:
        return None
    changes = data.model_dump(exclude_none=True)
    for field, value in changes.items():
        old = getattr(ticket, field)
        setattr(ticket, field, value)
        event = TicketEventORM(
            ticket_id=ticket.id,
            actor_type="agent",
            event_type=f"{field}_changed",
            old_value=str(old) if old is not None else None,
            new_value=str(value),
        )
        db.add(event)
    ticket.updated_at = _utc_now()
    await db.commit()
    await db.refresh(ticket)
    return ticket

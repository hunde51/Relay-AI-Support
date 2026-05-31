import math
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TicketEventORM, TicketMessageORM, TicketORM
from app.db.seed import DEFAULT_ORG_ID
from app.schemas.ticket import MessageCreate, TicketCreate, TicketFilters, TicketUpdate


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def create(db: AsyncSession, data: TicketCreate) -> TicketORM:
    ticket = TicketORM(
        id=f"TKT-{uuid4().hex[:6].upper()}",
        organization_id=DEFAULT_ORG_ID,
        title=data.title,
        message=data.message,
        priority=data.priority,
        category=data.category,
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


async def get_all(db: AsyncSession, filters: TicketFilters):
    q = select(TicketORM)
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


async def set_status(db: AsyncSession, ticket_id: str, status: str, event_type: str) -> TicketORM | None:
    ticket = await get_by_id(db, ticket_id)
    if not ticket:
        return None
    old_status = ticket.status
    ticket.status = status
    ticket.updated_at = _utc_now()
    if status == "resolved":
        ticket.resolved_at = _utc_now()
    elif status == "closed":
        ticket.closed_at = _utc_now()
    db.add(TicketEventORM(
        ticket_id=ticket.id,
        actor_type="agent",
        event_type=event_type,
        old_value=old_status,
        new_value=status,
    ))
    await db.commit()
    await db.refresh(ticket)
    return ticket


async def assign(db: AsyncSession, ticket_id: str, assignee_id: str) -> TicketORM | None:
    ticket = await get_by_id(db, ticket_id)
    if not ticket:
        return None
    old = ticket.assignee_id
    ticket.assignee_id = assignee_id
    ticket.updated_at = _utc_now()
    db.add(TicketEventORM(
        ticket_id=ticket.id,
        actor_type="agent",
        event_type="assigned",
        old_value=old,
        new_value=assignee_id,
    ))
    await db.commit()
    await db.refresh(ticket)
    return ticket



    ticket = await get_by_id(db, ticket_id)
    if not ticket:
        return None
    msg = TicketMessageORM(
        ticket_id=ticket_id,
        sender_type=data.sender_type,
        body=data.body,
        is_internal=data.is_internal,
    )
    db.add(msg)
    if not ticket.first_response_at and data.sender_type == "agent":
        ticket.first_response_at = _utc_now()
    ticket.updated_at = _utc_now()
    await db.commit()
    await db.refresh(msg)
    return msg


async def get_messages(db: AsyncSession, ticket_id: str) -> list[TicketMessageORM]:
    result = await db.execute(
        select(TicketMessageORM)
        .where(TicketMessageORM.ticket_id == ticket_id)
        .order_by(TicketMessageORM.created_at)
    )
    return result.scalars().all()


async def get_timeline(db: AsyncSession, ticket_id: str) -> list[TicketEventORM]:
    result = await db.execute(
        select(TicketEventORM)
        .where(TicketEventORM.ticket_id == ticket_id)
        .order_by(TicketEventORM.created_at)
    )
    return result.scalars().all()

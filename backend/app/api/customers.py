from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.database import get_db
from app.db.models import CustomerORM, TicketORM, TicketEventORM
from app.db.seed import DEFAULT_ORG_ID

router = APIRouter(prefix="/customers", tags=["customers"])


class CustomerCreate(BaseModel):
    name: str
    email: str
    company: Optional[str] = None
    external_id: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_or_404(db: AsyncSession, customer_id: str) -> CustomerORM:
    result = await db.execute(select(CustomerORM).where(CustomerORM.id == customer_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    return c


def _fmt(c: CustomerORM) -> dict:
    return {
        "id": c.id, "name": c.name, "email": c.email,
        "company": c.company, "external_id": c.external_id,
        "organization_id": c.organization_id,
        "created_at": c.created_at, "updated_at": c.updated_at,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("")
async def list_customers(
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(CustomerORM).where(CustomerORM.organization_id == DEFAULT_ORG_ID)
    if search:
        term = f"%{search}%"
        q = q.where(CustomerORM.name.ilike(term) | CustomerORM.email.ilike(term))
    result = await db.execute(q.order_by(CustomerORM.created_at.desc()))
    return [_fmt(c) for c in result.scalars().all()]


@router.post("", status_code=201)
async def create_customer(data: CustomerCreate, db: AsyncSession = Depends(get_db)):
    c = CustomerORM(
        organization_id=DEFAULT_ORG_ID,
        name=data.name,
        email=data.email,
        company=data.company,
        external_id=data.external_id,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return _fmt(c)


@router.get("/{customer_id}")
async def get_customer(customer_id: str, db: AsyncSession = Depends(get_db)):
    return _fmt(await _get_or_404(db, customer_id))


@router.get("/{customer_id}/tickets")
async def get_customer_tickets(customer_id: str, db: AsyncSession = Depends(get_db)):
    await _get_or_404(db, customer_id)
    result = await db.execute(
        select(TicketORM)
        .where(TicketORM.customer_id == customer_id)
        .order_by(TicketORM.created_at.desc())
    )
    return [
        {"id": t.id, "title": t.title, "status": t.status,
         "priority": t.priority, "category": t.category, "created_at": t.created_at}
        for t in result.scalars().all()
    ]


@router.get("/{customer_id}/timeline")
async def get_customer_timeline(customer_id: str, db: AsyncSession = Depends(get_db)):
    await _get_or_404(db, customer_id)
    result = await db.execute(
        select(TicketEventORM, TicketORM.title)
        .join(TicketORM, TicketEventORM.ticket_id == TicketORM.id)
        .where(TicketORM.customer_id == customer_id)
        .order_by(TicketEventORM.created_at.desc())
        .limit(50)
    )
    return [
        {
            "event_id": row.TicketEventORM.id,
            "ticket_id": row.TicketEventORM.ticket_id,
            "ticket_title": row.title,
            "event_type": row.TicketEventORM.event_type,
            "actor_type": row.TicketEventORM.actor_type,
            "old_value": row.TicketEventORM.old_value,
            "new_value": row.TicketEventORM.new_value,
            "created_at": row.TicketEventORM.created_at.isoformat(),
        }
        for row in result.all()
    ]

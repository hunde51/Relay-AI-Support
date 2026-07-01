"""Plan enforcement service — limit checks, usage vs limits, plan defaults.

This is the single source of truth for what each plan allows.
All enforcement goes through this service before any protected action.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.org import OrganizationORM, OrganizationSettingsORM
from app.models.knowledge import KnowledgeDocumentORM
from app.services.usage_service import (
    get_current_period,
    get_or_create_record,
)

# ── Plan-level default limits ─────────────────────────────────────────────────
# These apply when organization_settings has no explicit override.
PLAN_LIMITS: dict[str, dict[str, int]] = {
    "starter": {
        "monthly_ticket_limit": 500,
        "api_rate_limit": 100,
        "max_knowledge_docs": 50,
    },
    "pro": {
        "monthly_ticket_limit": 5_000,
        "api_rate_limit": 500,
        "max_knowledge_docs": 500,
    },
    "enterprise": {
        "monthly_ticket_limit": 50_000,
        "api_rate_limit": 2_000,
        "max_knowledge_docs": 5_000,
    },
}

VALID_PLANS = frozenset(PLAN_LIMITS.keys())


def validate_plan(plan: str) -> str:
    """Raise ValueError if plan is not a known tier."""
    if plan not in VALID_PLANS:
        raise ValueError(f"Invalid plan '{plan}'. Must be one of {sorted(VALID_PLANS)}")
    return plan


async def get_org_plan(db: AsyncSession, organization_id: str) -> str:
    """Return the organization's plan tier string."""
    result = await db.execute(
        select(OrganizationORM.plan).where(OrganizationORM.id == organization_id)
    )
    plan = result.scalar_one_or_none()
    return plan or "starter"


async def get_org_limits(db: AsyncSession, organization_id: str) -> dict[str, int | None]:
    """Return effective limits for an org (plan defaults overridden by settings).
    
    Returns a dict with keys: monthly_ticket_limit, api_rate_limit, max_knowledge_docs.
    None means unlimited.
    """
    plan = await get_org_plan(db, organization_id)
    defaults = dict(PLAN_LIMITS.get(plan, PLAN_LIMITS["starter"]))

    result = await db.execute(
        select(OrganizationSettingsORM).where(
            OrganizationSettingsORM.organization_id == organization_id
        )
    )
    settings = result.scalar_one_or_none()
    if not settings:
        return defaults

    for key in ("monthly_ticket_limit", "api_rate_limit", "max_knowledge_docs"):
        val = getattr(settings, key, None)
        if val is not None:
            defaults[key] = val

    return defaults


async def get_org_rate_limit(db: AsyncSession, organization_id: str) -> int:
    """Return the per-minute API rate limit for an org."""
    limits = await get_org_limits(db, organization_id)
    return limits.get("api_rate_limit") or 100


# ── Ticket limit enforcement ─────────────────────────────────────────────────


async def check_ticket_limit(db: AsyncSession, organization_id: str) -> None:
    """Raise 402 if the org has exceeded its monthly ticket limit.

    Must be called *before* creating a ticket.
    """
    period = get_current_period()
    record = await get_or_create_record(db, organization_id, period)
    limits = await get_org_limits(db, organization_id)

    limit = limits.get("monthly_ticket_limit")
    if limit is None:
        return  # unlimited

    if record.tickets_created >= limit:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "ticket_limit_exceeded",
                "message": (
                    f"Your organization has reached its monthly ticket limit "
                    f"({limit}). Upgrade your plan to create more tickets."
                ),
                "current": record.tickets_created,
                "limit": limit,
                "plan": await get_org_plan(db, organization_id),
            },
        )


# ── Knowledge document limit enforcement ──────────────────────────────────────


async def check_knowledge_doc_limit(db: AsyncSession, organization_id: str) -> None:
    """Raise 402 if the org has reached its max knowledge documents."""
    limits = await get_org_limits(db, organization_id)
    limit = limits.get("max_knowledge_docs")
    if limit is None:
        return  # unlimited

    result = await db.execute(
        select(func.count()).select_from(KnowledgeDocumentORM).where(
            KnowledgeDocumentORM.organization_id == organization_id,
        )
    )
    current_count: int = result.scalar_one()

    if current_count >= limit:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "knowledge_doc_limit_exceeded",
                "message": (
                    f"Your organization has reached its knowledge document limit "
                    f"({limit}). Upgrade your plan to add more documents."
                ),
                "current": current_count,
                "limit": limit,
                "plan": await get_org_plan(db, organization_id),
            },
        )


# ── Usage vs limits report (consolidated) ─────────────────────────────────────


async def get_usage_vs_limits(
    db: AsyncSession, organization_id: str, period: str | None = None
) -> dict:
    """Return current usage, limits, and remaining capacity for every tracked metric.

    This is the canonical response for /usage/limits and dashboard display.
    """
    period = period or get_current_period()
    limits = await get_org_limits(db, organization_id)
    plan = await get_org_plan(db, organization_id)
    record = await get_or_create_record(db, organization_id, period)

    # Current knowledge doc count
    result = await db.execute(
        select(func.count()).select_from(KnowledgeDocumentORM).where(
            KnowledgeDocumentORM.organization_id == organization_id,
        )
    )
    knowledge_docs: int = result.scalar_one()

    usage = {
        "tickets_created": record.tickets_created,
        "ai_runs_executed": record.ai_runs_executed,
        "api_requests": record.api_requests,
        "knowledge_docs": knowledge_docs,
    }

    remaining: dict[str, int | None] = {}
    for key, limit_key in [
        ("tickets", "monthly_ticket_limit"),
        ("ai_runs", None),
        ("api_requests", "api_rate_limit"),
        ("knowledge_docs", "max_knowledge_docs"),
    ]:
        lim = limits.get(limit_key) if limit_key else None
        if lim is not None:
            remaining[key] = max(0, lim - usage.get(key.replace("_", "_"), 0))
        else:
            remaining[key] = None

    return {
        "period": period,
        "plan": plan,
        "usage": usage,
        "limits": {
            "monthly_ticket_limit": limits.get("monthly_ticket_limit"),
            "api_rate_limit": limits.get("api_rate_limit"),
            "max_knowledge_docs": limits.get("max_knowledge_docs"),
        },
        "remaining": {
            "tickets": max(0, (limits.get("monthly_ticket_limit") or 0) - record.tickets_created)
            if limits.get("monthly_ticket_limit") is not None
            else None,
            "knowledge_docs": max(0, (limits.get("max_knowledge_docs") or 0) - knowledge_docs)
            if limits.get("max_knowledge_docs") is not None
            else None,
        },
    }

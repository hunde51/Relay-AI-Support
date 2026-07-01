"""Usage accounting service — monthly record upserts, token cost helpers, API request counting."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage import UsageEventORM, UsageRecordORM

# ── Model pricing table (USD per 1M tokens) ──────────────────────────────────
# Prices are for Gemini models via Google AI Studio / Vertex AI.
# Source: https://cloud.google.com/vertex-ai/generative-ai/pricing (June 2026)

MODEL_PRICING: dict[str, dict[str, float]] = {
    "gemini-1.5-flash": {
        "input_per_1m": 0.075,
        "output_per_1m": 0.300,
    },
    "gemini-1.5-pro": {
        "input_per_1m": 1.25,
        "output_per_1m": 5.00,
    },
    "gemini-2.0-flash": {
        "input_per_1m": 0.10,
        "output_per_1m": 0.40,
    },
    "gemini-2.0-pro": {
        "input_per_1m": 2.00,
        "output_per_1m": 8.00,
    },
    "text-embedding-004": {
        "input_per_1m": 0.00,
        "output_per_1m": 0.00,
    },
}

DEFAULT_MODEL = "gemini-1.5-flash"
DEFAULT_INPUT_PRICE = 0.075
DEFAULT_OUTPUT_PRICE = 0.300


def get_current_period() -> str:
    """Compute the current billing period as YYYY-MM."""
    now = datetime.now(UTC)
    return f"{now.year}-{now.month:02d}"


def estimate_cost(prompt_tokens: int, completion_tokens: int, model: str = DEFAULT_MODEL) -> float:
    """Estimate LLM cost in USD from token counts and model pricing.

    Returns a float rounded to 6 decimal places (micro-dollar precision).
    """
    pricing = MODEL_PRICING.get(model, {})
    input_price = pricing.get("input_per_1m", DEFAULT_INPUT_PRICE)
    output_price = pricing.get("output_per_1m", DEFAULT_OUTPUT_PRICE)

    input_cost = (prompt_tokens / 1_000_000) * input_price
    output_cost = (completion_tokens / 1_000_000) * output_price
    return round(input_cost + output_cost, 6)


async def get_or_create_record(db: AsyncSession, organization_id: str, period: str | None = None) -> UsageRecordORM:
    """Get the usage record for an org+period, creating it if none exists.

    Returns the record.  Safe to call concurrently — the unique constraint
    on (organization_id, period) prevents duplicates.
    """
    period = period or get_current_period()
    result = await db.execute(
        select(UsageRecordORM).where(
            UsageRecordORM.organization_id == organization_id,
            UsageRecordORM.period == period,
        )
    )
    record = result.scalar_one_or_none()
    if record:
        return record

    record = UsageRecordORM(
        organization_id=organization_id,
        period=period,
    )
    db.add(record)
    await db.flush()
    return record


async def increment_tickets_created(db: AsyncSession, organization_id: str, period: str | None = None) -> UsageRecordORM:
    """Increment tickets_created for the org's current period."""
    period = period or get_current_period()
    record = await get_or_create_record(db, organization_id, period)
    record.tickets_created = (record.tickets_created or 0) + 1
    await db.flush()
    await db.refresh(record)
    return record


async def increment_ai_runs(
    db: AsyncSession,
    organization_id: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    model: str = DEFAULT_MODEL,
    period: str | None = None,
    resource_id: str | None = None,
) -> UsageRecordORM:
    """Increment AI run counters and persist token + cost estimates.

    Call this when an AI run completes successfully.
    Failed/cancelled runs should NOT call this (they don't count as executed).
    """
    period = period or get_current_period()
    cost = estimate_cost(prompt_tokens, completion_tokens, model)

    record = await get_or_create_record(db, organization_id, period)
    record.ai_runs_executed = (record.ai_runs_executed or 0) + 1
    record.llm_prompt_tokens = (record.llm_prompt_tokens or 0) + prompt_tokens
    record.llm_completion_tokens = (record.llm_completion_tokens or 0) + completion_tokens
    record.llm_cost_usd = round((record.llm_cost_usd or 0.0) + cost, 6)
    await db.flush()
    await db.refresh(record)

    # Write granular event for auditability
    event = UsageEventORM(
        organization_id=organization_id,
        event_type="ai_run",
        resource_id=resource_id,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost,
        metadata_json={"model": model},
    )
    db.add(event)
    await db.flush()
    return record


async def increment_api_requests(
    db: AsyncSession, organization_id: str, period: str | None = None, count: int = 1
) -> UsageRecordORM:
    """Increment API request counter for the org's current period."""
    period = period or get_current_period()
    record = await get_or_create_record(db, organization_id, period)
    record.api_requests = (record.api_requests or 0) + count
    await db.flush()
    await db.refresh(record)
    return record


async def get_usage_summary(db: AsyncSession, organization_id: str, period: str | None = None) -> dict:
    """Return current-period usage summary with derived metrics."""
    period = period or get_current_period()
    record = await get_or_create_record(db, organization_id, period)

    # Derive knowledge chunks count
    from app.models.knowledge import KnowledgeChunkORM
    chunks_result = await db.execute(
        select(func.count()).select_from(KnowledgeChunkORM).where(
            KnowledgeChunkORM.organization_id == organization_id,
        )
    )
    knowledge_chunks = chunks_result.scalar_one()

    # Derive active users count
    from app.models.org import UserORM
    users_result = await db.execute(
        select(func.count()).select_from(UserORM).where(
            UserORM.organization_id == organization_id,
            UserORM.is_active == True,
        )
    )
    active_users = users_result.scalar_one()

    return {
        "period": period,
        "tickets_created": record.tickets_created,
        "ai_runs_executed": record.ai_runs_executed,
        "llm_prompt_tokens": record.llm_prompt_tokens,
        "llm_completion_tokens": record.llm_completion_tokens,
        "llm_total_tokens": record.llm_prompt_tokens + record.llm_completion_tokens,
        "llm_cost_usd": record.llm_cost_usd,
        "api_requests": record.api_requests,
        "knowledge_chunks": knowledge_chunks,
        "active_users": active_users,
    }


async def get_usage_history(db: AsyncSession, organization_id: str, months: int = 12) -> list[dict]:
    """Return monthly usage for the past N months, ordered ascending."""
    from datetime import timedelta
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=months * 31)
    cutoff_period = f"{cutoff.year}-{cutoff.month:02d}"

    result = await db.execute(
        select(UsageRecordORM)
        .where(
            UsageRecordORM.organization_id == organization_id,
            UsageRecordORM.period >= cutoff_period,
        )
        .order_by(UsageRecordORM.period.asc())
    )
    records = result.scalars().all()

    return [
        {
            "period": r.period,
            "tickets_created": r.tickets_created,
            "ai_runs_executed": r.ai_runs_executed,
            "llm_prompt_tokens": r.llm_prompt_tokens,
            "llm_completion_tokens": r.llm_completion_tokens,
            "llm_total_tokens": r.llm_prompt_tokens + r.llm_completion_tokens,
            "llm_cost_usd": r.llm_cost_usd,
            "api_requests": r.api_requests,
        }
        for r in records
    ]


async def get_ai_costs_breakdown(db: AsyncSession, organization_id: str, months: int = 6) -> list[dict]:
    """Return a breakdown of AI usage cost by model/node for recent months.

    Reads from usage_events for granularity.  If events lack model attribution,
    returns a single aggregated row per month.
    """
    from datetime import timedelta
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=months * 31)

    result = await db.execute(
        select(UsageEventORM)
        .where(
            UsageEventORM.organization_id == organization_id,
            UsageEventORM.event_type == "ai_run",
            UsageEventORM.created_at >= cutoff,
        )
        .order_by(UsageEventORM.created_at.desc())
    )
    events = result.scalars().all()

    # Group by month + model
    from collections import defaultdict
    buckets: dict[tuple[str, str], dict] = defaultdict(lambda: {"runs": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0})

    for ev in events:
        meta = ev.metadata_json or {}
        model = meta.get("model", DEFAULT_MODEL)
        month = ev.created_at.strftime("%Y-%m")
        key = (month, model)
        buckets[key]["runs"] += 1
        buckets[key]["prompt_tokens"] += ev.prompt_tokens or 0
        buckets[key]["completion_tokens"] += ev.completion_tokens or 0
        buckets[key]["cost_usd"] = round(buckets[key]["cost_usd"] + (ev.cost_usd or 0.0), 6)

    return [
        {
            "period": month,
            "model": model,
            "runs": data["runs"],
            "prompt_tokens": data["prompt_tokens"],
            "completion_tokens": data["completion_tokens"],
            "cost_usd": data["cost_usd"],
        }
        for (month, model), data in sorted(buckets.items())
    ]


async def get_usage_limits(db: AsyncSession, organization_id: str, period: str | None = None) -> dict:
    """Return current usage vs plan/configured limits.

    Limits are read from organization_settings or plan defaults.
    In Phase 11 no hard enforcement occurs — this is read-only reporting.
    """
    period = period or get_current_period()
    record = await get_or_create_record(db, organization_id, period)

    from app.models.org import OrganizationORM, OrganizationSettingsORM

    org_result = await db.execute(select(OrganizationORM).where(OrganizationORM.id == organization_id))
    org = org_result.scalar_one_or_none()
    plan = org.plan if org else "starter"

    settings_result = await db.execute(
        select(OrganizationSettingsORM).where(OrganizationSettingsORM.organization_id == organization_id)
    )
    settings = settings_result.scalar_one_or_none()

    # Plan-based default limits
    PLAN_LIMITS = {
        "starter": {"monthly_tickets": 500, "monthly_ai_runs": 500, "monthly_api_requests": 10000},
        "pro": {"monthly_tickets": 5000, "monthly_ai_runs": 5000, "monthly_api_requests": 100000},
        "enterprise": {"monthly_tickets": 50000, "monthly_ai_runs": 50000, "monthly_api_requests": 1000000},
    }
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["starter"])

    # Allow org settings to override plan defaults
    if settings and settings.settings:
        limits.update(settings.settings.get("usage_limits", {}))

    usage = {
        "tickets_created": record.tickets_created,
        "ai_runs_executed": record.ai_runs_executed,
        "api_requests": record.api_requests,
    }

    return {
        "period": period,
        "plan": plan,
        "usage": usage,
        "limits": limits,
        "remaining": {
            "tickets": max(0, limits["monthly_tickets"] - record.tickets_created),
            "ai_runs": max(0, limits["monthly_ai_runs"] - record.ai_runs_executed),
            "api_requests": max(0, limits["monthly_api_requests"] - record.api_requests),
        },
    }

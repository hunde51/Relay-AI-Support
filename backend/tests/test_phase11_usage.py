"""Phase 11 — Usage Tracking tests."""
import asyncio

from app.db.seed import DEFAULT_ORG_ID
from app.services.usage_service import (
    estimate_cost,
    get_current_period,
    get_or_create_record,
    increment_api_requests,
    increment_tickets_created,
    increment_ai_runs,
    get_usage_summary,
    get_usage_history,
    get_usage_limits,
    get_ai_costs_breakdown,
    MODEL_PRICING,
)


# ══════════════════════════════════════════════════════════════════════════════
# 1. Unit — cost estimation
# ══════════════════════════════════════════════════════════════════════════════


def test_estimate_cost_zero():
    assert estimate_cost(0, 0, "gemini-1.5-flash") == 0.0


def test_estimate_cost_typical():
    # 1000 prompt + 500 completion tokens @ flash pricing
    cost = estimate_cost(1000, 500, "gemini-1.5-flash")
    expected = (1000 / 1_000_000) * 0.075 + (500 / 1_000_000) * 0.300
    assert cost == round(expected, 6)


def test_estimate_cost_unknown_model_falls_back():
    cost = estimate_cost(1000, 500, "unknown-model")
    # Should use default pricing (gemini-1.5-flash)
    expected = (1000 / 1_000_000) * 0.075 + (500 / 1_000_000) * 0.300
    assert cost == round(expected, 6)


def test_estimate_cost_pro_model():
    cost = estimate_cost(1000, 500, "gemini-1.5-pro")
    expected = (1000 / 1_000_000) * 1.25 + (500 / 1_000_000) * 5.00
    assert cost == round(expected, 6)


# ══════════════════════════════════════════════════════════════════════════════
# 2. Unit — pricing table integrity
# ══════════════════════════════════════════════════════════════════════════════


def test_pricing_table_has_expected_models():
    assert "gemini-1.5-flash" in MODEL_PRICING
    assert "gemini-1.5-pro" in MODEL_PRICING
    assert "gemini-2.0-flash" in MODEL_PRICING
    for model, prices in MODEL_PRICING.items():
        assert "input_per_1m" in prices
        assert "output_per_1m" in prices
        assert prices["input_per_1m"] >= 0
        assert prices["output_per_1m"] >= 0


# ══════════════════════════════════════════════════════════════════════════════
# 3. Service — usage record CRUD
# ══════════════════════════════════════════════════════════════════════════════


def test_get_or_create_record_creates(session_factory):
    async def _check():
        async with session_factory() as db:
            period = get_current_period()
            record = await get_or_create_record(db, DEFAULT_ORG_ID, period)
            assert record.organization_id == DEFAULT_ORG_ID
            assert record.period == period
            assert record.tickets_created == 0
            assert record.ai_runs_executed == 0
            assert record.api_requests == 0
            assert record.llm_prompt_tokens == 0
            assert record.llm_completion_tokens == 0
            assert record.llm_cost_usd == 0.0

            # Same call returns existing record
            record2 = await get_or_create_record(db, DEFAULT_ORG_ID, period)
            assert record2.id == record.id

    asyncio.run(_check())


def test_increment_tickets_created(session_factory):
    async def _check():
        async with session_factory() as db:
            period = get_current_period()
            r1 = await increment_tickets_created(db, DEFAULT_ORG_ID, period)
            assert r1.tickets_created == 1

            r2 = await increment_tickets_created(db, DEFAULT_ORG_ID, period)
            assert r2.tickets_created == 2

    asyncio.run(_check())


def test_increment_api_requests(session_factory):
    async def _check():
        async with session_factory() as db:
            period = get_current_period()
            r = await increment_api_requests(db, DEFAULT_ORG_ID, period, count=5)
            assert r.api_requests == 5

    asyncio.run(_check())


def test_increment_ai_runs_and_token_counts(session_factory):
    async def _check():
        async with session_factory() as db:
            period = get_current_period()

            # Two AI runs with token counts
            r1 = await increment_ai_runs(
                db, DEFAULT_ORG_ID,
                prompt_tokens=500, completion_tokens=200,
                model="gemini-1.5-flash", period=period,
                resource_id="AIR-001",
            )
            assert r1.ai_runs_executed == 1
            assert r1.llm_prompt_tokens == 500
            assert r1.llm_completion_tokens == 200
            expected_cost = (500 / 1_000_000) * 0.075 + (200 / 1_000_000) * 0.300
            assert r1.llm_cost_usd == round(expected_cost, 6)

            r2 = await increment_ai_runs(
                db, DEFAULT_ORG_ID,
                prompt_tokens=1000, completion_tokens=400,
                model="gemini-1.5-flash", period=period,
                resource_id="AIR-002",
            )
            assert r2.ai_runs_executed == 2
            assert r2.llm_prompt_tokens == 1500
            assert r2.llm_completion_tokens == 600

    asyncio.run(_check())


# ══════════════════════════════════════════════════════════════════════════════
# 4. Service — usage summary
# ══════════════════════════════════════════════════════════════════════════════


def test_get_usage_summary(session_factory):
    async def _check():
        async with session_factory() as db:
            period = get_current_period()
            await increment_tickets_created(db, DEFAULT_ORG_ID, period)
            await increment_tickets_created(db, DEFAULT_ORG_ID, period)
            await increment_ai_runs(db, DEFAULT_ORG_ID, prompt_tokens=100, completion_tokens=50, period=period)
            await increment_api_requests(db, DEFAULT_ORG_ID, period, count=10)

            summary = await get_usage_summary(db, DEFAULT_ORG_ID, period)
            assert summary["period"] == period
            assert summary["tickets_created"] == 2
            assert summary["ai_runs_executed"] == 1
            assert summary["api_requests"] == 10
            assert summary["llm_prompt_tokens"] == 100
            assert summary["llm_completion_tokens"] == 50
            assert summary["llm_total_tokens"] == 150
            assert summary["llm_cost_usd"] > 0
            assert summary["knowledge_chunks"] >= 0
            assert summary["active_users"] >= 0

    asyncio.run(_check())


def test_get_usage_history(session_factory):
    async def _check():
        async with session_factory() as db:
            period = get_current_period()
            await increment_tickets_created(db, DEFAULT_ORG_ID, period)
            history = await get_usage_history(db, DEFAULT_ORG_ID, months=3)
            assert len(history) >= 1
            latest = history[-1]
            assert latest["period"] == period
            assert latest["tickets_created"] >= 1

    asyncio.run(_check())


def test_get_usage_limits(session_factory):
    async def _check():
        async with session_factory() as db:
            limits = await get_usage_limits(db, DEFAULT_ORG_ID)
            assert limits["period"] == get_current_period()
            assert limits["plan"] in ("starter", "pro", "enterprise")
            assert "usage" in limits
            assert "limits" in limits
            assert "remaining" in limits
            assert limits["remaining"]["tickets"] >= 0

    asyncio.run(_check())


def test_get_ai_costs_breakdown(session_factory):
    async def _check():
        async with session_factory() as db:
            period = get_current_period()
            await increment_ai_runs(
                db, DEFAULT_ORG_ID,
                prompt_tokens=500, completion_tokens=200,
                model="gemini-1.5-flash", period=period,
                resource_id="AIR-BRK1",
            )
            breakdown = await get_ai_costs_breakdown(db, DEFAULT_ORG_ID, months=3)
            assert len(breakdown) >= 1
            entry = breakdown[0]
            assert entry["period"] == period
            assert entry["model"] == "gemini-1.5-flash"
            assert entry["runs"] >= 1
            assert entry["prompt_tokens"] == 500
            assert entry["completion_tokens"] == 200
            assert entry["cost_usd"] > 0

    asyncio.run(_check())


# ══════════════════════════════════════════════════════════════════════════════
# 5. API — usage endpoints
# ══════════════════════════════════════════════════════════════════════════════


def test_usage_summary_endpoint(client, session_factory):
    headers = _admin_headers(client)

    # Seed some usage data
    async def _seed():
        async with session_factory() as db:
            await increment_tickets_created(db, DEFAULT_ORG_ID)
            await increment_api_requests(db, DEFAULT_ORG_ID, count=3)
            await db.commit()
    asyncio.run(_seed())

    resp = client.get("/usage/summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "period" in data
    assert data["tickets_created"] >= 1
    assert data["api_requests"] >= 3
    assert "ai_runs_executed" in data
    assert "llm_cost_usd" in data
    assert "knowledge_chunks" in data
    assert "active_users" in data


def test_usage_history_endpoint(client):
    headers = _admin_headers(client)
    resp = client.get("/usage/history?months=3", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_usage_ai_costs_endpoint(client):
    headers = _admin_headers(client)
    resp = client.get("/usage/ai-costs?months=3", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_usage_limits_endpoint(client):
    headers = _admin_headers(client)
    resp = client.get("/usage/limits", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "period" in data
    assert "plan" in data
    assert "usage" in data
    assert "limits" in data
    assert "remaining" in data


def test_usage_endpoints_require_auth(client):
    resp = client.get("/usage/summary")
    assert resp.status_code == 401
    resp = client.get("/usage/history")
    assert resp.status_code == 401
    resp = client.get("/usage/ai-costs")
    assert resp.status_code == 401
    resp = client.get("/usage/limits")
    assert resp.status_code == 401


def test_dashboard_includes_usage(client):
    headers = _admin_headers(client)
    resp = client.get("/dashboard/summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "usage" in data
    assert data["usage"]["tickets_created"] >= 0
    assert data["usage"]["ai_runs_executed"] >= 0


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════


def _admin_headers(client):
    resp = client.post("/auth/token", json={
        "user_id": "USR-ADMIN", "organization_id": DEFAULT_ORG_ID, "role": "admin"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

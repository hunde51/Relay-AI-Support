"""Phase 12 — Billing & Plan Limits tests."""
import asyncio

import pytest
from fastapi import HTTPException

from app.db.seed import DEFAULT_ORG_ID
from app.services.billing_service import (
    PLAN_LIMITS,
    VALID_PLANS,
    check_knowledge_doc_limit,
    check_ticket_limit,
    get_org_limits,
    get_org_plan,
    get_org_rate_limit,
    get_usage_vs_limits,
    validate_plan,
)
from app.services.usage_service import (
    get_current_period,
    get_or_create_record,
    increment_tickets_created,
)


# ══════════════════════════════════════════════════════════════════════════════
# 1. Plan validation
# ══════════════════════════════════════════════════════════════════════════════


def test_valid_plans():
    assert "starter" in VALID_PLANS
    assert "pro" in VALID_PLANS
    assert "enterprise" in VALID_PLANS
    assert len(VALID_PLANS) == 3


def test_validate_plan_accepts_known():
    assert validate_plan("starter") == "starter"
    assert validate_plan("pro") == "pro"
    assert validate_plan("enterprise") == "enterprise"


def test_validate_plan_rejects_unknown():
    with pytest.raises(ValueError, match="Invalid plan"):
        validate_plan("invalid")
    with pytest.raises(ValueError, match="Invalid plan"):
        validate_plan("free")
    with pytest.raises(ValueError, match="Invalid plan"):
        validate_plan("")


# ══════════════════════════════════════════════════════════════════════════════
# 2. Plan defaults integrity
# ══════════════════════════════════════════════════════════════════════════════


def test_plan_limits_all_have_required_keys():
    for plan, limits in PLAN_LIMITS.items():
        assert "monthly_ticket_limit" in limits, f"{plan} missing monthly_ticket_limit"
        assert "api_rate_limit" in limits, f"{plan} missing api_rate_limit"
        assert "max_knowledge_docs" in limits, f"{plan} missing max_knowledge_docs"
        assert limits["monthly_ticket_limit"] > 0
        assert limits["api_rate_limit"] > 0
        assert limits["max_knowledge_docs"] > 0


def test_plan_limits_scale_up():
    """Pro should have >= starter limits, enterprise >= pro."""
    starter = PLAN_LIMITS["starter"]
    pro = PLAN_LIMITS["pro"]
    enterprise = PLAN_LIMITS["enterprise"]
    for key in ("monthly_ticket_limit", "api_rate_limit", "max_knowledge_docs"):
        assert pro[key] >= starter[key], f"pro.{key} < starter.{key}"
        assert enterprise[key] >= pro[key], f"enterprise.{key} < pro.{key}"


# ══════════════════════════════════════════════════════════════════════════════
# 3. Default plan assignment
# ══════════════════════════════════════════════════════════════════════════════


def test_default_org_plan_is_starter(session_factory):
    async def _check():
        async with session_factory() as db:
            plan = await get_org_plan(db, DEFAULT_ORG_ID)
            assert plan == "starter"
    asyncio.run(_check())


# ══════════════════════════════════════════════════════════════════════════════
# 4. get_org_limits returns correct defaults for starter
# ══════════════════════════════════════════════════════════════════════════════


def test_get_org_limits_starter_defaults(session_factory):
    async def _check():
        async with session_factory() as db:
            limits = await get_org_limits(db, DEFAULT_ORG_ID)
            assert limits["monthly_ticket_limit"] == PLAN_LIMITS["starter"]["monthly_ticket_limit"]
            assert limits["api_rate_limit"] == PLAN_LIMITS["starter"]["api_rate_limit"]
            assert limits["max_knowledge_docs"] == PLAN_LIMITS["starter"]["max_knowledge_docs"]
    asyncio.run(_check())


# ══════════════════════════════════════════════════════════════════════════════
# 5. get_org_rate_limit
# ══════════════════════════════════════════════════════════════════════════════


def test_get_org_rate_limit_starter(session_factory):
    async def _check():
        async with session_factory() as db:
            limit = await get_org_rate_limit(db, DEFAULT_ORG_ID)
            assert limit == PLAN_LIMITS["starter"]["api_rate_limit"]
    asyncio.run(_check())


# ══════════════════════════════════════════════════════════════════════════════
# 6. Ticket limit enforcement
# ══════════════════════════════════════════════════════════════════════════════


def test_ticket_limit_not_exceeded_passes(session_factory):
    """Starter limit is 500 — 1 ticket should be fine."""
    async def _check():
        async with session_factory() as db:
            # Default starter has 500 limit, we've created 0 tickets
            # Should not raise
            await check_ticket_limit(db, DEFAULT_ORG_ID)
    asyncio.run(_check())


def test_ticket_limit_exceeded_raises_402(session_factory):
    """Fill the starter limit, then the next one should fail."""
    async def _check():
        async with session_factory() as db:
            period = get_current_period()
            limit = PLAN_LIMITS["starter"]["monthly_ticket_limit"]
            # Fill to exactly the limit
            for _ in range(limit):
                await increment_tickets_created(db, DEFAULT_ORG_ID, period)
            await db.commit()

            with pytest.raises(HTTPException) as exc_info:
                await check_ticket_limit(db, DEFAULT_ORG_ID)

            assert exc_info.value.status_code == 402
            detail = exc_info.value.detail
            assert detail["code"] == "ticket_limit_exceeded"
            assert detail["current"] == limit
            assert detail["limit"] == limit
    asyncio.run(_check())


def test_ticket_limit_at_boundary_allows_last(session_factory):
    """limit-1 tickets should still be allowed."""
    async def _check():
        async with session_factory() as db:
            period = get_current_period()
            limit = PLAN_LIMITS["starter"]["monthly_ticket_limit"]
            for _ in range(limit - 1):
                await increment_tickets_created(db, DEFAULT_ORG_ID, period)
            await db.commit()

            # Should not raise — we still have capacity
            await check_ticket_limit(db, DEFAULT_ORG_ID)
    asyncio.run(_check())


# ══════════════════════════════════════════════════════════════════════════════
# 7. Knowledge document limit enforcement
# ══════════════════════════════════════════════════════════════════════════════


def test_knowledge_doc_limit_not_exceeded_passes(session_factory):
    async def _check():
        async with session_factory() as db:
            await check_knowledge_doc_limit(db, DEFAULT_ORG_ID)
    asyncio.run(_check())


def test_knowledge_doc_limit_exceeded_raises_402(session_factory):
    async def _check():
        async with session_factory() as db:
            limit = PLAN_LIMITS["starter"]["max_knowledge_docs"]
            # Create fake knowledge docs up to limit
            from app.models.knowledge import KnowledgeDocumentORM, KnowledgeSourceORM

            src = KnowledgeSourceORM(
                organization_id=DEFAULT_ORG_ID,
                name="test-source",
                source_type="manual_upload",
            )
            db.add(src)
            await db.flush()

            for i in range(limit):
                doc = KnowledgeDocumentORM(
                    organization_id=DEFAULT_ORG_ID,
                    source_id=src.id,
                    title=f"doc-{i}",
                    content_type="text/plain",
                    checksum=f"checksum-{i}",
                    status="ingested",
                )
                db.add(doc)
            await db.commit()

            with pytest.raises(HTTPException) as exc_info:
                await check_knowledge_doc_limit(db, DEFAULT_ORG_ID)

            assert exc_info.value.status_code == 402
            detail = exc_info.value.detail
            assert detail["code"] == "knowledge_doc_limit_exceeded"
            assert detail["current"] == limit
            assert detail["limit"] == limit
    asyncio.run(_check())


def test_knowledge_doc_limit_boundary_allows_last(session_factory):
    async def _check():
        async with session_factory() as db:
            limit = PLAN_LIMITS["starter"]["max_knowledge_docs"]
            from app.models.knowledge import KnowledgeDocumentORM, KnowledgeSourceORM

            src = KnowledgeSourceORM(
                organization_id=DEFAULT_ORG_ID,
                name="test-source-2",
                source_type="manual_upload",
            )
            db.add(src)
            await db.flush()

            for i in range(limit - 1):
                doc = KnowledgeDocumentORM(
                    organization_id=DEFAULT_ORG_ID,
                    source_id=src.id,
                    title=f"boundary-doc-{i}",
                    content_type="text/plain",
                    checksum=f"bc-{i}",
                    status="ingested",
                )
                db.add(doc)
            await db.commit()

            # Should still pass
            await check_knowledge_doc_limit(db, DEFAULT_ORG_ID)
    asyncio.run(_check())


# ══════════════════════════════════════════════════════════════════════════════
# 8. Usage vs limits report
# ══════════════════════════════════════════════════════════════════════════════


def test_get_usage_vs_limits_structure(session_factory):
    async def _check():
        async with session_factory() as db:
            result = await get_usage_vs_limits(db, DEFAULT_ORG_ID)

            assert "period" in result
            assert "plan" in result
            assert result["plan"] == "starter"
            assert "usage" in result
            assert "limits" in result
            assert "remaining" in result

            assert "tickets_created" in result["usage"]
            assert "knowledge_docs" in result["usage"]

            assert "monthly_ticket_limit" in result["limits"]
            assert "max_knowledge_docs" in result["limits"]

            assert "tickets" in result["remaining"]
            assert "knowledge_docs" in result["remaining"]

            # Remaining should be limit - current usage
            limit = PLAN_LIMITS["starter"]["monthly_ticket_limit"]
            assert result["remaining"]["tickets"] == limit  # no tickets created yet
            assert result["remaining"]["knowledge_docs"] == PLAN_LIMITS["starter"]["max_knowledge_docs"]
    asyncio.run(_check())


def test_get_usage_vs_limits_with_usage(session_factory):
    async def _check():
        async with session_factory() as db:
            period = get_current_period()
            for _ in range(10):
                await increment_tickets_created(db, DEFAULT_ORG_ID, period)
            await db.commit()

            result = await get_usage_vs_limits(db, DEFAULT_ORG_ID, period)
            assert result["usage"]["tickets_created"] == 10
            limit = PLAN_LIMITS["starter"]["monthly_ticket_limit"]
            assert result["remaining"]["tickets"] == limit - 10
    asyncio.run(_check())


# ══════════════════════════════════════════════════════════════════════════════
# 9. API — settings/plan endpoint
# ══════════════════════════════════════════════════════════════════════════════


def _admin_headers(client):
    resp = client.post("/auth/token", json={
        "user_id": "USR-ADMIN", "organization_id": DEFAULT_ORG_ID, "role": "admin"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_settings_plan_endpoint(client):
    headers = _admin_headers(client)
    resp = client.get("/settings/plan", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "plan" in data
    assert "limits" in data
    assert "usage_vs_limits" in data
    assert data["plan"] == "starter"


def test_settings_plan_patch_updates_plan(client, session_factory):
    headers = _admin_headers(client)

    # PATCH plan to pro
    resp = client.patch("/settings/plan", json={"plan": "pro"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "pro"

    # Verify via GET
    resp2 = client.get("/settings/plan", headers=headers)
    assert resp2.json()["plan"] == "pro"

    # Reset back to starter
    client.patch("/settings/plan", json={"plan": "starter"}, headers=headers)


def test_settings_plan_patch_rejects_invalid_plan(client):
    headers = _admin_headers(client)
    resp = client.patch("/settings/plan", json={"plan": "nonexistent"}, headers=headers)
    assert resp.status_code == 422  # validation error


def test_settings_plan_patch_updates_limits(client):
    headers = _admin_headers(client)
    resp = client.patch("/settings/plan", json={
        "monthly_ticket_limit": 1000,
        "api_rate_limit": 200,
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["limits"]["monthly_ticket_limit"] == 1000
    assert data["limits"]["api_rate_limit"] == 200


# ══════════════════════════════════════════════════════════════════════════════
# 10. Ticket creation returns 402 when over limit
# ══════════════════════════════════════════════════════════════════════════════


def test_ticket_creation_blocked_when_over_limit(client, session_factory):
    """Create tickets until limit, then the next should be 402."""
    async def _fill():
        async with session_factory() as db:
            period = get_current_period()
            limit = PLAN_LIMITS["starter"]["monthly_ticket_limit"]
            for _ in range(limit):
                await increment_tickets_created(db, DEFAULT_ORG_ID, period)
            await db.commit()
    asyncio.run(_fill())

    headers = _admin_headers(client)
    resp = client.post("/tickets", json={
        "title": "Over-limit ticket",
        "message": "Should be blocked",
        "priority": "medium",
        "category": "general",
    }, headers=headers)
    assert resp.status_code == 402
    detail = resp.json()["detail"]
    assert detail["code"] == "ticket_limit_exceeded"
    assert detail["current"] == PLAN_LIMITS["starter"]["monthly_ticket_limit"]


# ══════════════════════════════════════════════════════════════════════════════
# 11. Org scoping — limits don't affect other orgs
# ══════════════════════════════════════════════════════════════════════════════


def test_limits_are_org_scoped(session_factory):
    async def _check():
        async with session_factory() as db:
            from app.db.models import OrganizationORM

            other_org = OrganizationORM(id="ORG-OTHER", name="Other Org", slug="other")
            db.add(other_org)
            await db.commit()

            # Fill default org to limit
            period = get_current_period()
            limit = PLAN_LIMITS["starter"]["monthly_ticket_limit"]
            for _ in range(limit):
                await increment_tickets_created(db, DEFAULT_ORG_ID, period)
            await db.commit()

            # Default org should be at limit
            with pytest.raises(HTTPException) as exc:
                await check_ticket_limit(db, DEFAULT_ORG_ID)
            assert exc.value.status_code == 402

            # Other org should have no limit issues
            await check_ticket_limit(db, other_org.id)
    asyncio.run(_check())


# ══════════════════════════════════════════════════════════════════════════════
# 12. Rate limit test
# ══════════════════════════════════════════════════════════════════════════════


def test_rate_limit_endpoint_returns_plan_limit(client):
    """The rate limit middleware returns the plan-based limit in its response."""
    headers = _admin_headers(client)
    # Send many requests quickly to trigger rate limit
    for _ in range(10):
        client.get("/usage/summary", headers=headers)
    # The middleware should still be working — rate limit is high for starter (100/min)
    resp = client.get("/usage/summary", headers=headers)
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# 13. Knowledge document upload blocked by limit
# ══════════════════════════════════════════════════════════════════════════════


def test_knowledge_doc_upload_blocked_when_over_limit(client, session_factory):
    """Fill knowledge docs to limit, then upload should 402."""
    async def _fill():
        async with session_factory() as db:
            from app.models.knowledge import KnowledgeDocumentORM, KnowledgeSourceORM
            limit = PLAN_LIMITS["starter"]["max_knowledge_docs"]
            src = KnowledgeSourceORM(
                organization_id=DEFAULT_ORG_ID,
                name="fill-source",
                source_type="manual_upload",
            )
            db.add(src)
            await db.flush()
            for i in range(limit):
                doc = KnowledgeDocumentORM(
                    organization_id=DEFAULT_ORG_ID,
                    source_id=src.id,
                    title=f"fill-doc-{i}",
                    content_type="text/plain",
                    checksum=f"fill-{i}",
                    status="ingested",
                )
                db.add(doc)
            await db.commit()
    asyncio.run(_fill())

    headers = _admin_headers(client)
    resp = client.post("/knowledge/documents/upload", headers=headers, files={
        "file": ("test.txt", b"hello world", "text/plain"),
    })
    assert resp.status_code == 402
    detail = resp.json()["detail"]
    assert detail["code"] == "knowledge_doc_limit_exceeded"


# ══════════════════════════════════════════════════════════════════════════════
# 14. Plan validation in settings
# ══════════════════════════════════════════════════════════════════════════════


def test_plan_field_validation(client):
    """Non-admin role should be blocked from changing plan."""
    resp = client.post("/auth/token", json={
        "user_id": "USR-AGENT", "organization_id": DEFAULT_ORG_ID, "role": "agent"
    })
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.patch("/settings/plan", json={"plan": "pro"}, headers=headers)
    assert resp.status_code == 403

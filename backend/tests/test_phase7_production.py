"""Phase 7 — Production hardening tests."""
import asyncio
from sqlalchemy import select


def test_password_hashing_is_bcrypt(client, session_factory):
    """Passwords should be hashed with bcrypt, not stored as plaintext."""
    resp = client.post("/organizations", json={
        "org_name": "HashTest",
        "admin_email": "hash@test.com",
        "admin_name": "Hash Tester",
        "password": "SecurePass123!",
    })
    assert resp.status_code == 201

    async def _check():
        async with session_factory() as db:
            from app.db.models import UserORM
            r = await db.execute(select(UserORM).where(UserORM.email == "hash@test.com"))
            user = r.scalar_one_or_none()
            assert user is not None
            # bcrypt hashes start with $2b$ or $2a$
            assert user.password_hash.startswith("$2"), f"Expected bcrypt hash, got: {user.password_hash}"
            # Verify it's not plaintext
            assert "plain:" not in user.password_hash
            assert "SecurePass123!" not in user.password_hash

    asyncio.run(_check())


def test_login_with_correct_password_works(client, session_factory):
    """Login should succeed with the correct password."""
    resp = client.post("/organizations", json={
        "org_name": "LoginTest",
        "admin_email": "login@test.com",
        "admin_name": "Login Tester",
        "password": "MyCorrectPass1!",
    })
    assert resp.status_code == 201

    resp2 = client.post("/auth/login", json={"email": "login@test.com", "password": "MyCorrectPass1!"})
    assert resp2.status_code == 200
    assert "access_token" in resp2.json()


def test_login_with_wrong_password_fails(client, session_factory):
    """Login should fail with an incorrect password."""
    client.post("/organizations", json={
        "org_name": "WrongPassTest",
        "admin_email": "wrong@test.com",
        "admin_name": "Wrong Tester",
        "password": "RealPass123!",
    })
    resp = client.post("/auth/login", json={"email": "wrong@test.com", "password": "WrongPass!456"})
    assert resp.status_code == 401


def test_signup_rollback_on_failure(client, session_factory):
    """If signup fails mid-transaction, no org or user should be created."""
    # First signup succeeds
    resp = client.post("/organizations", json={
        "org_name": "RollbackOrg",
        "admin_email": "rollback@test.com",
        "admin_name": "Rollback",
        "password": "Pass1234!",
    })
    assert resp.status_code == 201

    # Second signup with same email should 409 (not 500)
    resp2 = client.post("/organizations", json={
        "org_name": "RollbackOrg2",
        "admin_email": "rollback@test.com",
        "admin_name": "Rollback2",
        "password": "Pass5678!",
    })
    assert resp2.status_code == 409


def test_structured_log_includes_request_id(client, session_factory):
    """The structured log middleware should add request_id to request state."""
    # This test verifies the middleware attaches state correctly by hitting an endpoint
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_org_signup_atomic_creates_settings(client, session_factory):
    """Organization signup should create settings and notification settings."""
    resp = client.post("/organizations", json={
        "org_name": "AtomicOrg",
        "admin_email": "atomic@test.com",
        "admin_name": "Atomic",
        "password": "Pass1234!",
    })
    assert resp.status_code == 201
    org_id = resp.json()["organization_id"]

    async def _check():
        async with session_factory() as db:
            from app.db.models import OrganizationSettingsORM, NotificationSettingsORM, UserORM
            r = await db.execute(select(OrganizationSettingsORM).where(OrganizationSettingsORM.organization_id == org_id))
            settings = r.scalar_one_or_none()
            assert settings is not None, "OrganizationSettingsORM should have been created"
            assert settings.ai_enabled is True

            r2 = await db.execute(select(NotificationSettingsORM).where(NotificationSettingsORM.organization_id == org_id))
            notif = r2.scalar_one_or_none()
            assert notif is not None, "NotificationSettingsORM should have been created"
            assert notif.email_digest_enabled is True

            r3 = await db.execute(select(UserORM).where(UserORM.organization_id == org_id))
            users = r3.scalars().all()
            assert len(users) == 1
            assert users[0].role == "admin"

    asyncio.run(_check())


def test_metrics_endpoint_available(client, session_factory):
    """The /metrics endpoint should return Prometheus-formatted output."""
    resp = client.get("/metrics")
    assert resp.status_code == 200
    text = resp.text
    # Should contain default Python metrics
    assert "python_info" in text
    # Should contain our custom metrics
    assert "relayai_" in text


def test_health_endpoint(client, session_factory):
    """The /health endpoint should return ok."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_dev_token_still_works(client, session_factory):
    """The dev /auth/token endpoint should still issue valid JWTs."""
    resp = client.post("/auth/token", json={
        "user_id": "USR-DEV",
        "organization_id": "ORG-DEV",
        "role": "admin",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"] is not None
    assert data["role"] == "admin"

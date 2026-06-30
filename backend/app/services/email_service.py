"""Email integration service — Gmail & Outlook OAuth, polling, reply threading."""

import json
from datetime import UTC, datetime
from typing import Literal

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.encrypt import decrypt_token, encrypt_token
from app.db.models import (
    CustomerORM,
    EmailIntegrationORM,
    EmailMessageORM,
    TicketMessageORM,
    TicketORM,
)
from app.schemas.ticket import MessageCreate, TicketCreate
from app.services import ticket_service

_PROVIDER_GMAIL = "gmail"
_PROVIDER_OUTLOOK = "outlook"

# ── OAuth URLs ────────────────────────────────────────────────────────────────

GMAIL_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.modify"

OUTLOOK_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
OUTLOOK_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
OUTLOOK_SCOPE = "https://graph.microsoft.com/Mail.ReadWrite"


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ── OAuth URL builders ────────────────────────────────────────────────────────


def build_gmail_auth_url(state: str) -> str:
    params = (
        f"client_id={settings.GMAIL_CLIENT_ID}"
        f"&redirect_uri={settings.GMAIL_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={GMAIL_SCOPE}"
        f"&access_type=offline"
        f"&prompt=consent"
        f"&state={state}"
    )
    return f"{GMAIL_AUTH_URL}?{params}"


def build_outlook_auth_url(state: str) -> str:
    params = (
        f"client_id={settings.OUTLOOK_CLIENT_ID}"
        f"&redirect_uri={settings.OUTLOOK_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={OUTLOOK_SCOPE}"
        f"&access_type=offline"
        f"&prompt=consent"
        f"&state={state}"
    )
    return f"{OUTLOOK_AUTH_URL}?{params}"


# ── Token exchange ────────────────────────────────────────────────────────────


async def exchange_gmail_code(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GMAIL_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GMAIL_CLIENT_ID,
                "client_secret": settings.GMAIL_CLIENT_SECRET,
                "redirect_uri": settings.GMAIL_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def exchange_outlook_code(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            OUTLOOK_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.OUTLOOK_CLIENT_ID,
                "client_secret": settings.OUTLOOK_CLIENT_SECRET,
                "redirect_uri": settings.OUTLOOK_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def refresh_gmail_token(refresh_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GMAIL_TOKEN_URL,
            data={
                "client_id": settings.GMAIL_CLIENT_ID,
                "client_secret": settings.GMAIL_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def refresh_outlook_token(refresh_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            OUTLOOK_TOKEN_URL,
            data={
                "client_id": settings.OUTLOOK_CLIENT_ID,
                "client_secret": settings.OUTLOOK_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def get_gmail_email(access_token: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/profile",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()["emailAddress"]


# ── Store integration ─────────────────────────────────────────────────────────


async def store_integration(
    db: AsyncSession,
    org_id: str,
    provider: str,
    email_address: str,
    token_data: dict,
) -> EmailIntegrationORM:
    from datetime import timedelta

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 3600)

    integration = EmailIntegrationORM(
        organization_id=org_id,
        provider=provider,
        email_address=email_address,
        access_token_encrypted=encrypt_token(access_token),
        refresh_token_encrypted=encrypt_token(refresh_token) if refresh_token else "",
        token_expires_at=_utc_now().replace(tzinfo=None) + timedelta(seconds=expires_in) if expires_in else None,
    )
    db.add(integration)
    await db.commit()
    await db.refresh(integration)
    return integration


# ── Token refresh helper ──────────────────────────────────────────────────────


async def get_valid_access_token(db: AsyncSession, integration: EmailIntegrationORM) -> str:
    access = decrypt_token(integration.access_token_encrypted)
    refresh = decrypt_token(integration.refresh_token_encrypted) if integration.refresh_token_encrypted else ""

    if integration.token_expires_at and _utc_now() >= integration.token_expires_at and refresh:
        if integration.provider == _PROVIDER_GMAIL:
            token_data = await refresh_gmail_token(refresh)
        else:
            token_data = await refresh_outlook_token(refresh)
        access = token_data["access_token"]
        integration.access_token_encrypted = encrypt_token(access)
        if "refresh_token" in token_data:
            integration.refresh_token_encrypted = encrypt_token(token_data["refresh_token"])
        expires_in = token_data.get("expires_in", 3600)
        integration.token_expires_at = _utc_now().replace(tzinfo=None)
        await db.commit()

    return access


# ── Polling ────────────────────────────────────────────────────────────────────


async def poll_gmail(db: AsyncSession, integration: EmailIntegrationORM) -> int:
    """Poll Gmail for unread messages and create tickets. Returns count of new messages."""
    try:
        access = await get_valid_access_token(db, integration)
        headers = {"Authorization": f"Bearer {access}"}

        async with httpx.AsyncClient() as client:
            list_resp = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                headers=headers,
                params={"q": "is:unread", "maxResults": 20},
            )
            list_resp.raise_for_status()
            data = list_resp.json()
            msg_ids = [m["id"] for m in data.get("messages", [])]

        count = 0
        for msg_id in msg_ids:
            try:
                created = await _process_gmail_message(db, integration, msg_id, headers)
                if created:
                    count += 1
            except Exception:
                pass

        integration.last_polled_at = _utc_now()
        integration.last_error = None
        await db.commit()
        return count
    except Exception as exc:
        integration.last_error = str(exc)[:500]
        await db.commit()
        raise


async def poll_outlook(db: AsyncSession, integration: EmailIntegrationORM) -> int:
    """Poll Outlook for unread messages and create tickets. Returns count of new messages."""
    try:
        access = await get_valid_access_token(db, integration)
        headers = {"Authorization": f"Bearer {access}"}

        async with httpx.AsyncClient() as client:
            list_resp = await client.get(
                "https://graph.microsoft.com/v1.0/me/messages",
                headers=headers,
                params={"$filter": "isRead eq false", "$top": 20, "$orderby": "receivedDateTime desc"},
            )
            list_resp.raise_for_status()
            data = list_resp.json()
            msgs = data.get("value", [])

        count = 0
        for msg in msgs:
            try:
                created = await _process_outlook_message(db, integration, msg, headers)
                if created:
                    count += 1
            except Exception:
                pass

        integration.last_polled_at = _utc_now()
        integration.last_error = None
        await db.commit()
        return count
    except Exception as exc:
        integration.last_error = str(exc)[:500]
        await db.commit()
        raise


async def _process_gmail_message(
    db: AsyncSession, integration: EmailIntegrationORM, msg_id: str, headers: dict
) -> bool:
    # Dedup
    existing = await db.execute(
        select(EmailMessageORM).where(EmailMessageORM.provider_message_id == msg_id)
    )
    if existing.scalar_one_or_none():
        return False

    async with httpx.AsyncClient() as client:
        get_resp = await client.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
            headers=headers,
            params={"format": "full"},
        )
        get_resp.raise_for_status()
        msg = get_resp.json()

    headers_list = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
    subject = headers_list.get("subject", "(no subject)")
    from_ = headers_list.get("from", "")
    thread_id = msg.get("threadId", msg_id)
    body = _extract_gmail_body(msg)

    if not from_ or not body:
        return False

    org_id = integration.organization_id
    email_lower = _parse_email(from_)

    # Upsert customer
    customer = await _upsert_customer(db, org_id, email_lower, from_)

    # Create ticket
    ticket = await ticket_service.create_ticket(
        db,
        TicketCreate(title=subject, message=body),
        source="email_gmail",
        customer_id=customer.id,
        current_user=None,
        organization_id=org_id,
    )

    # Record email message
    db.add(EmailMessageORM(
        email_integration_id=integration.id,
        ticket_id=ticket.id,
        provider_message_id=msg_id,
        provider_thread_id=thread_id,
        from_address=email_lower,
        to_address=integration.email_address,
        subject=subject,
        body_text=body,
        direction="inbound",
    ))

    # Mark as read
    await _gmail_mark_read(headers, msg_id)

    await db.commit()
    return True


async def _process_outlook_message(
    db: AsyncSession, integration: EmailIntegrationORM, msg: dict, headers: dict
) -> bool:
    msg_id = msg.get("id", "")
    existing = await db.execute(
        select(EmailMessageORM).where(EmailMessageORM.provider_message_id == msg_id)
    )
    if existing.scalar_one_or_none():
        return False

    subject = msg.get("subject", "(no subject)")
    from_addr = msg.get("from", {}).get("emailAddress", {}).get("address", "")
    from_name = msg.get("from", {}).get("emailAddress", {}).get("name", "")
    thread_id = msg.get("conversationId", msg_id)
    body = msg.get("body", {}).get("content", "") or msg.get("bodyPreview", "")

    if not from_addr or not body:
        return False

    org_id = integration.organization_id
    email_lower = from_addr.lower().strip()

    customer = await _upsert_customer(db, org_id, email_lower, from_name or from_addr)

    ticket = await ticket_service.create_ticket(
        db,
        TicketCreate(title=subject, message=body),
        source="email_outlook",
        customer_id=customer.id,
        current_user=None,
        organization_id=org_id,
    )

    db.add(EmailMessageORM(
        email_integration_id=integration.id,
        ticket_id=ticket.id,
        provider_message_id=msg_id,
        provider_thread_id=thread_id,
        from_address=email_lower,
        to_address=integration.email_address,
        subject=subject,
        body_text=body,
        direction="inbound",
    ))

    # Mark as read
    await _outlook_mark_read(headers, msg_id)

    await db.commit()
    return True


# ── Reply threading ───────────────────────────────────────────────────────────


async def send_reply(db: AsyncSession, ticket_id: str, body: str) -> bool:
    """Send a reply to an email-sourced ticket via the correct provider."""
    ticket = await db.get(TicketORM, ticket_id)
    if not ticket or ticket.source not in ("email_gmail", "email_outlook"):
        return False

    email_msg_result = await db.execute(
        select(EmailMessageORM)
        .where(EmailMessageORM.ticket_id == ticket_id, EmailMessageORM.direction == "inbound")
        .order_by(EmailMessageORM.created_at.asc())
        .limit(1)
    )
    email_msg = email_msg_result.scalar_one_or_none()
    if not email_msg:
        return False

    integration = await db.get(EmailIntegrationORM, email_msg.email_integration_id)
    if not integration or not integration.is_active:
        return False

    access = await get_valid_access_token(db, integration)
    thread_id = email_msg.provider_thread_id

    if integration.provider == _PROVIDER_GMAIL:
        await _gmail_send_reply(access, integration.email_address, email_msg.from_address, thread_id, body, email_msg.provider_message_id)
    else:
        await _outlook_send_reply(access, thread_id, body, email_msg.provider_message_id)

    db.add(EmailMessageORM(
        email_integration_id=integration.id,
        ticket_id=ticket_id,
        provider_message_id=f"reply-{_utc_now().timestamp()}",
        provider_thread_id=thread_id,
        from_address=integration.email_address,
        to_address=email_msg.from_address,
        subject=f"Re: {email_msg.subject}",
        body_text=body,
        direction="outbound",
    ))
    await db.commit()
    return True


async def _gmail_send_reply(access: str, from_email: str, to_email: str, thread_id: str, body: str, in_reply_to: str):
    raw_message = _build_gmail_reply(from_email, to_email, body, thread_id, in_reply_to)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={"Authorization": f"Bearer {access}"},
            json={"raw": raw_message, "threadId": thread_id},
        )
        resp.raise_for_status()


async def _outlook_send_reply(access: str, thread_id: str, body: str, in_reply_to: str):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://graph.microsoft.com/v1.0/me/messages/{in_reply_to}/reply",
            headers={"Authorization": f"Bearer {access}"},
            json={"comment": body},
        )
        resp.raise_for_status()


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _upsert_customer(db: AsyncSession, org_id: str, email: str, display_name: str) -> CustomerORM:
    existing = await db.execute(
        select(CustomerORM).where(
            CustomerORM.organization_id == org_id,
            CustomerORM.email == email,
        )
    )
    customer = existing.scalar_one_or_none()
    if customer:
        return customer
    customer = CustomerORM(
        organization_id=org_id,
        name=display_name,
        email=email,
    )
    db.add(customer)
    await db.flush()
    return customer


def _parse_email(from_header: str) -> str:
    """Extract email address from a 'Name <email>' header."""
    if "<" in from_header:
        return from_header.split("<")[1].rstrip(">").lower().strip()
    return from_header.lower().strip()


def _extract_gmail_body(msg: dict) -> str:
    payload = msg.get("payload", {})
    parts = payload.get("parts") or [payload]
    for part in parts:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            import base64
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
        if part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
            import base64
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
    snippet = msg.get("snippet", "")
    return snippet


def _build_gmail_reply(from_email: str, to_email: str, body: str, thread_id: str, in_reply_to: str) -> str:
    import base64
    message = (
        f"From: {from_email}\r\n"
        f"To: {to_email}\r\n"
        f"Subject: \r\n"
        f"In-Reply-To: {in_reply_to}\r\n"
        f"References: {in_reply_to}\r\n"
        f"\r\n"
        f"{body}"
    )
    return base64.urlsafe_b64encode(message.encode()).decode()


async def _gmail_mark_read(headers: dict, msg_id: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}/modify",
            headers=headers,
            json={"removeLabelIds": ["UNREAD"]},
        )


async def _outlook_mark_read(headers: dict, msg_id: str):
    async with httpx.AsyncClient() as client:
        await client.patch(
            f"https://graph.microsoft.com/v1.0/me/messages/{msg_id}",
            headers=headers,
            json={"isRead": True},
        )


async def get_integration(db: AsyncSession, integration_id: str, org_id: str) -> EmailIntegrationORM | None:
    result = await db.execute(
        select(EmailIntegrationORM).where(
            EmailIntegrationORM.id == integration_id,
            EmailIntegrationORM.organization_id == org_id,
        )
    )
    return result.scalar_one_or_none()


async def update_integration(
    db: AsyncSession, integration_id: str, org_id: str, is_active: bool | None = None
) -> EmailIntegrationORM | None:
    integration = await get_integration(db, integration_id, org_id)
    if not integration:
        return None
    if is_active is not None:
        integration.is_active = is_active
    await db.commit()
    await db.refresh(integration)
    return integration


async def get_integrations_for_org(db: AsyncSession, org_id: str) -> list[EmailIntegrationORM]:
    result = await db.execute(
        select(EmailIntegrationORM)
        .where(EmailIntegrationORM.organization_id == org_id)
        .order_by(EmailIntegrationORM.created_at.desc())
    )
    return result.scalars().all()


async def disconnect_integration(db: AsyncSession, integration_id: str, org_id: str) -> bool:
    result = await db.execute(
        select(EmailIntegrationORM).where(
            EmailIntegrationORM.id == integration_id,
            EmailIntegrationORM.organization_id == org_id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        return False
    await db.delete(integration)
    await db.commit()
    return True

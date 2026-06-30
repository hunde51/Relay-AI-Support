"""Widget API — authenticated with widget keys and session tokens."""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.widget_key_service import verify_widget_key
from app.services.widget_service import create_widget_ticket, add_widget_message, check_widget_origin
from app.services.widget_session import verify_session
from app.services.ticket_service import get_ticket, get_messages

router = APIRouter(prefix="/widget", tags=["widget"])


# ── Request / Response models ──────────────────────────────────────────────────

class WidgetTicketCreate(BaseModel):
    name: str
    email: str
    message: str
    page_url: str | None = None
    browser_context: dict | None = None


class WidgetTicketResponse(BaseModel):
    ticket_id: str
    session_token: str
    status: str
    created_at: str


class WidgetMessageCreate(BaseModel):
    body: str


class WidgetMessageResponse(BaseModel):
    message_id: str | None
    body: str
    created_at: str


class WidgetTicketState(BaseModel):
    id: str
    status: str
    messages: list  # simplified message list


# ── Dependency: resolve widget key from X-Widget-Key header ──────────────────

async def _get_widget_key(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    raw_key = request.headers.get("x-widget-key") or request.headers.get("X-Widget-Key")
    if not raw_key:
        raise HTTPException(status_code=401, detail="X-Widget-Key required")

    key = await verify_widget_key(db, raw_key)
    if not key:
        raise HTTPException(status_code=401, detail="Invalid or revoked widget key")

    # Enforce allowed origins
    origin = request.headers.get("origin")
    if not check_widget_origin(key, origin):
        raise HTTPException(
            status_code=403,
            detail=f"Origin '{origin}' is not allowed for this widget key",
        )

    return {
        "organization_id": key.organization_id,
        "key_id": key.id,
        "allowed_origins": key.allowed_origins,
    }


# ── Dependency: resolve session token ─────────────────────────────────────────

async def _get_session_ticket(
    request: Request,
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
) -> str:
    token = request.headers.get("x-session-token") or request.headers.get("X-Session-Token")
    if not token:
        raise HTTPException(status_code=401, detail="X-Session-Token required")

    session = verify_session(token, expected_ticket_id=ticket_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    return session["organization_id"]


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/tickets", status_code=201, response_model=WidgetTicketResponse)
async def widget_create_ticket(
    data: WidgetTicketCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    widget_key: dict = Depends(_get_widget_key),
):
    result = await create_widget_ticket(
        db,
        # We need the ORM object for origin checks; but we have the dict from
        # the dependency.  Re-fetch the key ORM from the DB inside the service.
        # Actually, let's just pass the raw key to the service — best to re-fetch.
        # Simpler: pass organization_id directly, origin check already done.
        organization_id=widget_key["organization_id"],
        visitor_name=data.name,
        visitor_email=data.email,
        message=data.message,
        page_url=data.page_url,
        browser_context=data.browser_context,
    )
    return result


@router.get("/tickets/{ticket_id}", response_model=WidgetTicketState)
async def widget_get_ticket(
    ticket_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    org_id: str = Depends(_get_session_ticket),
):
    ticket = await get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    msgs = await get_messages(db, ticket_id)
    messages_list = [
        {
            "id": m.id,
            "sender_type": m.sender_type,
            "body": m.body,
            "is_internal": m.is_internal,
            "created_at": m.created_at.isoformat() if hasattr(m.created_at, "isoformat") else str(m.created_at),
        }
        for m in msgs
        if not m.is_internal  # widget visitors don't see internal notes
    ]

    return WidgetTicketState(
        id=ticket.id,
        status=ticket.status,
        messages=messages_list,
    )


@router.post("/tickets/{ticket_id}/messages", status_code=201)
async def widget_add_message(
    ticket_id: str,
    data: WidgetMessageCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    org_id: str = Depends(_get_session_ticket),
):
    ticket = await get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    result = await add_widget_message(db, ticket_id, org_id, data.body)
    return result

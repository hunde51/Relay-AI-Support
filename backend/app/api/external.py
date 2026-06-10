"""External API — authenticated with X-API-Key, used by company backends."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.ticket import TicketCreate, TicketResponse
from app.services import ticket_service

router = APIRouter(prefix="/v1", tags=["external"])


def _require_api_key(request: Request) -> dict:
    user = getattr(request.state, "current_user", None)
    if not user or user.get("auth_method") != "api_key":
        raise HTTPException(status_code=401, detail="X-API-Key required")
    if "tickets:write" not in (user.get("scopes") or []):
        raise HTTPException(status_code=403, detail="tickets:write scope required")
    return user


class ExternalTicketCreate(BaseModel):
    title: str
    message: str
    priority: str = "medium"
    category: str = "general"
    customer_email: str | None = None
    customer_name: str | None = None
    customer_external_id: str | None = None


@router.post("/tickets", status_code=201, response_model=TicketResponse)
async def external_create_ticket(
    data: ExternalTicketCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    current_user = _require_api_key(request)
    org_id = current_user["organization_id"]

    ticket_data = TicketCreate(
        title=data.title,
        message=data.message,
        priority=data.priority,  # type: ignore[arg-type]
        category=data.category,  # type: ignore[arg-type]
    )
    # inject org_id + source via current_user so ticket_service picks them up
    current_user["source"] = "api"
    return await ticket_service.create_ticket(db, ticket_data, current_user=current_user)


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def external_get_ticket(
    ticket_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    current_user = _require_api_key(request)
    if "tickets:read" not in (current_user.get("scopes") or []):
        raise HTTPException(status_code=403, detail="tickets:read scope required")
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.organization_id != current_user["organization_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    return ticket

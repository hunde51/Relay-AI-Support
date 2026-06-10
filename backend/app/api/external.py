"""External API — authenticated with X-API-Key, used by company backends."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.ticket import TicketCreate, TicketResponse
from app.services import ticket_service
from app.services.api_key_service import verify_api_key

router = APIRouter(prefix="/v1", tags=["external"])


async def _api_key_user(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    """Resolve X-API-Key header using the DI-provided DB session."""
    raw_key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
    if not raw_key:
        raise HTTPException(status_code=401, detail="X-API-Key required")
    key = await verify_api_key(db, raw_key)
    if not key:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    return {
        "auth_method": "api_key",
        "organization_id": key.organization_id,
        "scopes": key.scopes,
        "key_id": key.id,
        "role": "api_key",
    }


class ExternalTicketCreate(BaseModel):
    title: str
    message: str
    priority: str = "medium"
    category: str = "general"


@router.post("/tickets", status_code=201, response_model=TicketResponse)
async def external_create_ticket(
    data: ExternalTicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(_api_key_user),
):
    if "tickets:write" not in (current_user.get("scopes") or []):
        raise HTTPException(status_code=403, detail="tickets:write scope required")
    current_user["source"] = "api"
    ticket_data = TicketCreate(
        title=data.title,
        message=data.message,
        priority=data.priority,  # type: ignore[arg-type]
        category=data.category,  # type: ignore[arg-type]
    )
    return await ticket_service.create_ticket(db, ticket_data, current_user=current_user)


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def external_get_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(_api_key_user),
):
    if "tickets:read" not in (current_user.get("scopes") or []):
        raise HTTPException(status_code=403, detail="tickets:read scope required")
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.organization_id != current_user["organization_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    return ticket

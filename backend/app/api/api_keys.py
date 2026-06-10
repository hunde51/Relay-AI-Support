from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import get_db
from app.db.models import ApiKeyORM
from app.services import api_key_service

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def _require_admin_or_manager(user: dict):
    if user.get("role") not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="admin or manager role required")


def _key_response(key: ApiKeyORM, full_key: str | None = None) -> dict:
    r = {
        "id": key.id,
        "name": key.name,
        "key_prefix": key.key_prefix,
        "scopes": key.scopes,
        "is_active": key.is_active,
        "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
        "expires_at": key.expires_at.isoformat() if key.expires_at else None,
        "created_at": key.created_at.isoformat(),
    }
    if full_key:
        r["key"] = full_key  # shown once only
    return r


class CreateKeyRequest(BaseModel):
    name: str
    scopes: list[str] | None = None


@router.get("")
async def list_keys(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _require_admin_or_manager(current_user)
    org_id = current_user["organization_id"]
    keys = await api_key_service.list_api_keys(db, org_id)
    return [_key_response(k) for k in keys]


@router.post("", status_code=201)
async def create_key(
    data: CreateKeyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _require_admin_or_manager(current_user)
    org_id = current_user["organization_id"]
    user_id = current_user.get("user_id")
    key, full_key = await api_key_service.create_api_key(
        db, org_id, data.name, scopes=data.scopes, created_by_user_id=user_id
    )
    return _key_response(key, full_key=full_key)


@router.delete("/{key_id}", status_code=204)
async def revoke_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="admin role required")
    org_id = current_user["organization_id"]
    ok = await api_key_service.revoke_api_key(db, key_id, org_id)
    if not ok:
        raise HTTPException(status_code=404, detail="API key not found")


@router.post("/{key_id}/rotate", status_code=201)
async def rotate_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _require_admin_or_manager(current_user)
    org_id = current_user["organization_id"]
    result = await api_key_service.rotate_api_key(db, key_id, org_id)
    if not result:
        raise HTTPException(status_code=404, detail="API key not found")
    key, full_key = result
    return _key_response(key, full_key=full_key)

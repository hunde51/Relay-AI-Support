from app.db.seed import DEFAULT_ORG_ID


def resolve_org_id(current_user: dict | None = None, fallback: str = DEFAULT_ORG_ID) -> str:
    if current_user and current_user.get("organization_id"):
        return current_user["organization_id"]
    return fallback


def assert_org_access(resource_org_id: str | None, current_user: dict | None = None) -> None:
    if current_user and resource_org_id and resource_org_id != resolve_org_id(current_user):
        raise PermissionError("Forbidden")

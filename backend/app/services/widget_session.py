"""Widget session token management.

Session tokens are used by widget visitors for follow-up message submission,
ticket polling, and WebSocket access. Stored in-memory by default; swap in a
Redis backend for multi-process production deployments.
"""
from __future__ import annotations

import secrets
import time
from typing import TypedDict


class SessionData(TypedDict):
    ticket_id: str
    organization_id: str
    created_at: float


_sessions: dict[str, SessionData] = {}
SESSION_TTL = 86400  # 24 hours


def create_session(ticket_id: str, organization_id: str) -> str:
    """Generate a new session token and store it."""
    token = secrets.token_urlsafe(32)
    _sessions[token] = SessionData(
        ticket_id=ticket_id,
        organization_id=organization_id,
        created_at=time.time(),
    )
    return token


def verify_session(token: str, expected_ticket_id: str | None = None) -> SessionData | None:
    """Look up a session token. Optionally verify it matches a specific ticket."""
    data = _sessions.get(token)
    if not data:
        return None
    if time.time() - data["created_at"] > SESSION_TTL:
        del _sessions[token]
        return None
    if expected_ticket_id is not None and data["ticket_id"] != expected_ticket_id:
        return None
    return data


def revoke_session(token: str) -> None:
    _sessions.pop(token, None)

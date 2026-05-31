import json
import re
from typing import Literal, TypedDict

from sqlalchemy.ext.asyncio import AsyncSession


class AgentState(TypedDict):
    # ── Input ──────────────────────────────────────────────────────────────
    ticket_id: str
    organization_id: str
    ai_run_id: str
    # injected so nodes can write steps to DB in real-time
    db: AsyncSession

    # ── Ticket context (loaded by load_ticket_context) ─────────────────────
    title: str
    message: str
    category: str
    priority: str
    customer_id: str | None
    assignee_id: str | None
    ticket_context_loaded: bool

    # ── Classification (classify_ticket) ──────────────────────────────────
    classified_category: str
    intent: str
    confidence: float

    # ── Sentiment (detect_sentiment_and_urgency) ───────────────────────────
    sentiment: str          # neutral | frustrated | angry | satisfied
    urgency: str            # low | medium | high
    sla_risk: bool

    # ── Knowledge (retrieve_knowledge) ────────────────────────────────────
    knowledge_results: list[dict]   # chunk_id, document_id, source, content, score
    has_relevant_knowledge: bool

    # ── Customer history (check_customer_history) ─────────────────────────
    repeat_issue: bool
    recent_escalations: int

    # ── Decision (decide_next_action) ─────────────────────────────────────
    decision: Literal[
        "resolve", "ask_customer", "escalate",
        "draft_only", "add_internal_note", "no_action"
    ]
    decision_confidence: float
    risk_level: str         # low | medium | high
    decision_reason: str

    # ── Response drafting ─────────────────────────────────────────────────
    response: str
    citations: list[str]    # chunk_ids
    validation_valid: bool
    validation_issues: list[str]

    # ── Escalation ────────────────────────────────────────────────────────
    escalation_team: str
    escalation_note: str

    # ── Suggested action ──────────────────────────────────────────────────
    suggested_action_id: str
    requires_approval: bool

    # ── Step log (for WS streaming) ───────────────────────────────────────
    steps: list[dict]

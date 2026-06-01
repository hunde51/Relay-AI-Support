"""
Phase 5 — 14-node LangGraph agent implementation.

Node order:
  load_ticket_context
  -> classify_ticket
  -> detect_sentiment_and_urgency
  -> retrieve_knowledge
  -> check_customer_history
  -> decide_next_action
  -> route_by_decision  (conditional edge)
       resolve / draft_only  -> draft_response -> validate_response -> create_suggested_action
       ask_customer          -> draft_clarifying_question -> validate_response -> create_suggested_action
       escalate              -> prepare_escalation -> create_suggested_action
       add_internal_note     -> draft_response -> validate_response -> create_suggested_action
       no_action             -> persist_ai_run
  create_suggested_action -> determine_approval_required -> persist_ai_run -> notify_frontend
"""

import json
import re
from datetime import UTC, datetime

from sqlalchemy import select

from app.ai_engine.llm import get_llm
from app.ai_engine.state import AgentState
from app.core.ws_manager import manager
from app.db.models import AIStepORM, TicketORM, TicketMessageORM, CustomerORM, AIRunORM, AISuggestedActionORM
from app.services.rag_service import search_knowledge
from app.services.tool_service import invoke_tool


def _utc_now():
    return datetime.now(UTC).replace(tzinfo=None)


def _parse_json(text: str, fallback: dict) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return fallback


async def _emit(state: AgentState, step_name: str, message: str, extra: dict | None = None) -> dict:
    """Persist step to DB and stream to frontend."""
    step = {"step": step_name, "message": message, **(extra or {})}

    db = state["db"]
    orm = AIStepORM(
        ai_run_id=state["ai_run_id"],
        step_name=step_name,
        status="completed",
        output=step,
        confidence=str(extra.get("confidence", "")) if extra else "",
        started_at=_utc_now(),
        completed_at=_utc_now(),
    )
    db.add(orm)
    await db.flush()

    await manager.stream_ai_step(state["ticket_id"], step)
    return step


# ── Node 1 ────────────────────────────────────────────────────────────────────

async def load_ticket_context(state: AgentState) -> AgentState:
    db = state["db"]

    result = await db.execute(select(TicketORM).where(TicketORM.id == state["ticket_id"]))
    ticket = result.scalar_one_or_none()

    msgs_result = await db.execute(
        select(TicketMessageORM)
        .where(TicketMessageORM.ticket_id == state["ticket_id"])
        .order_by(TicketMessageORM.created_at)
        .limit(10)
    )
    messages = msgs_result.scalars().all()
    message_text = "\n".join(f"[{m.sender_type}] {m.body}" for m in messages) if messages else state["message"]

    step = await _emit(state, "load_ticket_context", "Ticket context loaded")

    return {
        **state,
        "title": ticket.title if ticket else state["title"],
        "message": message_text or state["message"],
        "category": ticket.category if ticket else state["category"],
        "priority": ticket.priority if ticket else state["priority"],
        "customer_id": ticket.customer_id if ticket else None,
        "assignee_id": ticket.assignee_id if ticket else None,
        "ticket_context_loaded": True,
        "steps": state.get("steps", []) + [step],
    }


# ── Node 2 ────────────────────────────────────────────────────────────────────

async def classify_ticket(state: AgentState) -> AgentState:
    prompt = f"""Classify this support ticket. Reply with JSON only.

Title: {state['title']}
Message: {state['message']}

Output schema:
{{"category": "billing|technical|account|general", "intent": "short_snake_case_intent", "confidence": 0.0-1.0}}"""

    from app.ai_engine.prompts import ClassifyOutput, render_and_validate

    parsed = await render_and_validate(prompt, ClassifyOutput, {"category": state["category"], "intent": "unknown", "confidence": 0.5})

    # Handle potential LLM-requested tool calls (function-calling like behavior)
    try:
        from app.ai_engine.tool_integration import handle_llm_tool_requests
        tool_results = await handle_llm_tool_requests(state, result.content)
        if tool_results:
            # Attach to state
            state_tool_calls = state.get("tool_calls", [])
            state_tool_calls.append(tool_results)
            state["tool_calls"] = state_tool_calls
    except Exception:
        pass

    step = await _emit(state, "classify_ticket",
        f"Category: {parsed['category']}, intent: {parsed['intent']}",
        {"confidence": parsed["confidence"]})

    return {
        **state,
        "classified_category": parsed["category"],
        "intent": parsed["intent"],
        "confidence": float(parsed["confidence"]),
        "steps": state["steps"] + [step],
    }


# ── Node 3 ────────────────────────────────────────────────────────────────────

async def detect_sentiment_and_urgency(state: AgentState) -> AgentState:
    llm = get_llm()
    prompt = f"""Analyze the sentiment and urgency of this support ticket. Reply with JSON only.

Title: {state['title']}
Message: {state['message']}
Priority: {state['priority']}

Output schema:
{{"sentiment": "neutral|frustrated|angry|satisfied", "urgency": "low|medium|high", "sla_risk": true|false, "confidence": 0.0-1.0}}"""

    from app.ai_engine.prompts import SentimentOutput, render_and_validate

    parsed = await render_and_validate(prompt, SentimentOutput, {"sentiment": "neutral", "urgency": "medium", "sla_risk": False, "confidence": 0.5})

    step = await _emit(state, "detect_sentiment_and_urgency",
        f"Sentiment: {parsed['sentiment']}, urgency: {parsed['urgency']}",
        {"confidence": parsed["confidence"]})

    return {
        **state,
        "sentiment": parsed["sentiment"],
        "urgency": parsed["urgency"],
        "sla_risk": bool(parsed["sla_risk"]),
        "steps": state["steps"] + [step],
    }


# ── Node 4 ────────────────────────────────────────────────────────────────────

async def retrieve_knowledge(state: AgentState) -> AgentState:
    query = f"{state['title']} {state['message']}"
    # Use the tool service to perform a knowledge search so the call is persisted and streamed
    try:
        res = await invoke_tool(state["db"], state.get("ai_run_id", ""), state.get("ticket_id"), "search_knowledge", {"query": query, "top_k": 4, "organization_id": state.get("organization_id")})
        results = res.get("results", [])
    except Exception:
        # Fallback to direct search if tool invocation fails
        results = await search_knowledge(query, top_k=4, organization_id=state["organization_id"])

    step = await _emit(state, "retrieve_knowledge",
        f"Retrieved {len(results)} chunks, has_relevant_knowledge={bool(results)}")

    return {
        **state,
        "knowledge_results": results,
        "has_relevant_knowledge": bool(results),
        "steps": state["steps"] + [step],
    }


# ── Node 5 ────────────────────────────────────────────────────────────────────

async def check_customer_history(state: AgentState) -> AgentState:
    db = state["db"]
    repeat_issue = False
    recent_escalations = 0

    if state.get("customer_id"):
        # Count recent tickets for this customer
        from sqlalchemy import func
        count_result = await db.execute(
            select(func.count()).select_from(TicketORM).where(
                TicketORM.customer_id == state["customer_id"],
                TicketORM.id != state["ticket_id"],
            )
        )
        past_count = count_result.scalar_one()
        repeat_issue = past_count > 0

        # Count escalated tickets
        esc_result = await db.execute(
            select(func.count()).select_from(TicketORM).where(
                TicketORM.customer_id == state["customer_id"],
                TicketORM.status == "closed",
                TicketORM.priority.in_(["high", "critical"]),
            )
        )
        recent_escalations = esc_result.scalar_one()

    step = await _emit(state, "check_customer_history",
        f"Repeat issue: {repeat_issue}, recent escalations: {recent_escalations}")

    return {
        **state,
        "repeat_issue": repeat_issue,
        "recent_escalations": recent_escalations,
        "steps": state["steps"] + [step],
    }


# ── Node 6 ────────────────────────────────────────────────────────────────────

async def decide_next_action(state: AgentState) -> AgentState:
    knowledge_text = "\n".join(
        f"[{r['source']}] {r['content']}" for r in state["knowledge_results"]
    ) or "No relevant knowledge found."

    prompt = f"""{BASE_SYSTEM_PROMPT}\n
You are RelayAI Support. Decide the next action for this ticket.

Ticket: {state['title']} — {state['message']}
Category: {state['classified_category']} | Intent: {state['intent']}
Sentiment: {state['sentiment']} | Urgency: {state['urgency']} | SLA risk: {state['sla_risk']}
Repeat issue: {state['repeat_issue']} | Recent escalations: {state['recent_escalations']}
Knowledge available: {state['has_relevant_knowledge']}
Knowledge:
{knowledge_text}

Choose one decision: resolve | ask_customer | escalate | draft_only | add_internal_note | no_action

Rules:
- resolve: knowledge clearly answers the issue and risk is low
- draft_only: knowledge applies but action needs human approval (billing, account, security)
- ask_customer: information is missing to resolve
- escalate: complex, angry customer, repeated issue, or high risk
- add_internal_note: no customer action needed but agent should be informed
- no_action: spam or already resolved

Reply with JSON only:
{{"decision": "...", "confidence": 0.0-1.0, "risk_level": "low|medium|high", "reason": "short reason"}}"""

    from app.ai_engine.prompts import render_and_validate_decision, BASE_SYSTEM_PROMPT

    parsed = await render_and_validate_decision(prompt, {"decision": "escalate", "confidence": 0.5, "risk_level": "medium", "reason": "parse error"})

    # Force high risk for billing/account regardless of LLM output
    category = state["classified_category"]
    sentiment = state["sentiment"]
    if category in ("billing", "account") or sentiment in ("angry", "frustrated"):
        if parsed["risk_level"] == "low":
            parsed["risk_level"] = "medium"

    step = await _emit(state, "decide_next_action",
        parsed["reason"],
        {"confidence": parsed["confidence"], "decision": parsed["decision"], "risk_level": parsed["risk_level"]})

    return {
        **state,
        "decision": parsed["decision"],
        "decision_confidence": float(parsed["confidence"]),
        "risk_level": parsed["risk_level"],
        "decision_reason": parsed["reason"],
        "steps": state["steps"] + [step],
    }


# ── Conditional router (not a node — used as edge function) ───────────────────

def route_by_decision(state: AgentState) -> str:
    d = state["decision"]
    if d in ("resolve", "draft_only", "add_internal_note"):
        return "draft_response"
    if d == "ask_customer":
        return "draft_clarifying_question"
    if d == "escalate":
        return "prepare_escalation"
    return "persist_ai_run"  # no_action


# ── Node 7 ────────────────────────────────────────────────────────────────────

async def draft_response(state: AgentState) -> AgentState:
    llm = get_llm()
    knowledge_text = "\n".join(
        f"[{r['source']}] {r['content']}" for r in state["knowledge_results"]
    ) or "No specific knowledge available."
    citations = [r["chunk_id"] for r in state["knowledge_results"] if r.get("chunk_id")]

    prompt = f"""Write a helpful, concise customer-facing support reply.
Use only the knowledge base content below. Do not invent facts.
Include citations as [source_name] inline where relevant.

Ticket: {state['title']} — {state['message']}
Knowledge:
{knowledge_text}"""

    result = await llm.ainvoke(prompt)
    step = await _emit(state, "draft_response", "Response drafted",
        {"response_preview": result.content[:120]})

    return {
        **state,
        "response": result.content.strip(),
        "citations": citations,
        "steps": state["steps"] + [step],
    }


# ── Node 8 ────────────────────────────────────────────────────────────────────

async def draft_clarifying_question(state: AgentState) -> AgentState:
    llm = get_llm()
    prompt = f"""Write a concise, polite question asking the customer for the missing information needed to resolve their issue.

Ticket: {state['title']} — {state['message']}
Intent: {state['intent']}"""

    result = await llm.ainvoke(prompt)
    step = await _emit(state, "draft_clarifying_question", "Clarifying question drafted")

    return {
        **state,
        "response": result.content.strip(),
        "citations": [],
        "steps": state["steps"] + [step],
    }


# ── Node 9 ────────────────────────────────────────────────────────────────────

async def prepare_escalation(state: AgentState) -> AgentState:
    llm = get_llm()
    prompt = f"""Write a brief internal escalation note for the support team.

Ticket: {state['title']} — {state['message']}
Category: {state['classified_category']} | Sentiment: {state['sentiment']}
Reason for escalation: {state['decision_reason']}

Reply with JSON only:
{{"team": "billing|technical|account|general", "reason": "one sentence", "internal_note": "2-3 sentence note for the agent"}}"""

    from app.ai_engine.prompts import EscalationOutput, render_and_validate

    parsed = await render_and_validate(prompt, EscalationOutput, {"team": state["classified_category"], "reason": state["decision_reason"], "internal_note": "Escalated for manual review."})

    step = await _emit(state, "prepare_escalation",
        f"Escalating to {parsed['team']} team: {parsed['reason']}")

    return {
        **state,
        "escalation_team": parsed["team"],
        "escalation_note": parsed["internal_note"],
        "response": parsed["internal_note"],
        "citations": [],
        "steps": state["steps"] + [step],
    }


# ── Node 10 ───────────────────────────────────────────────────────────────────

async def validate_response(state: AgentState) -> AgentState:
    llm = get_llm()
    prompt = f"""Validate this AI-generated support reply. Reply with JSON only.

Reply to validate:
{state['response']}

Check:
1. No invented policy, pricing, or technical facts
2. Tone is polite and professional
3. No unsafe promises (e.g. "we will refund immediately")
4. No internal reasoning or system details exposed

Output schema:
{{"valid": true|false, "issues": ["issue1", "issue2"]}}"""

    from app.ai_engine.prompts import ValidateOutput, render_and_validate

    parsed = await render_and_validate(prompt, ValidateOutput, {"valid": True, "issues": []})

    step = await _emit(state, "validate_response",
        f"Valid: {parsed['valid']}" + (f", issues: {parsed['issues']}" if parsed.get("issues") else ""))

    return {
        **state,
        "validation_valid": bool(parsed["valid"]),
        "validation_issues": parsed.get("issues", []),
        "steps": state["steps"] + [step],
    }


# ── Node 11 ───────────────────────────────────────────────────────────────────

async def create_suggested_action(state: AgentState) -> AgentState:
    db = state["db"]

    action = AISuggestedActionORM(
        ai_run_id=state["ai_run_id"],
        ticket_id=state["ticket_id"],
        action_type=state["decision"],
        payload={
            "response": state.get("response", ""),
            "citations": state.get("citations", []),
            "escalation_team": state.get("escalation_team", ""),
            "escalation_note": state.get("escalation_note", ""),
            "validation_issues": state.get("validation_issues", []),
        },
        risk_level=state["risk_level"],
        requires_approval=False,  # set by determine_approval_required
    )
    db.add(action)
    await db.flush()

    step = await _emit(state, "create_suggested_action",
        f"Suggested action created: {state['decision']}")

    return {
        **state,
        "suggested_action_id": action.id,
        "steps": state["steps"] + [step],
    }


# ── Node 12 ───────────────────────────────────────────────────────────────────

async def determine_approval_required(state: AgentState) -> AgentState:
    db = state["db"]

    requires = (
        state["risk_level"] in ("medium", "high")
        or state["decision_confidence"] < 0.85
        or state["classified_category"] in ("billing", "account")
        or state["sentiment"] in ("angry", "frustrated")
        or not state.get("validation_valid", True)
    )

    # Update the suggested action record
    if state.get("suggested_action_id"):
        result = await db.execute(
            select(AISuggestedActionORM).where(AISuggestedActionORM.id == state["suggested_action_id"])
        )
        action = result.scalar_one_or_none()
        if action:
            action.requires_approval = requires

    step = await _emit(state, "determine_approval_required",
        f"Requires human approval: {requires}")

    return {**state, "requires_approval": requires, "steps": state["steps"] + [step]}


# ── Node 13 ───────────────────────────────────────────────────────────────────

async def persist_ai_run(state: AgentState) -> AgentState:
    db = state["db"]

    result = await db.execute(select(AIRunORM).where(AIRunORM.id == state["ai_run_id"]))
    ai_run = result.scalar_one_or_none()
    if ai_run:
        ai_run.status = "completed"
        ai_run.final_decision = state["decision"]
        ai_run.confidence = str(state.get("decision_confidence", ""))
        ai_run.risk_level = state.get("risk_level", "")
        ai_run.completed_at = _utc_now()

    await db.commit()

    step = await _emit(state, "persist_ai_run", "AI run persisted")
    return {**state, "steps": state["steps"] + [step]}


# ── Node 14 ───────────────────────────────────────────────────────────────────

async def notify_frontend(state: AgentState) -> AgentState:
    await manager.broadcast_ticket({
        "event": "ai_run_completed",
        "ticket_id": state["ticket_id"],
        "run_id": state["ai_run_id"],
        "decision": state["decision"],
        "requires_approval": state.get("requires_approval", False),
        "suggested_action_id": state.get("suggested_action_id", ""),
        "status": "completed",
    })

    step = await _emit(state, "notify_frontend", "Frontend notified")
    return {**state, "steps": state["steps"] + [step]}

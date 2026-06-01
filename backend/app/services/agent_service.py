from app.ai_engine.graph import agent_graph
from app.ai_engine.state import AgentState

# In-memory store for agent results (legacy compatibility only)
_results: dict[str, dict] = {}


async def process_ticket(ticket_id: str, title: str, message: str, category: str, priority: str) -> dict:
    initial_state: AgentState = {
        "ticket_id": ticket_id,
        "organization_id": "",
        "ai_run_id": "",
        "db": None,  # legacy route; no persistence
        "title": title,
        "message": message,
        "category": category,
        "priority": priority,
        "customer_id": None,
        "assignee_id": None,
        "ticket_context_loaded": False,
        "classified_category": category,
        "intent": "",
        "confidence": 0.5,
        "sentiment": "neutral",
        "urgency": "medium",
        "sla_risk": False,
        "knowledge_results": [],
        "has_relevant_knowledge": False,
        "tool_calls": [],
        "tool_results": {},
        "repeat_issue": False,
        "recent_escalations": 0,
        "decision": "escalate",
        "decision_confidence": 0.5,
        "risk_level": "medium",
        "decision_reason": "",
        "response": "",
        "citations": [],
        "validation_valid": True,
        "validation_issues": [],
        "escalation_team": "",
        "escalation_note": "",
        "suggested_action_id": "",
        "requires_approval": True,
        "steps": [],
    }

    # Preserve legacy response shape without relying on the persistence graph.
    output = {
        "ticket_id": ticket_id,
        "decision": initial_state["decision"],
        "response": initial_state["response"],
        "steps": [],
    }
    _results[ticket_id] = output
    return output


def get_logs(ticket_id: str) -> dict | None:
    return _results.get(ticket_id)

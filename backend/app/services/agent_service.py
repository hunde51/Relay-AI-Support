from app.ai_engine.graph import agent_graph
from app.ai_engine.state import AgentState

# In-memory store for agent results (replaced by WebSocket stream in Phase 6)
_results: dict[str, dict] = {}


async def process_ticket(ticket_id: str, title: str, message: str, category: str, priority: str) -> dict:
    initial_state: AgentState = {
        "ticket_id": ticket_id,
        "title": title,
        "message": message,
        "category": category,
        "priority": priority,
        "issue_type": "",
        "knowledge_results": [],
        "decision": "escalate",
        "response": "",
        "steps": [],
    }

    result = await agent_graph.ainvoke(initial_state)

    output = {
        "ticket_id": result["ticket_id"],
        "issue_type": result["issue_type"],
        "decision": result["decision"],
        "response": result["response"],
        "steps": result["steps"],
    }
    _results[ticket_id] = output
    return output


def get_logs(ticket_id: str) -> dict | None:
    return _results.get(ticket_id)

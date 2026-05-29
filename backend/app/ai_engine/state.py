from typing import TypedDict, Literal


class AgentState(TypedDict):
    ticket_id: str
    title: str
    message: str
    category: str
    priority: str
    # filled by agents
    issue_type: str
    knowledge_results: list[dict]
    decision: Literal["resolve", "escalate", "ask"]
    response: str
    steps: list[dict]  # structured log for Phase 5

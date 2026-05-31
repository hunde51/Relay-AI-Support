from typing import TypedDict, Literal


class AgentState(TypedDict):
    ticket_id: str
    organization_id: str
    title: str
    message: str
    category: str
    priority: str
    # filled by agents
    issue_type: str
    knowledge_results: list[dict]  # each has chunk_id, document_id, source, content, score
    decision: Literal["resolve", "escalate", "ask"]
    response: str
    citations: list[str]  # chunk_ids cited in the response
    steps: list[dict]

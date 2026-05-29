from app.ai_engine.state import AgentState
from app.ai_engine.llm import get_llm
from app.services.rag_service import search_knowledge
from app.core.ws_manager import manager


async def triage_agent(state: AgentState) -> AgentState:
    llm = get_llm()
    prompt = f"""Classify this support ticket into one of: billing, technical, account, general.
Reply with only the category word.

Title: {state['title']}
Message: {state['message']}"""

    result = await llm.ainvoke(prompt)
    issue_type = result.content.strip().lower()

    step = {"step": "triage", "message": f"Classified as: {issue_type}", "confidence": 1.0}
    await manager.stream_ai_step(state["ticket_id"], step)

    return {**state, "issue_type": issue_type, "steps": state.get("steps", []) + [step]}


async def rag_agent(state: AgentState) -> AgentState:
    query = f"{state['title']} {state['message']}"
    results = await search_knowledge(query, top_k=3)

    step = {"step": "rag_retrieve", "message": f"Found {len(results)} relevant knowledge chunks", "confidence": 1.0}
    await manager.stream_ai_step(state["ticket_id"], step)

    return {**state, "knowledge_results": results, "steps": state["steps"] + [step]}


async def decision_agent(state: AgentState) -> AgentState:
    llm = get_llm()
    knowledge_text = "\n".join([r["content"] for r in state["knowledge_results"]])

    prompt = f"""You are a support AI. Based on the ticket and knowledge base, decide the action.

Ticket: {state['title']} — {state['message']}
Issue type: {state['issue_type']}
Knowledge base results:
{knowledge_text}

Reply with JSON only:
{{"decision": "resolve" | "escalate" | "ask", "confidence": 0.0-1.0, "reason": "short reason"}}"""

    result = await llm.ainvoke(prompt)

    import json, re
    raw = result.content.strip()
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    parsed = json.loads(match.group()) if match else {"decision": "escalate", "confidence": 0.5, "reason": "parse error"}

    step = {"step": "decision", "message": parsed["reason"], "confidence": parsed["confidence"], "decision": parsed["decision"]}
    await manager.stream_ai_step(state["ticket_id"], step)

    return {**state, "decision": parsed["decision"], "steps": state["steps"] + [step]}


async def action_agent(state: AgentState) -> AgentState:
    llm = get_llm()
    knowledge_text = "\n".join([r["content"] for r in state["knowledge_results"]])

    if state["decision"] == "resolve":
        prompt = f"""Write a helpful, concise support reply to resolve this ticket.
Use the knowledge base info below.

Ticket: {state['title']} — {state['message']}
Knowledge: {knowledge_text}"""
    elif state["decision"] == "escalate":
        prompt = f"""Write a polite message telling the customer their issue is being escalated to a human agent.
Ticket: {state['title']} — {state['message']}"""
    else:
        prompt = f"""Write a message asking the customer for more information to resolve their issue.
Ticket: {state['title']} — {state['message']}"""

    result = await llm.ainvoke(prompt)

    step = {"step": "action", "message": f"Action taken: {state['decision']}", "response_preview": result.content[:100]}
    await manager.stream_ai_step(state["ticket_id"], step)

    return {**state, "response": result.content.strip(), "steps": state["steps"] + [step]}


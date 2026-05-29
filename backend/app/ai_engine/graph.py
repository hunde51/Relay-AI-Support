from langgraph.graph import StateGraph, END
from app.ai_engine.state import AgentState
from app.ai_engine.agents import triage_agent, rag_agent, decision_agent, action_agent


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("triage", triage_agent)
    graph.add_node("rag_retrieve", rag_agent)
    graph.add_node("decision", decision_agent)
    graph.add_node("action", action_agent)

    graph.set_entry_point("triage")
    graph.add_edge("triage", "rag_retrieve")
    graph.add_edge("rag_retrieve", "decision")
    graph.add_edge("decision", "action")
    graph.add_edge("action", END)

    return graph.compile()


agent_graph = build_graph()

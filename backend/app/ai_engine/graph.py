from langgraph.graph import StateGraph, END
from app.ai_engine.state import AgentState
from app.ai_engine.agents import (
    load_ticket_context,
    classify_ticket,
    detect_sentiment_and_urgency,
    retrieve_knowledge,
    check_customer_history,
    decide_next_action,
    route_by_decision,
    draft_response,
    draft_clarifying_question,
    prepare_escalation,
    validate_response,
    create_suggested_action,
    determine_approval_required,
    persist_ai_run,
    notify_frontend,
)


def build_graph():
    g = StateGraph(AgentState)

    # Register all nodes
    g.add_node("load_ticket_context", load_ticket_context)
    g.add_node("classify_ticket", classify_ticket)
    g.add_node("detect_sentiment_and_urgency", detect_sentiment_and_urgency)
    g.add_node("retrieve_knowledge", retrieve_knowledge)
    g.add_node("check_customer_history", check_customer_history)
    g.add_node("decide_next_action", decide_next_action)
    g.add_node("draft_response", draft_response)
    g.add_node("draft_clarifying_question", draft_clarifying_question)
    g.add_node("prepare_escalation", prepare_escalation)
    g.add_node("validate_response", validate_response)
    g.add_node("create_suggested_action", create_suggested_action)
    g.add_node("determine_approval_required", determine_approval_required)
    g.add_node("persist_ai_run", persist_ai_run)
    g.add_node("notify_frontend", notify_frontend)

    # Linear pipeline up to decision
    g.set_entry_point("load_ticket_context")
    g.add_edge("load_ticket_context", "classify_ticket")
    g.add_edge("classify_ticket", "detect_sentiment_and_urgency")
    g.add_edge("detect_sentiment_and_urgency", "retrieve_knowledge")
    g.add_edge("retrieve_knowledge", "check_customer_history")
    g.add_edge("check_customer_history", "decide_next_action")

    # Conditional routing after decision
    g.add_conditional_edges(
        "decide_next_action",
        route_by_decision,
        {
            "draft_response": "draft_response",
            "draft_clarifying_question": "draft_clarifying_question",
            "prepare_escalation": "prepare_escalation",
            "persist_ai_run": "persist_ai_run",
        },
    )

    # Draft paths -> validate -> create_suggested_action
    g.add_edge("draft_response", "validate_response")
    g.add_edge("draft_clarifying_question", "validate_response")
    g.add_edge("validate_response", "create_suggested_action")

    # Escalation path -> create_suggested_action (no validation needed)
    g.add_edge("prepare_escalation", "create_suggested_action")

    # Final path
    g.add_edge("create_suggested_action", "determine_approval_required")
    g.add_edge("determine_approval_required", "persist_ai_run")
    g.add_edge("persist_ai_run", "notify_frontend")
    g.add_edge("notify_frontend", END)

    return g.compile()


agent_graph = build_graph()

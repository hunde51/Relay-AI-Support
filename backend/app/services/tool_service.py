from typing import Any, Callable
from sqlalchemy import select
from app.core.ws_manager import manager
from app.db.models import AIToolCallORM, AIRunORM, OrganizationSettingsORM, AISuggestedActionORM
from app.repositories import ticket_repository
from app.services import rag_service


TOOL_REGISTRY: dict[str, dict[str, Any]] = {}


def register_tool(name: str, func: Callable, tool_type: str = "read"):
    TOOL_REGISTRY[name] = {"handler": func, "type": tool_type}


async def _handler_get_ticket(db, args: dict):
    ticket_id = args.get("ticket_id")
    if not ticket_id:
        raise ValueError("ticket_id is required")
    ticket = await ticket_repository.get_by_id(db, ticket_id)
    return {
        "ticket": {
            "id": ticket.id,
            "title": ticket.title,
            "message": ticket.message,
            "status": ticket.status,
            "priority": ticket.priority,
            "category": ticket.category,
        }
    }


async def _handler_search_knowledge(db, args: dict):
    query = args.get("query", "")
    top_k = int(args.get("top_k", 4))
    org = args.get("organization_id")
    results = await rag_service.search_knowledge(query, top_k=top_k, organization_id=org)
    return {"results": results}


# Register built-in tools
register_tool("get_ticket", _handler_get_ticket, tool_type="read")
register_tool("search_knowledge", _handler_search_knowledge, tool_type="read")


# Controlled (high-risk) tool handlers — do not execute directly; create suggested action
async def _handler_resolve_ticket(db, args: dict):
    # Placeholder: resolution requires human approval via suggested action
    return {"note": "resolve requested"}


register_tool("resolve_ticket", _handler_resolve_ticket, tool_type="controlled")
register_tool("assign_ticket", _handler_resolve_ticket, tool_type="controlled")


async def invoke_tool(db, ai_run_id: str, ticket_id: str | None, tool_name: str, arguments: dict | None = None, requester_user_id: str | None = None, confidence: float | None = None, force_execute: bool = False) -> dict:
    """Persist a tool call, execute the handler, update the call record, and stream events.

    Returns the tool result as a dict.
    """
    arguments = arguments or {}
    entry = TOOL_REGISTRY.get(tool_name)
    if not entry:
        raise RuntimeError(f"Unknown tool: {tool_name}")

    # Ensure we have an ai_run_id; create a new AIRun if not provided
    if not ai_run_id:
        new_run = AIRunORM(ticket_id=ticket_id or "")
        db.add(new_run)
        await db.flush()
        ai_run_id = new_run.id

    tool_type = entry.get("type", "read")

    # For controlled tools, consult organization settings to decide whether to execute or create suggested action
    if tool_type == "controlled":
        org_id = None
        # Try to resolve organization from ai_run if available
        if ai_run_id:
            result = await db.execute(select(AIRunORM).where(AIRunORM.id == ai_run_id))
            ai_run = result.scalar_one_or_none()
            if ai_run:
                org_id = ai_run.organization_id

        # Load org settings if present
        settings = None
        if org_id:
            res = await db.execute(select(OrganizationSettingsORM).where(OrganizationSettingsORM.organization_id == org_id))
            settings = res.scalar_one_or_none()

        auto_resolve = bool(settings.ai_enabled) if settings else False
        threshold = float(settings.human_approval_threshold) if (settings and settings.human_approval_threshold) else 0.85

        should_execute = False
        if auto_resolve and confidence is not None and confidence >= threshold:
            should_execute = True

        if not should_execute and not force_execute:
            # Create suggested action instead of executing
            action = AISuggestedActionORM(
                ai_run_id=ai_run_id,
                ticket_id=ticket_id or "",
                action_type=tool_name,
                payload={"arguments": arguments},
                risk_level="high",
                requires_approval=True,
            )
            db.add(action)
            await db.flush()
            await db.commit()

            # Persist tool call record referencing the suggested action
            call = AIToolCallORM(ai_run_id=ai_run_id, step_id=None, tool_name=tool_name, arguments=arguments, result={"suggested_action_id": action.id}, status="suggested")
            db.add(call)
            await db.commit()

            await manager.stream_tool_call(ticket_id or "", {"id": call.id, "tool_name": tool_name, "status": "suggested", "suggested_action_id": action.id, "arguments": arguments})
            return {"suggested_action_id": action.id}

        # else: fall through to execute

    # For read or other types, persist a running call and execute
    call = AIToolCallORM(ai_run_id=ai_run_id, step_id=None, tool_name=tool_name, arguments=arguments, status="running")
    db.add(call)
    await db.flush()

    # Stream tool started
    await manager.stream_tool_call(ticket_id or "", {"id": call.id, "tool_name": tool_name, "status": "running", "arguments": arguments})

    try:
        handler = entry["handler"]
        result = await handler(db, arguments)

        call.result = result
        call.status = "completed"
        await db.commit()

        await manager.stream_tool_call(ticket_id or "", {"id": call.id, "tool_name": tool_name, "status": "completed", "result": result})
        return result
    except Exception as e:
        call.status = "failed"
        call.error = str(e)
        await db.commit()
        await manager.stream_tool_call(ticket_id or "", {"id": call.id, "tool_name": tool_name, "status": "failed", "error": str(e)})
        raise

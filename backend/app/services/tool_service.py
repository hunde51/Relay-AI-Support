from __future__ import annotations

from typing import Any, Callable

from sqlalchemy import func, select

from app.core.ws_manager import manager
from app.db.models import (
    AIResponseORM,
    AISuggestedActionORM,
    AIToolCallORM,
    AIRunORM,
    CustomerORM,
    IntegrationORM,
    NotificationSettingsORM,
    OrganizationSettingsORM,
    TicketEventORM,
    TicketORM,
)
from app.services import rag_service, ticket_service
from app.schemas.ticket import MessageCreate, TicketUpdate


TOOL_REGISTRY: dict[str, dict[str, Any]] = {}


def register_tool(name: str, func: Callable, tool_type: str = "read", description: str = ""):
    TOOL_REGISTRY[name] = {
        "handler": func,
        "type": tool_type,
        "description": description,
    }


async def _get_run_org_id(db, ai_run_id: str | None) -> str | None:
    if not ai_run_id:
        return None
    result = await db.execute(select(AIRunORM).where(AIRunORM.id == ai_run_id))
    run = result.scalar_one_or_none()
    return run.organization_id if run else None


async def _get_ticket_or_none(db, ticket_id: str | None) -> TicketORM | None:
    if not ticket_id:
        return None
    return await ticket_service.get_ticket(db, ticket_id)


async def _get_customer_or_none(db, customer_id: str | None) -> CustomerORM | None:
    if not customer_id:
        return None
    result = await db.execute(select(CustomerORM).where(CustomerORM.id == customer_id))
    return result.scalar_one_or_none()


async def _handler_get_ticket(db, args: dict):
    ticket = await _get_ticket_or_none(db, args.get("ticket_id"))
    if not ticket:
        raise ValueError("ticket not found")
    return {
        "ticket": {
            "id": ticket.id,
            "organization_id": ticket.organization_id,
            "customer_id": ticket.customer_id,
            "assignee_id": ticket.assignee_id,
            "title": ticket.title,
            "message": ticket.message,
            "status": ticket.status,
            "priority": ticket.priority,
            "category": ticket.category,
            "source": ticket.source,
            "sentiment": ticket.sentiment,
            "summary": ticket.summary,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at,
        }
    }


async def _handler_get_ticket_messages(db, args: dict):
    ticket_id = args.get("ticket_id")
    messages = await ticket_service.get_messages(db, ticket_id)
    return {
        "messages": [
            {
                "id": message.id,
                "ticket_id": message.ticket_id,
                "sender_type": message.sender_type,
                "sender_user_id": message.sender_user_id,
                "sender_customer_id": message.sender_customer_id,
                "body": message.body,
                "is_internal": message.is_internal,
                "created_at": message.created_at,
                "updated_at": message.updated_at,
            }
            for message in messages
        ]
    }


async def _handler_get_ticket_timeline(db, args: dict):
    ticket_id = args.get("ticket_id")
    events = await ticket_service.get_timeline(db, ticket_id)
    return {
        "events": [
            {
                "id": event.id,
                "ticket_id": event.ticket_id,
                "actor_type": event.actor_type,
                "actor_user_id": event.actor_user_id,
                "event_type": event.event_type,
                "old_value": event.old_value,
                "new_value": event.new_value,
                "metadata": event.metadata_json,
                "created_at": event.created_at,
            }
            for event in events
        ]
    }


async def _handler_get_customer_profile(db, args: dict):
    customer = await _get_customer_or_none(db, args.get("customer_id"))
    if not customer:
        raise ValueError("customer not found")
    ticket_count = (
        await db.execute(select(func.count()).select_from(TicketORM).where(TicketORM.customer_id == customer.id))
    ).scalar_one()
    open_tickets = (
        await db.execute(
            select(func.count()).select_from(TicketORM).where(
                TicketORM.customer_id == customer.id,
                TicketORM.status.in_(["open", "in_progress", "waiting_on_customer"]),
            )
        )
    ).scalar_one()
    return {
        "customer": {
            "id": customer.id,
            "organization_id": customer.organization_id,
            "name": customer.name,
            "email": customer.email,
            "external_id": customer.external_id,
            "company": customer.company,
            "metadata": customer.metadata_json,
        },
        "ticket_count": ticket_count,
        "open_tickets": open_tickets,
    }


async def _handler_get_customer_ticket_history(db, args: dict):
    customer_id = args.get("customer_id")
    result = await db.execute(
        select(TicketORM)
        .where(TicketORM.customer_id == customer_id)
        .order_by(TicketORM.created_at.desc())
    )
    tickets = result.scalars().all()
    return {
        "tickets": [
            {
                "id": ticket.id,
                "title": ticket.title,
                "status": ticket.status,
                "priority": ticket.priority,
                "category": ticket.category,
                "created_at": ticket.created_at,
                "resolved_at": ticket.resolved_at,
                "closed_at": ticket.closed_at,
            }
            for ticket in tickets
        ]
    }


async def _handler_get_organization_settings(db, args: dict):
    org_id = args.get("organization_id")
    settings = None
    notifications = None
    integrations = []

    if org_id:
        settings_result = await db.execute(
            select(OrganizationSettingsORM).where(OrganizationSettingsORM.organization_id == org_id)
        )
        settings = settings_result.scalar_one_or_none()
        notification_result = await db.execute(
            select(NotificationSettingsORM).where(NotificationSettingsORM.organization_id == org_id)
        )
        notifications = notification_result.scalar_one_or_none()
        integration_result = await db.execute(
            select(IntegrationORM).where(IntegrationORM.organization_id == org_id)
        )
        integrations = integration_result.scalars().all()

    return {
        "organization_id": org_id,
        "ai_settings": None if not settings else {
            "ai_enabled": settings.ai_enabled,
            "auto_resolve_enabled": settings.auto_resolve_enabled,
            "human_approval_threshold": settings.human_approval_threshold,
            "settings": settings.settings,
        },
        "notification_settings": None if not notifications else {
            "email_digest_enabled": notifications.email_digest_enabled,
            "slack_alerts_enabled": notifications.slack_alerts_enabled,
            "sms_incidents_enabled": notifications.sms_incidents_enabled,
            "settings": notifications.settings,
        },
        "integrations": [
            {
                "id": integration.id,
                "provider": integration.provider,
                "status": integration.status,
                "config": integration.config,
            }
            for integration in integrations
        ],
    }


async def _handler_check_policy(db, args: dict):
    org_id = args.get("organization_id")
    category = (args.get("category") or "").lower()
    sentiment = (args.get("sentiment") or "").lower()
    risk_level = (args.get("risk_level") or "medium").lower()
    confidence = float(args.get("confidence") or 0.5)
    amount = args.get("amount")

    approval_reasons: list[str] = []
    if category in {"billing", "account"}:
        approval_reasons.append("category_requires_review")
    if sentiment in {"angry", "frustrated"}:
        approval_reasons.append("customer_sentiment_requires_review")
    if confidence < 0.85:
        approval_reasons.append("low_confidence")
    if risk_level in {"medium", "high"}:
        approval_reasons.append("risk_level_requires_review")
    if amount is not None:
        approval_reasons.append("value_sensitive_action")

    org_settings = None
    if org_id:
        result = await db.execute(
            select(OrganizationSettingsORM).where(OrganizationSettingsORM.organization_id == org_id)
        )
        org_settings = result.scalar_one_or_none()
        if org_settings and not org_settings.ai_enabled:
            approval_reasons.append("ai_disabled_for_organization")

    requires_approval = bool(approval_reasons)
    if org_settings and org_settings.auto_resolve_enabled and confidence >= float(org_settings.human_approval_threshold or 0.85):
        requires_approval = False
        approval_reasons = []

    return {
        "requires_approval": requires_approval,
        "reasons": approval_reasons,
        "policy": {
            "ai_enabled": None if not org_settings else org_settings.ai_enabled,
            "auto_resolve_enabled": None if not org_settings else org_settings.auto_resolve_enabled,
            "human_approval_threshold": None if not org_settings else org_settings.human_approval_threshold,
        },
    }


async def _handler_search_knowledge(db, args: dict):
    query = args.get("query", "")
    top_k = int(args.get("top_k", 4))
    org = args.get("organization_id")
    source = args.get("source")
    results = await rag_service.search_knowledge(query, top_k=top_k, organization_id=org, source_filter=source)
    return {"results": results}


async def _handler_create_internal_note(db, args: dict):
    ticket_id = args.get("ticket_id")
    body = args.get("body") or args.get("note") or ""
    msg = await ticket_service.add_message(
        db,
        ticket_id,
        MessageCreate(body=body, is_internal=True, sender_type="agent"),
    )
    return {
        "message": {
            "id": msg.id,
            "ticket_id": msg.ticket_id,
            "body": msg.body,
            "is_internal": msg.is_internal,
        }
    }


async def _handler_draft_customer_reply(db, args: dict):
    ticket = await _get_ticket_or_none(db, args.get("ticket_id"))
    if not ticket:
        raise ValueError("ticket not found")
    query = f"{ticket.title}\n{ticket.message}"
    knowledge = await rag_service.search_knowledge(query, top_k=int(args.get("top_k", 3)), organization_id=ticket.organization_id)
    knowledge_snippets = "\n".join(f"- {item['source']}: {item['content']}" for item in knowledge)
    body = args.get("draft") or (
        f"Thanks for reaching out about {ticket.title.lower()}. "
        f"We reviewed the available guidance and recommend the following next step:\n{knowledge_snippets or '- No matching knowledge found.'}"
    )
    return {"draft": body, "citations": [item.get("chunk_id") for item in knowledge if item.get("chunk_id")]}


async def _handler_send_customer_reply(db, args: dict):
    ticket_id = args.get("ticket_id")
    body = args.get("body") or args.get("draft") or ""
    msg = await ticket_service.add_message(
        db,
        ticket_id,
        MessageCreate(body=body, is_internal=False, sender_type="agent"),
    )
    return {
        "message": {
            "id": msg.id,
            "ticket_id": msg.ticket_id,
            "body": msg.body,
            "is_internal": msg.is_internal,
        }
    }


async def _handler_update_ticket_status(db, args: dict):
    ticket_id = args.get("ticket_id")
    status = args.get("status")
    if status not in {"open", "in_progress", "waiting_on_customer", "resolved", "closed"}:
        raise ValueError("invalid status")
    ticket = await ticket_service.update_ticket(db, ticket_id, TicketUpdate(status=status))
    if not ticket:
        raise ValueError("ticket not found")
    return {"ticket": {"id": ticket.id, "status": ticket.status}}


async def _handler_update_ticket_priority(db, args: dict):
    ticket_id = args.get("ticket_id")
    priority = args.get("priority")
    if priority not in {"low", "medium", "high", "critical"}:
        raise ValueError("invalid priority")
    ticket = await ticket_service.update_ticket(db, ticket_id, TicketUpdate(priority=priority))
    if not ticket:
        raise ValueError("ticket not found")
    return {"ticket": {"id": ticket.id, "priority": ticket.priority}}


async def _handler_assign_ticket(db, args: dict):
    ticket_id = args.get("ticket_id")
    assignee_id = args.get("assignee_id")
    ticket = await ticket_service.assign_ticket(db, ticket_id, assignee_id)
    if not ticket:
        raise ValueError("ticket not found")
    return {"ticket": {"id": ticket.id, "assignee_id": ticket.assignee_id}}


async def _handler_resolve_ticket(db, args: dict):
    ticket_id = args.get("ticket_id")
    ticket = await ticket_service.resolve_ticket(db, ticket_id)
    if not ticket:
        raise ValueError("ticket not found")
    return {"ticket": {"id": ticket.id, "status": ticket.status}}


register_tool("get_ticket", _handler_get_ticket, tool_type="read", description="Fetch a ticket with its core fields.")
register_tool("get_ticket_messages", _handler_get_ticket_messages, tool_type="read", description="Fetch customer and agent messages for a ticket.")
register_tool("get_ticket_timeline", _handler_get_ticket_timeline, tool_type="read", description="Fetch the event timeline for a ticket.")
register_tool("get_customer_profile", _handler_get_customer_profile, tool_type="read", description="Fetch a customer profile and ticket counts.")
register_tool("get_customer_ticket_history", _handler_get_customer_ticket_history, tool_type="read", description="Fetch historical tickets for a customer.")
register_tool("get_organization_settings", _handler_get_organization_settings, tool_type="read", description="Fetch AI, notification, and integration settings for an org.")
register_tool("check_policy", _handler_check_policy, tool_type="read", description="Check whether a proposed action requires human approval.")
register_tool("search_knowledge", _handler_search_knowledge, tool_type="read", description="Search the knowledge base.")
register_tool("draft_customer_reply", _handler_draft_customer_reply, tool_type="write", description="Draft a customer-facing response.")
register_tool("create_internal_note", _handler_create_internal_note, tool_type="write", description="Create an internal note on a ticket.")
register_tool("send_customer_reply", _handler_send_customer_reply, tool_type="controlled", description="Send a customer reply with human approval when required.")
register_tool("update_ticket_status", _handler_update_ticket_status, tool_type="controlled", description="Update a ticket status with human approval when required.")
register_tool("update_ticket_priority", _handler_update_ticket_priority, tool_type="controlled", description="Update ticket priority with human approval when required.")
register_tool("resolve_ticket", _handler_resolve_ticket, tool_type="controlled", description="Resolve a ticket with human approval when required.")
register_tool("assign_ticket", _handler_assign_ticket, tool_type="controlled", description="Assign a ticket with human approval when required.")


async def invoke_tool(
    db,
    ai_run_id: str,
    ticket_id: str | None,
    tool_name: str,
    arguments: dict | None = None,
    requester_user_id: str | None = None,
    confidence: float | None = None,
    force_execute: bool = False,
) -> dict:
    """Persist a tool call, execute the handler, update the call record, and stream events."""
    arguments = arguments or {}
    entry = TOOL_REGISTRY.get(tool_name)
    if not entry:
        raise RuntimeError(f"Unknown tool: {tool_name}")

    if not ai_run_id:
        new_run = AIRunORM(ticket_id=ticket_id or "")
        db.add(new_run)
        await db.flush()
        ai_run_id = new_run.id

    run_org_id = await _get_run_org_id(db, ai_run_id)
    tool_type = entry.get("type", "read")

    if tool_type == "controlled":
        org_settings = None
        if run_org_id:
            result = await db.execute(
                select(OrganizationSettingsORM).where(OrganizationSettingsORM.organization_id == run_org_id)
            )
            org_settings = result.scalar_one_or_none()

        auto_resolve = bool(org_settings.ai_enabled) if org_settings else False
        threshold = float(org_settings.human_approval_threshold) if (org_settings and org_settings.human_approval_threshold) else 0.85

        should_execute = False
        if auto_resolve and confidence is not None and confidence >= threshold:
            should_execute = True

        if not should_execute and not force_execute:
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

            call = AIToolCallORM(
                ai_run_id=ai_run_id,
                step_id=None,
                tool_name=tool_name,
                arguments=arguments,
                result={"suggested_action_id": action.id},
                status="suggested",
            )
            db.add(call)
            await db.commit()

            await manager.stream_tool_call(
                ticket_id or "",
                {
                    "id": call.id,
                    "tool_name": tool_name,
                    "status": "suggested",
                    "suggested_action_id": action.id,
                    "arguments": arguments,
                },
            )
            return {"suggested_action_id": action.id}

    call = AIToolCallORM(ai_run_id=ai_run_id, step_id=None, tool_name=tool_name, arguments=arguments, status="running")
    db.add(call)
    await db.flush()

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


import re
import json
from typing import Any
from app.services.tool_service import invoke_tool


def _extract_json(text: str) -> Any | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except Exception:
        return None


async def handle_llm_tool_requests(state, llm_text: str) -> dict:
    """Parse LLM output for tool call requests and invoke tools.

    Looks for JSON in the LLM text with either {"tool": {"name":..., "arguments": {...}}}
    or {"tool_call": {...}}.
    Returns a dict with tool results keyed by tool name.
    """
    parsed = _extract_json(llm_text)
    results = {}
    if not parsed:
        return results

    call = None
    if isinstance(parsed, dict) and ("tool" in parsed or "tool_call" in parsed):
        call = parsed.get("tool") or parsed.get("tool_call")

    if call and isinstance(call, dict):
        name = call.get("name")
        args = call.get("arguments") or call.get("args") or {}
        if name:
            # invoke tool (state must include db and ai_run_id and ticket_id)
            db = state.get("db")
            ai_run_id = state.get("ai_run_id")
            ticket_id = state.get("ticket_id")
            res = await invoke_tool(db, ai_run_id, ticket_id, name, arguments=args)
            results[name] = res
    return results

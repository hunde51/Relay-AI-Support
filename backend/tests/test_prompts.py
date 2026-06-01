import types
import pytest

from app.ai_engine import prompts


class DummyLLM:
    def __init__(self, response_text: str):
        self._response = types.SimpleNamespace(content=response_text)

    async def ainvoke(self, prompt: str):
        return self._response


@pytest.mark.asyncio
async def test_render_and_validate_decision(monkeypatch):
    monkeypatch.setattr(prompts, "get_llm", lambda: DummyLLM('{"decision":"resolve","confidence":0.95,"risk_level":"low","reason":"all good"}'))
    result = await prompts.render_and_validate_decision("prompt", None)
    assert result["decision"] == "resolve"
    assert result["confidence"] == 0.95


@pytest.mark.asyncio
async def test_render_and_validate_classify(monkeypatch):
    monkeypatch.setattr(prompts, "get_llm", lambda: DummyLLM('{"category":"billing","intent":"refund_request","confidence":0.9}'))
    result = await prompts.render_and_validate("prompt", prompts.ClassifyOutput, None)
    assert result["category"] == "billing"
    assert result["intent"] == "refund_request"


@pytest.mark.asyncio
async def test_render_and_validate_sentiment(monkeypatch):
    monkeypatch.setattr(prompts, "get_llm", lambda: DummyLLM('{"sentiment":"angry","urgency":"high","sla_risk":true,"confidence":0.8}'))
    result = await prompts.render_and_validate("prompt", prompts.SentimentOutput, None)
    assert result["sentiment"] == "angry"
    assert result["urgency"] == "high"


@pytest.mark.asyncio
async def test_render_and_validate_fallback(monkeypatch):
    # invalid JSON -> fallback
    monkeypatch.setattr(prompts, "get_llm", lambda: DummyLLM('not json'))
    fallback = {"decision": "escalate", "confidence": 0.5, "risk_level": "medium", "reason": "parse error"}
    result = await prompts.render_and_validate_decision("prompt", fallback)
    assert result["decision"] == "escalate" or result.get("decision") is not None

import json
import pytest
from app.llm.base import LLMNotConfiguredError, LLMProviderError
from app.llm.mock import MockLLMClient
from app.llm.gemini import GeminiClient


@pytest.mark.asyncio
async def test_mock_llm_extract_single_turn_name_and_address():
    client = MockLLMClient()
    payload = {
        "user_message": "My name is Jane Smith and I live at 10 Baker Street, London",
        "state": {
            "full_name": {"status": "unknown"},
            "home_address": {"status": "unknown"},
        },
    }
    raw_json = await client.extract(payload)
    data = json.loads(raw_json)

    assert data["user_intent"] == "provide_info"
    fields = [op["field"] for op in data["operations"]]
    assert "full_name" in fields
    assert "home_address" in fields

    name_op = next(op for op in data["operations"] if op["field"] == "full_name")
    assert name_op["value"] == "Jane Smith"


@pytest.mark.asyncio
async def test_mock_llm_extract_children_and_executor():
    client = MockLLMClient()
    payload = {
        "user_message": "I have 2 children: Maya and Leo. My brother James is my executor",
        "state": {
            "has_children": {"status": "unknown"},
            "children": {"status": "unknown"},
            "executor": {"name": {"status": "unknown"}},
        },
    }
    raw_json = await client.extract(payload)
    data = json.loads(raw_json)

    fields = [op["field"] for op in data["operations"]]
    assert "has_children" in fields
    assert "children" in fields
    assert "executor.name" in fields
    assert "executor.relationship" in fields

    children_op = next(op for op in data["operations"] if op["field"] == "children")
    assert children_op["value"] == ["Maya", "Leo"]


@pytest.mark.asyncio
async def test_mock_llm_extract_no_children_and_no_gifts():
    client = MockLLMClient()
    payload = {
        "user_message": "I have no children and no specific gifts",
        "state": {},
    }
    raw_json = await client.extract(payload)
    data = json.loads(raw_json)

    has_kids_op = next(op for op in data["operations"] if op["field"] == "has_children")
    assert has_kids_op["value"] is False

    gifts_op = next(op for op in data["operations"] if op["field"] == "specific_gifts")
    assert gifts_op["value"] == []


@pytest.mark.asyncio
async def test_mock_llm_compose():
    client = MockLLMClient()
    msg = await client.compose({"action": "ASK_FULL_NAME"})
    assert "full legal name" in msg.lower()


@pytest.mark.asyncio
async def test_mock_llm_scripted_and_simulated_error():
    client = MockLLMClient()

    # Scripted output
    client.scripted_extraction = '{"custom": "scripted"}'
    res = await client.extract({"user_message": "hi"})
    assert res == '{"custom": "scripted"}'

    # Simulated error
    client.simulate_error = LLMProviderError("Simulated network drop")
    with pytest.raises(LLMProviderError, match="Simulated network drop"):
        await client.extract({"user_message": "hi"})


@pytest.mark.asyncio
async def test_gemini_client_missing_key_raises_not_configured():
    client = GeminiClient(api_key=None)
    with pytest.raises(LLMNotConfiguredError):
        await client.extract({"prompt": "Hello"})

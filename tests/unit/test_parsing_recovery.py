import pytest
from app.llm.base import LLMBadResponseError
from app.llm.mock import MockLLMClient
from app.llm.parsing import (
    extract_json_from_text,
    parse_extraction_response,
    extract_with_repair,
)


def test_plain_json_parsing():
    raw = '{"user_intent": "provide_info", "operations": [], "ambiguities": [], "contradictions": []}'
    result = parse_extraction_response(raw)
    assert result.user_intent == "provide_info"
    assert len(result.operations) == 0


def test_fenced_json_parsing():
    raw = """```json
{
  "user_intent": "provide_info",
  "operations": [
    {
      "op": "set",
      "field": "full_name",
      "value": "Jane Smith",
      "evidence": "Jane Smith",
      "confidence": "high",
      "is_correction": false
    }
  ],
  "ambiguities": [],
  "contradictions": []
}
```"""
    result = parse_extraction_response(raw)
    assert result.operations[0].field == "full_name"
    assert result.operations[0].value == "Jane Smith"


def test_json_with_surrounding_commentary():
    raw = """Here is the extracted information:
{
  "user_intent": "provide_info",
  "operations": [],
  "ambiguities": [],
  "contradictions": []
}
Hope this helps!"""
    result = parse_extraction_response(raw)
    assert result.user_intent == "provide_info"


def test_invalid_json_raises_bad_response_error():
    raw = "This is definitely not JSON at all."
    with pytest.raises(LLMBadResponseError):
        parse_extraction_response(raw)


@pytest.mark.asyncio
async def test_repair_succeeds_on_second_attempt():
    client = MockLLMClient()

    # First attempt: invalid JSON
    # Second attempt: valid JSON
    responses = [
        "Broken invalid json {",
        '{"user_intent": "provide_info", "operations": [{"op": "set", "field": "full_name", "value": "Jane", "evidence": "Jane"}], "ambiguities": [], "contradictions": []}',
    ]

    call_count = 0

    async def mock_extract(payload, schema=None):
        nonlocal call_count
        res = responses[call_count]
        call_count += 1
        return res

    client.extract = mock_extract

    result, err = await extract_with_repair(client, {"user_message": "My name is Jane"})
    assert err is None
    assert result is not None
    assert result.operations[0].field == "full_name"
    assert call_count == 2


@pytest.mark.asyncio
async def test_repair_fails_twice_returns_none_safely():
    client = MockLLMClient()

    async def mock_extract(payload, schema=None):
        return "Still completely broken text."

    client.extract = mock_extract

    result, err = await extract_with_repair(client, {"user_message": "Hello"})
    assert result is None
    assert err is not None
    assert "Extraction failed after repair" in err

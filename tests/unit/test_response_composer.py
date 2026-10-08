import pytest
from app.domain.planner import PlannerAction
from app.llm.base import LLMProviderError
from app.llm.mock import MockLLMClient
from app.llm.composer import ResponseComposer


@pytest.mark.asyncio
async def test_composer_all_actions_produce_valid_response():
    client = MockLLMClient()
    composer = ResponseComposer(llm_client=client)

    for action in PlannerAction:
        ctx = {}
        if action == PlannerAction.RESOLVE_CONTRADICTION:
            ctx = {"question": "Did you mean A or B?"}
        elif action == PlannerAction.CONFIRM_UNCONFIRMED:
            ctx = {"field": "home_address", "value": "10 High St"}

        response = await composer.compose_response(action=action, action_context=ctx)
        assert response is not None
        assert len(response.strip()) > 0


@pytest.mark.asyncio
async def test_composer_fallback_on_empty_llm_response():
    client = MockLLMClient()
    client.scripted_compose = "   "  # Whitespace only
    composer = ResponseComposer(llm_client=client)

    response = await composer.compose_response(
        action=PlannerAction.ASK_FULL_NAME, action_context={}
    )
    assert "full legal name" in response.lower()


@pytest.mark.asyncio
async def test_composer_fallback_on_llm_error():
    client = MockLLMClient()
    client.simulate_error = LLMProviderError("LLM API failure")
    composer = ResponseComposer(llm_client=client)

    response = await composer.compose_response(
        action=PlannerAction.ASK_EXECUTOR_NAME, action_context={}
    )
    assert "executor" in response.lower()


def test_composer_deterministic_fallback_formatting():
    client = MockLLMClient()
    composer = ResponseComposer(llm_client=client)

    # Contradiction
    c_text = composer.get_deterministic_fallback(
        PlannerAction.RESOLVE_CONTRADICTION,
        {"question": "Custom contradiction question?"},
    )
    assert c_text == "Custom contradiction question?"

    # Confirm unconfirmed
    u_text = composer.get_deterministic_fallback(
        PlannerAction.CONFIRM_UNCONFIRMED,
        {"field": "home_address", "value": "12 Baker St"},
    )
    assert "12 Baker St" in u_text

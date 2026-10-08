import pytest
from app.domain.models import Session, Field, FieldStatus
from app.llm.mock import MockLLMClient
from app.llm.base import LLMProviderError
from app.services.conversation import ConversationService


@pytest.mark.asyncio
async def test_conversation_service_multiple_fields_in_one_turn():
    mock_llm = MockLLMClient()
    service = ConversationService(llm_client=mock_llm)

    session = Session(id="sess_multi")
    user_msg = "My name is Jane Smith, I live at 10 Downing St, London, and I have no children."

    updated_session, assistant_msg, changes = await service.process_user_turn(session, user_msg)

    assert updated_session.state.full_name.value == "Jane Smith"
    assert updated_session.state.home_address.value == "10 Downing St, London"
    assert updated_session.state.has_children.value is False
    assert updated_session.state.children.status == FieldStatus.NOT_APPLICABLE
    assert len(changes) >= 3
    assert len(updated_session.messages) == 2  # 1 user, 1 assistant
    # Next question should be worldwide assets or executor
    assert "worldwide" in assistant_msg.lower() or "executor" in assistant_msg.lower()


@pytest.mark.asyncio
async def test_conversation_service_worldwide_and_named_children_multi_field():
    mock_llm = MockLLMClient()
    service = ConversationService(llm_client=mock_llm)

    session = Session(id="sess_regression_multi")
    user_msg = "I have assets around the world and I have two children named Aarav and Anaya."

    updated_session, assistant_msg, changes = await service.process_user_turn(session, user_msg)

    assert updated_session.state.covers_worldwide_assets.value is True
    assert updated_session.state.has_children.value is True
    assert updated_session.state.children.value == ["Aarav", "Anaya"]
    assert updated_session.state.additional_wishes.status == FieldStatus.UNKNOWN
    assert updated_session.state.additional_wishes.value is None
    assert len(changes) == 3



@pytest.mark.asyncio
async def test_conversation_service_contradiction_flow():
    mock_llm = MockLLMClient()
    service = ConversationService(llm_client=mock_llm)

    session = Session(
        id="sess_conflict",
        state=Session(id="base").state,
    )
    # Set has_children = False
    session.state.has_children = Field[bool](value=False, status=FieldStatus.CONFIRMED)
    session.state.children = Field[list[str]](status=FieldStatus.NOT_APPLICABLE)

    # User says: "Leave my car to my son Aarav"
    user_msg = "Leave my car to my son Aarav"
    updated_session, assistant_msg, changes = await service.process_user_turn(session, user_msg)

    # Contradiction should be pending and state not overwritten
    assert updated_session.pending_clarification is not None
    assert updated_session.pending_clarification.field == "has_children"
    assert updated_session.state.has_children.value is False
    assert "Earlier you stated that you do not have children" in assistant_msg or "clarify" in assistant_msg.lower()


@pytest.mark.asyncio
async def test_conversation_service_correction_flow():
    mock_llm = MockLLMClient()
    service = ConversationService(llm_client=mock_llm)

    session = Session(id="sess_corr")
    session.state.executor.name = Field[str](value="James Smith", status=FieldStatus.CONFIRMED)

    user_msg = "Actually, Bob Smith is my executor"
    updated_session, assistant_msg, changes = await service.process_user_turn(session, user_msg)

    assert updated_session.state.executor.name.value == "Bob Smith"
    assert any(c.kind == "correction" for c in changes)


@pytest.mark.asyncio
async def test_conversation_service_malformed_response_safe_fallback():
    mock_llm = MockLLMClient()
    service = ConversationService(llm_client=mock_llm)

    session = Session(id="sess_malformed")
    mock_llm.scripted_extraction = "TOTAL GIBBERISH THAT CANNOT BE PARSED {"

    updated_session, assistant_msg, changes = await service.process_user_turn(session, "Hello")

    # State must remain untouched
    assert updated_session.state.full_name.value is None
    assert len(changes) == 0
    assert "couldn't clearly understand" in assistant_msg.lower() or "rephrase" in assistant_msg.lower()


@pytest.mark.asyncio
async def test_conversation_service_provider_error_safe_fallback():
    mock_llm = MockLLMClient()
    service = ConversationService(llm_client=mock_llm)

    session = Session(id="sess_provider_err")
    mock_llm.simulate_error = LLMProviderError("Connection timeout")

    updated_session, assistant_msg, changes = await service.process_user_turn(session, "My name is Jane")

    # State remains untouched
    assert updated_session.state.full_name.value is None
    assert len(changes) == 0
    assert len(updated_session.messages) == 2

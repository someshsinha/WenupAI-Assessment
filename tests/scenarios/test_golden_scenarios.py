import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.domain.models import FieldStatus
from app.services.session_store import session_store
from app.llm.mock import MockLLMClient
from app.services.conversation import ConversationService


@pytest.mark.asyncio
async def test_scenario_1_happy_path_sequential():
    """
    Scenario 1: Sequential Happy Path
    Walk through all fields one-by-one until intake is complete and document is ready.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create session
        create_res = await client.post("/api/sessions")
        assert create_res.status_code == 201
        session_id = create_res.json()["session_id"]

        # 2. Provide Full Name
        turn_res = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "My full legal name is David Miller."}
        )
        assert turn_res.status_code == 200
        state = turn_res.json()["state"]
        assert state["full_name"]["value"] == "David Miller"
        assert state["full_name"]["status"] == "confirmed"

        # 3. Provide Home Address
        turn_res = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "I live at 10 Downing Street, London."}
        )
        assert turn_res.status_code == 200
        state = turn_res.json()["state"]
        assert state["home_address"]["value"] == "10 Downing Street, London"
        assert state["home_address"]["status"] == "confirmed"

        # 4. Provide Worldwide Assets
        turn_res = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "Yes, I have assets worldwide."}
        )
        assert turn_res.status_code == 200
        state = turn_res.json()["state"]
        assert state["covers_worldwide_assets"]["value"] is True
        assert state["covers_worldwide_assets"]["status"] == "confirmed"

        # 5. Provide Children (No children)
        turn_res = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "I have no children."}
        )
        assert turn_res.status_code == 200
        state = turn_res.json()["state"]
        assert state["has_children"]["value"] is False
        assert state["has_children"]["status"] == "confirmed"
        assert state["children"]["status"] == "not_applicable"

        # 6. Provide Executor
        turn_res = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "My executor is my brother James Miller."}
        )
        assert turn_res.status_code == 200
        state = turn_res.json()["state"]
        assert state["executor"]["name"]["value"] == "James Miller"
        assert state["executor"]["name"]["status"] == "confirmed"

        # 7. Provide Specific Gifts (None)
        turn_res = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "I do not have any specific gifts."}
        )
        assert turn_res.status_code == 200
        state = turn_res.json()["state"]
        assert state["specific_gifts"]["status"] == "confirmed"

        # 8. Provide Additional Wishes (None)
        turn_res = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "No additional wishes."}
        )
        assert turn_res.status_code == 200
        state = turn_res.json()["state"]
        assert state["additional_wishes"]["status"] == "confirmed"

        # Check Final Document
        doc_res = await client.get(f"/api/sessions/{session_id}/document")
        assert doc_res.status_code == 200
        doc_data = doc_res.json()
        assert doc_data["is_complete"] is True
        assert "NOT LEGAL ADVICE" in doc_data["text"]
        assert "David Miller" in doc_data["text"]
        assert "10 Downing Street, London" in doc_data["text"]


@pytest.mark.asyncio
async def test_scenario_2_multi_field_atomic():
    """
    Scenario 2: Multi-Field Single Turn
    Provide multiple pieces of information in one sentence; ensure atomic extraction and reducer update.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_res = await client.post("/api/sessions")
        session_id = create_res.json()["session_id"]

        turn_res = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "I have assets around the world and I have two children named Aarav and Anaya."}
        )
        assert turn_res.status_code == 200
        state = turn_res.json()["state"]
        assert state["covers_worldwide_assets"]["value"] is True
        assert state["has_children"]["value"] is True
        assert "Aarav" in state["children"]["value"]
        assert "Anaya" in state["children"]["value"]
        # Ensure additional_wishes was not polluted
        assert state["additional_wishes"]["value"] is None


@pytest.mark.asyncio
async def test_scenario_3_contradiction_pause_and_resolve():
    """
    Scenario 3: Contradiction Detection, Pause Mutation, and Explicit Resolution
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_res = await client.post("/api/sessions")
        session_id = create_res.json()["session_id"]

        # Step 1: Confirm has children with Aarav & Anaya
        await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "I have two children named Aarav and Anaya."}
        )
        session_obj = await session_store.get(session_id)
        assert session_obj.state.has_children.status == FieldStatus.CONFIRMED
        assert session_obj.state.has_children.value is True

        # Step 2: Unacknowledged negation creates a contradiction and pauses state update
        turn_res = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "Actually, I don't have any children."}
        )
        assert turn_res.status_code == 200
        data = turn_res.json()
        assert data["pending_clarification"] is not None
        assert data["pending_clarification"]["issue_type"] == "contradiction"
        # State must NOT be mutated silently
        assert data["state"]["has_children"]["value"] is True
        assert "Aarav" in data["state"]["children"]["value"]

        # Step 3: Resolve contradiction with explicit correction
        turn_res_resolved = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "Correction: I made a mistake earlier, I do not have children."}
        )
        assert turn_res_resolved.status_code == 200
        resolved_data = turn_res_resolved.json()
        assert resolved_data["pending_clarification"] is None
        assert resolved_data["state"]["has_children"]["value"] is False
        assert resolved_data["state"]["children"]["status"] == "not_applicable"


@pytest.mark.asyncio
async def test_scenario_4_mid_session_explicit_correction():
    """
    Scenario 4: Mid-Session Explicit Correction
    User explicitly corrects a confirmed field; system updates state with kind="correction".
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_res = await client.post("/api/sessions")
        session_id = create_res.json()["session_id"]

        # Step 1: Set address
        await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "I live at 10 Downing Street, London."}
        )
        session_obj = await session_store.get(session_id)
        assert session_obj.state.home_address.value == "10 Downing Street, London"

        # Step 2: Explicit correction to Baker Street
        turn_res = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "Correction: I moved, my address is 221B Baker Street, London."}
        )
        assert turn_res.status_code == 200
        state = turn_res.json()["state"]
        assert state["home_address"]["value"] == "221B Baker Street, London"
        assert state["home_address"]["status"] == "confirmed"
        # Verify changes recorded correction
        changes = turn_res.json()["changes"]
        assert any(ch["field"] == "home_address" and ch["kind"] == "correction" for ch in changes)


@pytest.mark.asyncio
async def test_scenario_5_invalid_input_rejection():
    """
    Scenario 5: Unrelated Chit-Chat & Hallucinated Operations Rejection
    Irrelevant talk without grounded facts must not mutate domain state.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_res = await client.post("/api/sessions")
        session_id = create_res.json()["session_id"]

        turn_res = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "The weather today is really lovely and sunny!"}
        )
        assert turn_res.status_code == 200
        state = turn_res.json()["state"]
        assert state["full_name"]["status"] == "unknown"
        assert state["home_address"]["status"] == "unknown"
        assert turn_res.json()["changes"] == []


@pytest.mark.asyncio
async def test_scenario_6_conditional_cascade_rules():
    """
    Scenario 6: Conditional Cascades
    has_children=False -> children=NOT_APPLICABLE.
    Subsequent change to has_children=True -> resets children to UNKNOWN.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_res = await client.post("/api/sessions")
        session_id = create_res.json()["session_id"]

        # Step 1: Explicit no children
        turn_res = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "I do not have children."}
        )
        assert turn_res.status_code == 200
        state = turn_res.json()["state"]
        assert state["has_children"]["value"] is False
        assert state["children"]["status"] == "not_applicable"

        # Step 2: Explicit correction to having children
        turn_res = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "Correction: I have two children named Aarav and Anaya."}
        )
        assert turn_res.status_code == 200
        state = turn_res.json()["state"]
        assert state["has_children"]["value"] is True
        assert state["children"]["value"] == ["Aarav", "Anaya"]
        assert state["children"]["status"] == "confirmed"


@pytest.mark.asyncio
async def test_scenario_7_direct_manual_override():
    """
    Scenario 7: Direct Manual Override via PATCH /api/sessions/{id}/state
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_res = await client.post("/api/sessions")
        session_id = create_res.json()["session_id"]

        # Directly patch full_name
        patch_res = await client.patch(
            f"/api/sessions/{session_id}/state",
            json={
                "field": "full_name",
                "op": "set",
                "value": "Alice Cooper"
            }
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["state"]["full_name"]["value"] == "Alice Cooper"

        # Check document preview immediately reflects change
        doc_res = await client.get(f"/api/sessions/{session_id}/document")
        assert "Alice Cooper" in doc_res.json()["text"]


@pytest.mark.asyncio
async def test_scenario_8_llm_failure_recovery():
    """
    Scenario 8: LLM Failure Recovery
    Simulated LLM network/provider exception falls back safely and does not crash or corrupt session.
    """
    failing_llm = MockLLMClient()
    failing_llm.simulate_error = Exception("API rate limit or connection timeout")
    conv_service = ConversationService(llm_client=failing_llm)

    session_obj = await session_store.create()
    session, assistant_message, changes = await conv_service.process_user_turn(session_obj, "Hello assistant")

    assert assistant_message != ""
    assert session.state.full_name.status == FieldStatus.UNKNOWN

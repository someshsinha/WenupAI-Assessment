import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.domain.models import FieldStatus
from app.services.session_store import session_store
from app.llm.mock import MockLLMClient
from app.services.conversation import ConversationService


@pytest.mark.asyncio
async def test_regression_unformatted_address_accepted_without_infinite_loop():
    """
    Bug 1 Regression:
    Unformatted locations / institutional addresses (e.g. 'allbakaspur' or
    'International Institute of Information Technology , Pune') must be accepted as home_address
    when asked, advancing the planner to the next field instead of repeating the address question.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create Session
        res = await client.post("/api/sessions")
        session_id = res.json()["session_id"]

        # 2. Provide Name
        await client.post(f"/api/sessions/{session_id}/messages", json={"message": "Gandu Sharma"})

        # 3. Provide Unformatted Institutional Address
        turn_res = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "International Institute of Information Technology , Pune"}
        )
        assert turn_res.status_code == 200
        data = turn_res.json()
        assert data["state"]["home_address"]["value"] == "International Institute of Information Technology , Pune"
        assert data["state"]["home_address"]["status"] == "confirmed"
        # Verify planner advances to next field (worldwide assets or has_children) and does NOT ask for address again
        assert "address" not in data["assistant_message"].lower()


@pytest.mark.asyncio
async def test_regression_executor_relationship_descriptor_not_stored_as_name():
    """
    Bug 2 Regression:
    Phrases like 'My mistress', 'my lover', 'my future wife' must be stored strictly under
    executor.relationship, leaving executor.name UNKNOWN and asking for the actual personal name.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/sessions")
        session_id = res.json()["session_id"]

        # Provide Name & Address & Worldwide Assets & No Children
        await client.post(f"/api/sessions/{session_id}/messages", json={"message": "John Doe"})
        await client.post(f"/api/sessions/{session_id}/messages", json={"message": "123 Main St, London"})
        await client.post(f"/api/sessions/{session_id}/messages", json={"message": "Yes, worldwide assets"})
        await client.post(f"/api/sessions/{session_id}/messages", json={"message": "No children"})

        # User provides relationship description without personal name
        turn_res = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "I would like to appoint my mistress as the executor of my personal wishes"}
        )
        assert turn_res.status_code == 200
        data = turn_res.json()
        assert data["state"]["executor"]["relationship"]["value"] == "mistress"
        assert data["state"]["executor"]["relationship"]["status"] == "confirmed"
        assert data["state"]["executor"]["name"]["value"] is None
        assert data["state"]["executor"]["name"]["status"] == "unknown"

        # User later provides the real name and spouse relationship
        turn_res2 = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "Her name is Emily , she is my spouse"}
        )
        assert turn_res2.status_code == 200
        data2 = turn_res2.json()
        assert data2["state"]["executor"]["name"]["value"] == "Emily"
        assert data2["state"]["executor"]["name"]["status"] == "confirmed"
        assert data2["state"]["executor"]["relationship"]["value"] == "spouse"


@pytest.mark.asyncio
async def test_regression_contradiction_resolution_not_stuck_in_infinite_loop():
    """
    Bug 3 Regression:
    When a pending clarification is flagged for conflicting information, responding with
    a valid clarifying statement (e.g. 'None of these is correct , my executor's name is Emily and she is my wife')
    must clear pending_clarification, record the valid state, and advance the conversation.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/sessions")
        session_id = res.json()["session_id"]

        # Step 1: Confirm executor name as Alice
        await client.post(f"/api/sessions/{session_id}/messages", json={"message": "My name is John Doe"})
        await client.post(f"/api/sessions/{session_id}/messages", json={"message": "London"})
        await client.post(f"/api/sessions/{session_id}/messages", json={"message": "No worldwide assets"})
        await client.post(f"/api/sessions/{session_id}/messages", json={"message": "No children"})
        await client.post(f"/api/sessions/{session_id}/messages", json={"message": "My executor is Alice"})

        # Step 2: Unacknowledged conflict triggers contradiction
        turn_res = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "My executor is Bob"}
        )
        data = turn_res.json()
        assert data["pending_clarification"] is not None
        assert data["pending_clarification"]["issue_type"] == "contradiction"

        # Step 3: User clarifies and provides the actual correct name
        turn_res_clarified = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "None of these is correct , my executor's name is Emily and she is my wife"}
        )
        assert turn_res_clarified.status_code == 200
        data_clarified = turn_res_clarified.json()
        assert data_clarified["pending_clarification"] is None
        assert data_clarified["state"]["executor"]["name"]["value"] == "Emily"
        assert data_clarified["state"]["executor"]["name"]["status"] == "confirmed"
        assert data_clarified["state"]["executor"]["relationship"]["value"] == "wife"

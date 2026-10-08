import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_api_session_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create Session
        res = await client.post("/api/sessions")
        assert res.status_code == 201
        data = res.json()
        session_id = data["session_id"]
        assert session_id is not None

        # 2. Get Session State
        res = await client.get(f"/api/sessions/{session_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["session_id"] == session_id
        assert data["state"]["full_name"]["status"] == "unknown"
        assert not data["is_complete"]
        assert "NOT LEGAL ADVICE" in data["document"]["text"]

        # 3. Send Message (multi-field)
        msg_payload = {
            "message": "My name is Jane Smith, I live at 10 Downing St, London, and I have no children."
        }
        res = await client.post(f"/api/sessions/{session_id}/messages", json=msg_payload)
        assert res.status_code == 200
        turn_data = res.json()
        assert turn_data["state"]["full_name"]["value"] == "Jane Smith"
        assert turn_data["state"]["home_address"]["value"] == "10 Downing St, London"
        assert turn_data["state"]["has_children"]["value"] is False
        assert turn_data["state"]["children"]["status"] == "not_applicable"
        assert len(turn_data["changes"]) >= 3
        assert "Jane Smith" in turn_data["document"]["text"]

        # 4. Get Document Endpoint
        res = await client.get(f"/api/sessions/{session_id}/document")
        assert res.status_code == 200
        doc_data = res.json()
        assert "Jane Smith" in doc_data["text"]
        assert "I declare that I have no children." in doc_data["text"]

        # 5. Delete Session
        res = await client.delete(f"/api/sessions/{session_id}")
        assert res.status_code == 200

        # 6. Verify 404 after deletion
        res = await client.get(f"/api/sessions/{session_id}")
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_api_multi_field_worldwide_and_children_regression():
    """Regression test for multi-field message containing worldwide assets and spelled-out children count."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        res = await client.post("/api/sessions")
        session_id = res.json()["session_id"]

        # Send multi-field message
        msg = "I have assets around the world and I have two children named Aarav and Anaya."
        res = await client.post(f"/api/sessions/{session_id}/messages", json={"message": msg})
        assert res.status_code == 200
        data = res.json()

        # Verify worldwide assets captured
        assert data["state"]["covers_worldwide_assets"]["value"] is True
        assert data["state"]["covers_worldwide_assets"]["status"] == "confirmed"

        # Verify has_children and children list captured
        assert data["state"]["has_children"]["value"] is True
        assert data["state"]["has_children"]["status"] == "confirmed"
        assert data["state"]["children"]["value"] == ["Aarav", "Anaya"]
        assert data["state"]["children"]["status"] == "confirmed"

        # Verify additional_wishes was NOT polluted
        assert data["state"]["additional_wishes"]["status"] == "unknown"
        assert data["state"]["additional_wishes"]["value"] is None

        # Verify document contains children and worldwide coverage
        doc_text = data["document"]["text"]
        assert "WORLDWIDE" in doc_text
        assert "Aarav" in doc_text
        assert "Anaya" in doc_text


@pytest.mark.asyncio
async def test_api_has_children_true_then_user_says_no_children_contradiction_regression():
    """Regression test: has_children=true confirmed -> user says 'Actually, I don't have any children.' -> contradiction generated, state unchanged."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        res = await client.post("/api/sessions")
        session_id = res.json()["session_id"]

        # Step 1: Set has_children=true and children
        await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "I have two children named Aarav and Anaya"},
        )

        # Step 2: Send negation statement
        res = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "Actually, I don't have any children."},
        )
        assert res.status_code == 200
        data = res.json()

        # Must flag pending clarification with contradiction
        assert data["pending_clarification"] is not None
        assert data["pending_clarification"]["field"] == "has_children"
        assert data["pending_clarification"]["issue_type"] == "contradiction"

        # State must remain confirmed true and children preserved until resolved
        assert data["state"]["has_children"]["value"] is True
        assert data["state"]["children"]["value"] == ["Aarav", "Anaya"]
        assert "Aarav" in data["document"]["text"]


@pytest.mark.asyncio
async def test_api_has_children_false_then_user_mentions_son_contradiction_regression():
    """Regression test: has_children=false confirmed -> user says 'I actually have a son named Aarav' -> contradiction generated, state unchanged."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        res = await client.post("/api/sessions")
        session_id = res.json()["session_id"]

        # Step 1: Set has_children=false
        await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "I have no children"},
        )

        # Step 2: User says "I actually have a son named Aarav."
        res = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "I actually have a son named Aarav."},
        )
        assert res.status_code == 200
        data = res.json()

        # Must flag pending clarification with contradiction
        assert data["pending_clarification"] is not None
        assert data["pending_clarification"]["field"] == "has_children"
        assert data["pending_clarification"]["issue_type"] == "contradiction"

        # State remains false until resolved
        assert data["state"]["has_children"]["value"] is False




@pytest.mark.asyncio
async def test_api_unknown_session_returns_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/sessions/non_existent_id")
        assert res.status_code == 404

        res = await client.post(
            "/api/sessions/non_existent_id/messages",
            json={"message": "Hello"},
        )
        assert res.status_code == 404

        res = await client.delete("/api/sessions/non_existent_id")
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_api_empty_message_returns_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        res = await client.post("/api/sessions")
        session_id = res.json()["session_id"]

        # Send empty message
        res = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": ""},
        )
        assert res.status_code == 422

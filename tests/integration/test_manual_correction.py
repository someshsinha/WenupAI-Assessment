import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_manual_correction_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create session
        res = await client.post("/api/sessions")
        session_id = res.json()["session_id"]

        # 2. Apply initial manual edit for full_name
        patch_payload = {
            "field": "full_name",
            "op": "set",
            "value": "Arthur Pendelton",
        }
        res = await client.patch(f"/api/sessions/{session_id}/state", json=patch_payload)
        assert res.status_code == 200
        data = res.json()

        assert data["state"]["full_name"]["value"] == "Arthur Pendelton"
        assert data["state"]["full_name"]["status"] == "confirmed"
        assert "Arthur Pendelton" in data["document"]["text"]
        assert len(data["changes"]) == 1
        assert data["changes"][0]["kind"] == "set" or data["changes"][0]["kind"] == "correction"
        assert data["changes"][0]["evidence"] == "Manual UI Edit"

        # 3. Direct correction of executor.relationship and executor.name
        await client.patch(
            f"/api/sessions/{session_id}/state",
            json={"field": "executor.name", "op": "set", "value": "Galahad"},
        )
        res = await client.patch(
            f"/api/sessions/{session_id}/state",
            json={"field": "executor.relationship", "op": "set", "value": "trusted friend"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["state"]["executor"]["name"]["value"] == "Galahad"
        assert data["state"]["executor"]["relationship"]["value"] == "trusted friend"
        assert "trusted friend, Galahad" in data["document"]["text"]


@pytest.mark.asyncio
async def test_manual_correction_rejects_invalid_field_or_type():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/sessions")
        session_id = res.json()["session_id"]

        # Invalid field
        res = await client.patch(
            f"/api/sessions/{session_id}/state",
            json={"field": "favorite_color", "op": "set", "value": "Purple"},
        )
        assert res.status_code == 422

        # Invalid type (string for boolean)
        res = await client.patch(
            f"/api/sessions/{session_id}/state",
            json={"field": "covers_worldwide_assets", "op": "set", "value": "NotABool"},
        )
        assert res.status_code == 422


@pytest.mark.asyncio
async def test_manual_correction_on_non_existent_session_returns_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.patch(
            "/api/sessions/unknown_sess_id/state",
            json={"field": "full_name", "op": "set", "value": "Test"},
        )
        assert res.status_code == 404

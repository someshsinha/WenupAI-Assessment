import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_frontend_index_html_serving():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        content = response.text
        assert "Wenup Intake Assistant" in content
        assert "column-chat" in content
        assert "column-state" in content
        assert "column-doc" in content
        assert "chat-input" in content


@pytest.mark.asyncio
async def test_frontend_static_assets():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Check styles.css
        css_res = await client.get("/styles.css")
        assert css_res.status_code == 200
        assert "three-column-layout" in css_res.text

        # Check app.js
        js_res = await client.get("/app.js")
        assert js_res.status_code == 200
        assert "initSession" in js_res.text


@pytest.mark.asyncio
async def test_api_routes_preserved_alongside_static_mount():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health_res = await client.get("/api/health")
        assert health_res.status_code == 200
        data = health_res.json()
        assert data["status"] == "healthy"

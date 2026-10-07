import pytest
import httpx
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_get_health_endpoint():
    """
    Test: GET /api/v1/health
    Expected: HTTP 200 with status: ok, service: sachcheck-backend, version: 0.1.0
    """
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data == {
            "status": "ok",
            "service": "sachcheck-backend",
            "version": "0.1.0",
        }


@pytest.mark.asyncio
async def test_cors_headers_present():
    """
    Test: CORS preflight / Origin header handling
    Expected: Access-Control-Allow-Origin header returned for configured origin
    """
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


@pytest.mark.asyncio
async def test_unknown_route_returns_404():
    """
    Test: GET /api/v1/unknown-endpoint
    Expected: HTTP 404 Not Found
    """
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/nonexistent-route")
        assert response.status_code == 404

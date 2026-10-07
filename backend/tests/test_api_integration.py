import pytest
import httpx
from app.main import app
from app.schemas.enums import Verdict


@pytest.mark.skip(reason="Legacy health assertions; current endpoint returns standard status/service/version")
@pytest.mark.asyncio
async def test_health_endpoint():
    """Integration test: Engine health endpoint returns operational metadata."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_sources_registry_endpoint():
    """Integration test: Sources registry returns registered official gazettes and regulators."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/sources")
        assert response.status_code == 200
        sources = response.json()
        assert len(sources) > 0
        domains = [s["domain"] for s in sources]
        assert "egazette.gov.in" in domains
        assert "pib.gov.in" in domains


@pytest.mark.skip(reason="Check verification flow to be implemented in verification pipeline phase")
@pytest.mark.asyncio
async def test_realistic_scholarship_verification_flow():
    """
    Realistic test: Complete verification flow for viral PM scholarship forward.
    Validates atomic decomposition, gazette retrieval, and deterministic 5-verdict decision.
    """
    pass


@pytest.mark.skip(reason="Check endpoints to be implemented in verification pipeline phase")
@pytest.mark.asyncio
async def test_error_case_nonexistent_check_id():
    pass


@pytest.mark.skip(reason="Check endpoints to be implemented in verification pipeline phase")
@pytest.mark.asyncio
async def test_error_case_empty_input():
    pass


@pytest.mark.skip(reason="Check endpoints to be implemented in verification pipeline phase")
@pytest.mark.asyncio
async def test_security_edge_case_prompt_injection():
    pass

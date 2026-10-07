from unittest.mock import MagicMock, patch
import httpx
import pytest

from app.core.exceptions import InvalidInputException
from app.main import app
from app.schemas.ingestion import URLIngestionResult
from app.services.url_ingestion import (
    URLIngestionService,
    url_ingestion_service,
)


# ==============================================================================
# 1. SSRF Security & Protection Tests
# ==============================================================================

@pytest.mark.parametrize(
    "forbidden_url,reason",
    [
        ("http://127.0.0.1/", "IPv4 loopback"),
        ("http://localhost/", "Localhost hostname"),
        ("http://[::1]/", "IPv6 loopback"),
        ("http://10.0.0.1/", "RFC 1918 10/8 private network"),
        ("http://192.168.1.50/", "RFC 1918 192.168/16 private network"),
        ("http://172.16.0.1/", "RFC 1918 172.16/12 private network"),
        ("http://169.254.169.254/latest/meta-data", "AWS/GCP/Azure link-local metadata"),
        ("http://metadata.google.internal/computeMetadata/v1", "GCP metadata internal domain"),
        ("http://instance-data/latest/meta-data", "Cloud instance metadata hostname"),
    ],
)
def test_ssrf_internal_ips_and_metadata_blocked(forbidden_url, reason):
    """
    Critical security test:
    Validates that loopback, RFC 1918 private subnets, and cloud metadata endpoints
    are strictly rejected with SSRF Protection error.
    """
    with pytest.raises(InvalidInputException) as exc_info:
        url_ingestion_service.validate_and_resolve_url(forbidden_url)
    assert "SSRF Protection" in str(exc_info.value)


@pytest.mark.parametrize(
    "bad_port_url",
    [
        "http://example.com:8080/path",
        "https://example.com:8443/path",
        "http://example.com:22/ssh",
        "http://example.com:3000/internal",
        "http://example.com:6379/redis",
    ],
)
def test_ssrf_non_standard_ports_rejected(bad_port_url):
    """Ensures only standard web ports (80, 443) are accepted."""
    with pytest.raises(InvalidInputException) as exc_info:
        url_ingestion_service.validate_and_resolve_url(bad_port_url)
    assert "Forbidden port" in str(exc_info.value)


@pytest.mark.parametrize(
    "bad_scheme_url",
    [
        "ftp://ftp.example.com/file.txt",
        "file:///etc/passwd",
        "gopher://gopher.floodgap.com/",
        "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
        "javascript:alert(1)",
    ],
)
def test_non_http_schemes_rejected(bad_scheme_url):
    """Ensures only HTTP and HTTPS protocols are accepted."""
    with pytest.raises(InvalidInputException) as exc_info:
        url_ingestion_service.validate_and_resolve_url(bad_scheme_url)
    assert "Unsupported URL scheme" in str(exc_info.value)


def test_ssrf_redirect_evasion_blocked():
    """
    Critical security test:
    Validates that a public URL redirecting to internal IP (e.g. 169.254.169.254 or 127.0.0.1)
    is caught and blocked on the redirect hop.
    """
    # Mocking client to simulate open redirect to cloud metadata IP
    mock_redirect_response = MagicMock(status_code=302)
    mock_redirect_response.headers = {"location": "http://169.254.169.254/latest/meta-data"}

    service = URLIngestionService()

    with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("93.184.216.34", 80))]), \
         patch.object(httpx.Client, "get", return_value=mock_redirect_response):

        with pytest.raises(InvalidInputException) as exc_info:
            service.fetch_url("http://example.com/shortlink")

        assert "SSRF Protection" in str(exc_info.value)


# ==============================================================================
# 2. Shortened URL Resolution Test
# ==============================================================================

def test_shortened_url_expanded_and_ingested():
    """
    Validates shortened URL (e.g. https://bit.ly/example):
    Service follows redirect to target article and returns final_url.
    """
    initial_url = "https://bit.ly/example"
    destination_url = "https://example.com/article"

    mock_resp_1 = MagicMock(status_code=301)
    mock_resp_1.headers = {"location": destination_url}

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Official Scheme Announced</title>
        <meta property="og:site_name" content="National News">
        <meta property="article:published_time" content="2026-04-15T10:00:00Z">
    </head>
    <body>
        <article>
            <p>The Ministry has officially notified the new scholarship initiative today.</p>
            <p>Undergraduate students can register through the national portal.</p>
        </article>
    </body>
    </html>
    """
    mock_resp_2 = MagicMock(status_code=200, url=httpx.URL(destination_url), text=html_content, content=html_content.encode("utf-8"))

    service = URLIngestionService()

    with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("93.184.216.34", 443))]), \
         patch.object(httpx.Client, "get", side_effect=[mock_resp_1, mock_resp_2]):

        result = service.ingest_url(initial_url)

        assert result.status == "SUCCESS"
        assert result.final_url == destination_url
        assert result.title == "Official Scheme Announced"
        assert result.publisher == "National News"
        assert result.published_date == "2026-04-15"
        assert "Ministry has officially notified" in result.text


# ==============================================================================
# 3. Article Metadata & Content Extraction Test
# ==============================================================================

def test_article_metadata_extraction():
    """
    Validates title, publisher, published date, and readable body extraction
    while stripping scripts, styles, and navigation footers.
    """
    html_sample = """
    <html>
    <head>
        <meta property="og:title" content="Fact Check: WhatsApp forward on UPI ban is false">
        <meta name="publisher" content="PIB Fact Check">
        <meta name="pubdate" content="2025-10-07">
    </head>
    <body>
        <nav><a href="/">Home</a></nav>
        <script>alert('bad');</script>
        <article>
            <h1>Fact Check: WhatsApp forward on UPI ban is false</h1>
            <p>A viral message claiming the government has banned UPI transactions is completely fabricated.</p>
            <p>NPCI clarified that all digital payment systems remain fully operational.</p>
        </article>
        <footer>Copyright 2026</footer>
    </body>
    </html>
    """

    service = URLIngestionService()
    meta = service.extract_article_metadata(html_sample, "https://factcheck.gov.in/post/123")

    assert meta["title"] == "Fact Check: WhatsApp forward on UPI ban is false"
    assert meta["publisher"] == "PIB Fact Check"
    assert meta["published_date"] == "2025-10-07"
    assert "viral message claiming" in meta["text"]
    assert "alert" not in meta["text"]
    assert "Copyright" not in meta["text"]


# ==============================================================================
# 4. Dead Page Detection Test
# ==============================================================================

def test_dead_page_detection_returns_dead_status():
    """
    Validates dead page detection:
    When server responds with HTTP 404 or 410, returns status="DEAD_PAGE".
    """
    mock_404 = MagicMock(status_code=404, url=httpx.URL("https://example.com/notfound"), text="", content=b"")

    service = URLIngestionService()
    with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("93.184.216.34", 443))]), \
         patch.object(httpx.Client, "get", return_value=mock_404):

        result = service.ingest_url("https://example.com/notfound")
        assert result.status == "DEAD_PAGE"
        assert result.text == ""


# ==============================================================================
# 5. Exceeded Redirect Limit Test
# ==============================================================================

def test_exceeded_redirect_limit_raises_error():
    """Validates that infinite redirect loops are caught and rejected."""
    mock_loop = MagicMock(status_code=302)
    mock_loop.headers = {"location": "https://example.com/loop"}

    service = URLIngestionService(max_redirects=3)
    with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("93.184.216.34", 443))]), \
         patch.object(httpx.Client, "get", return_value=mock_loop):

        with pytest.raises(InvalidInputException) as exc_info:
            service.ingest_url("https://example.com/loop")
        assert "Exceeded maximum redirect limit" in str(exc_info.value)


# ==============================================================================
# 6. API Route Integration Test
# ==============================================================================

@pytest.mark.asyncio
async def test_api_url_ingest_endpoint_success():
    """Tests POST /api/v1/ingest/url via HTTP API with mocked safe external response."""
    test_html = """
    <html>
        <head><title>Government Order</title></head>
        <body><article><p>This is official verification text.</p></article></body>
    </html>
    """
    mock_resp = MagicMock(
        status_code=200,
        url=httpx.URL("https://example.gov.in/notice"),
        text=test_html,
        content=test_html.encode("utf-8"),
    )

    with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("93.184.216.34", 443))]), \
         patch.object(httpx.Client, "get", return_value=mock_resp):

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/ingest/url", json={"url": "https://example.gov.in/notice"})

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "SUCCESS"
            assert data["final_url"] == "https://example.gov.in/notice"
            assert data["title"] == "Government Order"
            assert "official verification text" in data["text"]


@pytest.mark.asyncio
async def test_api_url_ingest_endpoint_ssrf_rejected():
    """Tests POST /api/v1/ingest/url rejects SSRF attempts with HTTP 400."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/ingest/url", json={"url": "http://127.0.0.1/internal"})
        assert response.status_code == 400
        error_data = response.json()
        assert error_data["error"]["code"] == "INVALID_INPUT"
        assert "SSRF Protection" in error_data["error"]["message"]

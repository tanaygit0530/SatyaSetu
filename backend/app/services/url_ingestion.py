import ipaddress
import json
import re
import socket
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from dateutil.parser import parse as parse_date
import httpx

from app.core.config import settings
from app.core.exceptions import InvalidInputException
from app.core.logging import logger
from app.schemas.ingestion import URLIngestionInput, URLIngestionResult


BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "instance-data",
    "metadata",
}

CLOUD_METADATA_IPS = {
    "169.254.169.254",  # AWS/GCP/Azure/OpenStack metadata
    "100.100.100.200",  # Alibaba Cloud metadata
    "fd00:ec2::254",    # AWS IPv6 metadata
}


class URLIngestionService:
    """
    Secure web article and URL ingestion service.
    Enforces strict SSRF protection, DNS IP filtering, redirect revalidation,
    dead page detection, and metadata extraction.
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
        max_response_bytes: Optional[int] = None,
        max_redirects: Optional[int] = None,
    ):
        self.timeout = timeout or settings.URL_FETCH_TIMEOUT_SECONDS
        self.max_response_bytes = max_response_bytes or settings.URL_MAX_RESPONSE_BYTES
        self.max_redirects = max_redirects or settings.URL_MAX_REDIRECTS

    def validate_and_resolve_url(self, url: str) -> Tuple[str, str, int]:
        """
        Validates URL scheme, port, hostname, and ensures resolved IPs do not target
        private networks, loopback, link-local, or cloud metadata services.
        """
        if not url or not url.strip():
            raise InvalidInputException("URL cannot be empty.")

        url = url.strip()
        parsed = urllib.parse.urlparse(url)

        # 1. Only HTTP/HTTPS schemes permitted
        if parsed.scheme.lower() not in ("http", "https"):
            raise InvalidInputException(
                f"Unsupported URL scheme '{parsed.scheme}'. Only HTTP and HTTPS protocols are allowed."
            )

        # 2. Hostname validation
        hostname = parsed.hostname
        if not hostname:
            raise InvalidInputException(f"Invalid URL: missing hostname in '{url}'.")

        hostname_lower = hostname.lower()
        if (
            hostname_lower in BLOCKED_HOSTNAMES
            or hostname_lower.endswith(".internal")
            or hostname_lower.endswith(".local")
        ):
            raise InvalidInputException(
                f"SSRF Protection: Access to internal hostname '{hostname}' is strictly blocked."
            )

        # 3. Port validation (80 and 443 only)
        port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
        if port not in (80, 443):
            raise InvalidInputException(
                f"Forbidden port '{port}'. Only standard web ports (80, 443) are allowed."
            )

        # 4. Immediate IP literal validation (SSRF defense against raw IPs)
        clean_host = hostname.strip("[]")
        try:
            direct_ip = ipaddress.ip_address(clean_host)
            if (
                direct_ip.is_private
                or direct_ip.is_loopback
                or direct_ip.is_link_local
                or direct_ip.is_multicast
                or direct_ip.is_reserved
                or direct_ip.is_unspecified
                or str(direct_ip) in CLOUD_METADATA_IPS
            ):
                raise InvalidInputException(
                    f"SSRF Protection: Host '{hostname}' is a forbidden IP address '{clean_host}'."
                )
        except ValueError:
            pass

        # 5. DNS Resolution & IP Address Validation (SSRF defense for domain names)
        try:
            addr_info = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
        except socket.gaierror as dns_err:
            raise InvalidInputException(
                f"DNS resolution failed for host '{hostname}': {str(dns_err)}"
            ) from dns_err

        for entry in addr_info:
            ip_str = entry[4][0]
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                continue

            # Block private, loopback, link-local, multicast, reserved
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
                or ip.is_unspecified
            ):
                raise InvalidInputException(
                    f"SSRF Protection: Host '{hostname}' resolves to forbidden IP address '{ip_str}'."
                )

            # Block cloud metadata addresses
            if str(ip) in CLOUD_METADATA_IPS:
                raise InvalidInputException(
                    f"SSRF Protection: Cloud metadata IP '{ip_str}' is strictly blocked."
                )

        return url, hostname, port

    def fetch_url(self, initial_url: str) -> Tuple[str, int, str]:
        """
        Executes HTTP GET following redirects step-by-step, revalidating every
        redirect target to prevent SSRF bypass via 30x open redirects.
        Returns (final_url, status_code, html_text).
        """
        current_url = initial_url
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; SachCheckBot/1.0; +https://sachcheck.org/bot)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        with httpx.Client(timeout=self.timeout, follow_redirects=False) as client:
            for redirect_idx in range(self.max_redirects + 1):
                # Revalidate URL and DNS IP on every hop!
                clean_url, _, _ = self.validate_and_resolve_url(current_url)

                try:
                    response = client.get(clean_url, headers=headers)
                except Exception as req_err:
                    raise InvalidInputException(
                        f"Failed to fetch URL '{clean_url}': {str(req_err)}"
                    ) from req_err

                # Handle HTTP redirects manually
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("location")
                    if not location:
                        break
                    # Resolve relative redirect URLs to absolute
                    current_url = urllib.parse.urljoin(clean_url, location)
                    logger.info("Redirect %d: %s -> %s", redirect_idx + 1, clean_url, current_url)
                    continue

                # Final response reached
                content_bytes = response.content
                if len(content_bytes) > self.max_response_bytes:
                    raise InvalidInputException(
                        f"Response size ({len(content_bytes)} bytes) exceeds maximum limit "
                        f"of {self.max_response_bytes} bytes."
                    )

                return str(response.url), response.status_code, response.text

        raise InvalidInputException(
            f"Exceeded maximum redirect limit of {self.max_redirects} hops."
        )

    def extract_article_metadata(self, html: str, final_url: str) -> Dict[str, Any]:
        """
        Extracts title, publisher, published date, and readable body text using BeautifulSoup.
        """
        soup = BeautifulSoup(html, "html.parser")

        # 1. Extract Title
        title = ""
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()
        elif soup.title and soup.title.string:
            title = soup.title.string.strip()
        elif soup.find("h1"):
            title = soup.find("h1").get_text().strip()

        # 2. Extract Publisher
        publisher = ""
        og_site = soup.find("meta", property="og:site_name")
        if og_site and og_site.get("content"):
            publisher = og_site["content"].strip()
        else:
            pub_meta = soup.find("meta", attrs={"name": "publisher"})
            if pub_meta and pub_meta.get("content"):
                publisher = pub_meta["content"].strip()
            else:
                parsed_url = urllib.parse.urlparse(final_url)
                publisher = parsed_url.hostname or ""

        # 3. Extract Published Date
        published_date = None
        date_candidates = []
        for prop in ("article:published_time", "og:pubdate", "pubdate", "date"):
            tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
            if tag and tag.get("content"):
                date_candidates.append(tag["content"])

        time_tag = soup.find("time")
        if time_tag and time_tag.get("datetime"):
            date_candidates.append(time_tag["datetime"])

        # Check Schema.org JSON-LD
        for ld in soup.find_all("script", type="application/ld+json"):
            try:
                ld_data = json.loads(ld.string)
                if isinstance(ld_data, dict):
                    if "datePublished" in ld_data:
                        date_candidates.append(str(ld_data["datePublished"]))
                elif isinstance(ld_data, list):
                    for item in ld_data:
                        if isinstance(item, dict) and "datePublished" in item:
                            date_candidates.append(str(item["datePublished"]))
            except Exception:
                pass

        for raw_d in date_candidates:
            try:
                parsed_d = parse_date(raw_d)
                published_date = parsed_d.strftime("%Y-%m-%d")
                break
            except Exception:
                continue

        # 4. Extract Readable Article Text
        # Decompose non-content tags
        for unwanted in soup.find_all(["script", "style", "nav", "footer", "header", "aside", "form", "noscript", "svg"]):
            unwanted.decompose()

        # Prioritize main article container
        article_container = (
            soup.find("article")
            or soup.find("main")
            or soup.find("div", class_=re.compile(r"article|content|story|post", re.I))
            or soup.body
        )

        text = ""
        if article_container:
            paragraphs = [p.get_text().strip() for p in article_container.find_all("p")]
            meaningful_paragraphs = [p for p in paragraphs if len(p) > 20]
            if meaningful_paragraphs:
                text = " ".join(meaningful_paragraphs)
            else:
                text = article_container.get_text()

        # Clean whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return {
            "title": title,
            "publisher": publisher,
            "published_date": published_date,
            "text": text,
        }

    def ingest_url(self, url: str) -> URLIngestionResult:
        """
        Executes complete secure URL ingestion workflow:
        Validation → DNS Filtering → Redirect Expansion → Fetching → Dead Page Detection → Text Extraction.
        """
        final_url, status_code, html = self.fetch_url(url)

        # Detect Dead Pages (404, 410, 5xx)
        if status_code in (404, 410):
            logger.info("URL %s returned dead page status %d", final_url, status_code)
            return URLIngestionResult(
                final_url=final_url,
                title="",
                publisher=urllib.parse.urlparse(final_url).hostname or "",
                published_date=None,
                text="",
                status="DEAD_PAGE",
            )

        if status_code >= 400:
            logger.info("URL %s returned error status %d", final_url, status_code)
            return URLIngestionResult(
                final_url=final_url,
                title="",
                publisher=urllib.parse.urlparse(final_url).hostname or "",
                published_date=None,
                text="",
                status="ERROR",
            )

        # Extract metadata and article content
        meta = self.extract_article_metadata(html, final_url)

        return URLIngestionResult(
            final_url=final_url,
            title=meta["title"],
            publisher=meta["publisher"],
            published_date=meta["published_date"],
            text=meta["text"],
            status="SUCCESS",
        )


url_ingestion_service = URLIngestionService()

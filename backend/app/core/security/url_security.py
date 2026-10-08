import ipaddress
import socket
import urllib.parse
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx

from app.core.config import settings
from app.core.exceptions import InvalidInputException, SecurityViolationException
from app.core.logging import logger

BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "instance-data",
    "metadata",
    "internal",
}

CLOUD_METADATA_IPS = {
    "169.254.169.254",  # AWS/GCP/Azure/OpenStack metadata
    "100.100.100.200",  # Alibaba Cloud metadata
    "fd00:ec2::254",    # AWS IPv6 metadata
}

ALLOWED_PORTS = {80, 443}
ALLOWED_SCHEMES = {"http", "https"}


class URLSecurityValidator:
    """
    Enterprise-grade SSRF (Server-Side Request Forgery) protection:
    - Blocks private IP address ranges (RFC 1918)
    - Blocks loopback addresses (127.0.0.0/8, ::1)
    - Blocks link-local addresses (169.254.0.0/16, fe80::/10)
    - Blocks cloud provider metadata endpoints (AWS, GCP, Azure, Alibaba)
    - Step-by-step redirect validation (re-validates every redirect hop)
    - Scheme restricted to HTTP / HTTPS
    - Port restricted to standard web ports (80, 443)
    - Enforces request timeouts and response payload byte caps
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

    def is_ip_allowed(self, ip_str: str) -> Tuple[bool, str]:
        """
        Validates an IP address against security blacklist.
        Returns (is_allowed, reason_if_blocked).
        """
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False, f"Malformed IP address string '{ip_str}'."

        if str(ip) in CLOUD_METADATA_IPS:
            return False, f"Cloud metadata endpoint IP '{ip}' is strictly blocked."

        if ip.is_private:
            return False, f"Private RFC 1918 IP address '{ip}' is forbidden."

        if ip.is_loopback:
            return False, f"Loopback address '{ip}' is forbidden."

        if ip.is_link_local:
            return False, f"Link-local address '{ip}' is forbidden."

        if ip.is_multicast:
            return False, f"Multicast address '{ip}' is forbidden."

        if ip.is_reserved:
            return False, f"Reserved address '{ip}' is forbidden."

        if ip.is_unspecified:
            return False, f"Unspecified address '{ip}' is forbidden."

        return True, ""

    def validate_url(self, url: str) -> Tuple[str, str, int]:
        """
        Validates URL scheme, port, hostname, and ensures all resolved IP addresses
        are safe public addresses.
        Returns (validated_url, hostname, port).
        """
        if not url or not url.strip():
            raise InvalidInputException("URL cannot be empty.")

        url = url.strip()
        parsed = urllib.parse.urlparse(url)

        # 1. HTTP/HTTPS scheme check
        scheme = parsed.scheme.lower()
        if scheme not in ALLOWED_SCHEMES:
            raise SecurityViolationException(
                f"Forbidden URL scheme '{parsed.scheme}'. Only HTTP and HTTPS are permitted."
            )

        # 2. Hostname check
        hostname = parsed.hostname
        if not hostname:
            raise InvalidInputException(f"Invalid URL: missing hostname in '{url}'.")

        hostname_lower = hostname.lower()
        if (
            hostname_lower in BLOCKED_HOSTNAMES
            or hostname_lower.endswith(".internal")
            or hostname_lower.endswith(".local")
            or hostname_lower.endswith(".localhost")
        ):
            raise SecurityViolationException(
                f"SSRF Protection: Access to internal hostname '{hostname}' is strictly blocked."
            )

        # 3. Port check (80 and 443 only)
        port = parsed.port or (443 if scheme == "https" else 80)
        if port not in ALLOWED_PORTS:
            raise SecurityViolationException(
                f"Forbidden port '{port}'. Only standard web ports (80, 443) are allowed."
            )

        # 4. Immediate IP literal validation
        clean_host = hostname.strip("[]")
        try:
            # If hostname is an IP literal, validate immediately
            ipaddress.ip_address(clean_host)
            allowed, reason = self.is_ip_allowed(clean_host)
            if not allowed:
                raise SecurityViolationException(f"SSRF Protection: {reason}")
        except ValueError:
            pass  # Hostname is a domain name, proceed to DNS resolution

        # 5. DNS Resolution & IP validation
        try:
            addr_info = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
        except socket.gaierror as dns_err:
            raise InvalidInputException(
                f"DNS resolution failed for host '{hostname}': {str(dns_err)}"
            ) from dns_err

        for entry in addr_info:
            ip_str = entry[4][0]
            allowed, reason = self.is_ip_allowed(ip_str)
            if not allowed:
                raise SecurityViolationException(
                    f"SSRF Protection: Host '{hostname}' resolves to forbidden IP '{ip_str}': {reason}"
                )

        return url, hostname, port

    def safe_fetch(self, initial_url: str) -> Tuple[str, int, str]:
        """
        Executes HTTP GET with strict redirect revalidation, timeouts, and byte caps.
        Returns (final_url, status_code, body_text).
        """
        current_url = initial_url
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; SachCheckSecurityBot/1.0)",
            "Accept": "text/html,application/xhtml+xml,text/plain",
        }

        with httpx.Client(timeout=self.timeout, follow_redirects=False) as client:
            for redirect_idx in range(self.max_redirects + 1):
                clean_url, _, _ = self.validate_url(current_url)

                try:
                    response = client.get(clean_url, headers=headers)
                except Exception as req_err:
                    raise InvalidInputException(
                        f"Failed to fetch URL '{clean_url}': {str(req_err)}"
                    ) from req_err

                # Step-by-step redirect handling
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("location")
                    if not location:
                        break
                    current_url = urllib.parse.urljoin(clean_url, location)
                    logger.info("Redirect %d: %s -> %s", redirect_idx + 1, clean_url, current_url)
                    continue

                # Final response reached
                content = response.content
                if len(content) > self.max_response_bytes:
                    raise SecurityViolationException(
                        f"Response size ({len(content)} bytes) exceeds the maximum allowed limit "
                        f"of {self.max_response_bytes} bytes."
                    )

                return str(response.url), response.status_code, response.text

        raise SecurityViolationException(
            f"Exceeded maximum redirect limit of {self.max_redirects} hops."
        )


url_security_validator = URLSecurityValidator()

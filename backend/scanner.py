"""
Nexus Shield AI - Scanner

Performs PASSIVE, read-only checks against a target website:
  - Is it reachable?
  - Is HTTPS enforced?
  - Is the TLS certificate valid / not expiring soon?
  - How fast does it respond?
  - Which recommended security headers are present or missing?
  - Does the server leak version info that helps attackers fingerprint it?

This module deliberately does NOT do anything active: no port scanning,
no vulnerability probing, no login attempts, no fuzzing. It only reads
what the server voluntarily sends back in a normal HTTP response.
"""

from __future__ import annotations

import socket
import ssl
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

DEFAULT_TIMEOUT = 10.0
USER_AGENT = "NexusShieldAI/1.0 (+https://nexusshield.ai; passive-security-scan)"

# Security headers we check for, with metadata used for scoring + plain-English fallback copy.
SECURITY_HEADERS = {
    "strict-transport-security": {
        "label": "Strict-Transport-Security (HSTS)",
        "weight": 12,
        "fallback": "This tells browsers to always use a secure connection to your site, "
                    "even if someone types the address without 'https://'.",
    },
    "content-security-policy": {
        "label": "Content-Security-Policy (CSP)",
        "weight": 15,
        "fallback": "This is an extra safety rule that helps block certain attacks where "
                    "malicious code gets injected into your pages.",
    },
    "x-content-type-options": {
        "label": "X-Content-Type-Options",
        "weight": 8,
        "fallback": "This stops browsers from misreading file types in a way that attackers "
                    "could exploit to run harmful code.",
    },
    "x-frame-options": {
        "label": "X-Frame-Options",
        "weight": 8,
        "fallback": "This prevents other sites from secretly embedding your page inside "
                    "an invisible frame to trick your visitors (a technique called clickjacking).",
    },
    "referrer-policy": {
        "label": "Referrer-Policy",
        "weight": 5,
        "fallback": "This controls how much information about your site is shared with other "
                    "sites when visitors click links away from it.",
    },
    "permissions-policy": {
        "label": "Permissions-Policy",
        "weight": 5,
        "fallback": "This lets you control which browser features (like camera or location) "
                    "your site is allowed to use, reducing risk if it's ever compromised.",
    },
}


@dataclass
class Issue:
    id: str
    severity: str  # "high" | "medium" | "low"
    technical: str
    category: str
    points_lost: int


@dataclass
class ScanResult:
    url: str
    normalized_url: str
    online: bool
    https_enabled: bool
    https_redirect: bool
    response_time_ms: int | None
    status_code: int | None
    tls_valid: bool | None
    tls_days_until_expiry: int | None
    server_header: str | None
    server_leaks_version: bool
    headers_present: list[str] = field(default_factory=list)
    headers_missing: list[str] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    error: str | None = None
    scanned_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _normalize_url(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        raise ValueError("URL is empty")
    if "://" not in raw:
        raw = "https://" + raw
    parsed = urlparse(raw)
    if not parsed.netloc:
        raise ValueError("Could not parse a valid host from the URL")
    return raw


def _check_tls(hostname: str, port: int = 443, timeout: float = DEFAULT_TIMEOUT):
    """Open a raw TLS connection to inspect certificate validity/expiry.
    Read-only: we just look at the cert, we don't send any application data."""
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
        not_after = cert.get("notAfter")
        if not_after:
            expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
            days_left = (expiry - datetime.now(timezone.utc)).days
            return True, days_left
        return True, None
    except (ssl.SSLCertVerificationError, ssl.SSLError):
        return False, None
    except (socket.timeout, socket.gaierror, ConnectionRefusedError, OSError):
        return None, None


async def scan_url(raw_url: str, timeout: float = DEFAULT_TIMEOUT) -> ScanResult:
    try:
        normalized = _normalize_url(raw_url)
    except ValueError as e:
        return ScanResult(
            url=raw_url,
            normalized_url=raw_url,
            online=False,
            https_enabled=False,
            https_redirect=False,
            response_time_ms=None,
            status_code=None,
            tls_valid=None,
            tls_days_until_expiry=None,
            server_header=None,
            server_leaks_version=False,
            error=str(e),
        )

    parsed = urlparse(normalized)
    hostname = parsed.hostname or ""
    https_enabled = parsed.scheme == "https"

    result = ScanResult(
        url=raw_url,
        normalized_url=normalized,
        online=False,
        https_enabled=https_enabled,
        https_redirect=False,
        response_time_ms=None,
        status_code=None,
        tls_valid=None,
        tls_days_until_expiry=None,
        server_header=None,
        server_leaks_version=False,
    )

    headers = {"User-Agent": USER_AGENT}

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout, headers=headers) as client:
            start = time.perf_counter()
            response = await client.get(normalized)
            elapsed_ms = int((time.perf_counter() - start) * 1000)

            result.online = True
            result.status_code = response.status_code
            result.response_time_ms = elapsed_ms

            final_url = str(response.url)
            result.https_redirect = final_url.startswith("https://")
            if final_url.startswith("https://"):
                result.https_enabled = True
                hostname = urlparse(final_url).hostname or hostname

            resp_headers = {k.lower(): v for k, v in response.headers.items()}

            for key, meta in SECURITY_HEADERS.items():
                if key in resp_headers:
                    result.headers_present.append(key)
                else:
                    result.headers_missing.append(key)
                    result.issues.append(Issue(
                        id=f"missing-header-{key}",
                        severity="medium" if meta["weight"] >= 10 else "low",
                        technical=f"Missing {meta['label']} header.",
                        category="headers",
                        points_lost=meta["weight"],
                    ))

            server_header = resp_headers.get("server")
            result.server_header = server_header
            if server_header and any(ch.isdigit() for ch in server_header):
                result.server_leaks_version = True
                result.issues.append(Issue(
                    id="server-version-leak",
                    severity="low",
                    technical=f"Server header discloses version info: '{server_header}'.",
                    category="fingerprinting",
                    points_lost=5,
                ))

    except httpx.TimeoutException:
        result.error = "The website took too long to respond."
        return result
    except httpx.ConnectError:
        result.error = "Could not connect to the website. It may be offline or blocking scans."
        return result
    except httpx.HTTPError as e:
        result.error = f"Could not complete the scan: {e}"
        return result

    # HTTPS / TLS checks
    if not https_enabled and not result.https_redirect:
        result.issues.append(Issue(
            id="no-https",
            severity="high",
            technical="Site does not enforce HTTPS; traffic may be sent unencrypted.",
            category="transport",
            points_lost=25,
        ))
    elif hostname:
        tls_valid, days_left = _check_tls(hostname, timeout=timeout)
        result.tls_valid = tls_valid
        result.tls_days_until_expiry = days_left
        if tls_valid is False:
            result.issues.append(Issue(
                id="invalid-tls-cert",
                severity="high",
                technical="TLS certificate is invalid, expired, or not trusted.",
                category="transport",
                points_lost=20,
            ))
        elif days_left is not None and days_left <= 14:
            result.issues.append(Issue(
                id="tls-expiring-soon",
                severity="medium",
                technical=f"TLS certificate expires in {days_left} day(s).",
                category="transport",
                points_lost=10,
            ))

    # Performance check
    if result.response_time_ms and result.response_time_ms > 3000:
        result.issues.append(Issue(
            id="slow-response",
            severity="low",
            technical=f"Server response time is slow ({result.response_time_ms}ms).",
            category="performance",
            points_lost=5,
        ))

    return result

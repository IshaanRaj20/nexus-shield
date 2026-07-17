from __future__ import annotations

import os
from typing import Any

import httpx

from email_templates import (
    render_alert_email_html,
    render_alert_email_text,
    render_test_email_html,
    render_test_email_text,
    render_weekly_digest_email_html,
    render_weekly_digest_email_text,
)

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://shield.zenithish.com")


class EmailServiceError(Exception):
    pass


def send_security_alert(
    to_email: str,
    website_url: str,
    current_score: int,
    previous_score: int | None,
    new_issues: list[dict[str, Any]],
    recommendations: list[str],
    scan_link: str | None = None,
) -> None:
    if not RESEND_API_KEY or not EMAIL_FROM:
        raise EmailServiceError("Email service is not configured.")

    subject = "Nexus Shield AI: Security alert for your website"
    if new_issues and previous_score is not None:
        subject = f"Nexus Shield AI: New security issue detected for {website_url}"
    elif previous_score is not None and current_score < previous_score:
        subject = f"Nexus Shield AI: Risk score dropped for {website_url}"
    elif scan_link:
        subject = f"Nexus Shield AI: Website scan update for {website_url}"

    html_body = render_alert_email_html(
        website_url=website_url,
        current_score=current_score,
        previous_score=previous_score,
        new_issues=new_issues,
        recommendations=recommendations,
        scan_link=scan_link or f"{FRONTEND_URL}",
    )
    text_body = render_alert_email_text(
        website_url=website_url,
        current_score=current_score,
        previous_score=previous_score,
        new_issues=new_issues,
        recommendations=recommendations,
        scan_link=scan_link or f"{FRONTEND_URL}",
    )

    payload = {
        "from": EMAIL_FROM,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
        "text": text_body,
    }

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=15.0)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise EmailServiceError(
            f"Resend returned {exc.response.status_code}: {exc.response.text}"
        ) from exc
    except Exception as exc:
        raise EmailServiceError(f"Failed to send email: {exc}") from exc


def send_test_email(to_email: str) -> None:
    if not RESEND_API_KEY or not EMAIL_FROM:
        raise EmailServiceError("Email service is not configured.")

    subject = "Nexus Shield AI: Test email"
    html_body = render_test_email_html()
    text_body = render_test_email_text()

    payload = {
        "from": EMAIL_FROM,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
        "text": text_body,
    }

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
            response = httpx.post(url, json=payload, headers=headers, timeout=15.0)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
            print("RESEND ERROR:", exc.response.text)
            raise EmailServiceError(
                f"Resend returned {exc.response.status_code}: {exc.response.text}"
            ) from exc
    except Exception as exc:
            raise EmailServiceError(f"Failed to send email: {exc}") from exc

def send_weekly_digest_email(
    to_email: str,
    scans: list[dict[str, Any]],
    length: int = 7,
) -> None:
    if not RESEND_API_KEY or not EMAIL_FROM:
        raise EmailServiceError("Email service is not configured.")

    subject = f"Nexus Shield AI Weekly Digest: {len(scans)} scans in the last {length} days"
    html_body = render_weekly_digest_email_html(scans, length)
    text_body = render_weekly_digest_email_text(scans, length)

    payload = {
        "from": EMAIL_FROM,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
        "text": text_body,
    }

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=15.0)
        response.raise_for_status()
    except Exception as exc:
        raise EmailServiceError(f"Failed to send email: {exc}") from exc

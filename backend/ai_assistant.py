from __future__ import annotations

import json
import os
from anthropic import AsyncAnthropic

MODEL = "claude-sonnet-4-6"
SYSTEM_PROMPT = """You are Nexus Shield AI, a helpful website security assistant. Use the provided scan data to answer the user question clearly and in friendly plain English. Keep your answer short, actionable, and avoid overly technical jargon unless it helps explain the problem."""


def _render_scan_context(scan: dict) -> str:
    lines = [
        f"Score: {scan.get('score', 'N/A')}/100",
        f"Status: {scan.get('status', 'Unknown')}",
        f"HTTPS enabled: {'Yes' if scan.get('https_enabled') else 'No'}",
        f"Issues found: {scan.get('issue_count', 0)}",
    ]
    if scan.get('response_time_ms') is not None:
        lines.append(f"Response time: {scan['response_time_ms']}ms")

    headers_missing = scan.get('headers_missing', [])
    if headers_missing:
        lines.append(f"Missing headers: {', '.join(headers_missing)}")
    else:
        lines.append("Missing headers: none")

    issues = scan.get('issues', [])
    if issues:
        lines.append("Issues:")
        for issue in issues[:6]:
            explanation = issue.get('explanation') or issue.get('technical')
            lines.append(f"- {issue.get('id')}: {explanation}")
    else:
        lines.append("Issues: none")
    return "\n".join(lines)


def _fallback_answer(scan: dict, question: str) -> str:
    normalized = question.strip().lower()
    issues = scan.get('issues', [])
    if "score" in normalized and "why" in normalized:
        if not issues:
            return "Your score is strong because the scan did not find any major issues. Keep monitoring your site and keep HTTPS and security headers configured."
        top = issues[0]
        return f"Your score is lower because of this issue: {top.get('explanation', top.get('technical'))}. Fix that first, then rerun the scan to see the score improve."
    if "fix" in normalized or "how" in normalized:
        if issues:
            top = issues[0]
            return f"Start by fixing this item: {top.get('fix', top.get('explanation', top.get('technical')))}. Then rerun the scan to confirm the problem is gone."
        return "There are no issues in the current scan result, so your site looks good. Keep HTTPS active and your security headers in place."
    if "https" in normalized:
        return "Nexus Shield checks whether your site uses HTTPS and keeps the connection encrypted. If HTTPS is missing, get a TLS certificate and redirect all traffic to https://."
    return "Nexus Shield has a summary of your site scan above. If you'd like, ask about your score, the top issue, or how to fix a specific problem."


async def answer_question(scan: dict, question: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return _fallback_answer(scan, question)

    context = _render_scan_context(scan)
    user_prompt = (
        "Here is the latest website scan result:\n"
        f"{context}\n\n"
        f"User question: {question}\n\n"
        "Answer in plain English, mention the scan findings, and include one concrete next step."
    )
    try:
        client = AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model=MODEL,
            max_tokens=800,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = "".join(
            block.text for block in response.content if block.type == "text").strip()
        return text
    except Exception:
        return _fallback_answer(scan, question)

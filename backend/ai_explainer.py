"""
Nexus Shield AI - Explanation layer

Takes the technical issue list from scanner.py and asks Claude to translate
it into short, friendly, non-scary explanations a non-technical site owner
can act on. Falls back to canned plain-English copy (already defined in
scanner.SECURITY_HEADERS) if no API key is configured or the call fails,
so the app always returns something useful.
"""

from __future__ import annotations

import json
import os

from scanner import Issue, SECURITY_HEADERS

MODEL = "claude-sonnet-4-6"
AI_PROVIDER = os.getenv("AI_PROVIDER", "anthropic").lower()

SYSTEM_PROMPT = """You are Nexus Shield AI, a friendly security assistant for people who are \
NOT security experts: indie game developers, students, small website owners, and startup founders.

You will be given a list of technical security findings from a website scan. For each finding, \
write a short plain-English summary with these fields:
1. name: a concise title for the issue.
2. severity: the severity level.
3. meaning: what this issue means in everyday language.
4. why: why it matters in a real-world context.
5. fix: one concrete next step to fix it.

Tone: calm, encouraging, never alarmist. Respond only with valid JSON and no markdown fences.
Format:
{
  "explanations": [
    {"id": "<issue id>", "name": "...", "severity": "...", "meaning": "...", "why": "...", "fix": "..."}
  ]
}
"""


def _default_issue_name(issue: Issue) -> str:
    if issue.id.startswith("missing-header-"):
        key = issue.id.replace("missing-header-", "")
        return SECURITY_HEADERS.get(key, {}).get("label", issue.technical)
    return issue.technical


def _fallback_explanation(issue: Issue) -> dict:
    if issue.id.startswith("missing-header-"):
        key = issue.id.replace("missing-header-", "")
        meta = SECURITY_HEADERS.get(key, {})
        return {
            "id": issue.id,
            "name": meta.get("label", _default_issue_name(issue)),
            "severity": issue.severity,
            "meaning": meta.get("fallback", "Your website is missing a recommended safety setting."),
            "why": "This makes it easier for attackers to exploit your site because it lacks a standard browser protection.",
            "fix": f"Add the {meta.get('label', key)} header in your server or hosting configuration.",
        }
    fallback_map = {
        "no-https": {
            "name": "Missing HTTPS",
            "meaning": "Your website doesn't force a secure connection, so visitors may be sending data without encryption.",
            "why": "Without HTTPS, attackers can intercept or modify traffic between your site and visitors.",
            "fix": "Get a TLS certificate and redirect all traffic to https://.",
        },
        "invalid-tls-cert": {
            "name": "Invalid TLS Certificate",
            "meaning": "Your website's certificate isn't trusted or has expired, so browsers may warn visitors before loading your site.",
            "why": "Visitors may be blocked or lose trust if their browser says the connection is not secure.",
            "fix": "Renew or reissue your TLS certificate through your hosting provider.",
        },
        "tls-expiring-soon": {
            "name": "TLS Certificate Expiring Soon",
            "meaning": "Your website's security certificate is about to expire, which can cause browser warnings soon.",
            "why": "If the certificate expires, visitors may not be able to access your site safely.",
            "fix": "Renew your TLS certificate now or enable automatic renewal.",
        },
        "server-version-leak": {
            "name": "Server Version Disclosure",
            "meaning": "Your website is exposing the server version it runs, which helps attackers find known vulnerabilities.",
            "why": "Attackers can use that version information to target your site with easier attacks.",
            "fix": "Configure your server to hide or generalize its version banner.",
        },
        "slow-response": {
            "name": "Slow Response Time",
            "meaning": "Your website is responding slowly, which can frustrate visitors and reduce trust.",
            "why": "Slow performance can hurt user experience and indicate server or configuration problems.",
            "fix": "Review server resources, enable caching, or use a CDN to speed up responses.",
        },
    }
    entry = fallback_map.get(issue.id, {
        "name": _default_issue_name(issue),
        "meaning": issue.technical,
        "why": "This is a security finding from the scan and should be addressed to keep your site safe.",
        "fix": "Consult your hosting provider's documentation for this setting.",
    })
    return {"id": issue.id, "severity": issue.severity, **entry}


async def _explain_with_anthropic(issues: list[Issue]) -> list[dict]:
    from anthropic import AsyncAnthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return [_fallback_explanation(issue) for issue in issues]

    payload = [{"id": issue.id, "technical": issue.technical,
                "severity": issue.severity} for issue in issues]

    try:
        client = AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(payload)}],
        )
        text = "".join(
            block.text for block in response.content if block.type == "text").strip()
        text = text.removeprefix("```json").removeprefix(
            "```").removesuffix("```").strip()
        parsed = json.loads(text)
        by_id = {item["id"]: item for item in parsed.get("explanations", [])}

        results = []
        for issue in issues:
            if issue.id in by_id:
                explanation = by_id[issue.id]
                explanation.setdefault("severity", issue.severity)
                explanation.setdefault("name", _default_issue_name(issue))
                explanation.setdefault("meaning", issue.technical)
                explanation.setdefault(
                    "why", "This issue matters for your website's security.")
                explanation.setdefault(
                    "fix", "Review the issue and apply a standard fix.")
                results.append(explanation)
            else:
                results.append(_fallback_explanation(issue))
        return results
    except Exception:
        return [_fallback_explanation(issue) for issue in issues]


async def explain_issues(issues: list[Issue]) -> list[dict]:
    if not issues:
        return []
    if AI_PROVIDER == "anthropic":
        return await _explain_with_anthropic(issues)
    return [_fallback_explanation(issue) for issue in issues]

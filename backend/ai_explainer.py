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

from anthropic import AsyncAnthropic

from scanner import Issue, SECURITY_HEADERS

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are Nexus Shield AI, a friendly security assistant for people who are \
NOT security experts: indie game developers, students, small website owners, and startup founders.

You will be given a list of technical security findings from a website scan. For each finding, \
write a short (1-2 sentence) plain-English explanation of:
1. What the issue means, in everyday language (no jargon like "header", "TLS", "CSP" unless you \
   immediately explain it in parentheses).
2. Why it matters, framed around a concrete real-world consequence, not abstract risk.
3. One concrete next step to fix it.

Tone: calm, encouraging, never alarmist. This is a checklist item to knock out, not a crisis.

Respond ONLY with valid JSON, no markdown fences, no preamble. Format:
{
  "explanations": [
    {"id": "<issue id exactly as given>", "explanation": "<your explanation>", "fix": "<one short actionable step>"}
  ]
}
"""


def _fallback_explanation(issue: Issue) -> dict:
    """Canned explanation used if the AI call is unavailable, keyed off issue id."""
    if issue.id.startswith("missing-header-"):
        key = issue.id.replace("missing-header-", "")
        meta = SECURITY_HEADERS.get(key, {})
        return {
            "id": issue.id,
            "explanation": meta.get("fallback", "Your website is missing a recommended safety setting."),
            "fix": f"Add the {meta.get('label', key)} header in your server or hosting config.",
        }
    fallback_map = {
        "no-https": {
            "explanation": "Your website doesn't force a secure (locked padlock) connection, so data "
                            "traveling between visitors and your site could be seen by others.",
            "fix": "Get a free TLS certificate (e.g. via Let's Encrypt or your host) and redirect all traffic to https://.",
        },
        "invalid-tls-cert": {
            "explanation": "Your website's security certificate isn't valid, so browsers may show visitors "
                            "a scary warning page.",
            "fix": "Renew or reissue your TLS certificate through your hosting provider or certificate authority.",
        },
        "tls-expiring-soon": {
            "explanation": "Your website's security certificate is about to expire, which would make browsers "
                            "warn visitors that your site isn't safe.",
            "fix": "Renew your TLS certificate now, or turn on auto-renewal if your host supports it.",
        },
        "server-version-leak": {
            "explanation": "Your website is broadcasting the exact software version it runs, which makes it "
                            "easier for attackers to look up known weaknesses in that version.",
            "fix": "Configure your web server to hide or generalize its version banner.",
        },
        "slow-response": {
            "explanation": "Your website is responding slowly, which can frustrate visitors and sometimes "
                            "signals an overloaded or misconfigured server.",
            "fix": "Check server resources, enable caching, or use a CDN to speed up responses.",
        },
    }
    entry = fallback_map.get(issue.id, {
        "explanation": issue.technical,
        "fix": "Consult your hosting provider's documentation for this setting.",
    })
    return {"id": issue.id, **entry}


async def explain_issues(issues: list[Issue]) -> list[dict]:
    if not issues:
        return []

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return [_fallback_explanation(i) for i in issues]

    payload = [{"id": i.id, "technical": i.technical, "severity": i.severity} for i in issues]

    try:
        client = AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(payload)}],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        parsed = json.loads(text)
        by_id = {e["id"]: e for e in parsed.get("explanations", [])}

        results = []
        for issue in issues:
            if issue.id in by_id:
                results.append(by_id[issue.id])
            else:
                results.append(_fallback_explanation(issue))
        return results
    except Exception:
        # Any failure (network, bad JSON, rate limit) -> fall back gracefully.
        return [_fallback_explanation(i) for i in issues]

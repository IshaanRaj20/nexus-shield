from __future__ import annotations

from typing import Any


def render_alert_email_html(
    website_url: str,
    current_score: int,
    previous_score: int | None,
    new_issues: list[dict[str, Any]],
    recommendations: list[str],
    scan_link: str,
) -> str:
    issue_rows = "".join(
        f"<li><strong>{issue.get('title', issue.get('id'))}</strong> ({issue.get('severity', '').capitalize()}): "
        f"{issue.get('meaning', issue.get('explanation', issue.get('technical')))}<br>"
        f"<em>Fix: {issue.get('fix')}</em></li>"
        for issue in new_issues
    )
    recommendations_html = "".join(
        f"<li>{rec}</li>" for rec in recommendations)
    previous_score_text = f"{previous_score}/100" if previous_score is not None else "N/A"

    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #e2e8f0; background: #020617; margin: 0; padding: 0;">
        <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 640px; margin: 0 auto; background: #071b2c; border-radius: 18px; overflow: hidden; box-shadow: 0 20px 50px rgba(0,0,0,0.35);">
          <tr>
            <td style="padding: 28px; background: linear-gradient(135deg, #0f172a 0%, #0f172a 60%, #0b1121 100%); color: #e2e8f0; text-align: center;">
              <h1 style="margin: 0; font-size: 28px; letter-spacing: 1px; color: #7dd3fc;">Nexus Shield AI</h1>
              <p style="margin: 8px 0 0; color: #a5b4fc;">Security alert for your website</p>
            </td>
          </tr>
          <tr>
            <td style="padding: 24px;">
              <p style="margin: 0 0 16px; font-size: 16px;">Hi there,</p>
              <p style="margin: 0 0 16px; font-size: 15px; line-height: 1.7;">
                Nexus Shield AI found an update for <strong>{website_url}</strong>. Here are the latest details:
              </p>
              <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse: collapse; margin-bottom: 20px;">
                <tr>
                  <td style="padding: 14px; background: #eef2ff; border-radius: 10px;">
                    <p style="margin: 0 0 6px; font-size: 14px; color: #334155;">Current score</p>
                    <p style="margin: 0; font-size: 26px; font-weight: bold; color: #0f172a;">{current_score}/100</p>
                    <p style="margin: 8px 0 0; font-size: 13px; color: #475569;">Previous score: {previous_score_text}</p>
                  </td>
                </tr>
              </table>
              <h2 style="font-size: 16px; margin: 0 0 12px; color: #0f172a;">What changed</h2>
              {f'<ul style="padding-left: 20px; margin: 0 0 20px; color: #334155;">{issue_rows}</ul>' if new_issues else '<p style="margin: 0 0 20px; color: #334155;">No new issues were detected.</p>'}
              <h2 style="font-size: 16px; margin: 0 0 12px; color: #0f172a;">Recommended actions</h2>
              <ul style="padding-left: 20px; margin: 0 0 24px; color: #334155;">
                {recommendations_html}
              </ul>
              <a href="{scan_link}" style="display: inline-block; padding: 12px 20px; background: #4fd1c5; color: #0f172a; border-radius: 8px; text-decoration: none; font-weight: 600;">View dashboard</a>
            </td>
          </tr>
          <tr>
            <td style="padding: 18px 24px; background: #071b2c; color: #94a3b8; font-size: 12px;">
              <p style="margin: 0;">This email is sent by Nexus Shield AI. Keep your site secure by checking alerts regularly.</p>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """


def render_alert_email_text(
    website_url: str,
    current_score: int,
    previous_score: int | None,
    new_issues: list[dict[str, Any]],
    recommendations: list[str],
    scan_link: str,
) -> str:
    issue_lines = "\n".join(
        f"- {issue.get('title', issue.get('id'))} ({issue.get('severity', '').capitalize()}): {issue.get('meaning', issue.get('explanation', issue.get('technical')))}\n  Fix: {issue.get('fix')}"
        for issue in new_issues
    )
    previous_score_text = f"{previous_score}/100" if previous_score is not None else "N/A"

    lines = [
        "Nexus Shield AI Security Alert",
        "===============================",
        "",
        f"Website: {website_url}",
        f"Current score: {current_score}/100",
        f"Previous score: {previous_score_text}",
        "",
        "What changed:",
        issue_lines or "- No new issues were detected.",
        "",
        "Recommended actions:",
        *recommendations,
        "",
        f"View the dashboard: {scan_link}",
        "",
        "This message is sent by Nexus Shield AI. Keep your site secure by checking alerts regularly.",
    ]
    return "\n".join(lines)


def render_test_email_html() -> str:
    return """
    <html>
      <body style="font-family: Arial, sans-serif; color: #e2e8f0; background: #020617; margin: 0; padding: 0;">
        <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 640px; margin: 0 auto; background: #071b2c; border-radius: 18px; overflow: hidden; box-shadow: 0 20px 50px rgba(0,0,0,0.35);">
          <tr>
            <td style="padding: 28px; background: #0f172a; text-align: center;">
              <h1 style="margin: 0; color: #7dd3fc;">Nexus Shield AI Test Email</h1>
              <p style="margin: 12px 0 0; color: #94a3b8;">You're all set to receive alerts from Nexus Shield AI.</p>
            </td>
          </tr>
          <tr>
            <td style="padding: 24px; color: #cbd5e1;">
              <p style="font-size: 15px; line-height: 1.7;">This is a confirmation message to let you know your email settings are working. If you receive this message, email delivery is configured correctly.</p>
              <p style="margin: 20px 0 0;"><a href="#" style="color: #7dd3fc; text-decoration: none;">Visit Nexus Shield</a></p>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """


def render_test_email_text() -> str:
    return """
Nexus Shield AI Test Email

You're all set to receive alerts from Nexus Shield AI.

This is a confirmation message to let you know your email settings are working. If you receive this message, email delivery is configured correctly.

Visit Nexus Shield
"""


def render_weekly_digest_email_html(scans: list[dict[str, Any]], length: int) -> str:
    scan_rows = "".join(
        f"<tr><td style='padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.08);'><strong>{scan['url']}</strong></td>"
        f"<td style='padding: 10px 0; text-align: right; color: #7dd3fc;'>{scan['score']}/100</td></tr>"
        for scan in scans[:10]
    )
    summary_line = f"{len(scans)} scans in the last {length} days"
    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #e2e8f0; background: #020617; margin: 0; padding: 0;">
        <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 640px; margin: 0 auto; background: #071b2c; border-radius: 18px; overflow: hidden;">
          <tr>
            <td style="padding: 28px; background: linear-gradient(135deg, #0f172a 0%, #0b1121 100%); text-align: center;">
              <h1 style="margin: 0; color: #7dd3fc;">Nexus Shield AI Weekly Digest</h1>
              <p style="margin: 10px 0 0; color: #94a3b8;">{summary_line}</p>
            </td>
          </tr>
          <tr>
            <td style="padding: 24px; color: #cbd5e1;">
              <p style="font-size: 15px; line-height: 1.7;">Here is the summary of your most recent saved scans. Review any lower scores or new issues in the Nexus Shield dashboard.</p>
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-top: 18px;">
                {scan_rows or '<tr><td style="padding: 10px 0; color: #94a3b8;">No scans found this week.</td></tr>'}
              </table>
              <p style="margin: 24px 0 0; text-align: center;"><a href="#" style="display: inline-block; padding: 12px 20px; background: #4fd1c5; color: #0f172a; border-radius: 8px; text-decoration: none; font-weight: 600;">View the dashboard</a></p>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """


def render_weekly_digest_email_text(scans: list[dict[str, Any]], length: int) -> str:
    lines = [
        "Nexus Shield AI Weekly Digest",
        "===============================",
        "",
        f"{len(scans)} scans in the last {length} days",
        "",
    ]
    for scan in scans[:10]:
        lines.append(f"- {scan['url']}: {scan['score']}/100")
    if not scans:
        lines.append("No scans found this week.")
    lines.append("")
    lines.append(
        "Review your most recent scans in the Nexus Shield dashboard.")
    return "\n".join(lines)

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
      <body style="font-family: Arial, sans-serif; color: #111; background: #f5f7fa; margin: 0; padding: 0;">
        <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 640px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden;">
          <tr>
            <td style="padding: 24px; background: #07151f; color: #fff; text-align: center;">
              <h1 style="margin: 0; font-size: 24px;">Nexus Shield AI</h1>
              <p style="margin: 8px 0 0; color: #cbd5e1;">Security alert for your website</p>
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
            <td style="padding: 18px 24px; background: #f8fafc; color: #64748b; font-size: 12px;">
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

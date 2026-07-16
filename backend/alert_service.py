from __future__ import annotations

from typing import Any

from email_service import EmailServiceError, send_security_alert


def _find_issue_by_id(issues: list[dict[str, Any]], issue_id: str) -> dict[str, Any] | None:
    for issue in issues:
        if issue.get("id") == issue_id:
            return issue
    return None


def _find_new_issues(current_issues: list[dict[str, Any]], previous_issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    previous_ids = {issue.get("id") for issue in previous_issues}
    return [issue for issue in current_issues if issue.get("id") not in previous_ids]


def _significant_score_drop(current_score: int, previous_score: int) -> bool:
    return current_score + 9 < previous_score


def _build_recommendations(new_issues: list[dict[str, Any]], current_score: int, previous_score: int | None) -> list[str]:
    recs: list[str] = []
    if new_issues:
        for issue in new_issues[:3]:
            title = issue.get("title") or issue.get(
                "category") or issue.get("id")
            fix = issue.get("fix") or issue.get(
                "meaning") or issue.get("explanation")
            recs.append(f"Fix {title}: {fix}")
    if previous_score is not None and current_score < previous_score:
        recs.append(
            "Review the most recent findings above and address the highest-severity issues first, then rerun the scan to confirm your score improves."
        )
    if not recs:
        recs.append(
            "Check the latest scan results in the dashboard and apply the recommended fixes for any issues shown."
        )
    return recs


def _should_send_alert(
    current_issues: list[dict[str, Any]],
    previous_issues: list[dict[str, Any]] | None,
    current_score: int,
    previous_score: int | None,
    scheduled: bool,
) -> bool:
    if previous_issues is None or previous_score is None:
        return False

    if current_score != previous_score:
        return True

    new_issues = _find_new_issues(current_issues, previous_issues)
    if new_issues:
        return True
    return False


def send_alert_for_scan(
    user: dict[str, Any],
    website_url: str,
    current_scan: dict[str, Any],
    previous_scan: dict[str, Any] | None,
    scheduled: bool = False,
) -> None:
    if not user.get("email_alerts_enabled"):
        return
    if not user.get("email"):
        return

    current_score = int(current_scan.get("score", 0))
    previous_score = int(previous_scan["score"]) if previous_scan else None
    current_issues = current_scan.get("issues", []) or []
    previous_issues = previous_scan.get("issues", []) if previous_scan else []

    if not _should_send_alert(current_issues, previous_issues, current_score, previous_score, scheduled):
        return

    new_issues = _find_new_issues(current_issues, previous_issues)
    recommendations = _build_recommendations(
        new_issues, current_score, previous_score)
    scan_link = current_scan.get("normalized_url")

    try:
        send_security_alert(
            to_email=user["email"],
            website_url=website_url,
            current_score=current_score,
            previous_score=previous_score,
            new_issues=new_issues,
            recommendations=recommendations,
            scan_link=scan_link,
        )
    except EmailServiceError as exc:
        print(f"Warning: failed to send alert email: {exc}")

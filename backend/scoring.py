"""
Nexus Shield AI - Scoring

Converts a ScanResult's list of Issues into a 0-100 score.
Rubric (v1, intentionally simple and documented so it can be tuned later):

  Start at 100.
  Subtract each issue's `points_lost`.
  Floor at 0.

Status bands:
  90-100: Excellent
  75-89:  Good
  50-74:  Needs Improvement
  0-49:   Poor
"""

from __future__ import annotations

from scanner import ScanResult


def compute_score(result: ScanResult) -> dict:
    if not result.online:
        return {
            "score": 0,
            "status": "Unreachable",
            "issue_count": 0,
        }

    score = 100
    for issue in result.issues:
        score -= issue.points_lost
    score = max(0, min(100, score))

    if score >= 90:
        status = "Excellent"
    elif score >= 75:
        status = "Good"
    elif score >= 50:
        status = "Needs Improvement"
    else:
        status = "Poor"

    return {
        "score": score,
        "status": status,
        "issue_count": len(result.issues),
    }

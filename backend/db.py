from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "nexus_shield.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    email_alerts_enabled INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    normalized_url TEXT NOT NULL,
    score INTEGER NOT NULL,
    status TEXT NOT NULL,
    issue_count INTEGER NOT NULL,
    https_enabled INTEGER NOT NULL,
    response_time_ms INTEGER,
    headers_present TEXT NOT NULL,
    headers_missing TEXT NOT NULL,
    issues TEXT NOT NULL,
    error TEXT,
    scanned_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
"""


def _connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DATABASE_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db() -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA)
        conn.commit()

        existing_columns = [row["name"] for row in conn.execute(
            "PRAGMA table_info(users)").fetchall()]
        if "email_alerts_enabled" not in existing_columns:
            conn.execute(
                "ALTER TABLE users ADD COLUMN email_alerts_enabled INTEGER NOT NULL DEFAULT 0"
            )
            conn.commit()


def create_user(email: str, password_hash: str, email_alerts_enabled: bool = False) -> dict[str, Any]:
    now = datetime.now().isoformat()
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash, created_at, email_alerts_enabled) VALUES (?, ?, ?, ?)",
            (email.lower(), password_hash, now, 1 if email_alerts_enabled else 0),
        )
        conn.commit()
        user_id = cursor.lastrowid
        return {
            "id": user_id,
            "email": email.lower(),
            "created_at": now,
            "email_alerts_enabled": email_alerts_enabled,
        }


def get_user_by_email(email: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?",
                           (email.lower(),)).fetchone()
    if not row:
        return None
    return {
        **dict(row),
        "email_alerts_enabled": bool(row["email_alerts_enabled"]),
    }


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?",
                           (user_id,)).fetchone()
    if not row:
        return None
    return {
        **dict(row),
        "email_alerts_enabled": bool(row["email_alerts_enabled"]),
    }


def set_user_alert_preferences(user_id: int, email_alerts_enabled: bool) -> bool:
    with _connect() as conn:
        cursor = conn.execute(
            "UPDATE users SET email_alerts_enabled = ? WHERE id = ?",
            (1 if email_alerts_enabled else 0, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def save_scan(user_id: int, scan_data: dict[str, Any]) -> int:
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO scans (user_id, url, normalized_url, score, status, issue_count, https_enabled, response_time_ms, headers_present, headers_missing, issues, error, scanned_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user_id,
                scan_data["url"],
                scan_data["normalized_url"],
                scan_data["score"],
                scan_data["status"],
                scan_data["issue_count"],
                1 if scan_data["https_enabled"] else 0,
                scan_data.get("response_time_ms"),
                json.dumps(scan_data.get("headers_present", [])),
                json.dumps(scan_data.get("headers_missing", [])),
                json.dumps(scan_data.get("issues", [])),
                scan_data.get("error"),
                scan_data.get("scanned_at", datetime.now().isoformat()),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def list_scans(user_id: int) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT s.*
            FROM scans s
            JOIN (
                SELECT normalized_url, MAX(scanned_at) AS latest_scanned_at
                FROM scans
                WHERE user_id = ?
                GROUP BY normalized_url
            ) latest
            ON s.normalized_url = latest.normalized_url
            AND s.scanned_at = latest.latest_scanned_at
            WHERE s.user_id = ?
            ORDER BY s.scanned_at DESC
            LIMIT 50
            """,
            (user_id, user_id),
        ).fetchall()
    history = []
    for row in rows:
        history.append({
            "id": row["id"],
            "url": row["url"],
            "normalized_url": row["normalized_url"],
            "score": row["score"],
            "status": row["status"],
            "issue_count": row["issue_count"],
            "https_enabled": bool(row["https_enabled"]),
            "response_time_ms": row["response_time_ms"],
            "headers_present": json.loads(row["headers_present"]),
            "headers_missing": json.loads(row["headers_missing"]),
            "issues": json.loads(row["issues"]),
            "error": row["error"],
            "scanned_at": row["scanned_at"],
        })
    return history


def get_scan(scan_id: int, user_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM scans WHERE id = ? AND user_id = ?",
            (scan_id, user_id),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "url": row["url"],
        "normalized_url": row["normalized_url"],
        "score": row["score"],
        "status": row["status"],
        "issue_count": row["issue_count"],
        "https_enabled": bool(row["https_enabled"]),
        "response_time_ms": row["response_time_ms"],
        "headers_present": json.loads(row["headers_present"]),
        "headers_missing": json.loads(row["headers_missing"]),
        "issues": json.loads(row["issues"]),
        "error": row["error"],
        "scanned_at": row["scanned_at"],
        "normalized_url": row["normalized_url"],
    }


def get_latest_scan_for_url(user_id: int, normalized_url: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM scans WHERE user_id = ? AND normalized_url = ? ORDER BY scanned_at DESC LIMIT 1",
            (user_id, normalized_url),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "url": row["url"],
        "normalized_url": row["normalized_url"],
        "score": row["score"],
        "status": row["status"],
        "issue_count": row["issue_count"],
        "https_enabled": bool(row["https_enabled"]),
        "response_time_ms": row["response_time_ms"],
        "headers_present": json.loads(row["headers_present"]),
        "headers_missing": json.loads(row["headers_missing"]),
        "issues": json.loads(row["issues"]),
        "error": row["error"],
        "scanned_at": row["scanned_at"],
        "normalized_url": row["normalized_url"],
    }


def get_latest_scan(user_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM scans WHERE user_id = ? ORDER BY scanned_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "url": row["url"],
        "normalized_url": row["normalized_url"],
        "score": row["score"],
        "status": row["status"],
        "issue_count": row["issue_count"],
        "https_enabled": bool(row["https_enabled"]),
        "response_time_ms": row["response_time_ms"],
        "headers_present": json.loads(row["headers_present"]),
        "headers_missing": json.loads(row["headers_missing"]),
        "issues": json.loads(row["issues"]),
        "error": row["error"],
        "scanned_at": row["scanned_at"],
        "normalized_url": row["normalized_url"],
    }

"""
Nexus Shield AI - Backend

Run with:
    uvicorn main:app --reload --port 8000

Endpoints:
    POST /api/scan        -> run a full scan, return score + issues + AI explanations
    POST /api/report      -> same as /scan but returns a plain-text report string too
    GET  /api/health       -> liveness check
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ai_assistant import answer_question
from ai_explainer import explain_issues
from alert_service import send_alert_for_scan
from auth import create_token, decode_token, hash_password, verify_password
from db import (
    create_user,
    get_scan,
    get_latest_scan_for_url,
    get_user_by_email,
    get_user_by_id,
    initialize_db,
    list_scans,
    save_scan,
    set_scan_notifications,
    set_user_alert_preferences,
)
from report import build_report_text
from scanner import scan_url
from scoring import compute_score

load_dotenv()

app = FastAPI(title="Nexus Shield AI", version="1.0.0")

allowed_origins = [
    "https://shield.zenithish.com",
    "http://localhost:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://shield.zenithish.com",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=[
        "Content-Type",
        "Authorization",
    ],
)

SCAN_TIMEOUT = float(os.getenv("SCAN_TIMEOUT_SECONDS", "10"))
initialize_db()


class ScanRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)
    consent: bool = Field(
        ...,
        description="Must be true: confirms the user owns this site or has permission to scan it.",
    )
    scheduled: bool = Field(
        False,
        description="Set true when this scan is part of an automated scheduled check.",
    )


class ScanResponse(BaseModel):
    url: str
    online: bool
    score: int
    status: str
    issue_count: int
    https_enabled: bool
    response_time_ms: int | None
    headers_present: list[str]
    headers_missing: list[str]
    issues: list[dict]
    notifications_enabled: bool | None = None
    scan_id: int | None = None
    error: str | None = None


class ReportResponse(ScanResponse):
    report_text: str


class SignupRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=320)
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=320)
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AskRequest(BaseModel):
    scan_id: int
    question: str = Field(..., min_length=5, max_length=300)


class AlertPreferencesRequest(BaseModel):
    email_alerts_enabled: bool


class ScanNotificationRequest(BaseModel):
    notifications_enabled: bool


def _get_user_from_token(authorization: str | None) -> dict | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ")
    payload = decode_token(token)
    if not payload:
        return None
    return get_user_by_id(payload["user_id"])


def _require_authenticated_user(authorization: str | None = Header(None)) -> dict:
    user = _get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or missing authentication token.")
    return user


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.head("/api/health")
async def health_head():
    return


async def _run_full_scan(req: ScanRequest):
    if not req.consent:
        raise HTTPException(
            status_code=400,
            detail="Please confirm you own this website or have permission to scan it.",
        )

    result = await scan_url(req.url, timeout=SCAN_TIMEOUT)

    if not result.online:
        return result, {"score": 0, "status": "Unreachable", "issue_count": 0}, []

    score_info = compute_score(result)
    explanations = await explain_issues(result.issues)

    # Merge technical + explained info for the API response
    by_id = {e["id"]: e for e in explanations}
    merged_issues = []
    for issue in result.issues:
        e = by_id.get(issue.id, {})
        merged_issues.append({
            "id": issue.id,
            "name": e.get("name", issue.category.title()),
            "severity": issue.severity,
            "category": issue.category,
            "technical": issue.technical,
            "meaning": e.get("meaning", e.get("explanation", issue.technical)),
            "why": e.get("why", "This issue matters for your website's security."),
            "explanation": e.get("explanation", e.get("meaning", issue.technical)),
            "fix": e.get("fix", "See documentation for this setting."),
        })

    return result, score_info, merged_issues


@app.post("/api/signup", response_model=TokenResponse)
async def signup(req: SignupRequest):
    existing = get_user_by_email(req.email)
    if existing:
        raise HTTPException(
            status_code=400, detail="A user with that email already exists.")
    user = create_user(req.email, hash_password(req.password))
    token = create_token(user["id"], user["email"])
    return TokenResponse(access_token=token)


@app.post("/api/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    user = get_user_by_email(req.email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(
            status_code=401, detail="Invalid email or password.")
    token = create_token(user["id"], user["email"])
    return TokenResponse(access_token=token)


@app.get("/api/me")
async def me(user: dict = Depends(_require_authenticated_user)):
    return {
        "id": user["id"],
        "email": user["email"],
        "email_alerts_enabled": user.get("email_alerts_enabled", False),
    }


@app.patch("/api/user/alerts")
async def update_alert_preferences(
    req: AlertPreferencesRequest,
    user: dict = Depends(_require_authenticated_user),
):
    success = set_user_alert_preferences(user["id"], req.email_alerts_enabled)
    if not success:
        raise HTTPException(
            status_code=500, detail="Unable to update alert preferences.")
    return {"email_alerts_enabled": req.email_alerts_enabled}


@app.patch("/api/scan/{scan_id}/notifications")
async def update_scan_notifications(
    scan_id: int,
    req: ScanNotificationRequest,
    user: dict = Depends(_require_authenticated_user),
):
    success = set_scan_notifications(
        scan_id, user["id"], req.notifications_enabled)
    if not success:
        raise HTTPException(status_code=404, detail="Scan not found.")
    return {"notifications_enabled": req.notifications_enabled}


@app.get("/api/history")
async def history(user: dict = Depends(_require_authenticated_user)):
    return list_scans(user["id"])


@app.get("/api/scan/{scan_id}")
async def get_saved_scan(scan_id: int, user: dict = Depends(_require_authenticated_user)):
    scan_item = get_scan(scan_id, user["id"])
    if not scan_item:
        raise HTTPException(status_code=404, detail="Scan not found.")
    return scan_item


@app.post("/api/ask")
async def ask(req: AskRequest, user: dict = Depends(_require_authenticated_user)):
    scan_item = get_scan(req.scan_id, user["id"])
    if not scan_item:
        raise HTTPException(status_code=404, detail="Scan not found.")
    answer = await answer_question(scan_item, req.question)
    return {"answer": answer}


@app.post("/api/scan", response_model=ScanResponse)
async def scan(
    req: ScanRequest,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(None),
):
    result, score_info, merged_issues = await _run_full_scan(req)
    response = ScanResponse(
        url=result.normalized_url,
        online=result.online,
        score=score_info["score"],
        status=score_info["status"],
        issue_count=score_info["issue_count"],
        https_enabled=result.https_enabled,
        response_time_ms=result.response_time_ms,
        headers_present=result.headers_present,
        headers_missing=result.headers_missing,
        issues=merged_issues,
        error=result.error,
    )
    user = _get_user_from_token(authorization)
    if user and result.online:
        scan_data = response.model_dump()
        scan_data["normalized_url"] = result.normalized_url
        scan_data["scanned_at"] = result.scanned_at
        previous_scan = get_latest_scan_for_url(
            user["id"], scan_data["normalized_url"])
        scan_data["notifications_enabled"] = (
            previous_scan["notifications_enabled"]
            if previous_scan is not None
            else True
        )
        saved_id = save_scan(user["id"], scan_data)
        background_tasks.add_task(
            send_alert_for_scan,
            user,
            scan_data["normalized_url"],
            scan_data,
            previous_scan,
            req.scheduled,
        )
        response_data = response.model_dump()
        response_data["scan_id"] = saved_id
        response_data["notifications_enabled"] = scan_data["notifications_enabled"]
        return response_data
    return response


@app.post("/api/report", response_model=ReportResponse)
async def report(req: ScanRequest):
    result, score_info, merged_issues = await _run_full_scan(req)
    report_text = build_report_text(
        url=result.normalized_url,
        score=score_info["score"],
        status=score_info["status"],
        explained_issues=merged_issues,
    )
    return ReportResponse(
        url=result.normalized_url,
        online=result.online,
        score=score_info["score"],
        status=score_info["status"],
        issue_count=score_info["issue_count"],
        https_enabled=result.https_enabled,
        response_time_ms=result.response_time_ms,
        headers_present=result.headers_present,
        headers_missing=result.headers_missing,
        issues=merged_issues,
        error=result.error,
        report_text=report_text,
    )

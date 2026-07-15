from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from typing import Any

SECRET_KEY = os.getenv("APP_SECRET_KEY", "nexus_shield_change_this_secret")
TOKEN_TTL = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", "86400"))


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(
        "utf-8"), salt.encode("utf-8"), 180_000)
    return f"{salt}${_b64url_encode(digest)}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, expected = stored_hash.split("$", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(
        "utf-8"), salt.encode("utf-8"), 180_000)
    return hmac.compare_digest(_b64url_encode(digest), expected)


def create_token(user_id: int, email: str) -> str:
    issued_at = int(time.time())
    expires_at = issued_at + TOKEN_TTL
    payload = f"{user_id}:{email}:{expires_at}".encode("utf-8")
    signature = hmac.new(SECRET_KEY.encode("utf-8"),
                         payload, hashlib.sha256).digest()
    return f"{_b64url_encode(payload)}.{_b64url_encode(signature)}"


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        payload_b64, signature_b64 = token.split(".", 1)
        payload = _b64url_decode(payload_b64)
        signature = _b64url_decode(signature_b64)
        expected = hmac.new(SECRET_KEY.encode("utf-8"),
                            payload, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, signature):
            return None
        payload_text = payload.decode("utf-8")
        user_id_str, email, expires_at_str = payload_text.split(":", 2)
        expires_at = int(expires_at_str)
        if int(time.time()) > expires_at:
            return None
        return {"user_id": int(user_id_str), "email": email}
    except Exception:
        return None

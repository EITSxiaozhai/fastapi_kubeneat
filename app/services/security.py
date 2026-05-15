from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from binascii import Error as Base64DecodeError
from base64 import b64encode, urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

import httpx
import redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.models import User


def hash_password(password: str, salt: str | None = None) -> str:
    password_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), password_salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256$120000${password_salt}${b64encode(digest).decode('ascii')}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False

    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations))
    actual = b64encode(digest).decode("ascii")
    return hmac.compare_digest(actual, expected)


def _b64url_encode(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padded = data + "=" * (-len(data) % 4)
    return urlsafe_b64decode(padded.encode("ascii"))


def _json_b64url(data: dict[str, Any]) -> str:
    return _b64url_encode(json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8"))


@lru_cache
def get_jwt_redis() -> redis.Redis:
    settings = get_settings()
    return redis.Redis.from_url(settings.jwt_redis_url, decode_responses=True)


def _jwt_key(jti: str) -> str:
    settings = get_settings()
    return f"{settings.jwt_redis_key_prefix}:{jti}"


def _sign_jwt(signing_input: str) -> str:
    settings = get_settings()
    digest = hmac.new(settings.jwt_secret_key.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return _b64url_encode(digest)


def _decode_jwt(token: str) -> dict[str, Any] | None:
    settings = get_settings()
    try:
        header_part, payload_part, signature_part = token.split(".", 2)
        signing_input = f"{header_part}.{payload_part}"
        if not hmac.compare_digest(_sign_jwt(signing_input), signature_part):
            return None

        header = json.loads(_b64url_decode(header_part))
        payload = json.loads(_b64url_decode(payload_part))
    except (Base64DecodeError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None

    if not isinstance(header, dict) or not isinstance(payload, dict):
        return None

    if header.get("alg") != settings.jwt_algorithm or header.get("typ") != "JWT":
        return None
    if payload.get("iss") != settings.jwt_issuer:
        return None

    exp = payload.get("exp")
    if not isinstance(exp, int) or exp <= int(datetime.now(timezone.utc).timestamp()):
        return None

    return payload


def create_access_token(user: User) -> tuple[str, datetime, str]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=settings.jwt_ttl_hours)
    jti = secrets.token_urlsafe(32)
    header = {"alg": settings.jwt_algorithm, "typ": "JWT"}
    payload = {
        "iss": settings.jwt_issuer,
        "sub": user.id,
        "username": user.username,
        "access": user.access,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": jti,
    }
    signing_input = f"{_json_b64url(header)}.{_json_b64url(payload)}"
    token = f"{signing_input}.{_sign_jwt(signing_input)}"

    ttl = max(int((expires_at - now).total_seconds()), 1)
    get_jwt_redis().setex(_jwt_key(jti), ttl, user.id)
    return token, expires_at, jti


def get_user_by_jwt_token(db: Session, token: str | None) -> User | None:
    if not token:
        return None

    payload = _decode_jwt(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    jti = payload.get("jti")
    if not isinstance(user_id, str) or not isinstance(jti, str):
        return None

    cached_user_id = get_jwt_redis().get(_jwt_key(jti))
    if cached_user_id != user_id:
        return None

    user = db.get(User, user_id)
    if not user or not user.is_active:
        return None
    return user


def revoke_jwt_token(token: str | None) -> bool:
    if not token:
        return False

    payload = _decode_jwt(token)
    jti = payload.get("jti") if payload else None
    if not isinstance(jti, str):
        return False
    return bool(get_jwt_redis().delete(_jwt_key(jti)))


def revoke_jwt_id(jti: str) -> bool:
    return bool(get_jwt_redis().delete(_jwt_key(jti)))


async def verify_turnstile_token(token: str | None, remote_ip: str | None) -> bool:
    settings = get_settings()
    if not settings.cloudflare_turnstile_secret_key:
        return not settings.cloudflare_turnstile_required
    if not token:
        return False

    payload = {
        "secret": settings.cloudflare_turnstile_secret_key,
        "response": token,
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(settings.cloudflare_turnstile_siteverify_url, data=payload)
        response.raise_for_status()
        data = response.json()

    return bool(data.get("success"))


def ensure_initial_admin(db: Session) -> None:
    settings = get_settings()
    if db.scalar(select(User).limit(1)):
        return

    db.add(
        User(
            username=settings.initial_admin_username,
            email=settings.initial_admin_email or None,
            password_hash=hash_password(settings.initial_admin_password),
            display_name=settings.initial_admin_display_name,
            access="admin",
        )
    )
    db.commit()

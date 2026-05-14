from __future__ import annotations

import hashlib
import hmac
import secrets
from base64 import b64encode
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.models import User, UserSession


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


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(db: Session, user: User) -> str:
    settings = get_settings()
    token = secrets.token_urlsafe(48)
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.session_ttl_hours),
        )
    )
    db.commit()
    return token


def get_user_by_session_token(db: Session, token: str | None) -> User | None:
    if not token:
        return None

    session = db.scalar(
        select(UserSession)
        .where(UserSession.token_hash == hash_session_token(token))
        .where(UserSession.expires_at > datetime.now(timezone.utc))
    )
    if not session or not session.user.is_active:
        return None
    return session.user


def delete_session(db: Session, token: str | None) -> None:
    if not token:
        return

    session = db.scalar(select(UserSession).where(UserSession.token_hash == hash_session_token(token)))
    if session:
        db.delete(session)
        db.commit()


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

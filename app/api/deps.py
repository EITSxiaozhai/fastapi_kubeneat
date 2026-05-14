from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.models import User
from app.services.security import get_user_by_session_token


def get_current_user(
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None),
) -> User:
    user = get_user_by_session_token(db, session_token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return user


def get_optional_current_user(
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None),
) -> User | None:
    return get_user_by_session_token(db, session_token)

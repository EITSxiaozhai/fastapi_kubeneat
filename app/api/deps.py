from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.models import User
from app.services.security import get_user_by_jwt_token


def get_bearer_token(authorization: str | None = Header(default=None)) -> str | None:
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def get_current_user(
    db: Session = Depends(get_db),
    token: str | None = Depends(get_bearer_token),
) -> User:
    user = get_user_by_jwt_token(db, token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return user


def get_optional_current_user(
    db: Session = Depends(get_db),
    token: str | None = Depends(get_bearer_token),
) -> User | None:
    return get_user_by_jwt_token(db, token)

import logging
from collections.abc import Callable, Generator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.permissions import Permission, has_permission
from app.db.engine import engine
from app.models import Role, TokenPayload, User

logger = logging.getLogger("app.authz")

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


def get_db() -> Generator:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permission(permission: Permission) -> Callable[[User], User]:
    """Return a dependency that allows the request only if the current user's
    role grants `permission`. Returns the user so handlers can reuse it."""

    def dependency(current_user: CurrentUser) -> User:
        if not has_permission(current_user.role, permission):
            logger.warning(
                "Authorization denied: user=%s role=%s permission=%s",
                current_user.id,
                current_user.role,
                permission,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user doesn't have enough privileges",
            )
        return current_user

    return dependency


def get_current_active_superuser(current_user: CurrentUser) -> User:
    """Kept for backward compatibility. Prefer require_permission() in new routes."""
    if current_user.role != Role.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user

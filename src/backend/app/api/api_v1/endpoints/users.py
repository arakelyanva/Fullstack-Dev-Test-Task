from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import delete, func, select

from app import crud
from app.api.deps import (
    CurrentUser,
    SessionDep,
    require_permission,
)
from app.core.config import settings
from app.core.permissions import Permission, has_permission
from app.core.security import get_password_hash, verify_password
from app.models import (
    Item,
    Message,
    UpdatePassword,
    User,
    UserCreate,
    UserCreateOpen,
    UserOut,
    UsersOut,
    UserUpdate,
    UserUpdateMe,
)
from app.utils import send_new_account_email

router = APIRouter()


@router.get(
    "/",
    dependencies=[Depends(require_permission(Permission.USER_LIST))],
    response_model=UsersOut,
)
def read_users(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    Retrieve users. Allowed for admin and manager.
    """
    count = session.exec(select(func.count()).select_from(User)).one()
    users = session.exec(select(User).offset(skip).limit(limit)).all()
    return UsersOut(data=users, count=count)


@router.post(
    "/",
    dependencies=[Depends(require_permission(Permission.USER_CREATE))],
    response_model=UserOut,
)
def create_user(*, session: SessionDep, user_in: UserCreate) -> Any:
    """
    Create new user. Admin only.
    """
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )

    user = crud.create_user(session=session, user_create=user_in)
    if settings.EMAILS_ENABLED and user_in.email:
        send_new_account_email(
            email_to=user_in.email, username=user_in.email, password=user_in.password
        )
    return user


@router.patch("/me", response_model=UserOut)
def update_user_me(
    *, session: SessionDep, user_in: UserUpdateMe, current_user: CurrentUser
) -> Any:
    """
    Update own user. Role is intentionally absent from UserUpdateMe to prevent escalation.
    """
    user_data = user_in.model_dump(exclude_unset=True)
    current_user.sqlmodel_update(user_data)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.patch("/me/password", response_model=Message)
def update_password_me(
    *, session: SessionDep, body: UpdatePassword, current_user: CurrentUser
) -> Any:
    """
    Update own password.
    """
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=400, detail="New password cannot be the same as the current one"
        )
    hashed_password = get_password_hash(body.new_password)
    current_user.hashed_password = hashed_password
    session.add(current_user)
    session.commit()
    return Message(message="Password updated successfully")


@router.get("/me", response_model=UserOut)
def read_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Get current user.
    """
    return current_user


@router.post("/open", response_model=UserOut)
def create_user_open(session: SessionDep, user_in: UserCreateOpen) -> Any:
    """
    Create new user without the need to be logged in. Role is always member.
    """
    if not settings.USERS_OPEN_REGISTRATION:
        raise HTTPException(
            status_code=403,
            detail="Open user registration is forbidden on this server",
        )
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system",
        )
    user_create = UserCreate.from_orm(user_in)
    user = crud.create_user(session=session, user_create=user_create)
    return user


@router.get("/{user_id}", response_model=UserOut)
def read_user_by_id(
    user_id: int, session: SessionDep, current_user: CurrentUser
) -> Any:
    """
    Get a specific user by id. Any user can read their own profile; reading others requires USER_READ_ANY.
    """
    user = session.get(User, user_id)
    if user == current_user:
        return user
    if not has_permission(current_user.role, Permission.USER_READ_ANY):
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges",
        )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch(
    "/{user_id}",
    dependencies=[Depends(require_permission(Permission.USER_UPDATE_ANY))],
    response_model=UserOut,
)
def update_user(
    *,
    session: SessionDep,
    user_id: int,
    user_in: UserUpdate,
) -> Any:
    """
    Update a user. Admin only. Includes role assignment.
    """
    db_user = crud.update_user(session=session, user_id=user_id, user_in=user_in)
    if db_user is None:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system",
        )
    return db_user


@router.delete("/{user_id}")
def delete_user(
    session: SessionDep, current_user: CurrentUser, user_id: int
) -> Message:
    """
    Delete a user. Any user can delete their own account (except admins).
    Deleting another user requires USER_DELETE_ANY (admin only).
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user == current_user:
        if current_user.is_superuser:
            raise HTTPException(
                status_code=400, detail="Super users are not allowed to delete themselves"
            )
    elif not has_permission(current_user.role, Permission.USER_DELETE_ANY):
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )

    statement = delete(Item).where(Item.owner_id == user_id)
    session.exec(statement)
    session.delete(user)
    session.commit()
    return Message(message="User deleted successfully")

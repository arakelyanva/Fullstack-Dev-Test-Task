from sqlmodel import Session, select

from app import crud
from app.core.config import settings
from app.models import Role, User, UserCreate  # noqa: F401

# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/tiangolo/full-stack-fastapi-postgresql/issues/28


def _ensure_user(
    session: Session, email: str | None, password: str | None, role: Role
) -> None:
    """Create a user with the given role if the email/password settings are present and the user doesn't exist yet."""
    if not email or not password:
        return
    if not crud.get_user_by_email(session=session, email=email):
        crud.create_user(
            session=session,
            user_create=UserCreate(email=email, password=password, role=role),
        )


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # from app.db.engine import engine
    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            role=Role.admin,
        )
        crud.create_user(session=session, user_create=user_in)

    _ensure_user(
        session, settings.FIRST_MANAGER, settings.FIRST_MANAGER_PASSWORD, Role.manager
    )
    _ensure_user(
        session, settings.FIRST_MEMBER, settings.FIRST_MEMBER_PASSWORD, Role.member
    )

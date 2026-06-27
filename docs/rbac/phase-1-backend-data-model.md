# Phase 1 - Backend Data Model & Migration

Goal: introduce the `Role` enum as the single source of truth on the `User` model, adapt the
Pydantic/SQLModel schemas, write the Alembic migration that backfills roles from `is_superuser`,
and update seeding. After this phase the data layer is role-aware; enforcement comes in Phase 2.

Files touched:
- `backend/app/models.py`
- `backend/app/crud.py`
- `backend/app/core/db.py`
- `backend/app/core/config.py` (optional, for seed users)
- `backend/app/alembic/versions/<new_revision>_add_role_to_user.py` (new)

---

## 1. Add the `Role` enum and update `User` models

In `backend/app/models.py`:

### 1.1 Define the enum (top of file, after imports)

```python
from enum import Enum

from pydantic import EmailStr, computed_field


class Role(str, Enum):
    admin = "admin"
    manager = "manager"
    member = "member"
```

`Role` subclasses `str` so it serializes to a plain string in JSON and is stored as a string in the
DB.

### 1.2 Replace `is_superuser` with `role` in `UserBase`

Current `UserBase`:

```python
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)
```

New `UserBase` (drop `is_superuser`, add `role`):

```python
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    role: Role = Field(default=Role.member, max_length=20)
    full_name: str | None = Field(default=None, max_length=255)
```

Notes:
- Default is `Role.member` - new and self-registered users are members.
- `max_length=20` keeps the backing column a short `VARCHAR`. Storing a string (not a native PG
  enum) is intentional: adding a role later is a code-only change.

### 1.3 Keep `is_superuser` as a backward-compatible derived value

Add a property to the `User` table model so existing internal checks
(`current_user.is_superuser` in `items.py`, `users.py`, etc.) keep working:

```python
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)

    @property
    def is_superuser(self) -> bool:
        return self.role == Role.admin
```

Expose the same derived value in the API response model so existing API consumers and tests that
read `is_superuser` keep working, while `role` becomes the real field:

```python
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_superuser(self) -> bool:
        return self.role == Role.admin
```

`UserPublic` therefore returns both `role` (source of truth) and `is_superuser` (derived). The
frontend will switch to `role` in Phase 4; the `is_superuser` computed field is the compat shim.

Implementation note: if SQLModel complains about defining a `property` named `is_superuser` on the
table model that also exists as a `computed_field` on `UserPublic`, keep the plain `@property` on
`User` and the `@computed_field @property` only on `UserPublic`. Verify with a quick
`UserPublic.model_validate(user)` round-trip.

### 1.4 Update `UserCreate` and `UserUpdate`

`UserCreate` already inherits `role` from `UserBase`, so it now accepts `role` on creation:

```python
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
```

`UserRegister` stays role-free (public signup must not let users pick a role); since it does not
inherit `UserBase`, `UserCreate.model_validate(user_register)` falls back to `role=Role.member`.

Replace `is_superuser` with `role` in `UserUpdate` (admin-only field, optional):

```python
class UserUpdate(SQLModel):
    email: EmailStr | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    role: Role | None = None
    full_name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
```

`UserUpdateMe` is unchanged - it must NOT contain `role` (prevents self privilege escalation):

```python
class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)
```

---

## 2. CRUD layer

`backend/app/crud.py` requires no logic changes:
- `create_user` uses `User.model_validate(user_create, ...)`, which now carries `role`.
- `update_user` uses `model_dump(exclude_unset=True)`, which now carries `role` when provided.

Update the import line only if you reference `Role` here (not strictly required):

```python
from app.models import Item, ItemCreate, User, UserCreate, UserUpdate
```

---

## 3. Seeding (`backend/app/core/db.py`)

Change the first-superuser seed to set `role=Role.admin` instead of `is_superuser=True`:

```python
from app.models import Role, User, UserCreate

def init_db(session: Session) -> None:
    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            role=Role.admin,
        )
        user = crud.create_user(session=session, user_create=user_in)
```

### 3.1 Optional: seed a manager and a member for easy evaluation

The task requires being able to seed at least one admin and one non-admin. Add optional settings
in `backend/app/core/config.py` and seed them when present. Example settings:

```python
# config.py (Settings)
FIRST_MANAGER: EmailStr | None = None
FIRST_MANAGER_PASSWORD: str | None = None
FIRST_MEMBER: EmailStr | None = None
FIRST_MEMBER_PASSWORD: str | None = None
```

Then in `init_db`, after the admin block, add a small helper to create each non-admin user if the
corresponding settings are set:

```python
def _ensure_user(session: Session, email: str | None, password: str | None, role: Role) -> None:
    if not email or not password:
        return
    if not crud.get_user_by_email(session=session, email=email):
        crud.create_user(
            session=session,
            user_create=UserCreate(email=email, password=password, role=role),
        )

# inside init_db, after the admin is ensured:
_ensure_user(session, settings.FIRST_MANAGER, settings.FIRST_MANAGER_PASSWORD, Role.manager)
_ensure_user(session, settings.FIRST_MEMBER, settings.FIRST_MEMBER_PASSWORD, Role.member)
```

This keeps seeding declarative and driven by `.env`, with no extra script to run. Document these
`.env` keys in Phase 5.

---

## 4. Alembic migration

Create a new revision whose `down_revision` is the current head `fe56fa70289e`.

Generate it with autogenerate as a starting point, then hand-edit to add the backfill and column
drop:

```bash
cd backend
uv run alembic revision -m "add role to user"
```

Edit the new file under `backend/app/alembic/versions/` to:

```python
"""add role to user

Revision ID: <generated>
Revises: fe56fa70289e
Create Date: <generated>
"""
from alembic import op
import sqlalchemy as sa


revision = "<generated>"
down_revision = "fe56fa70289e"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add role with a safe default so existing rows are valid.
    op.add_column(
        "user",
        sa.Column("role", sa.String(length=20), nullable=False, server_default="member"),
    )
    # 2. Backfill: existing superusers become admins.
    op.execute("UPDATE \"user\" SET role = 'admin' WHERE is_superuser = true")
    # 3. Drop the now-derived column.
    op.drop_column("user", "is_superuser")
    # 4. Optional: drop the server_default now that all rows are populated,
    #    so the application default (Role.member) is the single source of truth.
    op.alter_column("user", "role", server_default=None)


def downgrade():
    op.add_column(
        "user",
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute("UPDATE \"user\" SET is_superuser = true WHERE role = 'admin'")
    op.alter_column("user", "is_superuser", server_default=None)
    op.drop_column("user", "role")
```

Notes:
- Step 1's `server_default="member"` makes the migration safe on a non-empty table; step 4 removes
  it so the Python-side default governs new rows.
- `"user"` is quoted because `user` is a reserved word in Postgres.
- Storing `role` as `sa.String(20)` (not `sa.Enum`) matches decision #2 in Phase 0: no native enum
  type, so adding a role later never needs a DDL `ALTER TYPE`.

---

## 5. Verification checklist for this phase

- `uv run alembic upgrade head` applies cleanly on a fresh DB and on a DB that already has a
  superuser (the superuser becomes `role=admin`).
- `uv run alembic downgrade -1` reverses cleanly.
- `python -c "from app.models import UserPublic"` imports without errors.
- A quick REPL check: `UserPublic.model_validate(some_user)` includes both `role` and the derived
  `is_superuser`.
- The app starts and `app/initial_data.py` seeds an admin (and optional manager/member).

The data model is now role-aware. Phase 2 adds the enforcement layer that consumes `role`.

---

## Ready to build

**Start here.** All subsequent phases depend on the data model being stable.

Implementation order within this phase:

1. Add `Role` enum and update `UserBase`, `User`, `UserPublic`, `UserUpdate` in `models.py`.
2. Write the Alembic migration (`add role to user`), verify upgrade/downgrade round-trip.
3. Update `backend/app/core/db.py` seeding.
4. Optionally add `FIRST_MANAGER` / `FIRST_MEMBER` to `config.py` and `init_db`.
5. **Fix the existing CRUD tests immediately** — `backend/tests/crud/test_user.py` has
   `UserCreate(..., is_superuser=True)` calls that will fail once `is_superuser` is gone from
   `UserBase`. Change them to `role=Role.admin` as part of this phase, not Phase 3, to avoid a
   broken test window between phases.

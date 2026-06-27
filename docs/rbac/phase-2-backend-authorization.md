# Phase 2 - Backend Authorization Layer

Goal: turn the `role` field from Phase 1 into enforced authorization. Introduce one central policy
module and one reusable dependency, then apply them across the realistic surface (users, items,
metrics). After this phase the backend is the complete, consistent enforcement boundary.

Files touched:
- `backend/app/core/permissions.py` (new - the policy)
- `backend/app/api/deps.py` (the dependency factory)
- `backend/app/api/routes/users.py`
- `backend/app/api/routes/items.py`
- `backend/app/api/routes/metrics.py` (new)
- `backend/app/api/main.py`
- `backend/app/api/routes/utils.py` (optional, label the admin-only util)

---

## 1. The policy module: `backend/app/core/permissions.py`

This is the one place that encodes "who can do what". Adding a permission or role touches only this
file (and the `Role` enum).

```python
from enum import Enum

from app.models import Role


class Permission(str, Enum):
    USER_LIST = "user:list"
    USER_CREATE = "user:create"
    USER_READ_ANY = "user:read_any"
    USER_UPDATE_ANY = "user:update_any"
    USER_DELETE_ANY = "user:delete_any"
    METRICS_VIEW = "metrics:view"
    SETTINGS_MANAGE = "settings:manage"
    ITEM_MANAGE_ANY = "item:manage_any"


# The single source of truth for backend authorization. Mirrored (for UX only) on the frontend.
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.admin: {
        Permission.USER_LIST,
        Permission.USER_CREATE,
        Permission.USER_READ_ANY,
        Permission.USER_UPDATE_ANY,
        Permission.USER_DELETE_ANY,
        Permission.METRICS_VIEW,
        Permission.SETTINGS_MANAGE,
        Permission.ITEM_MANAGE_ANY,
    },
    Role.manager: {
        Permission.USER_LIST,
        Permission.METRICS_VIEW,
    },
    Role.member: set(),
}


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
```

Notes:
- `member` has an empty permission set: members only ever act on their own resources, which is
  expressed as ownership checks in the handlers, not as a global permission.
- The matrix here is exactly the one in `phase-0-overview.md`.

---

## 2. The dependency factory: `backend/app/api/deps.py`

Add a `require_permission(...)` factory that returns a FastAPI dependency. It builds on the existing
`CurrentUser` (which already validates the token and `is_active`).

```python
from collections.abc import Callable

from app.core.permissions import Permission, has_permission
from app.models import Role, User

# ... existing get_current_user / CurrentUser above ...


def require_permission(permission: Permission) -> Callable[[User], User]:
    """Return a dependency that allows the request only if the current user's
    role grants `permission`. Returns the user so handlers can reuse it."""

    def dependency(current_user: CurrentUser) -> User:
        if not has_permission(current_user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user doesn't have enough privileges",
            )
        return current_user

    return dependency
```

Optionally also provide a role-based variant for the rare case you want to gate on a role rather
than a permission:

```python
def require_role(*roles: Role) -> Callable[[User], User]:
    def dependency(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user doesn't have enough privileges",
            )
        return current_user

    return dependency
```

Keep `get_current_active_superuser` for backward compatibility but re-express it via the new layer,
so there is one mental model:

```python
def get_current_active_superuser(current_user: CurrentUser) -> User:
    if current_user.role != Role.admin:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user
```

Prefer `require_permission(...)` in new/edited routes; `get_current_active_superuser` remains only
to avoid churn where a route is truly admin-only and not part of this surface.

---

## 3. Apply to `users.py`

Swap the superuser dependency for permission-scoped dependencies. The permission names make each
route self-documenting.

| Route | Was | Now |
|-------|-----|-----|
| `GET /users/` | `Depends(get_current_active_superuser)` | `Depends(require_permission(Permission.USER_LIST))` |
| `POST /users/` | `Depends(get_current_active_superuser)` | `Depends(require_permission(Permission.USER_CREATE))` |
| `GET /users/{user_id}` | inline `is_superuser` | `require_permission(Permission.USER_READ_ANY)` for non-self |
| `PATCH /users/{user_id}` | `Depends(get_current_active_superuser)` | `Depends(require_permission(Permission.USER_UPDATE_ANY))` |
| `DELETE /users/{user_id}` | `Depends(get_current_active_superuser)` | `Depends(require_permission(Permission.USER_DELETE_ANY))` |

Examples:

```python
from app.api.deps import CurrentUser, SessionDep, require_permission
from app.core.permissions import Permission

@router.get(
    "/",
    dependencies=[Depends(require_permission(Permission.USER_LIST))],
    response_model=UsersPublic,
)
def read_users(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    ...

@router.post(
    "/",
    dependencies=[Depends(require_permission(Permission.USER_CREATE))],
    response_model=UserPublic,
)
def create_user(*, session: SessionDep, user_in: UserCreate) -> Any:
    ...
```

For `GET /users/{user_id}`, keep "self is always allowed", and require the permission only when
reading someone else:

```python
@router.get("/{user_id}", response_model=UserPublic)
def read_user_by_id(
    user_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Any:
    user = session.get(User, user_id)
    if user == current_user:
        return user
    if not has_permission(current_user.role, Permission.USER_READ_ANY):
        raise HTTPException(status_code=403, detail="The user doesn't have enough privileges")
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

`PATCH /users/me` and `DELETE /users/me` stay as-is (self-service via `CurrentUser`).

### 3.1 Privilege-escalation guard (important)

`UserUpdate` now includes `role`, and `PATCH /users/{user_id}` is gated by `USER_UPDATE_ANY`
(admin only), so only admins can change roles - good. But double-check that `UserUpdateMe` does
**not** contain `role` (confirmed in Phase 1) so members/managers cannot promote themselves via
`PATCH /users/me`. This is covered by a test in Phase 3.

---

## 4. Apply to `items.py`

Replace the inline `current_user.is_superuser` checks with a single readable ownership helper that
also honors `ITEM_MANAGE_ANY`. The behavior is unchanged (admin sees/manages all, others only
their own) but now expressed through the policy.

Add a small helper (either in `items.py` or `permissions.py`):

```python
def can_manage_item(user: User, item: Item) -> bool:
    return item.owner_id == user.id or has_permission(user.role, Permission.ITEM_MANAGE_ANY)
```

Use it in `read_item`, `update_item`, `delete_item`:

```python
if not can_manage_item(current_user, item):
    raise HTTPException(status_code=403, detail="Not enough permissions")
```

And in `read_items`, branch the query on the permission instead of `is_superuser`:

```python
if has_permission(current_user.role, Permission.ITEM_MANAGE_ANY):
    # all items
else:
    # only current_user's items
```

This keeps managers scoped to their own items (managers do not get `ITEM_MANAGE_ANY`), matching the
matrix.

---

## 5. Metrics / insights stub: `backend/app/api/routes/metrics.py`

Add the realistic "metrics/insights" surface required by the task, gated to admin + manager via
`METRICS_VIEW`. A simple computed stub is acceptable.

```python
from typing import Any

from fastapi import APIRouter, Depends
from sqlmodel import func, select

from app.api.deps import SessionDep, require_permission
from app.core.permissions import Permission
from app.models import Item, Message, User

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get(
    "/",
    dependencies=[Depends(require_permission(Permission.METRICS_VIEW))],
)
def read_metrics(session: SessionDep) -> dict[str, int]:
    """Lightweight insights stub. Visible to admin and manager only."""
    total_users = session.exec(select(func.count()).select_from(User)).one()
    active_users = session.exec(
        select(func.count()).select_from(User).where(User.is_active == True)  # noqa: E712
    ).one()
    total_items = session.exec(select(func.count()).select_from(Item)).one()
    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_items": total_items,
    }
```

Optionally define a small `MetricsPublic(SQLModel)` response model in `models.py` for a typed
client; the dict above is fine for a stub but a typed model produces a cleaner generated client in
Phase 4.

Register the router in `backend/app/api/main.py`:

```python
from app.api.routes import items, login, metrics, private, users, utils

api_router.include_router(metrics.router)
```

---

## 6. Optional: observability (nice-to-have)

In `require_permission`'s denial branch, log the denied attempt before raising. This satisfies the
"logging denied attempts" nice-to-have without adding noise:

```python
import logging
logger = logging.getLogger("app.authz")
# ...
logger.warning("Authorization denied: user=%s role=%s permission=%s",
               current_user.id, current_user.role, permission)
```

---

## 7. Verification checklist for this phase

- `member` token: `GET /users/` and `GET /metrics/` return 403; `GET /users/me` returns 200.
- `manager` token: `GET /users/` and `GET /metrics/` return 200; `POST /users/` and
  `PATCH /users/{id}` return 403.
- `admin` token: all of the above return 200.
- All 403s carry a clear `detail` and the correct status code (not 401, not 500).
- `items` behavior matches before for admin/owner; managers see only their own items.
- `PATCH /users/me` cannot set `role` (field is absent from `UserUpdateMe`).

Enforcement is complete. Phase 3 proves it with focused tests.

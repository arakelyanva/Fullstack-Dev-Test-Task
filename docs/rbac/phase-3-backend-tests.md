# Phase 3 - Backend Authorization Tests

Goal: prove the matrix with a small set of clear, well-named tests covering both allowed and denied
paths, plus a privilege-escalation guard. Quality over quantity - 5-7 focused tests.

Files touched:
- `backend/tests/utils/user.py` (role-aware helper)
- `backend/tests/conftest.py` (manager/member token fixtures)
- `backend/tests/api/routes/test_rbac.py` (new, the focused suite)

The existing `db` fixture in `conftest.py` already wipes `User`/`Item` after the session, so created
test users do not leak.

---

## 1. Role-aware token helper

Extend `backend/tests/utils/user.py` so tests can mint a user of a given role and get its auth
headers. Reuse the existing `user_authentication_headers` and `random_*` helpers.

```python
from app.models import Role, User, UserCreate, UserUpdate

def authentication_token_from_email(
    *, client: TestClient, email: str, db: Session, role: Role = Role.member
) -> dict[str, str]:
    """Return a valid token for the user with given email, creating it (with `role`)
    if needed and resetting the password so login is deterministic."""
    password = random_lower_string()
    user = crud.get_user_by_email(session=db, email=email)
    if not user:
        user_in_create = UserCreate(email=email, password=password, role=role)
        user = crud.create_user(session=db, user_create=user_in_create)
    else:
        user_in_update = UserUpdate(password=password, role=role)
        user = crud.update_user(session=db, db_user=user, user_in=user_in_update)
    return user_authentication_headers(client=client, email=email, password=password)
```

This keeps the existing default behavior (`role=member`) so `normal_user_token_headers` is
unchanged.

---

## 2. Fixtures in `conftest.py`

Add module-scoped fixtures for manager and member tokens, mirroring the existing
`normal_user_token_headers`:

```python
from app.models import Role
from tests.utils.utils import random_email

@pytest.fixture(scope="module")
def manager_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email="manager@example.com", db=db, role=Role.manager
    )

@pytest.fixture(scope="module")
def member_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email="member@example.com", db=db, role=Role.member
    )
```

`superuser_token_headers` (the seeded admin) is reused as the admin fixture.

---

## 3. The focused suite: `backend/tests/api/routes/test_rbac.py`

Cover the critical matrix cells, both allowed and denied, with names that read as specifications.

```python
from fastapi.testclient import TestClient

from app.core.config import settings

API = settings.API_V1_STR


# --- List users: admin + manager allowed, member denied ---

def test_admin_can_list_users(client: TestClient, superuser_token_headers):
    r = client.get(f"{API}/users/", headers=superuser_token_headers)
    assert r.status_code == 200

def test_manager_can_list_users(client: TestClient, manager_token_headers):
    r = client.get(f"{API}/users/", headers=manager_token_headers)
    assert r.status_code == 200

def test_member_cannot_list_users(client: TestClient, member_token_headers):
    r = client.get(f"{API}/users/", headers=member_token_headers)
    assert r.status_code == 403


# --- Create user: admin only ---

def test_manager_cannot_create_user(client: TestClient, manager_token_headers):
    payload = {"email": "new@example.com", "password": "changethis123"}
    r = client.post(f"{API}/users/", headers=manager_token_headers, json=payload)
    assert r.status_code == 403


# --- Metrics: admin + manager allowed, member denied ---

def test_manager_can_view_metrics(client: TestClient, manager_token_headers):
    r = client.get(f"{API}/metrics/", headers=manager_token_headers)
    assert r.status_code == 200

def test_member_cannot_view_metrics(client: TestClient, member_token_headers):
    r = client.get(f"{API}/metrics/", headers=member_token_headers)
    assert r.status_code == 403


# --- Own profile: every role can read its own profile ---

def test_member_can_read_own_profile(client: TestClient, member_token_headers):
    r = client.get(f"{API}/users/me", headers=member_token_headers)
    assert r.status_code == 200
    assert r.json()["role"] == "member"


# --- Privilege-escalation guard: self-update cannot change role ---

def test_member_cannot_escalate_role_via_update_me(client: TestClient, member_token_headers):
    # `role` is not part of UserUpdateMe, so it must be ignored, not applied.
    r = client.patch(
        f"{API}/users/me",
        headers=member_token_headers,
        json={"full_name": "Member", "role": "admin"},
    )
    assert r.status_code == 200
    assert r.json()["role"] == "member"
```

Notes:
- The escalation test relies on FastAPI ignoring unknown body fields for `UserUpdateMe`; assert the
  role is still `member` afterward.
- If you used `random_email()` for the manager/member fixtures instead of fixed emails, adjust
  accordingly. Fixed emails make failures easier to read.

---

## 4. Keep existing suites green

The template's `tests/api/routes/test_users.py` and `test_items.py` assert on `is_superuser` in
responses. Because Phase 1 keeps `is_superuser` as a `@computed_field` on `UserPublic`, those
assertions still pass. If any test constructs `UserCreate(..., is_superuser=True)`, update it to
`UserCreate(..., role=Role.admin)`. Grep for `is_superuser=` and `"is_superuser"` under
`backend/tests/` and reconcile.

---

## 5. How to run

```bash
# Full backend suite (spins up via the test script)
bash backend/scripts/test.sh

# Or directly with uv from the backend/ directory
cd backend
uv run pytest tests/api/routes/test_rbac.py -v

# Coverage (the repo already configures coverage in scripts/test.sh)
uv run coverage run -m pytest && uv run coverage report
```

A test DB must be reachable (the same Postgres the app uses, per `.env`). `scripts/test.sh` handles
setup in the standard template workflow.

---

## 6. Verification checklist for this phase

- All new tests pass.
- Pre-existing `test_users.py` / `test_items.py` / `test_login.py` still pass (compat shim intact).
- Both allowed and denied directions are covered for the three protected actions (list users,
  create user, metrics).
- The escalation test fails loudly if `role` ever leaks into `UserUpdateMe`.

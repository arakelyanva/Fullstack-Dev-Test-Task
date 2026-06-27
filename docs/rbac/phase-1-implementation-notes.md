# Phase 1 - Implementation Notes

Notes captured during implementation for follow-up in later phases.

---

## Existing tests that reference `is_superuser` (address in Phase 3)

After removing `is_superuser` from `UserBase`, three test files have references that need updating:

### `backend/tests/crud/test_user.py` — breaks after Phase 1

These calls will fail with a validation error because `is_superuser` is no longer a field on
`UserCreate` or `UserUpdate`:

```python
# line 56
UserCreate(email=email, password=password, is_superuser=True)
# line 72
UserCreate(email=username, password=password, is_superuser=True)
# line 83 / 86
UserCreate(email=email, password=password, is_superuser=True)
UserUpdate(password=new_password, is_superuser=True)
```

**Fix**: replace `is_superuser=True` with `role=Role.admin`. These should be updated before running
the full test suite post-Phase-1. They are deferred to Phase 3 per the user's instruction.

### `backend/tests/api/routes/test_users.py` — still passes (computed field)

```python
assert current_user["is_superuser"]       # line 22
assert current_user["is_superuser"] is False  # line 33
```

These read `is_superuser` from the JSON response. Because `UserPublic` keeps `is_superuser` as a
`@computed_field`, the API response still includes it and these assertions will continue to pass.

### `backend/tests/api/routes/test_login.py` — still passes

```python
is_superuser=False,  # line 92
```

Same as above — reading from the response payload which still includes the derived field.

---

## `config.py` — `extra="ignore"` protects against unknown settings

The `Settings` model already has `extra="ignore"`, so any pre-existing `.env` files that don't
include `FIRST_MANAGER` / `FIRST_MEMBER` / `FIRST_MANAGER_PASSWORD` / `FIRST_MEMBER_PASSWORD` will
simply skip those optional seeds without an error.

---

## Migration revision chain

```
e2412789c190 → d98dd8ec85a3 → 1a31ce608336 → fe56fa70289e → 40f64d88faa2 (new head)
```

The new migration (`40f64d88faa2`) sets `down_revision = "fe56fa70289e"`, which matches the
confirmed current head before this phase.

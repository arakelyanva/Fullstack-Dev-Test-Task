# Phase 1 & 2 - Implementation Notes

Notes captured during implementation for follow-up in later phases.

---

## Actual codebase structure (differs from phase docs)

The phase docs were written against the *newer* full-stack-fastapi-template (UUID IDs, `pyjwt`,
TanStack Router). After the rebase, the actual working code is the **older** template version:

| Concern | Phase docs assumed | Actual location |
|---|---|---|
| Backend source | `backend/app/` | `src/backend/app/` |
| Frontend source | `frontend/src/` | `src/new-frontend/src/` |
| Route files | `api/routes/*.py` | `api/api_v1/endpoints/*.py` |
| Router registry | `api/main.py` | `api/api_v1/api.py` |
| DB seeding | `core/db.py` | `db/init_db.py` |
| IDs | UUID | integer |
| JWT library | `pyjwt` | `python-jose` |
| Response model | `UserPublic` | `UserOut` |
| Alembic head | `fe56fa70289e` | `e2412789c190` |

All Phase 1 and Phase 2 changes have been applied to the **actual** locations.

---

## Existing tests that reference `is_superuser` or expect old status codes (address in Phase 3)

### `src/backend/app/tests/api/api_v1/test_users.py`

- **lines 17, 28**: `current_user["is_superuser"]` — reads from JSON response. Still passes
  because `UserOut` keeps `is_superuser` as a `@computed_field`. No change needed.
- **line 99**: `assert r.status_code == 400` — `test_create_user_by_normal_user` expects 400
  (old `get_current_active_superuser` returned 400). After RBAC, `require_permission` returns
  **403**. This test needs updating to `assert r.status_code == 403`.

### `src/backend/app/tests/crud/test_user.py`

- Any `UserCreate(..., is_superuser=True)` call will fail because `is_superuser` is no longer a
  field. Change to `UserCreate(..., role=Role.admin)`.

---

## Delete-user bug fix (incidental, not RBAC)

The original `delete_user` had a silent fall-through: if a non-superuser tried to delete
*another* user, neither `if` nor `elif` matched, and the endpoint returned `None` with a 200.
This was fixed as part of the Phase 2 rewrite — the handler now raises 403 in that case.

---

## Migration revision chain

```
e2412789c190 (initialize models) → a5b6c7d8e9f0 (add role to user, new head)
```

Migration file: `src/backend/app/alembic/versions/a5b6c7d8e9f0_add_role_to_user.py`

The orphaned migration that was placed at `backend/app/alembic/versions/40f64d88faa2_add_role_to_user.py`
(from the previous Phase 1 session, referencing a non-existent `fe56fa70289e` head) has been deleted.

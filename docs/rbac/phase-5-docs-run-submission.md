# Phase 5 - Documentation, Running & Submission

Goal: make the solution easy to run and review on the first try, document the authorization model
and approach, and capture trade-offs. This phase produces the README updates, optional ADRs/diagram,
`NOTES.md`, and a final review checklist.

Files touched / created:
- `README.md` (run/seed/test + permission matrix + approach)
- `docs/rbac/adr/0001-role-enum-as-source-of-truth.md` (optional bonus)
- `docs/rbac/adr/0002-authz-in-dependencies.md` (optional bonus)
- `NOTES.md` (scope cuts / trade-offs)

---

## 1. README updates

Add an "Authorization (RBAC)" section to `README.md`. It must contain the three required pieces from
the task: the permission matrix, a brief explanation of the approach, and developer setup.

### 1.1 Permission matrix (paste the table from `phase-0-overview.md`)

| Action | admin | manager | member |
|--------|:-----:|:-------:|:------:|
| List all users | yes | yes | no |
| Create user | yes | no | no |
| View metrics / insights | yes | yes | no |
| Read / update own profile | yes | yes | yes |
| Read / update / delete any user | yes | no | no |
| Change global settings | yes | no | no |
| Manage own items | yes | yes | yes |
| Manage any item | yes | no | no |

### 1.2 Approach (2-4 paragraphs - draft)

> Authorization checks live in FastAPI dependencies, not middleware or scattered conditionals. A
> single policy module (`backend/app/core/permissions.py`) defines a `Permission` enum and a
> `ROLE_PERMISSIONS` matrix mapping each `Role` to the permissions it grants. A `require_permission`
> dependency factory (`backend/app/api/deps.py`) reads the current user's role and returns 403 if
> the required permission is missing. Routes declare the permission they need, so each endpoint is
> self-documenting.
>
> Roles are stored as a single `role` string column on the `User` table, validated by a `Role` enum.
> This replaces the template's binary `is_superuser` flag, which is preserved only as a derived
> value (`role == admin`) for backward compatibility. Roles are read from the database on each
> request as part of loading the authenticated user; they are not encoded in the JWT, so a role
> change takes effect immediately.
>
> The frontend learns about capabilities from `GET /users/me`, which returns the user's `role`. A
> small mirror of the permission matrix (`frontend/src/lib/permissions.ts`) drives UX only: it hides
> navigation and actions the user cannot use and renders a Forbidden page on direct navigation to an
> unauthorized route. The backend remains the sole enforcement boundary; the frontend never grants
> access the API would deny.
>
> Extensibility: adding a role or permission is a code-only change to the enums and the two matrices
> (backend + frontend mirror). No database DDL is required because `role` is stored as a string.

### 1.3 Run locally

Document both the Docker Compose path (simplest for reviewers) and the local-dev path.

```bash
# Option A - Docker Compose (recommended for review)
# 1. Copy/edit .env (set SECRET_KEY, FIRST_SUPERUSER, FIRST_SUPERUSER_PASSWORD, POSTGRES_PASSWORD)
docker compose up -d --wait
# Backend:   http://localhost:8000   API docs: http://localhost:8000/docs
# Frontend:  http://localhost:5173 (dev) or http://localhost (via proxy)
# Migrations + seeding run automatically via backend/scripts/prestart.sh

# Option B - Local dev
# Backend
cd backend
uv sync
uv run alembic upgrade head
uv run python app/initial_data.py        # seeds users
uv run fastapi dev app/main.py
# Frontend (separate terminal)
cd frontend
bun install      # or: npm install
bun run dev      # or: npm run dev
```

### 1.4 Seed test data (admin + non-admin)

The first superuser (admin) is always seeded from `.env`. To also seed a manager and a member, set
the optional keys added in Phase 1 and re-run seeding:

```dotenv
# .env
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=changethis
FIRST_MANAGER=manager@example.com
FIRST_MANAGER_PASSWORD=changethis
FIRST_MEMBER=member@example.com
FIRST_MEMBER_PASSWORD=changethis
```

```bash
# Local dev
cd backend && uv run python app/initial_data.py
# Docker: re-running `docker compose up` re-runs prestart seeding
```

Alternatively, log in as admin and assign roles through the Admin UI.

### 1.5 Run tests

```bash
# Backend (authorization tests included)
bash backend/scripts/test.sh
# or
cd backend && uv run pytest tests/api/routes/test_rbac.py -v

# Frontend E2E (optional)
cd frontend && bunx playwright test
```

### 1.6 Database migrations

State that the RBAC change ships an Alembic migration (`add role to user`) that adds the `role`
column, backfills `admin` from `is_superuser`, and drops `is_superuser`. It runs automatically via
`backend/scripts/prestart.sh` (`alembic upgrade head`) or manually with
`uv run alembic upgrade head`.

---

## 2. ADRs (optional bonus)

Create `docs/rbac/adr/` with 1-2 short ADRs (200-400 words each). Suggested:

### `0001-role-enum-as-source-of-truth.md`
- Problem: the template only has `is_superuser`; we need three roles without a big refactor.
- Options: (a) add `role` enum as source of truth + derived `is_superuser`; (b) keep `is_superuser`
  and add `role` independently; (c) full roles/permissions tables.
- Decision: (a). Single column, string-backed, enum-validated.
- Trade-offs: minimal churn and clear model; no per-permission DB customization at runtime; string
  column trades referential strictness for migration simplicity and easy role addition.

### `0002-authz-in-dependencies.md`
- Problem: where should checks live - middleware, decorators, inline `if`s, or dependencies?
- Options: middleware (centralized but path-coupled and verbose for per-route rules); inline checks
  (what the template does - scattered, easy to miss); FastAPI dependencies (composable, declarative,
  testable).
- Decision: dependencies via `require_permission(...)`.
- Trade-offs: per-route declaration is explicit (a feature, not a bug); slightly more boilevarate at
  call sites than a blanket middleware, but each endpoint documents its own requirement and is unit
  testable.

---

## 3. Architecture diagram

Include the auth-flow mermaid diagram from `phase-0-overview.md` in the README (or link to it). It
shows where authentication (`get_current_user`) and authorization (`require_permission`) happen
relative to the route handler and ownership checks. This satisfies the "simple diagram" nice-to-have.

---

## 4. `NOTES.md` (optional but recommended)

Capture, briefly:
- Scope cuts: no roles/permissions DB table; metrics is a stub; no role hierarchy; frontend role
  assignment limited to admin UI.
- Trade-offs: string `role` column vs native PG enum; derived `is_superuser` kept for compatibility
  rather than a hard cutover.
- What I'd do with more time: typed `MetricsPublic` model + richer metrics page; centralized
  frontend route-guard wrapper; audit log for denied attempts; E2E coverage of the full matrix.

---

## 5. Final review checklist (mapped to TASK.md "What We Review")

Primary (60%):
- [ ] RBAC enforced consistently in backend (dependencies) and frontend (nav + guards).
- [ ] No privilege escalation: `role` not settable via `PATCH /users/me`; role changes admin-only.
- [ ] Correct status codes: 401 for unauthenticated, 403 for forbidden, 404 where appropriate.
- [ ] Clear separation of concerns: one policy module, one dependency, mirrored matrix on FE.
- [ ] Easy to extend: adding a role touches enums + two matrices only.

Secondary (30%):
- [ ] Focused tests cover allowed AND denied paths for list users, create user, metrics.
- [ ] Setup instructions work first try; permission matrix + approach documented in README.

Nice to have (10%):
- [ ] Forbidden page (not silent failure, not logout-on-403).
- [ ] Denied-attempt logging in `require_permission`.
- [ ] ADRs + diagram.

---

## 6. Suggested commit/PR sequence

1. Phase 1: model + migration + seeding.
2. Phase 2: permissions module + dependency + route protection + metrics endpoint.
3. Phase 3: tests.
4. Phase 4: client regen + frontend gating + Forbidden + 403 fix + role selector.
5. Phase 5: README + ADRs + NOTES.

Each commit should leave the app runnable; run `bash backend/scripts/test.sh` before the
frontend-only commits to confirm the API contract is stable before regenerating the client.

# Implementation Notes

## Scope Cuts

- **No roles/permissions database tables.** A string-backed `Role` enum on the `User` table is sufficient for three fixed roles and simpler to migrate and reason about than a normalized roles/permissions schema.
- **Metrics endpoint is a stub.** `GET /api/v1/metrics/` returns `total_users`, `active_users`, and `total_items` — enough to demonstrate the permission gate. No aggregation pipeline, time-series data, or caching.
- **No role hierarchy or inheritance.** Roles are flat; each role's permission set is declared explicitly in `ROLE_PERMISSIONS`. A manager does not "inherit" member permissions by derivation — they are listed separately. This makes the matrix easy to read and reason about.
- **Frontend role assignment limited to admin UI.** Only admins reach the Edit User modal which now contains a role selector. Managers can view the user list but cannot assign or change roles (the backend enforces this; the UI also hides the control).
- **No E2E tests.** Playwright tests extending the existing `admin.spec.ts` are described in the phase-4 doc as optional. Backend authorization tests (Phase 3) cover the required scenarios.

## Trade-offs

- **String `role` column vs. native Postgres enum.** A native `ENUM` type gives DB-level enforcement but requires an `ALTER TYPE` DDL statement to add a new value, which can be problematic on large tables or in managed environments with restricted DDL access. A plain `VARCHAR` column validated at the application boundary keeps role additions as code-only changes.
- **`is_superuser` kept as a compat shim.** Rather than a hard cutover (removing `is_superuser` from the API response), `UserOut.is_superuser` is a `@computed_field` derived from `role == admin`. This preserves backward compatibility for any external consumer or test that reads `is_superuser` from the JSON without requiring a coordinated breaking change.
- **Roles read from DB per request (not in JWT).** The JWT carries only the user ID. The role is loaded with the user on every authenticated request. This means a role change takes effect on the next request — no token invalidation needed — at the cost of one extra DB lookup per request. Acceptable for this scale; a token-embedded role would need cache invalidation or token rotation on role change.

## What I'd Do With More Time

- **Typed `MetricsPublic` response model.** The current `GET /metrics/` returns `dict[str, int]`. A dedicated Pydantic model (`MetricsPublic`) with named fields and docstrings would make the contract explicit and generate a clean OpenAPI schema, avoiding the `Record<string, number>` cast on the frontend.
- **Richer metrics page.** Beyond the three counters, the page could show a role breakdown (admins/managers/members counts), recent signup trend, and active sessions — all queryable from the existing tables.
- **Centralized frontend route guard.** Currently each page component contains its own `if (!can(...)) return <Forbidden />` guard. A higher-order component or a `ProtectedRoute` wrapper in `private_route.tsx` would remove the repetition and make it impossible to forget the guard on a new page.
- **Audit log for denied attempts.** `require_permission` already logs a warning with user ID, role, and permission on denial. With more time, these would be persisted to a dedicated audit table or shipped to a log aggregator for security review.
- **E2E test coverage of the full matrix.** A Playwright spec covering member (no Admin/Metrics links, Forbidden on direct navigation), manager (sees Metrics + Admin, no Add User), and admin (full access, role selector functional) would close the loop on the frontend RBAC surface.

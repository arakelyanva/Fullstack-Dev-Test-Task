# ADR 0001 — Role Enum as Source of Truth

**Date:** 2026-06-27  
**Status:** Accepted

---

## Context

The full-stack-fastapi-template ships with a binary `is_superuser: bool` column on the `User` table. The task requires three distinct roles — `admin`, `manager`, and `member` — with different permission sets. A decision was needed on how to model this without a large refactor.

---

## Problem

How do we represent multiple roles cleanly while keeping the migration simple, preserving backward compatibility for existing callers that rely on `is_superuser`, and making it easy to add a fourth role later?

---

## Options Considered

**Option A — `role` enum as sole source of truth, `is_superuser` as a derived value**  
Add a `role: VARCHAR` column validated by a `Role` enum (`admin`, `manager`, `member`). Remove `is_superuser` from the database and expose it as a `@computed_field` (`role == admin`) on the response model for backward compatibility.

**Option B — Keep `is_superuser`, add `role` as an independent column**  
Maintain both columns in the database. `is_superuser` continues to be the admin gate; `role` carries the finer-grained value. Two columns must stay in sync; any role-assignment code must update both.

**Option C — Roles/permissions tables**  
Add `roles` and `user_roles` tables. Maximum flexibility for per-object or per-user custom permissions at runtime, but far more migration and application complexity than the task scope warrants.

---

## Decision

**Option A.** A single `role` string column, validated by the `Role` enum at the application boundary.

The migration (`a5b6c7d8e9f0_add_role_to_user.py`) adds the column, backfills `admin` for every row where `is_superuser = true`, and sets `member` as the default for all others. `is_superuser` is removed from the database schema but kept as a `@computed_field` on `UserOut` so existing API consumers and tests that read it from the response continue to work without change.

---

## Consequences

**Positive:**
- Single source of truth — no sync risk between two columns.
- Adding a fourth role is a code-only change: extend the `Role` enum and add an entry to `ROLE_PERMISSIONS`. No `ALTER TABLE` or `ALTER TYPE` DDL required because `role` is a plain `VARCHAR`.
- The migration is a straightforward `ALTER TABLE … ADD COLUMN` with a backfill, not a type change.

**Negative / trade-offs:**
- A plain `VARCHAR` gives up the referential strictness of a native Postgres enum. Invalid role strings are rejected at the application boundary, not the database boundary. This is an acceptable trade-off for a three-value enum unlikely to drift.
- No runtime per-user permission customization. All users of the same role have identical capabilities; deviations would require a new role.

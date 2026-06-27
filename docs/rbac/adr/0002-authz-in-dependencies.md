# ADR 0002 — Authorization in FastAPI Dependencies

**Date:** 2026-06-27  
**Status:** Accepted

---

## Context

The original template gates sensitive routes with a `get_current_active_superuser` dependency that raises 400 if the user is not a superuser. Items routes use inline `if current_user.is_superuser` checks. With three roles and a richer permission surface, a consistent and maintainable authorization pattern was needed.

---

## Problem

Where should role-based permission checks live — in HTTP middleware, inline inside route handlers, or in FastAPI dependency factories?

---

## Options Considered

**Option A — HTTP middleware**  
A middleware function intercepts every request, reads the path and method, and looks up the required permission. Centralized in one place, but tightly coupled to URL patterns. Per-route granularity requires mapping every path to a permission, which becomes fragile with parameterized paths and is hard to keep in sync with the router.

**Option B — Inline checks in route handlers**  
Each handler calls `if not has_permission(current_user.role, Permission.X): raise HTTPException(403)` directly. Simple to read in isolation, but the check is scattered across every protected handler, easy to forget on a new endpoint, and requires reading the handler body to understand what is gated.

**Option C — FastAPI dependency factory**  
A `require_permission(permission)` factory in `src/backend/app/api/deps.py` returns a dependency function. Routes declare their permission requirement in the `Depends(...)` call — at the point of route registration, not inside the handler body. The dependency raises 403 if the current user's role does not grant the required permission, and returns the user otherwise so the handler can reuse it.

---

## Decision

**Option C.** A single `require_permission(...)` dependency factory.

```python
# src/backend/app/api/deps.py
def require_permission(permission: Permission) -> Callable[[User], User]:
    def dependency(current_user: CurrentUser) -> User:
        if not has_permission(current_user.role, permission):
            raise HTTPException(status_code=403, ...)
        return current_user
    return dependency

# Usage at route registration:
@router.get("/", dependencies=[Depends(require_permission(Permission.USER_LIST))])
def list_users(...): ...
```

The policy itself lives in one module (`src/backend/app/core/permissions.py`) as a `ROLE_PERMISSIONS` dict. The dependency only enforces it; it never duplicates it.

---

## Consequences

**Positive:**
- Each route self-documents its access requirement at the point of declaration — no need to read the handler body.
- Adding a new protected route means adding one `Depends(require_permission(...))` call. Forgetting it fails loudly in review rather than silently in production.
- The dependency is independently testable: pass a mock `CurrentUser` with a given role and assert the correct response without spinning up the full app.
- Denied attempts are logged centrally inside the dependency with the user ID, role, and permission, giving a single place for observability.

**Negative / trade-offs:**
- Slightly more boilerplate at call sites than a blanket middleware, since each route must declare its permission. This is intentional: explicit per-route declarations are easier to audit than a path-pattern table.
- The dependency runs after `get_current_user`, so unauthenticated requests are handled by the authentication layer first (401), and the permission check is only reached by authenticated users (403 on denial). This is the correct layering.

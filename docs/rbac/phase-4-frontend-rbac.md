# Phase 4 - Frontend RBAC & UX

Goal: make the frontend role-aware so it (a) hides nav/actions the user cannot use, (b) shows a
friendly Forbidden page on direct navigation to unauthorized routes instead of failing silently or
logging the user out, and (c) lets admins assign roles. The backend remains the only enforcement
boundary; the frontend mirrors the matrix purely for UX.

Files touched:
- `frontend/src/client/*` (regenerated)
- `frontend/src/lib/permissions.ts` (new - the mirror)
- `frontend/src/hooks/useAuth.ts`
- `frontend/src/components/Sidebar/AppSidebar.tsx`
- `frontend/src/components/Common/Forbidden.tsx` (new)
- `frontend/src/routes/_layout/admin.tsx`
- `frontend/src/routes/_layout/metrics.tsx` (new)
- `frontend/src/main.tsx` (403 handling)
- `frontend/src/components/Admin/AddUser.tsx`, `EditUser.tsx`, `columns.tsx` (role selector)

---

## 1. Regenerate the API client

The backend now returns `role` on `UserPublic` and exposes `GET /metrics/`. Regenerate so the
TypeScript types/services pick this up:

```bash
# From repo root - exports OpenAPI from the backend, then regenerates + lints the client
bash ./scripts/generate-client.sh
```

After regeneration, confirm:
- `frontend/src/client/types.gen.ts` has `role` on `UserPublic` (a string union like
  `"admin" | "manager" | "member"`, plus the still-present derived `is_superuser`).
- A `MetricsService` (or equivalent) exists for `GET /metrics/`.

Do not hand-edit generated files.

---

## 2. The permission mirror: `frontend/src/lib/permissions.ts`

Mirror the backend matrix from `phase-0-overview.md`. This is the single frontend source of truth
for UX gating.

```typescript
import type { UserPublic } from "@/client"

export type Role = "admin" | "manager" | "member"

// Immutable lookup of the permission strings. The values are identical to the
// backend `Permission` enum values so the two matrices stay trivially diffable;
// the named keys give call sites autocompletable references (e.g. PERMISSIONS.UserList).
export const PERMISSIONS = {
  UserList: "user:list",
  UserCreate: "user:create",
  MetricsView: "metrics:view",
  UserUpdateAny: "user:update_any",
  SettingsManage: "settings:manage",
} as const

export type Permission = (typeof PERMISSIONS)[keyof typeof PERMISSIONS]

const ROLE_PERMISSIONS: Record<Role, Permission[]> = {
  admin: ["user:list", "user:create", "metrics:view", "user:update_any", "settings:manage"],
  manager: ["user:list", "metrics:view"],
  member: [],
}

export function roleOf(user?: UserPublic | null): Role {
  return (user?.role as Role) ?? "member"
}

export function can(user: UserPublic | null | undefined, permission: Permission): boolean {
  return ROLE_PERMISSIONS[roleOf(user)].includes(permission)
}
```

Notes:
- `PERMISSIONS` is declared `as const`, so `Permission` is derived from its values rather than
  hand-maintained as a separate union - the literal strings exist in exactly one place. Deriving the
  type this way also keeps it fully erasable (no runtime `enum` object) and structurally compatible
  with the string `role` field the generated client emits (no nominal-enum casts at the boundary).
- The `ROLE_PERMISSIONS` matrix intentionally keeps the raw string values so it diffs 1:1 against
  the backend `ROLE_PERMISSIONS`. Call sites may use either the raw string (`can(user, "user:list")`)
  or the named reference (`can(user, PERMISSIONS.UserList)`); both type-check against `Permission`.
- Only the permissions the UI actually checks need to be listed here.

---

## 3. Expose role/capabilities from `useAuth`

`useAuth` already returns `user`. Add convenience helpers so components do not import the matrix
everywhere:

```typescript
import { can, roleOf, type Permission } from "@/lib/permissions"

// inside useAuth(), after `user` is fetched:
return {
  signUpMutation,
  loginMutation,
  logout,
  user,
  role: roleOf(user),
  can: (permission: Permission) => can(user, permission),
}
```

Components then call `const { can } = useAuth()` and `can("user:list")`.

---

## 4. Role-based navigation

Replace the `is_superuser` check in `frontend/src/components/Sidebar/AppSidebar.tsx` with
permission checks. Admin link requires user management; a new Metrics link requires metrics view.

```typescript
import { BarChart3, Briefcase, Home, Users } from "lucide-react"
import useAuth from "@/hooks/useAuth"

export function AppSidebar() {
  const { user: currentUser, can } = useAuth()

  const items: Item[] = [
    { icon: Home, title: "Dashboard", path: "/" },
    { icon: Briefcase, title: "Items", path: "/items" },
    ...(can("metrics:view") ? [{ icon: BarChart3, title: "Metrics", path: "/metrics" }] : []),
    ...(can("user:list") ? [{ icon: Users, title: "Admin", path: "/admin" }] : []),
  ]
  // ... unchanged render
}
```

Now managers see Metrics + Admin (list-only), members see neither.

---

## 5. Forbidden page + reusable route guard

Add `frontend/src/components/Common/Forbidden.tsx` (model it on the existing
`Common/NotFound.tsx` / `Common/ErrorComponent.tsx` for visual consistency):

```tsx
import { Link } from "@tanstack/react-router"
import { Button } from "@/components/ui/button"

export default function Forbidden() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
      <h1 className="text-3xl font-bold">403 - Access Denied</h1>
      <p className="text-muted-foreground">
        You don't have permission to view this page.
      </p>
      <Button asChild>
        <Link to="/">Go to Dashboard</Link>
      </Button>
    </div>
  )
}
```

Guard approach for protected routes: instead of the current silent `redirect({ to: "/" })`, render
the Forbidden component so the user gets clear feedback. Two clean options:

- Option A (component-level): in the route component, read `useAuth()` and return `<Forbidden />`
  when the capability check fails. Simple and keeps everything in React.
- Option B (route-level): keep `beforeLoad` but `throw` a typed error and render `<Forbidden />` via
  the route's `errorComponent`.

Use Option A for clarity. Example for `frontend/src/routes/_layout/admin.tsx`:

```tsx
import { can } from "@/lib/permissions"

export const Route = createFileRoute("/_layout/admin")({
  component: Admin,
  beforeLoad: async () => {
    const user = await UsersService.readUserMe()
    if (!can(user, "user:list")) {
      throw redirect({ to: "/forbidden" })
    }
  },
  // ...
})
```

Provide a `/forbidden` route (`frontend/src/routes/_layout/forbidden.tsx`) that renders
`<Forbidden />`, OR render `<Forbidden />` inline in the component without redirecting. Pick one and
apply it consistently to `/admin` and `/metrics`. Inline rendering avoids an extra route and keeps
the URL meaningful; redirect-to-`/forbidden` gives a shareable URL. Recommended: inline render in
the component, keeping `beforeLoad` only for the not-logged-in case already handled by `_layout`.

Recommended inline pattern:

```tsx
function Admin() {
  const { can } = useAuth()
  if (!can("user:list")) return <Forbidden />
  // ...existing admin UI
}
```

---

## 6. The Metrics page: `frontend/src/routes/_layout/metrics.tsx`

A simple page that calls the new metrics endpoint and is guarded like `/admin`:

```tsx
import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { MetricsService } from "@/client"
import Forbidden from "@/components/Common/Forbidden"
import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/metrics")({ component: Metrics })

function Metrics() {
  const { can } = useAuth()
  if (!can("metrics:view")) return <Forbidden />

  const { data } = useQuery({
    queryKey: ["metrics"],
    queryFn: () => MetricsService.readMetrics(),
  })

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold">Metrics & Insights</h1>
      {/* render data.total_users, data.active_users, data.total_items as cards */}
    </div>
  )
}
```

(The route file name/path must match the generated `routeTree.gen.ts` conventions; the TanStack
plugin regenerates it on save.)

---

## 7. Fix global 403 handling in `main.tsx`

Today `handleApiError` logs the user out on BOTH 401 and 403. With managers/members now legitimately
hitting 403s for parts of the API, a 403 must NOT destroy the session. Only 401 (invalid/expired
token) should log out.

```typescript
const handleApiError = (error: Error) => {
  if (error instanceof ApiError && error.status === 401) {
    localStorage.removeItem("access_token")
    window.location.href = "/login"
  }
  // 403 is an authorization failure for an authenticated user:
  // let route guards show <Forbidden /> and let mutations surface a toast.
}
```

This is the key UX fix: a member who somehow triggers a forbidden API call sees a Forbidden state /
toast rather than being kicked to the login screen.

---

## 8. Admin user management: role selector

Replace the binary `is_superuser` checkbox with a role `<Select>` (admin / manager / member) in:
- `frontend/src/components/Admin/AddUser.tsx`
- `frontend/src/components/Admin/EditUser.tsx`

The form field becomes `role` (sent in `UserCreate` / `UserUpdate`, which now accept `role` after
the Phase 1 changes and client regen). Use the existing shadcn `Select` component
(`@/components/ui/select` if present; otherwise add it via the established components.json setup).

Update `frontend/src/components/Admin/columns.tsx`: replace the "Superuser vs User" label with the
actual `role` value (e.g. a `Badge` showing `admin` / `manager` / `member`).

`frontend/src/components/Admin/UserActionsMenu.tsx` keeps hiding edit/delete for the current user;
no role logic needed there beyond what already exists.

Note on `settings.tsx`: the existing `currentUser?.is_superuser ? tabsConfig.slice(0,3) : tabsConfig`
branch is a no-op (both arms are identical). Leave it or simplify to just `tabsConfig`; it is not
part of the RBAC surface.

---

## 9. E2E tests (optional, aligns with template's Playwright setup)

`frontend/tests/admin.spec.ts` already checks superuser access vs non-superuser redirect. Extend or
add a spec to cover:
- member: no Admin/Metrics links in sidebar; visiting `/admin` shows Forbidden.
- manager: sees Admin (list) + Metrics; `/metrics` loads; Create User control is hidden/disabled.

This is a nice-to-have; the required tests are the backend ones in Phase 3.

---

## 10. Verification checklist for this phase

- `bash ./scripts/generate-client.sh` regenerates without errors and `role` appears on `UserPublic`.
- Logged in as member: sidebar shows only Dashboard + Items; `/admin` and `/metrics` render
  Forbidden; session is NOT lost when hitting a 403.
- Logged in as manager: sidebar shows Metrics + Admin; user list loads; Create User is hidden; role
  cannot be changed (no such control surfaced to managers).
- Logged in as admin: full access; can assign roles via the role selector; the users table shows the
  role badge.
- No direct `is_superuser` checks remain in app code except the generated client field (kept as a
  compat shim).

import type { Role, UserOut } from '../client'

export type { Role }

export const PERMISSIONS = {
  UserList: 'user:list',
  UserCreate: 'user:create',
  MetricsView: 'metrics:view',
  UserUpdateAny: 'user:update_any',
  SettingsManage: 'settings:manage',
} as const

export type Permission = (typeof PERMISSIONS)[keyof typeof PERMISSIONS]

const ROLE_PERMISSIONS: Record<Role, Permission[]> = {
  admin: ['user:list', 'user:create', 'metrics:view', 'user:update_any', 'settings:manage'],
  manager: ['user:list', 'metrics:view'],
  member: [],
}

export function roleOf(user?: UserOut | null): Role {
  return (user?.role as Role) ?? 'member'
}

export function can(user: UserOut | null | undefined, permission: Permission): boolean {
  return ROLE_PERMISSIONS[roleOf(user)].includes(permission)
}

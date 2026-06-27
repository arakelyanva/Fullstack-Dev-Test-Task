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

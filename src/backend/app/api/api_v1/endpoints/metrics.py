from fastapi import APIRouter, Depends
from sqlmodel import func, select

from app.api.deps import SessionDep, require_permission
from app.core.permissions import Permission
from app.models import Item, User

router = APIRouter()


@router.get(
    "/",
    dependencies=[Depends(require_permission(Permission.METRICS_VIEW))],
)
def read_metrics(session: SessionDep) -> dict[str, int]:
    """Lightweight insights stub. Visible to admin and manager only."""
    total_users = session.exec(select(func.count()).select_from(User)).one()
    active_users = session.exec(
        select(func.count()).select_from(User).where(User.is_active == True)  # noqa: E712
    ).one()
    total_items = session.exec(select(func.count()).select_from(Item)).one()
    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_items": total_items,
    }

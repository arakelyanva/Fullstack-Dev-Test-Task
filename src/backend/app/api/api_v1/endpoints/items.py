from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep
from app.core.permissions import Permission, has_permission
from app.models import Item, ItemCreate, ItemOut, ItemsOut, ItemUpdate, Message, User

router = APIRouter()


def can_manage_item(user: User, item: Item) -> bool:
    """Returns True if the user owns the item or has the ITEM_MANAGE_ANY permission."""
    return item.owner_id == user.id or has_permission(user.role, Permission.ITEM_MANAGE_ANY)


@router.get("/", response_model=ItemsOut)
def read_items(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve items. Admins see all items; all other roles see only their own.
    """
    count = session.exec(select(func.count()).select_from(Item)).one()

    if has_permission(current_user.role, Permission.ITEM_MANAGE_ANY):
        items = session.exec(select(Item).offset(skip).limit(limit)).all()
    else:
        items = session.exec(
            select(Item)
            .where(Item.owner_id == current_user.id)
            .offset(skip)
            .limit(limit)
        ).all()

    return ItemsOut(data=items, count=count)


@router.get("/{id}", response_model=ItemOut)
def read_item(session: SessionDep, current_user: CurrentUser, id: int) -> Any:
    """
    Get item by ID.
    """
    item = session.get(Item, id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not can_manage_item(current_user, item):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return item


@router.post("/", response_model=ItemOut)
def create_item(
    *, session: SessionDep, current_user: CurrentUser, item_in: ItemCreate
) -> Any:
    """
    Create new item.
    """
    item = Item.model_validate(item_in, update={"owner_id": current_user.id})
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.put("/{id}", response_model=ItemOut)
def update_item(
    *, session: SessionDep, current_user: CurrentUser, id: int, item_in: ItemUpdate
) -> Any:
    """
    Update an item.
    """
    item = session.get(Item, id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not can_manage_item(current_user, item):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    update_dict = item_in.model_dump(exclude_unset=True)
    item.sqlmodel_update(update_dict)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.delete("/{id}")
def delete_item(session: SessionDep, current_user: CurrentUser, id: int) -> Message:
    """
    Delete an item.
    """
    item = session.get(Item, id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not can_manage_item(current_user, item):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    session.delete(item)
    session.commit()
    return Message(message="Item deleted successfully")

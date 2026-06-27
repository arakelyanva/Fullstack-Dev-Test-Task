from enum import Enum

from pydantic import computed_field
from sqlmodel import Field, Relationship, SQLModel


class Role(str, Enum):
    admin = "admin"
    manager = "manager"
    member = "member"


# Shared properties
class UserBase(SQLModel):
    email: str = Field(unique=True, index=True)
    is_active: bool = True
    role: Role = Field(default=Role.member)
    full_name: str | None = None


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str


# Properties to receive via API on open registration (no role - always member)
class UserCreateOpen(SQLModel):
    email: str
    password: str
    full_name: str | None = None


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: str | None = None
    password: str | None = None


class UserUpdateMe(SQLModel):
    full_name: str | None = None
    email: str | None = None


class UpdatePassword(SQLModel):
    current_password: str
    new_password: str


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str
    items: list["Item"] = Relationship(back_populates="owner")

    @property
    def is_superuser(self) -> bool:
        """Backward-compatible derived value. Use role checks for new code."""
        return self.role == Role.admin


# Properties to return via API, id is always required
class UserOut(UserBase):
    id: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_superuser(self) -> bool:
        """Backward-compatible derived field for existing API consumers and tests."""
        return self.role == Role.admin


class UsersOut(SQLModel):
    data: list[UserOut]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str
    description: str | None = None


# Properties to receive on item creation
class ItemCreate(ItemBase):
    title: str


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = None


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    owner_id: int | None = Field(default=None, foreign_key="user.id", nullable=False)
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemOut(ItemBase):
    id: int
    owner_id: int


class ItemsOut(SQLModel):
    data: list[ItemOut]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: int | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str

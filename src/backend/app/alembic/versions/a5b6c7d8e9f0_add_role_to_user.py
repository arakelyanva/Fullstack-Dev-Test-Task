"""add role to user

Revision ID: a5b6c7d8e9f0
Revises: e2412789c190
Create Date: 2026-06-27

"""
from alembic import op
import sqlalchemy as sa


revision = "a5b6c7d8e9f0"
down_revision = "e2412789c190"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add role with a safe server_default so existing rows get a valid value immediately.
    op.add_column(
        "user",
        sa.Column("role", sa.String(length=20), nullable=False, server_default="member"),
    )
    # 2. Backfill: existing superusers become admins.
    op.execute('UPDATE "user" SET role = \'admin\' WHERE is_superuser = true')
    # 3. Drop the now-derived column.
    op.drop_column("user", "is_superuser")
    # 4. Remove the server_default so the application-side default (Role.member) is the
    #    single source of truth for new rows going forward.
    op.alter_column("user", "role", server_default=None)


def downgrade():
    op.add_column(
        "user",
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute('UPDATE "user" SET is_superuser = true WHERE role = \'admin\'')
    op.alter_column("user", "is_superuser", server_default=None)
    op.drop_column("user", "role")

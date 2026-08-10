"""add enterprise group, membership and event tables

Revision ID: 6f7e8a9b0c1d
Revises: 4d5e6f7a8b9c
Create Date: 2026-08-11 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6f7e8a9b0c1d"
down_revision: str | None = "4d5e6f7a8b9c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "enterprise_groups",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("owner_id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_enterprise_groups_owner_id", "enterprise_groups", ["owner_id"], unique=False
    )

    op.create_table(
        "enterprise_group_members",
        sa.Column("group_id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("group_id", "user_id"),
    )

    op.create_table(
        "enterprise_events",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("group_id", sa.String(length=26), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_enterprise_events_group_id", "enterprise_events", ["group_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_enterprise_events_group_id", table_name="enterprise_events")
    op.drop_table("enterprise_events")
    op.drop_table("enterprise_group_members")
    op.drop_index("ix_enterprise_groups_owner_id", table_name="enterprise_groups")
    op.drop_table("enterprise_groups")

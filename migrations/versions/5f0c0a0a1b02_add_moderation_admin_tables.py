"""add moderation and admin action tables

Revision ID: 5f0c0a0a1b02
Revises: 3c86a14d29e1
Create Date: 2026-08-10 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5f0c0a0a1b02"
down_revision: str | None = "3c86a14d29e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "moderation_items",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("object_type", sa.String(length=20), nullable=False),
        sa.Column("object_id", sa.String(length=26), nullable=False),
        sa.Column("reporter_id", sa.String(length=26), nullable=True),
        sa.Column("reason", sa.String(length=100), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("decision", sa.String(length=20), nullable=True),
        sa.Column("auto_flag", sa.Boolean(), nullable=False),
        sa.Column("reviewed_by", sa.String(length=26), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_moderation_items_decision", "moderation_items", ["decision"], unique=False)
    op.create_index(
        "ix_moderation_items_object_id", "moderation_items", ["object_id"], unique=False
    )
    op.create_index(
        "ix_moderation_items_object_type", "moderation_items", ["object_type"], unique=False
    )

    op.create_table(
        "admin_actions",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("admin_id", sa.String(length=26), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("target_type", sa.String(length=20), nullable=False),
        sa.Column("target_id", sa.String(length=26), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_actions_admin_id", "admin_actions", ["admin_id"], unique=False)
    op.create_index("ix_admin_actions_target_id", "admin_actions", ["target_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_admin_actions_target_id", table_name="admin_actions")
    op.drop_index("ix_admin_actions_admin_id", table_name="admin_actions")
    op.drop_table("admin_actions")
    op.drop_index("ix_moderation_items_object_type", table_name="moderation_items")
    op.drop_index("ix_moderation_items_object_id", table_name="moderation_items")
    op.drop_index("ix_moderation_items_decision", table_name="moderation_items")
    op.drop_table("moderation_items")

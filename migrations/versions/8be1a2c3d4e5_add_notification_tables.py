"""add notification tables

Revision ID: 8be1a2c3d4e5
Revises: 2ac491d3cc91
Create Date: 2026-08-11 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8be1a2c3d4e5"
down_revision: str | None = "2ac491d3cc91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("platform", sa.String(length=10), nullable=False),
        sa.Column("push_token", sa.String(length=300), nullable=False),
        sa.Column("topics", sa.Text(), nullable=True),
        sa.Column("disabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_push_subscriptions_user_id", "push_subscriptions", ["user_id"], unique=False
    )

    op.create_table(
        "notification_log",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.String(length=26), nullable=True),
        sa.Column("topic", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_log_status", "notification_log", ["status"], unique=False)
    op.create_index("ix_notification_log_user_id", "notification_log", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_notification_log_user_id", table_name="notification_log")
    op.drop_index("ix_notification_log_status", table_name="notification_log")
    op.drop_table("notification_log")
    op.drop_index("ix_push_subscriptions_user_id", table_name="push_subscriptions")
    op.drop_table("push_subscriptions")

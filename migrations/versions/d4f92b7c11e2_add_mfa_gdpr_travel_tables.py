"""add mfa, consent, travel list, bookmark and capture tables

Revision ID: d4f92b7c11e2
Revises: c33628766081
Create Date: 2026-08-10 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4f92b7c11e2"
down_revision: str | None = "c33628766081"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "mfa_devices",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("secret", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mfa_devices_user_id"), "mfa_devices", ["user_id"], unique=False)

    op.create_table(
        "consent_records",
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("policy_id", sa.String(length=80), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=300), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "policy_id"),
    )

    op.create_table(
        "travel_lists",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_travel_lists_user_id"), "travel_lists", ["user_id"], unique=False)

    op.create_table(
        "bookmarks",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("tour_id", sa.String(length=26), nullable=True),
        sa.Column("poi_id", sa.String(length=26), nullable=True),
        sa.Column("list_id", sa.String(length=26), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bookmarks_poi_id"), "bookmarks", ["poi_id"], unique=False)
    op.create_index(op.f("ix_bookmarks_user_id"), "bookmarks", ["user_id"], unique=False)

    op.create_table(
        "captures",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("tour_id", sa.String(length=26), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("t_begin", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("t_end", sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_captures_tour_id"), "captures", ["tour_id"], unique=False)
    op.create_index(op.f("ix_captures_user_id"), "captures", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_captures_user_id"), table_name="captures")
    op.drop_index(op.f("ix_captures_tour_id"), table_name="captures")
    op.drop_table("captures")
    op.drop_index(op.f("ix_bookmarks_user_id"), table_name="bookmarks")
    op.drop_index(op.f("ix_bookmarks_poi_id"), table_name="bookmarks")
    op.drop_table("bookmarks")
    op.drop_index(op.f("ix_travel_lists_user_id"), table_name="travel_lists")
    op.drop_table("travel_lists")
    op.drop_table("consent_records")
    op.drop_index(op.f("ix_mfa_devices_user_id"), table_name="mfa_devices")
    op.drop_table("mfa_devices")
    op.drop_column("users", "deleted_at")

"""add tour_categories table and enforce users.accessibility NOT NULL

Revision ID: 7b1c2d3e4f5a
Revises: 6f7e8a9b0c1d
Create Date: 2026-08-10 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7b1c2d3e4f5a"
down_revision: str | None = "6f7e8a9b0c1d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tour_categories",
        sa.Column("tour_id", sa.String(length=26), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.ForeignKeyConstraint(["tour_id"], ["tours.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tour_id", "category"),
    )

    # The ORM model declares accessibility as a required JSON column; backfill
    # any rows created before the constraint was tightened before enforcing it.
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        bind.execute(sa.text("UPDATE users SET accessibility = '{}' WHERE accessibility IS NULL"))
    else:
        bind.execute(
            sa.text("UPDATE users SET accessibility = '{}'::json WHERE accessibility IS NULL")
        )
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "accessibility", existing_type=sa.JSON(), existing_nullable=True, nullable=False
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "accessibility", existing_type=sa.JSON(), existing_nullable=False, nullable=True
        )
    op.drop_table("tour_categories")

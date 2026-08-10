"""add user profile avatar_url and accessibility columns

Revision ID: 4d5e6f7a8b9c
Revises: 8be1a2c3d4e5
Create Date: 2026-08-11 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4d5e6f7a8b9c"
down_revision: str | None = "8be1a2c3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_url", sa.String(length=500), nullable=True))
    op.add_column("users", sa.Column("accessibility", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "accessibility")
    op.drop_column("users", "avatar_url")

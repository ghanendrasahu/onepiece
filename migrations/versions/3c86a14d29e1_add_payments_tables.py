"""add payments tables (subscriptions, transactions, tips)

Revision ID: 3c86a14d29e1
Revises: d4f92b7c11e2
Create Date: 2026-08-10 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3c86a14d29e1"
down_revision: str | None = "d4f92b7c11e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("plan_id", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("provider_sub_id", sa.String(length=200), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"], unique=False)
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=False)

    op.create_table(
        "transactions",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("gross_cents", sa.BigInteger(), nullable=False),
        sa.Column("fee_cents", sa.BigInteger(), nullable=False),
        sa.Column("net_cents", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=5), nullable=False),
        sa.Column("provider_tx_id", sa.String(length=200), nullable=True),
        sa.Column("idempotency_key", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_transactions_status", "transactions", ["status"], unique=False)
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"], unique=False)

    op.create_table(
        "tips",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("stream_id", sa.String(length=26), nullable=True),
        sa.Column("from_user", sa.String(length=26), nullable=False),
        sa.Column("to_creator", sa.String(length=26), nullable=False),
        sa.Column("cents", sa.BigInteger(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tips_from_user", "tips", ["from_user"], unique=False)
    op.create_index("ix_tips_stream_id", "tips", ["stream_id"], unique=False)
    op.create_index("ix_tips_to_creator", "tips", ["to_creator"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tips_to_creator", table_name="tips")
    op.drop_index("ix_tips_stream_id", table_name="tips")
    op.drop_index("ix_tips_from_user", table_name="tips")
    op.drop_table("tips")
    op.drop_index("ix_transactions_user_id", table_name="transactions")
    op.drop_index("ix_transactions_status", table_name="transactions")
    op.drop_table("transactions")
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_status", table_name="subscriptions")
    op.drop_table("subscriptions")

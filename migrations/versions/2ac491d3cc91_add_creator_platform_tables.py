"""add creator platform tables

Revision ID: 2ac491d3cc91
Revises: 5f0c0a0a1b02
Create Date: 2026-08-11 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2ac491d3cc91"
down_revision: str | None = "5f0c0a0a1b02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "creator_profiles",
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("equipment", sa.Text(), nullable=True),
        sa.Column("region", sa.String(length=40), nullable=True),
        sa.Column("id_doc_token", sa.String(length=120), nullable=True),
        sa.Column("liveness_token", sa.String(length=120), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index("ix_creator_profiles_status", "creator_profiles", ["status"], unique=False)

    op.create_table(
        "equipment_loans",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("equipment", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_equipment_loans_status", "equipment_loans", ["status"], unique=False)
    op.create_index("ix_equipment_loans_user_id", "equipment_loans", ["user_id"], unique=False)

    op.create_table(
        "payouts",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("creator_id", sa.String(length=26), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=5), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("provider_tx_id", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payouts_creator_id", "payouts", ["creator_id"], unique=False)
    op.create_index("ix_payouts_status", "payouts", ["status"], unique=False)

    op.create_table(
        "private_tour_offers",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("creator_id", sa.String(length=26), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_cents", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=5), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_private_tour_offers_creator_id", "private_tour_offers", ["creator_id"], unique=False
    )
    op.create_index(
        "ix_private_tour_offers_status", "private_tour_offers", ["status"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_private_tour_offers_status", table_name="private_tour_offers")
    op.drop_index("ix_private_tour_offers_creator_id", table_name="private_tour_offers")
    op.drop_table("private_tour_offers")
    op.drop_index("ix_payouts_status", table_name="payouts")
    op.drop_index("ix_payouts_creator_id", table_name="payouts")
    op.drop_table("payouts")
    op.drop_index("ix_equipment_loans_user_id", table_name="equipment_loans")
    op.drop_index("ix_equipment_loans_status", table_name="equipment_loans")
    op.drop_table("equipment_loans")
    op.drop_index("ix_creator_profiles_status", table_name="creator_profiles")
    op.drop_table("creator_profiles")

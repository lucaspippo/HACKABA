"""add location column to purchase_orders

Revision ID: 0033
Revises: 0032
Create Date: 2026-08-26

Manual purchase orders (core/ordenes.py: crear_manual) carry a delivery
location; Angela-drafted ones (preparar()) don't set it. Nullable, additive —
existing rows and the AI-drafting path are unaffected.
"""
from alembic import op
import sqlalchemy as sa

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("purchase_orders", sa.Column("location", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("purchase_orders", "location")

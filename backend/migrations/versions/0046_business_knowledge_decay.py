"""add decay columns to business_knowledge_pieces

Revision ID: 0046
Revises: 0045
Create Date: 2026-09-11
"""
from alembic import op
import sqlalchemy as sa

revision = "0046"
down_revision = "0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("business_knowledge_pieces",
        sa.Column("confidence", sa.Numeric, nullable=False, server_default="0.7"))
    op.add_column("business_knowledge_pieces",
        sa.Column("evidence_count", sa.Integer, nullable=False, server_default="1"))
    # DEFAULT can't reference another column, so backfill from created_at
    # before locking the column down to NOT NULL.
    op.add_column("business_knowledge_pieces",
        sa.Column("last_reinforced_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.execute("UPDATE business_knowledge_pieces SET last_reinforced_at = created_at")
    op.alter_column("business_knowledge_pieces", "last_reinforced_at",
        nullable=False, server_default=sa.text("now()"))
    op.add_column("business_knowledge_pieces",
        sa.Column("half_life_days", sa.Integer, nullable=True))


def downgrade() -> None:
    op.drop_column("business_knowledge_pieces", "half_life_days")
    op.drop_column("business_knowledge_pieces", "last_reinforced_at")
    op.drop_column("business_knowledge_pieces", "evidence_count")
    op.drop_column("business_knowledge_pieces", "confidence")

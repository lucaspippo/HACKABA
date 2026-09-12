"""add archive/supersede states to business_knowledge_pieces

Revision ID: 0047
Revises: 0046
Create Date: 2026-09-11
"""
from alembic import op
import sqlalchemy as sa

revision = "0047"
down_revision = "0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("business_knowledge_pieces",
        sa.Column("superseded_by", sa.Text, nullable=True))
    op.drop_constraint("business_knowledge_pieces_estado_check", "business_knowledge_pieces")
    op.create_check_constraint(
        "business_knowledge_pieces_estado_check", "business_knowledge_pieces",
        "estado IN ('activo', 'pausado', 'pendiente', 'revisar', 'superada', 'archivada')")


def downgrade() -> None:
    op.drop_constraint("business_knowledge_pieces_estado_check", "business_knowledge_pieces")
    op.create_check_constraint(
        "business_knowledge_pieces_estado_check", "business_knowledge_pieces",
        "estado IN ('activo', 'pausado', 'pendiente')")
    op.drop_column("business_knowledge_pieces", "superseded_by")

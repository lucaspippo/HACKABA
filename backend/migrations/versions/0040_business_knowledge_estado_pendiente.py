"""allow 'pendiente' in business_knowledge_pieces.estado

Revision ID: 0040
Revises: 0039
Create Date: 2026-09-02

A piece proposed via chat (angela.py's proponer_conocimiento) lands as
"pendiente" — visible, but never picked up by aplicables()/para() — until
someone with the right node reviews it (aprobar/rechazar in
core/conocimiento.py). Widens the check constraint 0039 created; no data
migration needed, nothing existing ever used this value yet.
"""
from alembic import op

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("business_knowledge_pieces_estado_check", "business_knowledge_pieces")
    op.create_check_constraint(
        "business_knowledge_pieces_estado_check", "business_knowledge_pieces",
        "estado IN ('activo', 'pausado', 'pendiente')")


def downgrade() -> None:
    op.drop_constraint("business_knowledge_pieces_estado_check", "business_knowledge_pieces")
    op.create_check_constraint(
        "business_knowledge_pieces_estado_check", "business_knowledge_pieces",
        "estado IN ('activo', 'pausado')")

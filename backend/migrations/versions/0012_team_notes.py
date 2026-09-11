"""create team_notes table with RLS

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-24

One row per tenant holding core/notas.py's whole read-only free-text notes
blob as JSONB — same pattern as supplier_conditions. No write API exists
at the application layer; seeded once from data-demo/notas_equipo.json
(the tenant's real file) on first read.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "team_notes",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("data", psql.JSONB, nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.execute("ALTER TABLE team_notes ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE team_notes FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON team_notes
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_table("team_notes")

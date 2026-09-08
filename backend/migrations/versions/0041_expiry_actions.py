"""create expiry_actions table with RLS

Revision ID: 0041
Revises: 0040
Create Date: 2026-09-08

One row per tenant holding the {"<codigo>|<lote>": {tipo, cantidad, actor,
cuando, producto}} dict as JSONB — core/vencimientos.py reads/writes the whole
per-tenant map, like core/cobranza.py does with collection_actions. This is
what "Aprobar" on the expiry card persists: before it, the button set local
state and showed a toast, and a reload showed the lot again as if nothing
had been decided.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "expiry_actions",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("data", psql.JSONB, nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.execute("ALTER TABLE expiry_actions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE expiry_actions FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON expiry_actions
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_table("expiry_actions")

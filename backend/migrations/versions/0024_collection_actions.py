"""create collection_actions table with RLS

Revision ID: 0024
Revises: 0023
Create Date: 2026-08-26

One row per tenant holding the {cliente_id: {estado, cuando, actor, nota,
promesa_fecha, mensaje}} dict as JSONB — core/cobranza.py always
reads/writes the whole per-tenant map, never a single field in SQL.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "collection_actions",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("data", psql.JSONB, nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.execute("ALTER TABLE collection_actions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE collection_actions FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON collection_actions
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_table("collection_actions")

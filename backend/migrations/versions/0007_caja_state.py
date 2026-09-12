"""create caja_state table with RLS

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-24

One row per tenant holding the full caja state (abierta/fecha/saldo_inicial/
movimientos/historial) as JSONB — same one-blob-per-tenant shape as
inventory_working, for the same reason: core/caja.py always reads/writes
the whole dict, never queries a field in SQL.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "caja_state",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("data", psql.JSONB, nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.execute("ALTER TABLE caja_state ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE caja_state FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON caja_state
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_table("caja_state")

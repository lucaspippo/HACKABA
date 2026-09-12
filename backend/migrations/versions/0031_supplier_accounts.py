"""create supplier_accounts table with RLS

Revision ID: 0031
Revises: 0030
Create Date: 2026-08-26

One row per tenant holding the list of supplier running-account dicts
({proveedor, saldo, movimientos}) as JSONB — core/comprobantes.py always
reads/writes the whole per-tenant list, never a single field in SQL.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "supplier_accounts",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("data", psql.JSONB, nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.execute("ALTER TABLE supplier_accounts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE supplier_accounts FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON supplier_accounts
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_table("supplier_accounts")

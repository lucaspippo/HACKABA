"""create client_sales_data table with RLS

Revision ID: 0023
Revises: 0022
Create Date: 2026-08-26

One row per tenant holding the {clientes: [...]} dict (what each client
bought, per order) as JSONB — read-only reference. core/ventas_cliente.py
always reads the whole blob, never a single field in SQL.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "client_sales_data",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("data", psql.JSONB, nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.execute("ALTER TABLE client_sales_data ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE client_sales_data FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON client_sales_data
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_table("client_sales_data")

"""create data_sections table with RLS

Revision ID: 0026
Revises: 0025
Create Date: 2026-08-26

One row per tenant holding the {tipo: {nombre, filas: [...]}} dict as
JSONB — core/esquema.py's "apartados" (which data sections exist for this
tenant, e.g. venta/cliente/deposito). Always read/written whole, never a
single field in SQL.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_sections",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("data", psql.JSONB, nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.execute("ALTER TABLE data_sections ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE data_sections FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON data_sections
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_table("data_sections")

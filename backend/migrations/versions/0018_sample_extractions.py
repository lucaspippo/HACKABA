"""create sample_extractions table with RLS

Revision ID: 0018
Revises: 0017
Create Date: 2026-08-26

One row per tenant holding the {sha256: extraccion} canonical-sample lookup
as JSONB — read-only reference data emitted by
data-demo/comprobantes/generar_comprobantes.py. core/extraccion.py always
reads the whole map, never a single field in SQL.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sample_extractions",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("data", psql.JSONB, nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.execute("ALTER TABLE sample_extractions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE sample_extractions FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON sample_extractions
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_table("sample_extractions")

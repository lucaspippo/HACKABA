"""create organization_config table with RLS

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-24

One row per tenant holding organization-level config (name, industry,
margin thresholds, etc.) as JSONB — same one-blob-per-tenant shape as
caja_state/inventory_working: core/organizacion.py always reads/writes the
whole config dict, never a single field in SQL.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organization_config",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("data", psql.JSONB, nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.execute("ALTER TABLE organization_config ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE organization_config FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON organization_config
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_table("organization_config")

"""create automation_policies table with RLS

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-26

One row per tenant holding the owner's autonomy-level overrides (class ->
level) as JSONB — same one-blob-per-tenant shape as organization_config:
core/autonomia.py always reads/writes the whole dict, never a single field
in SQL.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "automation_policies",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("data", psql.JSONB, nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.execute("ALTER TABLE automation_policies ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE automation_policies FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON automation_policies
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_table("automation_policies")

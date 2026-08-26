"""create supplier_conditions table with RLS

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-24

One row per tenant holding core/reposicion.py's whole read-only reference
blob (supplier conditions, active offers, default replenishment days) as
JSONB. No write API exists at the application layer for this data (it's a
reference dataset, not user-editable state) — this table is seeded once
from data-demo/proveedores_condiciones.json (or the tenant's own copy) and
never updated afterward, same read-only role the JSON file plays today.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "supplier_conditions",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("data", psql.JSONB, nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.execute("ALTER TABLE supplier_conditions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE supplier_conditions FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON supplier_conditions
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_table("supplier_conditions")

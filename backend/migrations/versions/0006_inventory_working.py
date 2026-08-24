"""create inventory_working table with RLS

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-24

One row per tenant holding the full working-copy article list as JSONB —
mirrors inventory_actual.json's shape exactly ({"articulos": [...]}). Never
queried in SQL; every consumer (core/store.py) loads it whole into Python,
same as it always has. The canonical inventory.json stays a read-only file
on disk (the seed source), same role data-demo/cuentas.json plays for
core/cuentas.py — see core/db/MIGRATING_A_MODULE.md.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inventory_working",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("articulos", psql.JSONB, nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.execute("ALTER TABLE inventory_working ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE inventory_working FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON inventory_working
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_table("inventory_working")

"""create inventory_baseline table with RLS

Revision ID: 0017
Revises: 0016
Create Date: 2026-08-26

One row per tenant holding the ORIGINAL (pre-correction) article list as
JSONB — the source-system baseline core/sync.py diffs the working copy
against to compute deltas. Seeded once from the same inventory.json seed
source as inventory_working (see core/store.py), then never mutated again:
it is a snapshot of what came from the external system, not a working copy.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inventory_baseline",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("data", psql.JSONB, nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.execute("ALTER TABLE inventory_baseline ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE inventory_baseline FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON inventory_baseline
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_table("inventory_baseline")

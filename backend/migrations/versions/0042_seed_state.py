"""create seed_state table with RLS

Revision ID: 0042
Revises: 0041
Create Date: 2026-09-08

One row per (tenant, domain) holding the SHA-256 of the on-disk JSON that
domain was last seeded from. Every domain module seeds itself on first read
ONLY when its blob is missing, which is right for a productive tenant and a
trap for the demo: generar.py rewrites the dataset on every boot, the blob
already exists, and the new dataset never arrives. This table is what lets
`core/db/seed_state.py` notice that the seed file changed — see that module
for why the comparison is against the FILE and never against the blob.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "seed_state",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("dominio", sa.Text, primary_key=True),
        sa.Column("seed_hash", sa.Text, nullable=False),
        sa.Column("seeded_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.execute("ALTER TABLE seed_state ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE seed_state FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON seed_state
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_table("seed_state")

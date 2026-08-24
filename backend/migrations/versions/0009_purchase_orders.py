"""create purchase_orders table with RLS

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-24

Purchase orders core/ordenes.py drafts (never sent to a supplier on its
own — an "Angela proposes, the owner approves" workflow). No seed data:
these only exist once someone/something creates one, so a new tenant
starts with none.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "purchase_orders",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("number", sa.Text, nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("supplier", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("origin", sa.Text, nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("prepared_by", sa.Text, nullable=False),
        sa.Column("approved_by", sa.Text, nullable=False),
        sa.Column("prepared_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("items", psql.JSONB, nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "number"),
    )

    op.execute("ALTER TABLE purchase_orders ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE purchase_orders FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON purchase_orders
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_table("purchase_orders")

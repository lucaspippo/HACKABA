"""create reminders table with RLS

Revision ID: 0019
Revises: 0018
Create Date: 2026-08-26

Per-row table for core/recordatorios.py's reminders (simple, condition-based,
and event-based). `id` is client-generated ("r" + hex) like team_goals; the
module always operates on the tenant's full list, so core/recordatorios.py's
_save() does a full delete+reinsert per call — same semantics as the old
whole-file JSON rewrite, just per-row storage underneath.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reminders",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("id", sa.Text, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("recipient", sa.Text, nullable=False),
        sa.Column("created_by", sa.Text, nullable=False),
        sa.Column("condition", psql.JSONB, nullable=True),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("triggered_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("trigger_detail", sa.Text, nullable=True),
        sa.Column("channels", psql.JSONB, nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "id"),
    )

    op.execute("ALTER TABLE reminders ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE reminders FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON reminders
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_table("reminders")

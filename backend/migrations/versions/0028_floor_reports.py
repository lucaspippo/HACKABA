"""create floor_reports table with RLS

Revision ID: 0028
Revises: 0027
Create Date: 2026-08-26

Per-row table for core/piso.py's floor reports (faltante/conteo/entrega/
reposicion/pedido). `id` is client-generated ("p" + hex), matching the
pattern of other client-id per-row tables (team_goals, reminders).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "floor_reports",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("id", sa.Text, nullable=False),
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("actor", sa.Text, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("report_date", sa.Date, nullable=False),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("data", psql.JSONB, nullable=False),
        sa.Column("attachment", sa.Text, nullable=True),
        sa.Column("resolved_by", sa.Text, nullable=True),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("resolved_note", sa.Text, nullable=True),
        sa.PrimaryKeyConstraint("tenant_id", "id"),
    )

    op.execute("ALTER TABLE floor_reports ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE floor_reports FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON floor_reports
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_table("floor_reports")

"""create team_goals table with RLS

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-24

Team goals core/objetivos.py persists server-side (P9-C5, M9). No seed
data — a new tenant starts with none. The id can come from the client
(the board's own uid), so it's the primary key, not a generated one.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "team_goals",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("id", sa.Text, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("owner", sa.Text, nullable=False),
        sa.Column("target_date", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("created_by", sa.Text, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("tenant_id", "id"),
    )

    op.execute("ALTER TABLE team_goals ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE team_goals FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON team_goals
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_table("team_goals")

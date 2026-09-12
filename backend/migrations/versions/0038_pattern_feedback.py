"""create pattern_feedback table with RLS

Revision ID: 0038
Revises: 0037
Create Date: 2026-08-31

One row per feedback event on a core/patrones.py finding (accepted /
dismissed / already knew), keyed by (pattern_id, fingerprint) so a
recurring instance of the same underlying finding (e.g. the same product
pair, the same flagged weekday) is recognized as "already handled" even
after its live numbers change, while a genuinely different instance (a
different pair, a different weekday) is treated as new. `snapshot` freezes
the finding's display text at feedback time, so a history view can still
show what the finding was about after it stops firing live.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pattern_feedback",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pattern_id", sa.Text, nullable=False),
        sa.Column("fingerprint", sa.Text, nullable=False),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("actor", sa.Text, nullable=False),
        sa.Column("snapshot", psql.JSONB, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint(
            "action IN ('accepted', 'dismissed', 'already_knew')",
            name="pattern_feedback_action_check"),
    )
    op.create_index("ix_pattern_feedback_tenant_id", "pattern_feedback", ["tenant_id"])
    op.create_index("ix_pattern_feedback_lookup", "pattern_feedback",
                    ["tenant_id", "pattern_id", "fingerprint"])

    op.execute("ALTER TABLE pattern_feedback ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pattern_feedback FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON pattern_feedback
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_table("pattern_feedback")

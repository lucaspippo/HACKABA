"""floor_reports: recipient, and the receipt that says somebody saw it

Revision ID: 0044
Revises: 0043
Create Date: 2026-09-08

A floor report was born with an author and no addressee. It landed in a pool
only the owner could read, and closing it told nobody — so the person who
reported eight broken boxes never learned whether anything came of it, and went
back to the WhatsApp group, where at least somebody answers.

Three columns close that loop:

  recipient  — who it was directed to. Ángela proposes it and the person
               confirms; it is never chosen from a list of fourteen names.
  seen_at    — the receipt. Without it, "nobody owns this" and "somebody owns
  seen_by      it and has not opened it" look identical to the sender, and the
               difference is the whole point.

`status` gains an intermediate value, so the lifecycle reads nuevo → visto →
resuelto. Existing rows keep their status and get a NULL recipient: they are
the reports that were filed before anyone could direct them, and they stay
readable by the owner exactly as they were.
"""
from alembic import op
import sqlalchemy as sa

revision = "0044"
down_revision = "0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("floor_reports", sa.Column("recipient", sa.Text(), nullable=True))
    op.add_column("floor_reports",
                  sa.Column("seen_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("floor_reports", sa.Column("seen_by", sa.Text(), nullable=True))
    # The two questions this table is asked from now on: "what did I send?" and
    # "what is waiting for me?". Both are per-tenant scans today; the indexes
    # keep them that way as the table grows.
    op.create_index("ix_floor_reports_recipient", "floor_reports",
                    ["tenant_id", "recipient"])
    op.create_index("ix_floor_reports_actor", "floor_reports",
                    ["tenant_id", "actor"])


def downgrade() -> None:
    op.drop_index("ix_floor_reports_actor", table_name="floor_reports")
    op.drop_index("ix_floor_reports_recipient", table_name="floor_reports")
    op.drop_column("floor_reports", "seen_by")
    op.drop_column("floor_reports", "seen_at")
    op.drop_column("floor_reports", "recipient")

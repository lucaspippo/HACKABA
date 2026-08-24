"""create customer_accounts and account_movements tables with RLS

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_accounts",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("id", sa.Text, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("balance", sa.Numeric, nullable=False, server_default="0"),
        sa.Column("credit_limit", sa.Numeric, nullable=False, server_default="0"),
        sa.Column("payment_term_days", sa.Integer, nullable=False, server_default="30"),
        sa.Column("days_overdue", sa.Integer, nullable=False, server_default="0"),
        sa.Column("average_payment_days", sa.Integer, nullable=True),
        sa.PrimaryKeyConstraint("tenant_id", "id"),
    )
    op.create_table(
        "account_movements",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("tenant_id", psql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", sa.Text, nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("amount", sa.Numeric, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id", "customer_id"], ["customer_accounts.tenant_id", "customer_accounts.id"],
            ondelete="CASCADE",
        ),
    )

    for tbl in ("customer_accounts", "account_movements"):
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {tbl}
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
        """)


def downgrade() -> None:
    op.drop_table("account_movements")
    op.drop_table("customer_accounts")

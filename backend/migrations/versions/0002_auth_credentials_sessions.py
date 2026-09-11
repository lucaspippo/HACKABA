"""create auth_credentials and sessions tables with RLS

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_credentials",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("username", sa.Text, nullable=False),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("tenant_id", "username"),
    )
    op.create_table(
        "sessions",
        sa.Column("token", sa.Text, primary_key=True),
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("username", sa.Text, nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )

    for tbl in ("auth_credentials", "sessions"):
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {tbl}
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
        """)


def downgrade() -> None:
    op.drop_table("sessions")
    op.drop_table("auth_credentials")

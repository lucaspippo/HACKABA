"""create user_memory table with RLS

Revision ID: 0020
Revises: 0019
Create Date: 2026-08-26

One row per tenant holding the {username: {preferencias, vista,
categorias_auto, objetivos, datos_cargados, recomendaciones, ...}} dict as
JSONB — core/memoria.py always reads/writes the whole per-tenant map, never
a single field in SQL.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_memory",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("data", psql.JSONB, nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.execute("ALTER TABLE user_memory ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE user_memory FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON user_memory
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_table("user_memory")

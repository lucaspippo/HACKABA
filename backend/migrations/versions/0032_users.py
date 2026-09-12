"""create users table with RLS

Revision ID: 0032
Revises: 0031
Create Date: 2026-08-26

Per-row table replacing the hardcoded auth.USUARIOS / usuarios_demo.USUARIOS
dicts. `(tenant_id, username)` composite PK, matching auth_credentials and
sessions. `activo` is new — there was no deactivation concept in the old
hardcoded roster.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("username", sa.Text, nullable=False),
        sa.Column("nombre", sa.Text, nullable=False),
        sa.Column("rol", sa.Text, nullable=False),
        sa.Column("es_admin", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("interno", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("telefono", sa.Text, nullable=True),
        sa.Column("color", sa.Text, nullable=True),
        sa.Column("superficies", psql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("descripcion", sa.Text, nullable=True),
        sa.Column("descripcion_en", sa.Text, nullable=True),
        sa.Column("features", psql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("ingreso", sa.Date, nullable=True),
        sa.Column("puesto", psql.JSONB, nullable=True),
        sa.Column("activo", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("tenant_id", "username"),
    )

    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON users
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_table("users")

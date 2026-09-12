"""structured business rules: a deterministic condition/action engine
alongside core/conocimiento.py's free-text memory

Revision ID: 0048
Revises: 0047
Create Date: 2026-09-11

New table, no data migration: this is a sibling of business_knowledge_pieces
(0039), not a replacement for anything. See
docs/superpowers/specs/2026-09-11-structured-business-rules-design.md.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0048"
down_revision = "0047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "business_rules",
        sa.Column("id", sa.Text, nullable=False),
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("condition", psql.JSONB, nullable=False),
        sa.Column("action", psql.JSONB, nullable=False),
        sa.Column("node", sa.Text, nullable=False),
        sa.Column("scope", sa.Text, nullable=False),
        sa.Column("entity_name", sa.Text, nullable=True),
        sa.Column("entity_type", sa.Text, nullable=True),
        sa.Column("entity_id", sa.Text, nullable=True),
        sa.Column("origin", psql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("knowledge_piece_id", sa.Text, nullable=True),
        sa.Column("status", sa.Text, nullable=False, server_default="active"),
        sa.Column("supersedes", sa.Text, nullable=True),
        sa.Column("superseded_by", sa.Text, nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("test_cases", psql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("tenant_id", "id"),
        sa.CheckConstraint(
            "node IN ('ventas', 'inventario', 'deposito', 'proveedores', "
            "'clientes', 'caja', 'equipo', 'contexto')",
            name="business_rules_node_check"),
        sa.CheckConstraint(
            "scope IN ('cliente', 'proveedor', 'categoria', 'empleado', 'global')",
            name="business_rules_scope_check"),
        sa.CheckConstraint(
            "status IN ('active', 'paused', 'pending', 'archived', 'superseded')",
            name="business_rules_status_check"),
    )
    op.create_index("ix_business_rules_tenant_id", "business_rules", ["tenant_id"])

    op.execute("ALTER TABLE business_rules ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE business_rules FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON business_rules
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_table("business_rules")

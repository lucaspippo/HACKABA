"""normalize business_knowledge into one row per piece, with RLS

Revision ID: 0039
Revises: 0038
Create Date: 2026-09-02

`business_knowledge` (0025) stored the tenant's ENTIRE knowledge base as one
JSONB blob (`{"piezas": [...]}`) per tenant — every read/write of a single
piece meant loading and re-saving the whole array. This replaces it with
`business_knowledge_pieces`, one row per piece, so a single piece can be
read, created, or updated without touching the rest of the tenant's
knowledge base.

Existing rows are migrated in place (`jsonb_array_elements` unpacks each
tenant's `piezas` array into rows) before the old blob table is dropped, so
no tenant's already-taught knowledge is lost.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "business_knowledge_pieces",
        sa.Column("id", sa.Text, nullable=False),
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("texto", sa.Text, nullable=False),
        sa.Column("texto_en", sa.Text, nullable=True),
        sa.Column("tipo", sa.Text, nullable=False),
        sa.Column("ambito", sa.Text, nullable=False),
        sa.Column("entidad", sa.Text, nullable=True),
        sa.Column("nodo", sa.Text, nullable=False),
        sa.Column("efecto", sa.Text, nullable=False),
        sa.Column("efecto_profundo", sa.Boolean, nullable=False,
                  server_default=sa.text("false")),
        sa.Column("params", psql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("origen", psql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("estado", sa.Text, nullable=False, server_default="activo"),
        sa.Column("veces_aplicada", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("tenant_id", "id"),
        sa.CheckConstraint(
            "tipo IN ('regla', 'excepcion', 'protocolo', 'contexto')",
            name="business_knowledge_pieces_tipo_check"),
        sa.CheckConstraint(
            "ambito IN ('cliente', 'proveedor', 'categoria', 'empleado', 'global')",
            name="business_knowledge_pieces_ambito_check"),
        sa.CheckConstraint(
            "efecto IN ('ajusta_umbral', 'suprime_alerta', 'genera_alerta', "
            "'contexto_para_angela', 'requiere_aprobacion')",
            name="business_knowledge_pieces_efecto_check"),
        sa.CheckConstraint(
            "nodo IN ('ventas', 'inventario', 'deposito', 'proveedores', "
            "'clientes', 'caja', 'equipo', 'contexto')",
            name="business_knowledge_pieces_nodo_check"),
        sa.CheckConstraint(
            "estado IN ('activo', 'pausado')",
            name="business_knowledge_pieces_estado_check"),
    )
    op.create_index("ix_business_knowledge_pieces_tenant_id",
                    "business_knowledge_pieces", ["tenant_id"])

    op.execute("ALTER TABLE business_knowledge_pieces ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE business_knowledge_pieces FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON business_knowledge_pieces
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)

    # Carry over any tenant's already-taught knowledge from the old blob
    # table before dropping it — this runs against real data, not just the
    # demo seed file, so nothing a paying tenant already taught Ángela is lost.
    op.execute("""
        INSERT INTO business_knowledge_pieces
            (id, tenant_id, texto, texto_en, tipo, ambito, entidad, nodo,
             efecto, efecto_profundo, params, origen, estado, veces_aplicada)
        SELECT
            piece->>'id', bk.tenant_id, piece->>'texto', piece->>'texto_en',
            piece->>'tipo', piece->>'ambito', piece->>'entidad', piece->>'nodo',
            piece->>'efecto',
            COALESCE((piece->>'efecto_profundo')::boolean, false),
            COALESCE(piece->'params', '{}'::jsonb),
            COALESCE(piece->'origen', '{}'::jsonb),
            COALESCE(piece->>'estado', 'activo'),
            COALESCE((piece->>'veces_aplicada')::int, 0)
        FROM business_knowledge bk,
             jsonb_array_elements(COALESCE(bk.data->'piezas', '[]'::jsonb)) AS piece
        WHERE piece->>'id' IS NOT NULL
        ON CONFLICT (tenant_id, id) DO NOTHING
    """)

    op.drop_table("business_knowledge")


def downgrade() -> None:
    op.create_table(
        "business_knowledge",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("data", psql.JSONB, nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.execute("ALTER TABLE business_knowledge ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE business_knowledge FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON business_knowledge
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)
    op.execute("""
        INSERT INTO business_knowledge (tenant_id, data)
        SELECT tenant_id, jsonb_build_object('piezas', jsonb_agg(
            jsonb_build_object(
                'id', id, 'texto', texto, 'texto_en', texto_en, 'tipo', tipo,
                'ambito', ambito, 'entidad', entidad, 'nodo', nodo,
                'efecto', efecto, 'efecto_profundo', efecto_profundo,
                'params', params, 'origen', origen, 'estado', estado,
                'veces_aplicada', veces_aplicada
            )
        ))
        FROM business_knowledge_pieces
        GROUP BY tenant_id
    """)
    op.drop_table("business_knowledge_pieces")

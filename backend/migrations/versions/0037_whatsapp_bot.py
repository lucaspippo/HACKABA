"""create whatsapp_channels, whatsapp_conversations, whatsapp_messages with RLS

Revision ID: 0037
Revises: 0036
Create Date: 2026-08-29

The customer-facing WhatsApp sales channel (core/whatsapp_channel.py,
backend/whatsapp_bot.py) — separate from the existing internal-employee
WhatsApp entry point (main.py's `/api/whatsapp`, auth.usuario_por_numero).

whatsapp_channels: one row per tenant, the Meta WhatsApp Business Cloud API
credentials for its bot (phone_number_id, tokens). Same shape/pattern as
odoo_connections (0034): one row per tenant, secrets encrypted at rest.

whatsapp_conversations / whatsapp_messages: a customer (by phone number) and
the message history with them, so Ángela's tool-use loop can be handed real
back-and-forth context on every inbound webhook call instead of only the
single latest message.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "whatsapp_channels",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phone_number_id", sa.Text, nullable=False),
        sa.Column("display_phone_number", sa.Text, nullable=True),
        sa.Column("business_name", sa.Text, nullable=True),
        sa.Column("access_token_encrypted", sa.Text, nullable=False),
        sa.Column("app_secret_encrypted", sa.Text, nullable=False),
        sa.Column("verify_token", sa.Text, nullable=False),
        sa.Column("greeting_message", sa.Text, nullable=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("tenant_id"),
    )
    op.execute("ALTER TABLE whatsapp_channels ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE whatsapp_channels FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON whatsapp_channels
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)

    op.create_table(
        "whatsapp_conversations",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("id", sa.Text, nullable=False),
        sa.Column("customer_phone", sa.Text, nullable=False),
        sa.Column("customer_name", sa.Text, nullable=True),
        sa.Column("status", sa.Text, nullable=False, server_default=sa.text("'abierta'")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("last_message_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("tenant_id", "id"),
        sa.UniqueConstraint("tenant_id", "customer_phone", name="uq_whatsapp_conv_phone"),
    )
    op.execute("ALTER TABLE whatsapp_conversations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE whatsapp_conversations FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON whatsapp_conversations
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)

    op.create_table(
        "whatsapp_messages",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("id", sa.Text, nullable=False),
        sa.Column("conversation_id", sa.Text, nullable=False),
        sa.Column("direction", sa.Text, nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("wa_message_id", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("tenant_id", "id"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "conversation_id"],
            ["whatsapp_conversations.tenant_id", "whatsapp_conversations.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_whatsapp_messages_conversation",
        "whatsapp_messages", ["tenant_id", "conversation_id", "created_at"],
    )
    op.execute("ALTER TABLE whatsapp_messages ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE whatsapp_messages FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON whatsapp_messages
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_table("whatsapp_messages")
    op.drop_table("whatsapp_conversations")
    op.drop_table("whatsapp_channels")

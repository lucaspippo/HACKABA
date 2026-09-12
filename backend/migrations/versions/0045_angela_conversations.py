"""create angela_conversations, angela_messages with RLS

Revision ID: 0045
Revises: 0044
Create Date: 2026-09-11

Ángela's chat (`/api/angela`, `/api/angela/stream`) and the voice surface
(core/voz.py) have never persisted a single word said to them: `history` is
round-tripped from the browser on every request, and the only server-side
trace was a scrubbed `store.audit` event — tool names and latency, no text
(see main.py's `consulta_angela` audit call). That is fine for the admin
activity feed it was built for, but it leaves no raw transcript to go back to
for a dispute, a training review, or a "what exactly did the model tell this
person" audit.

angela_conversations / angela_messages give that a home, same shape as
whatsapp_conversations/whatsapp_messages (0037): one row per turn, tenant-
isolated, append-only. `channel` distinguishes the surface a conversation
came from (`chat` today; `voz`/`voz_viva` land in later PRs) without needing
a separate table per surface.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0045"
down_revision = "0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "angela_conversations",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("id", sa.Text, nullable=False),
        sa.Column("actor", sa.Text, nullable=False),
        sa.Column("channel", sa.Text, nullable=False, server_default=sa.text("'chat'")),
        sa.Column("status", sa.Text, nullable=False, server_default=sa.text("'abierta'")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("last_message_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("tenant_id", "id"),
    )
    op.create_index(
        "ix_angela_conversations_actor",
        "angela_conversations", ["tenant_id", "actor", "channel", "last_message_at"],
    )
    op.execute("ALTER TABLE angela_conversations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE angela_conversations FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON angela_conversations
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)

    op.create_table(
        "angela_messages",
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("id", sa.Text, nullable=False),
        sa.Column("conversation_id", sa.Text, nullable=False),
        sa.Column("role", sa.Text, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("tools_used", psql.JSONB, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("tenant_id", "id"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "conversation_id"],
            ["angela_conversations.tenant_id", "angela_conversations.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_angela_messages_conversation",
        "angela_messages", ["tenant_id", "conversation_id", "created_at"],
    )
    op.execute("ALTER TABLE angela_messages ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE angela_messages FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON angela_messages
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_table("angela_messages")
    op.drop_table("angela_conversations")

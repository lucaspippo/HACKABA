"""
angela_transcripts.py · the RAW record of what was said to/by Ángela.

Twin of core/whatsapp_channel.py (same table shape), but for the internal
chat: `/api/angela` and `/api/angela/stream` in main.py, and — since voice
became conversational — also core/voz.py, when a voice note ends in a free
question instead of a floor report.

WHY THIS IS DIFFERENT from store.audit: the audit log (core/audit.py) already
records EVERY consultation with Ángela, deliberately LIGHTWEIGHT — actor,
tools used, latency, no text — to feed the activity feed without bloating it.
This module is the opposite on purpose: the full text, to look back at raw
for a dispute, an audit, or a "what exactly did it tell this person?". The
two coexist because they serve different questions.

HOW TURNS GET GROUPED INTO A CONVERSATION: there's no thread id the frontend
sends today — assistant-ui manages its threads in the browser's localStorage,
the backend never sees them. So grouping is by recency: consecutive turns
from the same actor/channel that arrive within
core/db/angela_conversations_repo.STALE_AFTER_MINUTES fall into the same
conversation; a longer pause opens a new one. It's a best-effort, not an
exact correlation with "which assistant-ui tab this was" — good enough for
the audit purpose (reconstructing a work session), and if the product needs
more precision later, it's solved by passing a real thread_id from the
frontend without touching this module.

Recording NEVER breaks the chat: every caller wraps it in try/except, same
as store.audit.record already does. A Postgres failure must not turn into
Ángela not answering.
"""
from __future__ import annotations


def record_turn(actor: str, user_message: str, response: str,
                 tools_used: list[str] | None = None, channel: str = "chat") -> dict:
    """One full turn: what the person said + what Ángela answered. Returns
    the conversation (so a caller that wants the id has it), but the return
    value is best-effort — nobody should depend on it to keep working."""
    from core.db import angela_conversations_repo as repo, tenant as _tenant
    tid = _tenant.current_tenant_id()
    conv = repo.get_or_create_open_conversation(tid, actor, channel=channel)
    if (user_message or "").strip():
        repo.add_message(tid, conv["id"], "user", user_message)
    if (response or "").strip():
        repo.add_message(tid, conv["id"], "assistant", response, tools_used=tools_used)
    return conv


def list_conversations(actor: str | None = None, channel: str | None = None,
                       limit: int = 100) -> list[dict]:
    from core.db import angela_conversations_repo as repo, tenant as _tenant
    tid = _tenant.current_tenant_id()
    return repo.list_conversations(tid, actor=actor, channel=channel, limit=limit)


def get_transcript(conversation_id: str) -> dict | None:
    """The conversation + its messages in order, raw — not summarized or
    translated: exactly what was said."""
    from core.db import angela_conversations_repo as repo, tenant as _tenant
    tid = _tenant.current_tenant_id()
    conv = repo.get_conversation(tid, conversation_id)
    if not conv:
        return None
    conv["messages"] = repo.list_messages(tid, conversation_id)
    return conv

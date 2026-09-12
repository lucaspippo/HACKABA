from __future__ import annotations

import datetime
import json
import secrets

from sqlalchemy import text

from core.db.engine import tenant_connection, to_local_iso

# A conversation "closes" itself after this much silence: the NEXT turn from
# the same actor/channel starts a fresh row instead of appending to a
# stale one. There is no explicit thread id coming from the client today
# (see the design note in core/angela_transcripts.py), so recency is the
# only signal available to tell "still the same chat" from "a new one,
# hours later".
STALE_AFTER_MINUTES = 180


def _ahora() -> datetime.datetime:
    return datetime.datetime.now().astimezone()


def _to_conversation(row) -> dict:
    return {
        "id": row["id"],
        "actor": row["actor"],
        "channel": row["channel"],
        "status": row["status"],
        "created_at": to_local_iso(row["created_at"]),
        "last_message_at": to_local_iso(row["last_message_at"]),
    }


def get_or_create_open_conversation(tenant_id: str, actor: str, channel: str = "chat",
                                     stale_after_minutes: int = STALE_AFTER_MINUTES) -> dict:
    cutoff = _ahora() - datetime.timedelta(minutes=stale_after_minutes)
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                "SELECT id, actor, channel, status, created_at, last_message_at "
                "FROM angela_conversations "
                "WHERE actor = :actor AND channel = :channel AND status = 'abierta' "
                "AND last_message_at >= :cutoff "
                "ORDER BY last_message_at DESC LIMIT 1"
            ),
            {"actor": actor, "channel": channel, "cutoff": cutoff},
        ).mappings().first()
        if row:
            return _to_conversation(row)
        cid = "ac" + secrets.token_hex(4)
        now = _ahora()
        conn.execute(
            text(
                "INSERT INTO angela_conversations "
                "(tenant_id, id, actor, channel, status, created_at, last_message_at) "
                "VALUES (:tid, :id, :actor, :channel, 'abierta', :now, :now)"
            ),
            {"tid": tenant_id, "id": cid, "actor": actor, "channel": channel, "now": now},
        )
        return {"id": cid, "actor": actor, "channel": channel, "status": "abierta",
                "created_at": to_local_iso(now), "last_message_at": to_local_iso(now)}


def get_conversation(tenant_id: str, conversation_id: str) -> dict | None:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                "SELECT id, actor, channel, status, created_at, last_message_at "
                "FROM angela_conversations WHERE id = :id"
            ),
            {"id": conversation_id},
        ).mappings().first()
    return _to_conversation(row) if row else None


def add_message(tenant_id: str, conversation_id: str, role: str, content: str,
                 tools_used: list[str] | None = None) -> None:
    mid = "am" + secrets.token_hex(4)
    now = _ahora()
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text(
                "INSERT INTO angela_messages "
                "(tenant_id, id, conversation_id, role, content, tools_used, created_at) "
                "VALUES (:tid, :id, :cid, :role, :content, :tools, :now)"
            ),
            {"tid": tenant_id, "id": mid, "cid": conversation_id, "role": role,
             "content": content,
             "tools": json.dumps(tools_used) if tools_used else None, "now": now},
        )
        conn.execute(
            text(
                "UPDATE angela_conversations SET last_message_at = :now "
                "WHERE tenant_id = :tid AND id = :cid"
            ),
            {"now": now, "tid": tenant_id, "cid": conversation_id},
        )


def list_messages(tenant_id: str, conversation_id: str, limit: int = 200) -> list[dict]:
    with tenant_connection(tenant_id) as conn:
        rows = conn.execute(
            text(
                "SELECT id, role, content, tools_used, created_at FROM angela_messages "
                "WHERE conversation_id = :cid ORDER BY created_at DESC LIMIT :lim"
            ),
            {"cid": conversation_id, "lim": limit},
        ).mappings().all()
    out = [
        {"id": r["id"], "role": r["role"], "content": r["content"],
         "tools_used": r["tools_used"] or [], "cuando": to_local_iso(r["created_at"])}
        for r in rows
    ]
    out.reverse()
    return out


def list_conversations(tenant_id: str, actor: str | None = None,
                        channel: str | None = None, limit: int = 100) -> list[dict]:
    clauses = []
    params: dict = {"lim": limit}
    if actor:
        clauses.append("actor = :actor")
        params["actor"] = actor
    if channel:
        clauses.append("channel = :channel")
        params["channel"] = channel
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with tenant_connection(tenant_id) as conn:
        rows = conn.execute(
            text(
                "SELECT id, actor, channel, status, created_at, last_message_at "
                f"FROM angela_conversations {where} "
                "ORDER BY last_message_at DESC LIMIT :lim"
            ),
            params,
        ).mappings().all()
    return [_to_conversation(r) for r in rows]

"""Feedback events on core/patrones.py findings (accepted / dismissed /
already knew), one row per event, keyed by (pattern_id, fingerprint) so a
recurring instance of the same underlying finding is recognized across
requests without needing its own table per pattern."""
from __future__ import annotations

import json

from sqlalchemy import text

from core.db.engine import tenant_connection, to_local_iso

ACTIONS = ("accepted", "dismissed", "already_knew")

_COLS = ("id, pattern_id, fingerprint, action, note, actor, snapshot, created_at")


def _to_feedback(row) -> dict:
    return {
        "id": row["id"],
        "pattern_id": row["pattern_id"],
        "fingerprint": row["fingerprint"],
        "action": row["action"],
        "note": row["note"],
        "actor": row["actor"],
        "snapshot": row["snapshot"],
        "created_at": to_local_iso(row["created_at"]),
    }


def create(tenant_id: str, *, pattern_id: str, fingerprint: str, action: str,
           actor: str, snapshot: dict, note: str | None = None) -> dict:
    if action not in ACTIONS:
        raise ValueError(f"unknown pattern feedback action: {action!r}")
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                "INSERT INTO pattern_feedback "
                "(tenant_id, pattern_id, fingerprint, action, note, actor, snapshot) "
                "VALUES (:tid, :pattern_id, :fingerprint, :action, :note, :actor, :snapshot) "
                f"RETURNING {_COLS}"
            ),
            {"tid": tenant_id, "pattern_id": pattern_id, "fingerprint": fingerprint,
             "action": action, "note": note, "actor": actor,
             "snapshot": json.dumps(snapshot)},
        ).mappings().one()
    return _to_feedback(row)


def latest_by_fingerprint(tenant_id: str) -> dict[str, dict]:
    """The most recent feedback row for every (pattern_id, fingerprint) pair
    this tenant has ever given feedback on — what core/patrones.py checks to
    decide whether an already-handled finding should stay hidden."""
    with tenant_connection(tenant_id) as conn:
        rows = conn.execute(text(
            "SELECT DISTINCT ON (pattern_id, fingerprint) "
            f"{_COLS} FROM pattern_feedback "
            "ORDER BY pattern_id, fingerprint, created_at DESC, id DESC"
        )).mappings().all()
    return {f"{r['pattern_id']}:{r['fingerprint']}": _to_feedback(r) for r in rows}


def history(tenant_id: str, limit: int = 50) -> list[dict]:
    """Every feedback event, most recent first — the tenant's own record of
    what Ángela has told them and what they said back."""
    with tenant_connection(tenant_id) as conn:
        rows = conn.execute(
            text(f"SELECT {_COLS} FROM pattern_feedback "
                 "ORDER BY created_at DESC, id DESC LIMIT :limit"),
            {"limit": limit},
        ).mappings().all()
    return [_to_feedback(r) for r in rows]

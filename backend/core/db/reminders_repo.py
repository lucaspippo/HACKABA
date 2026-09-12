from __future__ import annotations

import datetime
import json

from sqlalchemy import text

from core.db.engine import tenant_connection, to_local_iso

_COLS = ("id, text, recipient, created_by, condition, status, "
         "created_at, triggered_at, trigger_detail, channels")


def _to_reminder(row) -> dict:
    return {
        "id": row["id"],
        "texto": row["text"],
        "para": row["recipient"],
        "creado_por": row["created_by"],
        "condicion": row["condition"],
        "estado": row["status"],
        "creado": to_local_iso(row["created_at"]),
        "disparado_en": to_local_iso(row["triggered_at"]) if row["triggered_at"] else None,
        "detalle_disparo": row["trigger_detail"],
        "canales": row["channels"],
    }


def list_all(tenant_id: str) -> list[dict]:
    with tenant_connection(tenant_id) as conn:
        rows = conn.execute(text(f"SELECT {_COLS} FROM reminders")).mappings().all()
    return [_to_reminder(r) for r in rows]


def save_all(tenant_id: str, items: list[dict]) -> None:
    """Full replace — mirrors the old JSON file's whole-list rewrite, which
    is what every caller in core/recordatorios.py already expects."""
    with tenant_connection(tenant_id) as conn:
        conn.execute(text("DELETE FROM reminders WHERE tenant_id = :tid"), {"tid": tenant_id})
        for r in items:
            conn.execute(
                text(
                    "INSERT INTO reminders "
                    "(tenant_id, id, text, recipient, created_by, condition, status, "
                    "created_at, triggered_at, trigger_detail, channels) "
                    "VALUES (:tid, :id, :text, :recipient, :created_by, :condition, :status, "
                    ":created_at, :triggered_at, :trigger_detail, :channels)"
                ),
                {
                    "tid": tenant_id,
                    "id": r["id"],
                    "text": r["texto"],
                    "recipient": r["para"],
                    "created_by": r["creado_por"],
                    "condition": json.dumps(r["condicion"]) if r.get("condicion") is not None else None,
                    "status": r["estado"],
                    "created_at": datetime.datetime.fromisoformat(r["creado"]).astimezone(),
                    "triggered_at": (datetime.datetime.fromisoformat(r["disparado_en"]).astimezone()
                                     if r.get("disparado_en") else None),
                    "trigger_detail": r.get("detalle_disparo"),
                    "channels": json.dumps(r.get("canales") or []),
                },
            )

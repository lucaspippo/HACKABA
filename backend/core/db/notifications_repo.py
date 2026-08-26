from __future__ import annotations

import datetime

from sqlalchemy import text

from core.db.engine import tenant_connection, to_local_iso

_COLS = "id, recipient, title, body, type, ref, read, created_at"


def _to_evento(row) -> dict:
    return {
        "id": row["id"],
        "para": row["recipient"],
        "titulo": row["title"],
        "cuerpo": row["body"],
        "tipo": row["type"],
        "ref": row["ref"],
        "leida": row["read"],
        "fecha": to_local_iso(row["created_at"]),
    }


def create(tenant_id: str, evento: dict) -> None:
    """evento["fecha"] (a naive local-time string — core/notificaciones.py's
    _ahora()) is stored explicitly rather than left to a `now()` default, so
    the timestamp emitir() returns to its caller always matches what
    actually landed in the row. Attach the correct local offset before
    sending it to a TIMESTAMP(timezone=True) column — same fix as
    audit_repo.seed_if_empty()/purchase_orders_repo.create()."""
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text(
                "INSERT INTO notifications "
                "(tenant_id, id, recipient, title, body, type, ref, read, created_at) "
                "VALUES (:tid, :id, :recipient, :title, :body, :type, :ref, :read, :created_at)"
            ),
            {
                "tid": tenant_id,
                "id": evento["id"],
                "recipient": evento["para"],
                "title": evento["titulo"],
                "body": evento.get("cuerpo"),
                "type": evento.get("tipo", "general"),
                "ref": evento.get("ref"),
                "read": evento.get("leida", False),
                "created_at": datetime.datetime.fromisoformat(evento["fecha"]).astimezone(),
            },
        )


def list_for(tenant_id: str, para: str, solo_no_leidas: bool = False) -> list[dict]:
    query = f"SELECT {_COLS} FROM notifications WHERE recipient = :para"
    if solo_no_leidas:
        query += " AND read = false"
    query += " ORDER BY created_at DESC"
    with tenant_connection(tenant_id) as conn:
        rows = conn.execute(text(query), {"para": para}).mappings().all()
    return [_to_evento(r) for r in rows]


def mark_read(tenant_id: str, notification_id: str) -> dict:
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text("UPDATE notifications SET read = true WHERE id = :id"),
            {"id": notification_id},
        )
        row = conn.execute(
            text(f"SELECT {_COLS} FROM notifications WHERE id = :id"),
            {"id": notification_id},
        ).mappings().first()
    if row is None:
        raise KeyError("notificación inexistente")
    return _to_evento(row)


def total_emitidas(tenant_id: str, hasta_iso: str | None = None) -> int:
    """Counts all notifications, or only those up to hasta_iso (a LOCAL date,
    e.g. the demo's frozen "today"). The cutoff is applied in Python against
    the local-converted timestamp, not `created_at::date` in SQL — Postgres
    has no portable notion of "the app host's timezone" to compare against,
    and `created_at` is UTC, so a SQL-side date cast would reintroduce the
    same UTC-vs-local mismatch to_local_iso exists to avoid."""
    with tenant_connection(tenant_id) as conn:
        if hasta_iso is None:
            return conn.execute(text("SELECT count(*) FROM notifications")).scalar_one()
        rows = conn.execute(text("SELECT created_at FROM notifications")).scalars().all()
    return sum(1 for created_at in rows if to_local_iso(created_at)[:10] <= hasta_iso)

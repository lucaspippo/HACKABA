from __future__ import annotations

import datetime

from sqlalchemy import text

from core.db.engine import tenant_connection, to_local_iso


def record(tenant_id: str, *, actor: str, action: str, before=None, after=None) -> dict:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                "INSERT INTO audit_events (tenant_id, actor, action, before, after) "
                "VALUES (:tid, :actor, :action, :before, :after) "
                "RETURNING id, actor, action, before, after, created_at"
            ),
            {
                "tid": tenant_id,
                "actor": actor,
                "action": action,
                "before": _to_json_param(before),
                "after": _to_json_param(after),
            },
        ).mappings().one()
    return _to_evento(row)


def list_events(tenant_id: str) -> list[dict]:
    with tenant_connection(tenant_id) as conn:
        rows = conn.execute(
            text("SELECT id, actor, action, before, after, created_at "
                 "FROM audit_events ORDER BY id")
        ).mappings().all()
    return [_to_evento(r) for r in rows]


def seed_if_empty(tenant_id: str, eventos: list[dict]) -> None:
    """Bulk-loads a tenant's real, already-generated audit history (e.g. the
    demo tenant's data-demo/audit.json, produced by generar.py) exactly once
    — the same fallback-vs-real-dataset pattern used for cuentas. `eventos`
    dicts use the same Spanish-keyed shape record()/list_events() return."""
    with tenant_connection(tenant_id) as conn:
        count = conn.execute(text("SELECT count(*) FROM audit_events")).scalar_one()
        if count:
            return
        for ev in eventos:
            conn.execute(
                text(
                    "INSERT INTO audit_events (tenant_id, actor, action, before, after, created_at) "
                    "VALUES (:tid, :actor, :action, :before, :after, :created_at)"
                ),
                {
                    "tid": tenant_id,
                    "actor": ev["actor"],
                    "action": ev["accion"],
                    "before": _to_json_param(ev.get("antes")),
                    "after": _to_json_param(ev.get("despues")),
                    # ev["cuando"] is a naive local-time string (the seed file's
                    # own format) — attach the correct local offset explicitly
                    # so Postgres stores the right instant regardless of session
                    # timezone, instead of silently mis-parsing it as UTC.
                    "created_at": datetime.datetime.fromisoformat(ev["cuando"]).astimezone(),
                },
            )


def _to_json_param(value):
    import json

    return json.dumps(value) if value is not None else None


def _to_evento(row) -> dict:
    return {
        "id": row["id"],
        "actor": row["actor"],
        "accion": row["action"],
        "antes": row["before"],
        "despues": row["after"],
        "cuando": to_local_iso(row["created_at"]),
    }

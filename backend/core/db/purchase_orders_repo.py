from __future__ import annotations

import datetime
import json

from sqlalchemy import text

from core.db.engine import tenant_connection, to_local_iso

_COLS = ("number", "date", "supplier", "status", "origin", "reason",
         "prepared_by", "approved_by", "prepared_at", "items", "location")


def _to_orden(row) -> dict:
    return {
        "numero": row["number"],
        "fecha": row["date"].isoformat(),
        "proveedor": row["supplier"],
        "estado": row["status"],
        "origen": row["origin"],
        "motivo": row["reason"],
        "preparada_por": row["prepared_by"],
        "aprobada_por": row["approved_by"],
        "preparada": to_local_iso(row["prepared_at"]),
        "items": row["items"],
        "ubicacion_entrega": row["location"],
    }


def list_orders(tenant_id: str) -> list[dict]:
    with tenant_connection(tenant_id) as conn:
        rows = conn.execute(
            text(f"SELECT {', '.join(_COLS)} FROM purchase_orders ORDER BY prepared_at DESC")
        ).mappings().all()
    return [_to_orden(r) for r in rows]


def find_draft(tenant_id: str, *, codigo: int | None, origen: str) -> dict | None:
    """The one existing draft order for (codigo, origen), if any — preparar()
    in core/ordenes.py uses this to stay idempotent.

    Faithful port of the pre-existing JSON-file logic: `o.get("codigo")` was
    always compared against the stored order *dict's own top-level key* —
    which `preparar()` never actually sets (codigo only ever lands inside
    `items[0]["codigo"]`) — so the old check was effectively always `None ==
    codigo`, matching only when the caller passes codigo=None. That's almost
    certainly a pre-existing bug (the docstring promises idempotency by
    (codigo, origen)), but it's not this migration's job to change behavior,
    only where it's stored — preserved exactly, including the bug."""
    if codigo is not None:
        return None
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(f"SELECT {', '.join(_COLS)} FROM purchase_orders "
                 "WHERE status = 'borrador' AND origin = :origen LIMIT 1"),
            {"origen": origen},
        ).mappings().first()
    return _to_orden(row) if row else None


def create(tenant_id: str, orden: dict) -> None:
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text(
                "INSERT INTO purchase_orders "
                "(tenant_id, number, date, supplier, status, origin, reason, "
                "prepared_by, approved_by, prepared_at, items, location) "
                "VALUES (:tid, :number, :date, :supplier, :status, :origin, :reason, "
                ":prepared_by, :approved_by, :prepared_at, :items, :location)"
            ),
            {
                "tid": tenant_id,
                "number": orden["numero"],
                "date": orden["fecha"],
                "supplier": orden["proveedor"],
                "status": orden["estado"],
                "origin": orden["origen"],
                "reason": orden.get("motivo"),
                "prepared_by": orden["preparada_por"],
                "approved_by": orden["aprobada_por"],
                # orden["preparada"] is a naive local-time string (computed by
                # datetime.datetime.now().isoformat() in core/ordenes.py) —
                # attach the correct local offset so Postgres stores the right
                # instant regardless of session timezone, same fix as
                # audit_repo.seed_if_empty().
                "prepared_at": datetime.datetime.fromisoformat(orden["preparada"]).astimezone(),
                "items": json.dumps(orden["items"]),
                "location": orden.get("ubicacion_entrega"),
            },
        )


def count(tenant_id: str) -> int:
    with tenant_connection(tenant_id) as conn:
        return conn.execute(text("SELECT count(*) FROM purchase_orders")).scalar_one()


def update_status(tenant_id: str, numero: str, estado: str) -> dict | None:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                f"UPDATE purchase_orders SET status = :estado "
                f"WHERE number = :numero RETURNING {', '.join(_COLS)}"
            ),
            {"estado": estado, "numero": numero},
        ).mappings().first()
    return _to_orden(row) if row else None

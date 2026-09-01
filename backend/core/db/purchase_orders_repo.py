from __future__ import annotations

import datetime
import json

from sqlalchemy import text

from core.db.engine import tenant_connection, to_local_iso

_COLS = ("number", "date", "supplier", "status", "origin", "reason",
         "prepared_by", "approved_by", "prepared_at", "items", "location",
         "source", "source_id", "source_status")


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
        "source": row["source"],
        "source_id": row["source_id"],
        "source_status": row["source_status"],
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

    `codigo` lives inside the JSONB `items` payload, not in a column, so the
    match happens in Python over the drafts sharing this origin. That set is
    tiny, and it avoids both a schema migration and JSON-in-SQL differences
    between the SQLite and Postgres backends.
    """
    with tenant_connection(tenant_id) as conn:
        rows = conn.execute(
            text(f"SELECT {', '.join(_COLS)} FROM purchase_orders "
                 "WHERE status = 'borrador' AND origin = :origen"),
            {"origen": origen},
        ).mappings().all()
    for row in rows:
        orden = _to_orden(row)
        items = orden.get("items") or []
        if items and items[0].get("codigo") == codigo:
            return orden
    return None


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


def find_by_number(tenant_id: str, number: str) -> dict | None:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(f"SELECT {', '.join(_COLS)} FROM purchase_orders WHERE number = :number"),
            {"number": number},
        ).mappings().first()
    return _to_orden(row) if row else None


def upsert_from_odoo(tenant_id: str, orden: dict) -> None:
    """Create-or-update a purchase order by its number — Odoo ingestion
    (core/odoo_ingest.py) uses this to stay idempotent across re-syncs.
    (tenant_id, number) is already this table's primary key (0009), and
    Odoo's own PO numbers (e.g. "P00006") never collide with
    PolPilot-originated ones (e.g. "OC-2026-0901"), so no extra index or
    lookup by source_id is needed — ON CONFLICT on number is enough."""
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text(
                "INSERT INTO purchase_orders "
                "(tenant_id, number, date, supplier, status, origin, reason, "
                "prepared_by, approved_by, prepared_at, items, location, "
                "source, source_id, source_status) "
                "VALUES (:tid, :number, :date, :supplier, :status, :origin, :reason, "
                ":prepared_by, :approved_by, :prepared_at, :items, :location, "
                ":source, :source_id, :source_status) "
                "ON CONFLICT (tenant_id, number) DO UPDATE SET "
                "status = EXCLUDED.status, source_status = EXCLUDED.source_status, "
                "supplier = EXCLUDED.supplier, items = EXCLUDED.items, date = EXCLUDED.date"
            ),
            {
                "tid": tenant_id,
                "number": orden["numero"],
                "date": orden["fecha"],
                "supplier": orden["proveedor"],
                "status": orden["estado"],
                "origin": "odoo",
                "reason": None,
                "prepared_by": "Odoo",
                "approved_by": "Odoo",
                "prepared_at": datetime.datetime.now().astimezone(),
                "items": json.dumps(orden["items"]),
                "location": None,
                "source": "odoo",
                "source_id": orden["source_id"],
                "source_status": orden["source_status"],
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

from __future__ import annotations

import datetime
import json

from sqlalchemy import text

from core.db.engine import tenant_connection, to_local_iso

_COLS = ("id, type, actor, created_at, report_date, status, data, "
         "attachment, resolved_by, resolved_at, resolved_note, "
         "recipient, seen_at, seen_by")


def _to_reporte(row) -> dict:
    r = {
        "id": row["id"],
        "tipo": row["type"],
        "actor": row["actor"],
        "cuando": to_local_iso(row["created_at"]),
        "fecha": row["report_date"].isoformat(),
        "estado": row["status"],
        "datos": row["data"],
    }
    if row["attachment"]:
        r["adjunto"] = row["attachment"]
    if row["resolved_by"]:
        r["resuelto_por"] = row["resolved_by"]
    if row["resolved_at"]:
        r["resuelto"] = to_local_iso(row["resolved_at"])
    if row["resolved_note"]:
        r["nota_dueno"] = row["resolved_note"]
    if row["recipient"]:
        r["destinatario"] = row["recipient"]
    if row["seen_at"]:
        r["visto"] = to_local_iso(row["seen_at"])
        r["visto_por"] = row["seen_by"]
    return r


def list_all(tenant_id: str) -> list[dict]:
    with tenant_connection(tenant_id) as conn:
        rows = conn.execute(
            text(f"SELECT {_COLS} FROM floor_reports ORDER BY created_at DESC")
        ).mappings().all()
    return [_to_reporte(r) for r in rows]


def get(tenant_id: str, rid: str) -> dict | None:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(f"SELECT {_COLS} FROM floor_reports WHERE id = :id"),
            {"id": rid},
        ).mappings().first()
    return _to_reporte(row) if row else None


def create(tenant_id: str, reporte: dict) -> None:
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text(
                "INSERT INTO floor_reports "
                "(tenant_id, id, type, actor, created_at, report_date, status, data, "
                "attachment, recipient) "
                "VALUES (:tid, :id, :type, :actor, :created_at, :report_date, :status, "
                ":data, :attachment, :recipient)"
            ),
            {
                "tid": tenant_id,
                "id": reporte["id"],
                "type": reporte["tipo"],
                "actor": reporte["actor"],
                "created_at": datetime.datetime.fromisoformat(reporte["cuando"]).astimezone(),
                "report_date": reporte["fecha"],
                "status": reporte["estado"],
                "data": json.dumps(reporte["datos"]),
                "attachment": reporte.get("adjunto"),
                "recipient": reporte.get("destinatario"),
            },
        )


def mark_seen(tenant_id: str, rid: str, actor: str, visto_iso: str) -> dict | None:
    """El acuse. Idempotente a propósito: el primero que lo abre es el que
    queda, y abrirlo de nuevo no reescribe la hora — el que reportó ya vio
    "visto a las 9:31" y ese dato no se mueve bajo sus pies."""
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text(
                "UPDATE floor_reports SET seen_at = :seen_at, seen_by = :actor, "
                "status = CASE WHEN status = 'nuevo' THEN 'visto' ELSE status END "
                "WHERE id = :id AND seen_at IS NULL"
            ),
            {
                "actor": actor,
                "seen_at": datetime.datetime.fromisoformat(visto_iso).astimezone(),
                "id": rid,
            },
        )
        row = conn.execute(
            text(f"SELECT {_COLS} FROM floor_reports WHERE id = :id"),
            {"id": rid},
        ).mappings().first()
    return _to_reporte(row) if row else None


def resolve(tenant_id: str, rid: str, actor: str, nota: str,
            resuelto_iso: str) -> dict | None:
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text(
                "UPDATE floor_reports SET status = 'resuelto', resolved_by = :actor, "
                "resolved_at = :resolved_at, resolved_note = :nota WHERE id = :id"
            ),
            {
                "actor": actor,
                "resolved_at": datetime.datetime.fromisoformat(resuelto_iso).astimezone(),
                "nota": nota or None,
                "id": rid,
            },
        )
        row = conn.execute(
            text(f"SELECT {_COLS} FROM floor_reports WHERE id = :id"),
            {"id": rid},
        ).mappings().first()
    return _to_reporte(row) if row else None

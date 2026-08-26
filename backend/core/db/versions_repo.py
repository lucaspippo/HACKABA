from __future__ import annotations

import json

from sqlalchemy import text

from core.db.engine import tenant_connection, to_local_iso


def save(tenant_id: str, data: dict, *, reason: str, author: str = "sistema") -> dict:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                "INSERT INTO data_versions (tenant_id, reason, author, data) "
                "VALUES (:tid, :reason, :author, :data) "
                "RETURNING id, reason, author, created_at"
            ),
            {"tid": tenant_id, "reason": reason, "author": author, "data": json.dumps(data)},
        ).mappings().one()
    return {
        "id": row["id"],
        "motivo": row["reason"],
        "autor": row["author"],
        "creado": to_local_iso(row["created_at"]),
    }


def list_versions(tenant_id: str) -> list[dict]:
    with tenant_connection(tenant_id) as conn:
        rows = conn.execute(
            text("SELECT id, reason, author, created_at FROM data_versions ORDER BY id")
        ).mappings().all()
    return [
        {
            "id": r["id"],
            "motivo": r["reason"],
            "autor": r["author"],
            "creado": to_local_iso(r["created_at"]),
        }
        for r in rows
    ]


def restore(tenant_id: str, version_id: int) -> dict:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text("SELECT data FROM data_versions WHERE id = :id"),
            {"id": version_id},
        ).scalar_one_or_none()
    if row is None:
        raise KeyError(f"Versión inexistente: {version_id}")
    return row

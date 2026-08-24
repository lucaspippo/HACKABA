from __future__ import annotations

import json

from sqlalchemy import text

from core.db.engine import tenant_connection


def get_state(tenant_id: str) -> dict | None:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text("SELECT data FROM caja_state WHERE tenant_id = :tid"),
            {"tid": tenant_id},
        ).scalar_one_or_none()
    return row


def save_state(tenant_id: str, data: dict) -> None:
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text(
                "INSERT INTO caja_state (tenant_id, data, updated_at) "
                "VALUES (:tid, :data, now()) "
                "ON CONFLICT (tenant_id) DO UPDATE SET "
                "data = EXCLUDED.data, updated_at = now()"
            ),
            {"tid": tenant_id, "data": json.dumps(data)},
        )

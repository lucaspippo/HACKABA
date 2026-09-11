from __future__ import annotations

import json

from sqlalchemy import text

from core.db.engine import tenant_connection

# Shared read/write for the one-JSONB-row-per-tenant tables (autonomia,
# mostrador, traslados, inventory_baseline, sample_extractions, ...). `table`
# is always a hardcoded literal from the caller's own code, never user
# input — safe to interpolate into the query text.


def get_blob(table: str, tenant_id: str):
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(f"SELECT data FROM {table} WHERE tenant_id = :tid"),
            {"tid": tenant_id},
        ).scalar_one_or_none()
    return row


def save_blob(table: str, tenant_id: str, data) -> None:
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text(
                f"INSERT INTO {table} (tenant_id, data, updated_at) "
                f"VALUES (:tid, :data, now()) "
                f"ON CONFLICT (tenant_id) DO UPDATE SET "
                f"data = EXCLUDED.data, updated_at = now()"
            ),
            {"tid": tenant_id, "data": json.dumps(data)},
        )

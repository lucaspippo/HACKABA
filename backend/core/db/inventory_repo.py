from __future__ import annotations

import json

from sqlalchemy import text

from core.db.engine import tenant_connection


def get_articles(tenant_id: str) -> list[dict] | None:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text("SELECT articulos FROM inventory_working WHERE tenant_id = :tid"),
            {"tid": tenant_id},
        ).scalar_one_or_none()
    return row


def save_articles(tenant_id: str, articulos: list[dict]) -> None:
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text(
                "INSERT INTO inventory_working (tenant_id, articulos, updated_at) "
                "VALUES (:tid, :articulos, now()) "
                "ON CONFLICT (tenant_id) DO UPDATE SET "
                "articulos = EXCLUDED.articulos, updated_at = now()"
            ),
            {"tid": tenant_id, "articulos": json.dumps(articulos)},
        )

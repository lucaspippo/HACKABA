from __future__ import annotations

from sqlalchemy import text

from core.db.engine import tenant_connection


def get(tenant_id: str, username: str) -> str | None:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text("SELECT password_hash FROM auth_credentials WHERE tenant_id = :tid AND username = :u"),
            {"tid": tenant_id, "u": username},
        ).scalar_one_or_none()
    return row


def set(tenant_id: str, username: str, password_hash: str) -> None:
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text(
                "INSERT INTO auth_credentials (tenant_id, username, password_hash) "
                "VALUES (:tid, :u, :h) "
                "ON CONFLICT (tenant_id, username) "
                "DO UPDATE SET password_hash = EXCLUDED.password_hash, updated_at = now()"
            ),
            {"tid": tenant_id, "u": username, "h": password_hash},
        )

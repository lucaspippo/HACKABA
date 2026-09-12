from __future__ import annotations

import os

from cryptography.fernet import Fernet
from sqlalchemy import text

from core.db.engine import tenant_connection


def _fernet() -> Fernet:
    key = os.environ.get("ODOO_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError(
            "ODOO_ENCRYPTION_KEY is not set — required to store/read Odoo API keys. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode("utf-8"))


def get(tenant_id: str) -> dict | None:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                "SELECT url, database, username, api_key_encrypted, updated_at "
                "FROM odoo_connections WHERE tenant_id = :tid"
            ),
            {"tid": tenant_id},
        ).mappings().first()
    if not row:
        return None
    return {
        "url": row["url"],
        "database": row["database"],
        "username": row["username"],
        "api_key": _fernet().decrypt(row["api_key_encrypted"].encode("utf-8")).decode("utf-8"),
        "updated_at": row["updated_at"].isoformat(),
    }


def save(tenant_id: str, url: str, database: str, username: str, api_key: str) -> None:
    encrypted = _fernet().encrypt(api_key.encode("utf-8")).decode("utf-8")
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text(
                "INSERT INTO odoo_connections (tenant_id, url, database, username, api_key_encrypted) "
                "VALUES (:tid, :url, :db, :user, :key) "
                "ON CONFLICT (tenant_id) DO UPDATE SET "
                "url = EXCLUDED.url, database = EXCLUDED.database, username = EXCLUDED.username, "
                "api_key_encrypted = EXCLUDED.api_key_encrypted, updated_at = now()"
            ),
            {"tid": tenant_id, "url": url, "db": database, "user": username, "key": encrypted},
        )


def delete(tenant_id: str) -> None:
    with tenant_connection(tenant_id) as conn:
        conn.execute(text("DELETE FROM odoo_connections WHERE tenant_id = :tid"), {"tid": tenant_id})

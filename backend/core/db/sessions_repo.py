from __future__ import annotations

from sqlalchemy import text

from core.db.engine import tenant_connection


def create(tenant_id: str, username: str, token: str, ttl_seconds: float) -> None:
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text(
                "INSERT INTO sessions (token, tenant_id, username, expires_at) "
                "VALUES (:token, :tid, :u, now() + make_interval(secs => :ttl))"
            ),
            {"token": token, "tid": tenant_id, "u": username, "ttl": ttl_seconds},
        )


def get(tenant_id: str, token: str) -> dict | None:
    """Expiry is checked entirely in Postgres (`expires_at > now()`), never
    against Python's local clock — the app host and the database can and do
    drift (observed ~9s drift between this dev machine and its Docker/WSL2
    Postgres container), so a Python-side time.time() comparison would be
    unreliable by design, not just on this machine."""
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text("SELECT username, expires_at FROM sessions WHERE token = :token AND expires_at > now()"),
            {"token": token},
        ).mappings().first()
        if row:
            return {"username": row["username"], "expires_at": row["expires_at"]}
        conn.execute(
            text("DELETE FROM sessions WHERE token = :token AND expires_at <= now()"),
            {"token": token},
        )
        return None


def purge_expired(tenant_id: str) -> None:
    with tenant_connection(tenant_id) as conn:
        conn.execute(text("DELETE FROM sessions WHERE expires_at <= now()"))

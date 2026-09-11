"""Resolves the running process's tenant slug (core.paths.TENANT — set once
at process start, same deployment topology as today) to its database row id.
Cached for the life of the process: one process still serves one tenant.

Uses the admin engine: looking up a row in `tenants` itself is not a
tenant-scoped query — RLS doesn't apply to that table at all — so this is
correctly outside the tenant_connection() boundary."""
from __future__ import annotations

from functools import lru_cache

from sqlalchemy import text

from core import paths
from core.db.engine import get_admin_engine


@lru_cache(maxsize=1)
def current_tenant_id() -> str:
    engine = get_admin_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id FROM tenants WHERE slug = :slug"), {"slug": paths.TENANT}
        ).mappings().first()
    if not row:
        raise RuntimeError(
            f"tenant '{paths.TENANT}' has no row in the tenants table — seed it first"
        )
    return str(row["id"])

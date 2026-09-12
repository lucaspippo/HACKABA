"""Resets a tenant's Postgres business data back to "freshly seeded" —
the DB-backed half of the admin reset endpoint (see main.py's
admin_reset_demo). Deliberately never touches auth_credentials/sessions:
resetting those would log every visitor out and rotate their already-known
password.
"""
from __future__ import annotations

from sqlalchemy import text

from core.db.engine import tenant_connection
from core.db.tenant_tables import BUSINESS_DATA_TABLES


def truncate_tables(tenant_id: str, tablas) -> None:
    """Empties the given tables for one tenant, in the order given — a caller
    with a foreign key between two of them lists the child first. One
    primitive, so a partial reset (see core/db/seed_state.sembrar) and the
    full one below cannot drift apart."""
    with tenant_connection(tenant_id) as conn:
        for tabla in tablas:
            conn.execute(text(f"DELETE FROM {tabla} WHERE tenant_id = :tid"),
                         {"tid": tenant_id})


def truncate_business_data(tenant_id: str) -> None:
    """Deletes every row of every migrated business-data table for this
    tenant. Callers are responsible for re-seeding afterward (see
    data-demo/seed_db.py's seed_domains(), which each domain module's own
    first-read already knows how to do from its real on-disk dataset)."""
    truncate_tables(tenant_id, BUSINESS_DATA_TABLES)

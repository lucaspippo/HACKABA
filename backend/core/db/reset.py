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


def truncate_business_data(tenant_id: str) -> None:
    """Deletes every row of every migrated business-data table for this
    tenant. Callers are responsible for re-seeding afterward (see
    data-demo/seed_db.py's seed_domains(), which each domain module's own
    first-read already knows how to do from its real on-disk dataset)."""
    with tenant_connection(tenant_id) as conn:
        for tabla in BUSINESS_DATA_TABLES:
            conn.execute(text(f"DELETE FROM {tabla} WHERE tenant_id = :tid"),
                         {"tid": tenant_id})

"""core/db/reset.py — truncating a tenant's business data must clear every
table in BUSINESS_DATA_TABLES and must never touch AUTH_TABLES (a reset
that logged every visitor out would be a much worse bug than the one it's
fixing — see main.py's admin_reset_demo)."""
from __future__ import annotations

from sqlalchemy import text

from core.db import blob_repo, credentials_repo, reset
from core.db.engine import tenant_connection
from core.db.tenant_tables import AUTH_TABLES, BUSINESS_DATA_TABLES


def _count(tenant_id: str, table: str) -> int:
    with tenant_connection(tenant_id) as conn:
        return conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()


def test_truncate_clears_every_business_table_but_not_auth(db_tenant):
    # one representative row per blob-shaped table, plus real credentials
    blob_repo.save_blob("organization_config", db_tenant, {"nombre": "x"})
    blob_repo.save_blob("data_sections", db_tenant, {"venta": {"filas": [1]}})
    credentials_repo.set(db_tenant, "someone", "hashed-not-a-real-password")

    assert _count(db_tenant, "organization_config") == 1
    assert _count(db_tenant, "data_sections") == 1
    assert _count(db_tenant, "auth_credentials") == 1

    reset.truncate_business_data(db_tenant)

    for table in BUSINESS_DATA_TABLES:
        assert _count(db_tenant, table) == 0, f"{table} was not cleared"
    assert _count(db_tenant, "auth_credentials") == 1, \
        "auth_credentials should not be touched by a business-data reset"
    assert "sessions" in AUTH_TABLES  # sanity: the table this reset must never touch

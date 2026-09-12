from sqlalchemy import text

from core.db import odoo_connections_repo
from core.db.engine import tenant_connection


def test_save_then_get_roundtrip(db_tenant):
    odoo_connections_repo.save(db_tenant, "https://mi-empresa.odoo.com", "mi_empresa",
                                "admin", "s3cr3t-api-key")
    c = odoo_connections_repo.get(db_tenant)
    assert c["url"] == "https://mi-empresa.odoo.com"
    assert c["database"] == "mi_empresa"
    assert c["username"] == "admin"
    assert c["api_key"] == "s3cr3t-api-key"


def test_get_missing_returns_none(db_tenant):
    assert odoo_connections_repo.get(db_tenant) is None


def test_api_key_stored_encrypted_at_rest(db_tenant):
    odoo_connections_repo.save(db_tenant, "https://x.odoo.com", "x", "admin", "s3cr3t-api-key")
    with tenant_connection(db_tenant) as conn:
        raw = conn.execute(
            text("SELECT api_key_encrypted FROM odoo_connections WHERE tenant_id = :tid"),
            {"tid": db_tenant},
        ).scalar_one()
    assert "s3cr3t-api-key" not in raw


def test_save_is_idempotent_upsert(db_tenant):
    odoo_connections_repo.save(db_tenant, "https://a.odoo.com", "a", "admin", "key-1")
    odoo_connections_repo.save(db_tenant, "https://a.odoo.com", "a", "admin", "key-2")
    assert odoo_connections_repo.get(db_tenant)["api_key"] == "key-2"


def test_delete_removes_connection(db_tenant):
    odoo_connections_repo.save(db_tenant, "https://a.odoo.com", "a", "admin", "key")
    odoo_connections_repo.delete(db_tenant)
    assert odoo_connections_repo.get(db_tenant) is None

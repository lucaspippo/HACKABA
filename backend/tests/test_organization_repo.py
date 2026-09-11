from core.db import organization_repo


def test_get_returns_none_when_no_row(db_tenant):
    assert organization_repo.get_config(db_tenant) is None


def test_save_then_get_roundtrip(db_tenant):
    data = {"id": "test", "nombre": "Test Org", "config": {"margen_minimo": 20}}
    organization_repo.save_config(db_tenant, data)
    assert organization_repo.get_config(db_tenant) == data


def test_save_is_full_replace_upsert(db_tenant):
    organization_repo.save_config(db_tenant, {"nombre": "A"})
    organization_repo.save_config(db_tenant, {"nombre": "B"})
    assert organization_repo.get_config(db_tenant) == {"nombre": "B"}

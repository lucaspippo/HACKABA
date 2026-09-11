import pytest

from core.db import versions_repo


def test_save_then_list(db_tenant):
    m1 = versions_repo.save(db_tenant, {"x": 1}, reason="primera", author="a")
    m2 = versions_repo.save(db_tenant, {"x": 2}, reason="segunda", author="a")
    assert m2["id"] > m1["id"]
    assert m2["motivo"] == "segunda"
    versiones = versions_repo.list_versions(db_tenant)
    assert len(versiones) == 2


def test_restore_devuelve_snapshot_exacto(db_tenant):
    m1 = versions_repo.save(db_tenant, {"x": 1}, reason="a", author="a")
    m2 = versions_repo.save(db_tenant, {"x": 2}, reason="b", author="a")
    assert versions_repo.restore(db_tenant, m1["id"]) == {"x": 1}
    assert versions_repo.restore(db_tenant, m2["id"]) == {"x": 2}


def test_restore_inexistente_levanta(db_tenant):
    with pytest.raises(KeyError):
        versions_repo.restore(db_tenant, 999_999_999)

import pytest

from core.versioning import VersionStore


def _vs(db_tenant, monkeypatch):
    monkeypatch.setattr("core.db.tenant.current_tenant_id", lambda: db_tenant)
    return VersionStore()


def test_save_asigna_ids_incrementales(db_tenant, monkeypatch):
    vs = _vs(db_tenant, monkeypatch)
    m1 = vs.save({"x": 1}, motivo="primera")
    m2 = vs.save({"x": 2}, motivo="segunda")
    assert m2["id"] > m1["id"]
    assert m2["motivo"] == "segunda"


def test_list_devuelve_todas(db_tenant, monkeypatch):
    vs = _vs(db_tenant, monkeypatch)
    vs.save({"x": 1}, motivo="a")
    vs.save({"x": 2}, motivo="b")
    assert len(vs.list()) == 2


def test_restore_devuelve_snapshot_exacto(db_tenant, monkeypatch):
    vs = _vs(db_tenant, monkeypatch)
    m1 = vs.save({"x": 1}, motivo="a")
    m2 = vs.save({"x": 2}, motivo="b")
    assert vs.restore(m1["id"]) == {"x": 1}
    assert vs.restore(m2["id"]) == {"x": 2}


def test_restore_inexistente_levanta(db_tenant, monkeypatch):
    vs = _vs(db_tenant, monkeypatch)
    with pytest.raises(KeyError):
        vs.restore(999_999_999)


def test_persiste_entre_instancias(db_tenant, monkeypatch):
    monkeypatch.setattr("core.db.tenant.current_tenant_id", lambda: db_tenant)
    m = VersionStore().save({"x": 1}, motivo="a")
    otra = VersionStore()
    assert len(otra.list()) == 1
    assert otra.restore(m["id"]) == {"x": 1}

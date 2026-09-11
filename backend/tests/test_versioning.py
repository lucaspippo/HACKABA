import pytest

from core.versioning import VersionStore


def test_save_asigna_ids_incrementales(tmp_path):
    vs = VersionStore(str(tmp_path))
    m1 = vs.save({"x": 1}, motivo="primera")
    m2 = vs.save({"x": 2}, motivo="segunda")
    assert m1["id"] == 1
    assert m2["id"] == 2
    assert m2["motivo"] == "segunda"


def test_list_devuelve_todas(tmp_path):
    vs = VersionStore(str(tmp_path))
    vs.save({"x": 1}, motivo="a")
    vs.save({"x": 2}, motivo="b")
    assert len(vs.list()) == 2


def test_restore_devuelve_snapshot_exacto(tmp_path):
    vs = VersionStore(str(tmp_path))
    vs.save({"x": 1}, motivo="a")
    vs.save({"x": 2}, motivo="b")
    assert vs.restore(1) == {"x": 1}
    assert vs.restore(2) == {"x": 2}


def test_restore_inexistente_levanta(tmp_path):
    vs = VersionStore(str(tmp_path))
    with pytest.raises(KeyError):
        vs.restore(99)


def test_persiste_entre_instancias(tmp_path):
    VersionStore(str(tmp_path)).save({"x": 1}, motivo="a")
    otra = VersionStore(str(tmp_path))
    assert len(otra.list()) == 1
    assert otra.restore(1) == {"x": 1}

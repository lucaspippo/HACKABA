from core.db import caja_repo


def test_get_returns_none_when_no_row(db_tenant):
    assert caja_repo.get_state(db_tenant) is None


def test_save_then_get_roundtrip(db_tenant):
    estado = {"abierta": True, "saldo_inicial": 1000, "movimientos": []}
    caja_repo.save_state(db_tenant, estado)
    assert caja_repo.get_state(db_tenant) == estado


def test_save_is_full_replace_upsert(db_tenant):
    caja_repo.save_state(db_tenant, {"abierta": True})
    caja_repo.save_state(db_tenant, {"abierta": False})
    assert caja_repo.get_state(db_tenant) == {"abierta": False}

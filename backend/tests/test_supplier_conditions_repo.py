from core.db import supplier_conditions_repo


def test_get_returns_none_when_no_row(db_tenant):
    assert supplier_conditions_repo.get_data(db_tenant) is None


def test_save_then_get_roundtrip(db_tenant):
    data = {"proveedores": [{"proveedor": "Molinos", "dias_reposicion": 4}], "ofertas": []}
    supplier_conditions_repo.save_data(db_tenant, data)
    assert supplier_conditions_repo.get_data(db_tenant) == data

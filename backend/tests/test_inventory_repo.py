from core.db import inventory_repo


def test_get_returns_none_when_no_row(db_tenant):
    assert inventory_repo.get_articles(db_tenant) is None


def test_save_then_get_roundtrip(db_tenant):
    articulos = [{"codigo": 1, "descripcion": "QUESO", "stock": 10}]
    inventory_repo.save_articles(db_tenant, articulos)
    assert inventory_repo.get_articles(db_tenant) == articulos


def test_save_is_full_replace_upsert(db_tenant):
    inventory_repo.save_articles(db_tenant, [{"codigo": 1, "stock": 10}])
    inventory_repo.save_articles(db_tenant, [{"codigo": 2, "stock": 5}])
    assert inventory_repo.get_articles(db_tenant) == [{"codigo": 2, "stock": 5}]

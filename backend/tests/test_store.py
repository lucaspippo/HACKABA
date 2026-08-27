from core import store


def test_upsert_desde_conector_crea_producto_nuevo():
    store.resetear_actual()
    antes = len(store.raw_actual())
    fila = {"descripcion": "Producto Odoo Nuevo", "stock": 10, "costo_iva": None,
            "pvp": 500, "sku": "ODOO-1", "source": "odoo", "source_id": "999"}
    r = store.upsert_desde_conector(fila, actor="test")
    assert len(store.raw_actual()) == antes + 1
    assert r["descripcion"] == "Producto Odoo Nuevo"
    assert r["sku"] == "ODOO-1"
    assert r["source"] == "odoo" and r["source_id"] == "999"


def test_upsert_desde_conector_actualiza_si_ya_vinculado():
    store.resetear_actual()
    fila = {"descripcion": "Producto Odoo", "stock": 10, "costo_iva": None,
            "pvp": 500, "sku": "ODOO-2", "source": "odoo", "source_id": "888"}
    store.upsert_desde_conector(fila, actor="test")
    antes = len(store.raw_actual())
    fila["stock"] = 25
    fila["pvp"] = 600
    r = store.upsert_desde_conector(fila, actor="test")
    assert len(store.raw_actual()) == antes  # no duplica
    assert r["stock"] == 25
    assert r["pvp"] == 600

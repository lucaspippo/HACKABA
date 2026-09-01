from core.db import purchase_orders_repo


def test_list_empty_when_no_orders(db_tenant):
    assert purchase_orders_repo.list_orders(db_tenant) == []


def test_create_then_list(db_tenant):
    orden = {
        "numero": "OC-2026-0901", "fecha": "2026-08-24", "proveedor": "Molinos SA",
        "estado": "borrador", "origen": "quiebre_inminente", "motivo": "",
        "preparada_por": "Ángela", "aprobada_por": "emilio",
        "preparada": "2026-08-24T10:00:00", "items": [{"codigo": 1, "producto": "Harina", "cantidad": 50}],
    }
    purchase_orders_repo.create(db_tenant, orden)
    orders = purchase_orders_repo.list_orders(db_tenant)
    assert len(orders) == 1
    assert orders[0]["numero"] == "OC-2026-0901"
    assert orders[0]["items"] == orden["items"]


def test_upsert_from_odoo_crea_y_luego_actualiza_por_number(db_tenant):
    from core.db import purchase_orders_repo
    orden = {
        "numero": "P00099", "fecha": "2026-08-20", "proveedor": "Proveedor Odoo",
        "estado": "borrador", "items": [{"producto": "X", "cantidad": 5, "precio_unitario": 10}],
        "source_id": "77", "source_status": "borrador",
    }
    purchase_orders_repo.upsert_from_odoo(db_tenant, orden)
    creada = purchase_orders_repo.find_by_number(db_tenant, "P00099")
    assert creada["estado"] == "borrador"
    assert creada["source"] == "odoo" and creada["source_id"] == "77"

    orden["estado"] = "aprobada"
    orden["source_status"] = "confirmada"
    purchase_orders_repo.upsert_from_odoo(db_tenant, orden)
    actualizada = purchase_orders_repo.find_by_number(db_tenant, "P00099")
    assert actualizada["estado"] == "aprobada"
    todas = purchase_orders_repo.list_orders(db_tenant)
    assert sum(1 for o in todas if o["numero"] == "P00099") == 1


def test_find_draft_none_codigo_does_not_match_item_with_a_codigo(db_tenant):
    """find_draft(codigo=None) must not match a draft whose stored item has a
    real codigo — it only matches a draft whose item codigo is also None.
    (Before the fix, a None codigo matched the first draft found for the
    origin regardless of that draft's own item codigo.)"""
    orden = {
        "numero": "OC-2026-0901", "fecha": "2026-08-24", "proveedor": "Molinos SA",
        "estado": "borrador", "origen": "quiebre_inminente", "motivo": "",
        "preparada_por": "Ángela", "aprobada_por": "emilio",
        "preparada": "2026-08-24T10:00:00", "items": [{"codigo": 1, "producto": "Harina", "cantidad": 50}],
    }
    purchase_orders_repo.create(db_tenant, orden)
    found = purchase_orders_repo.find_draft(db_tenant, codigo=None, origen="quiebre_inminente")
    assert found is None


def _draft(numero, codigo, origen="quiebre_inminente"):
    return {
        "numero": numero, "fecha": "2026-08-24", "proveedor": "Molinos SA",
        "estado": "borrador", "origen": origen, "motivo": "",
        "preparada_por": "Ángela", "aprobada_por": "emilio",
        "preparada": "2026-08-24T10:00:00",
        "items": [{"codigo": codigo, "producto": "Harina", "cantidad": 50}],
    }


def test_find_draft_matches_on_item_codigo(db_tenant):
    purchase_orders_repo.create(db_tenant, _draft("OC-2026-0901", 7))
    found = purchase_orders_repo.find_draft(db_tenant, codigo=7,
                                            origen="quiebre_inminente")
    assert found is not None
    assert found["numero"] == "OC-2026-0901"


def test_find_draft_ignores_other_codigo_same_origin(db_tenant):
    purchase_orders_repo.create(db_tenant, _draft("OC-2026-0901", 7))
    assert purchase_orders_repo.find_draft(
        db_tenant, codigo=8, origen="quiebre_inminente") is None


def test_find_draft_ignores_other_origin(db_tenant):
    purchase_orders_repo.create(db_tenant, _draft("OC-2026-0901", 7, origen="sobrecompra"))
    assert purchase_orders_repo.find_draft(
        db_tenant, codigo=7, origen="quiebre_inminente") is None

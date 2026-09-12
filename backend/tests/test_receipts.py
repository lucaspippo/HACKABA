from core import esquema, receipts
from core.db import purchase_orders_repo, tenant as _tenant
from tests.conftest import limpiar_tabla_tenant


def test_match_receipt_to_purchase_order_short():
    tid = _tenant.current_tenant_id()
    purchase_orders_repo.upsert_from_odoo(tid, {
        "numero": "P00011", "fecha": "2026-08-02", "proveedor": "Sur",
        "estado": "aprobada",
        "items": [{"codigo": 1, "producto": "X", "cantidad": 2.0, "precio_unitario": 10}],
        "source_id": "11", "source_status": "confirmada",
    })
    esquema.reemplazar_filas("recepciones", [
        {"po_number": "P00011", "codigo": 1, "producto": "X", "cantidad": 1.5,
         "source": "odoo", "source_id": "500"},
    ])
    r = receipts.match_receipt_to_purchase_order("P00011")
    assert r["found"] is True
    assert r["matches"] == []
    assert len(r["short"]) == 1
    assert r["short"][0]["ordered"] == 2.0
    assert r["short"][0]["received"] == 1.5
    assert r["extra"] == []
    limpiar_tabla_tenant("data_sections")
    limpiar_tabla_tenant("purchase_orders")


def test_match_receipt_unknown_po():
    r = receipts.match_receipt_to_purchase_order("NO-SUCH")
    assert r["found"] is False

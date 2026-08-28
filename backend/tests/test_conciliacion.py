"""Warehouse count reconciliation: hypothesis cascade + accept the count."""
from __future__ import annotations

import pytest

from core import conciliacion, lotes, receipts, sales, store
from tests.conftest import limpiar_tabla_tenant


@pytest.fixture(autouse=True)
def _tenant_ctx(db_tenant, monkeypatch):
    monkeypatch.setattr("core.db.tenant.current_tenant_id", lambda: db_tenant)
    monkeypatch.setenv("POLPILOT_DEMO_TODAY", "2026-07-07")
    store.resetear_actual()
    yield db_tenant
    limpiar_tabla_tenant("data_sections")
    store.resetear_actual()


def _producto(codigo, **kw):
    return store.crear_articulo({
        "codigo": codigo,
        "descripcion": kw.get("descripcion", f"SKU {codigo}"),
        "stock": kw.get("stock", 100),
        "costo_iva": kw.get("costo_iva", 10),
        "pvp": kw.get("pvp", 20),
        "tipo": kw.get("tipo", ""),
    }, "emilio")


def _lote(codigo, cantidad, counted, **kw):
    return lotes.crear({
        "codigo": codigo,
        "producto": kw.get("producto", f"SKU {codigo}"),
        "ubicacion": kw.get("ubicacion", "A1"),
        "lote": kw.get("lote", "L1"),
        "cantidad": cantidad,
        "counted_qty": counted,
        "vencimiento": kw.get("vencimiento"),
    }, "emilio")


def _item(codigo):
    packed = conciliacion.resumen()
    for row in packed["diferencias"]:
        if int(row["codigo"]) == int(codigo):
            return row
    return None


def _clase(codigo):
    row = _item(codigo)
    assert row is not None, f"no open difference for {codigo}"
    return row["hipotesis"]["clase"], row["hipotesis"]["confianza"]


def test_incomplete_count_beats_matching_sale():
    _producto(98001, stock=80)
    counted = _lote(98001, 50, 40, lote="L-counted")
    _lote(98001, 30, None, lote="L-sibling")
    sales.create({"fecha": "2026-07-01", "producto": "SKU 98001",
                  "codigo": 98001, "cantidad": 10}, "emilio")
    clase, confianza = _clase(98001)
    assert clase == "conteo_incompleto"
    assert confianza == "unverified"
    hip = _item(98001)["hipotesis"]
    assert "sibling_counts" in (hip.get("evidencia") or {}).get("buscado_en", [])
    assert counted["id"] == _item(98001)["id"]


def test_tiny_tara_is_folded_out_of_open_differences():
    _producto(98002, stock=100)
    _lote(98002, 100, 99.6)
    packed = conciliacion.resumen()
    assert _item(98002) is None
    taras = [t for t in packed["taras"] if int(t["codigo"]) == 98002]
    assert len(taras) == 1
    assert taras[0]["hipotesis"]["clase"] == "tara"
    assert taras[0]["hipotesis"]["confianza"] == "medium"


def test_ten_percent_gap_is_not_tara():
    _producto(98003, stock=100)
    _lote(98003, 100, 90)
    clase, _ = _clase(98003)
    assert clase != "tara"
    assert _item(98003) is not None


def test_sale_qty_matching_shortage_is_high():
    _producto(98004, stock=50)
    _lote(98004, 50, 40)
    sales.create({"fecha": "2026-07-01", "producto": "SKU 98004",
                  "codigo": 98004, "cantidad": 10}, "emilio")
    clase, confianza = _clase(98004)
    assert clase == "venta_sin_bajar_stock"
    assert confianza == "high"
    assert "aceptar_conteo" in _item(98004)["hipotesis"]["acciones"]


def test_close_but_not_exact_sale_is_medium_not_high():
    _producto(98005, stock=50)
    _lote(98005, 50, 38)
    sales.create({"fecha": "2026-07-01", "producto": "SKU 98005",
                  "codigo": 98005, "cantidad": 10}, "emilio")
    clase, confianza = _clase(98005)
    assert clase == "venta_sin_bajar_stock"
    assert confianza == "medium"


def test_window_sum_of_sales_is_medium():
    _producto(98006, stock=50)
    _lote(98006, 50, 40)
    sales.create({"fecha": "2026-07-01", "producto": "SKU 98006",
                  "codigo": 98006, "cantidad": 6}, "emilio")
    sales.create({"fecha": "2026-07-02", "producto": "SKU 98006",
                  "codigo": 98006, "cantidad": 4}, "emilio")
    clase, confianza = _clase(98006)
    assert clase == "venta_sin_bajar_stock"
    assert confianza == "medium"


def test_receipt_qty_matching_surplus_is_high():
    _producto(98007, stock=50)
    _lote(98007, 50, 60)
    receipts.create({"fecha": "2026-07-02", "producto": "SKU 98007",
                     "codigo": 98007, "cantidad": 10, "proveedor": "Molinos"}, "emilio")
    clase, confianza = _clase(98007)
    assert clase == "recepcion_sin_cargar"
    assert confianza == "high"
    assert "preguntar_angela" in _item(98007)["hipotesis"]["acciones"]
    assert "aceptar_conteo" not in _item(98007)["hipotesis"]["acciones"]


def test_incoming_qty_matching_surplus_is_in_transit():
    _producto(98008, stock=50)
    raw = store.raw_actual()
    for d in raw:
        if d.get("codigo") == 98008:
            d["incoming_qty"] = 10
    store.guardar(raw)
    _lote(98008, 50, 60)
    clase, confianza = _clase(98008)
    assert clase == "en_transito"
    assert confianza == "high"
    assert "aceptar_conteo" not in _item(98008)["hipotesis"]["acciones"]


def test_tenx_typo_is_medium():
    _producto(98009, stock=420)
    _lote(98009, 420, 42)
    clase, confianza = _clase(98009)
    assert clase == "cantidad_mal_tipeada"
    assert confianza == "medium"
    assert "aceptar_conteo" in _item(98009)["hipotesis"]["acciones"]


def test_expired_lot_shortage_is_writeoff_via_angela():
    _producto(98010, stock=50)
    _lote(98010, 50, 40, vencimiento="2026-01-01")
    clase, confianza = _clase(98010)
    assert clase == "lote_vencido"
    assert confianza == "medium"
    assert "preguntar_angela" in _item(98010)["hipotesis"]["acciones"]


def test_unexplained_gap_lists_what_was_searched():
    _producto(98011, stock=50, costo_iva=10)
    _lote(98011, 50, 33)
    clase, confianza = _clase(98011)
    assert clase == "sin_explicacion"
    assert confianza == "low"
    buscado = _item(98011)["hipotesis"]["evidencia"]["buscado_en"]
    assert buscado == ["sales", "receipts", "pipeline", "expiry", "sibling_counts"]
    assert _item(98011)["impacto"] == 170.0  # 17 units * $10
    acciones = _item(98011)["hipotesis"]["acciones"]
    assert "aceptar_conteo" in acciones
    assert "preguntar_angela" in acciones


def test_no_cost_omits_peso_impact():
    _producto(98012, stock=50, costo_iva=None, pvp=None)
    _lote(98012, 50, 33)
    row = _item(98012)
    assert row["impacto"] is None


def test_accept_writes_counted_qty_and_moves_product_stock():
    _producto(98013, stock=100)
    lot = _lote(98013, 50, 40)
    updated = conciliacion.aceptar(lot["id"], "emilio")
    assert updated["cantidad"] == 40
    art = next(d for d in store.raw_actual() if d.get("codigo") == 98013)
    assert art["stock"] == 90
    assert _item(98013) is None


def test_accept_without_count_raises():
    _producto(98014, stock=50)
    lot = _lote(98014, 50, None)
    with pytest.raises(ValueError):
        conciliacion.aceptar(lot["id"], "emilio")

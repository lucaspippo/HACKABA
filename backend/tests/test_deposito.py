import datetime

from core import deposito, esquema, store
from tests.conftest import limpiar_tabla_tenant


def setup_function():
    limpiar_tabla_tenant("data_sections")
    store.resetear_actual()


def teardown_function():
    limpiar_tabla_tenant("data_sections")
    store.resetear_actual()


def test_aging_buckets_with_frozen_today():
    art = store.raw_actual()[0]
    esquema.reemplazar_filas("deposito", [
        {"codigo": art["codigo"], "producto": art["descripcion"], "cantidad": 4,
         "in_date": "2026-03-01", "ubicacion": "A"},
        {"codigo": art["codigo"], "producto": art["descripcion"], "cantidad": 3,
         "in_date": "2025-11-01", "ubicacion": "B"},
        {"codigo": art["codigo"], "producto": art["descripcion"], "cantidad": 2,
         "in_date": "2025-06-01", "ubicacion": "C"},
        {"codigo": art["codigo"], "producto": art["descripcion"], "cantidad": 1,
         "in_date": "2024-01-01", "ubicacion": "D"},
        {"codigo": art["codigo"], "producto": art["descripcion"], "cantidad": 9,
         "ubicacion": "sin fecha"},
    ])
    buckets = {b["bucket"]: b for b in deposito.aging(as_of=datetime.date(2026, 4, 7))}
    assert buckets["0_90"]["units"] == 4
    assert buckets["91_180"]["units"] == 3
    assert buckets["181_365"]["units"] == 2
    assert buckets["365_plus"]["units"] == 1
    costo = float(art.get("costo_iva") or 0)
    assert buckets["0_90"]["inmovilizado"] == round(4 * costo, 2)


def test_discrepancias_counted_vs_system():
    art = store.raw_actual()[0]
    esquema.reemplazar_filas("deposito", [
        {"codigo": art["codigo"], "producto": art["descripcion"], "cantidad": 5,
         "counted_qty": 3, "ubicacion": "WH"},
        {"codigo": art["codigo"], "producto": art["descripcion"], "cantidad": 2,
         "ubicacion": "WH2"},
    ])
    disc = deposito.discrepancias()
    row = next(x for x in disc if x["codigo"] == art["codigo"])
    assert row["stock_contable"] == 7
    assert row["stock_fisico"] == 3

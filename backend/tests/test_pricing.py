"""
Pricing por peso vs por unidad. La regla de dominio: un producto de balanza se
pricea en $/kg (stock en kg, costo en $/kg) y NUNCA se calcula ni exporta como
si fuera por unidad. La frontera vive en core/pricing.py.
"""
from __future__ import annotations

import csv
import io

import pytest

from core import anomalias, pricing, store, sync


BALANZA = {"codigo": 1, "descripcion": "JAMON COCIDO", "venta_x_peso": True,
           "costo_iva": 8000.0, "pvp": 12000.0, "stock": 50.0, "estado": "activo"}
UNIDAD = {"codigo": 2, "descripcion": "ACEITE 900CC", "venta_x_peso": False,
          "costo_iva": 8000.0, "pvp": 12000.0, "stock": 50.0, "estado": "activo"}


# --- la unidad se deriva de venta_x_peso, en un solo lugar ---

def test_unidad_y_etiquetas():
    assert pricing.unidad(BALANZA) == "kg" and pricing.label_precio(BALANZA) == "$/kg"
    assert pricing.unidad(UNIDAD) == "unidad" and pricing.label_precio(UNIDAD) == "$/u"


def test_margen_es_consciente_de_unidad():
    # mismos números crudos, mismo margen aritmético — pero cada uno en SU unidad
    assert pricing.margen_pct(BALANZA) == 50.0   # $/kg vs $/kg
    assert pricing.margen_pct(UNIDAD) == 50.0    # $/u vs $/u
    assert pricing.margen_pct({"venta_x_peso": True, "pvp": None, "costo_iva": 100}) is None


def test_perdida_compara_en_la_misma_unidad():
    perd_kg = {**BALANZA, "costo_iva": 15000.0, "pvp": 12000.0}
    assert pricing.es_a_perdida(perd_kg) is True      # $15.000/kg de costo vs $12.000/kg
    assert pricing.es_a_perdida(BALANZA) is False
    anulado = {**perd_kg, "estado": "anulado"}
    assert pricing.es_a_perdida(anulado) is False     # los anulados no cuentan


def test_anomalias_usa_la_frontera():
    # la detección de pérdida del sistema delega en pricing (no compara a ciegas)
    raw = [dict(BALANZA), {**UNIDAD, "costo_iva": 900.0, "pvp": 500.0}]
    perdida = anomalias._perdida(raw)
    assert [d["codigo"] for d in perdida] == [2]


def test_enriquecer_no_pisa_nada():
    e = pricing.enriquecer(BALANZA)
    assert e["unidad_pricing"] == "kg" and e["label_precio"] == "$/kg"
    assert e["pvp"] == BALANZA["pvp"] and e["descripcion"] == BALANZA["descripcion"]


# --- el punto crítico: el delta export dice la unidad, siempre ---

@pytest.fixture()
def _store_limpio():
    store.resetear_actual()
    yield
    store.resetear_actual()


def test_delta_export_marca_la_unidad(_store_limpio):
    raw = store.raw_actual()
    bal = next(d for d in raw if d.get("venta_x_peso"))
    uni = next(d for d in raw if not d.get("venta_x_peso") and d.get("pvp"))
    bal["pvp"] = (bal.get("pvp") or 1000) + 111   # tocar ambos para que entren al delta
    uni["pvp"] = uni["pvp"] + 111
    store.guardar(raw)

    r = sync.generar_delta_export("faro")
    filas = list(csv.reader(io.StringIO(r["csv"])))
    header = filas[0]
    assert "UNIDAD_PRECIO" in header              # la columna existe SIEMPRE
    i_cod, i_uni = header.index("CODIGO"), header.index("UNIDAD_PRECIO")
    por_codigo = {f[i_cod]: f[i_uni] for f in filas[1:]}
    assert por_codigo[str(bal["codigo"])] == "kg"      # balanza → $/kg, jamás "unidad"
    assert por_codigo[str(uni["codigo"])] == "unidad"
    assert r["balanzas"] >= 1
    assert "$/kg" in r["nota"]                    # la nota lo advierte en criollo


def test_articulos_con_estado_expone_pipeline(_store_limpio):
    items = store.articulos_con_estado()
    assert items
    assert "incoming_qty" in items[0]
    assert "outgoing_qty" in items[0]
    assert "source" in items[0]


def test_articulos_con_estado_expone_unidad(_store_limpio):
    items = store.articulos_con_estado()
    balanzas = [i for i in items if i["unidad_pricing"] == "kg"]
    unidades = [i for i in items if i["unidad_pricing"] == "unidad"]
    assert balanzas and unidades                  # el piloto tiene de los dos
    assert all(i["label_precio"] == "$/kg" for i in balanzas)

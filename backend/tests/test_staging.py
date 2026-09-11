import os

import pytest

from core import staging, store

CSV = (
    "Codigo,Producto,Stock,Costo,Precio\n"
    ",QUESO NUEVO A PERDIDA,10,200,100\n"          # costo > precio
    ",GALLETA SIN PRECIO,5,50,\n"                  # sin precio
    ",MANTECA SANTA CLARA 200G (X30U),3,100,150\n"  # duplicado de uno existente
    ",INSUMO LIMPIEZA,50000,10,20\n"               # stock outlier
)


@pytest.fixture(autouse=True)
def limpio():
    if os.path.exists(staging.STAGING_JSON):
        os.remove(staging.STAGING_JSON)
    store.resetear_actual()
    yield
    if os.path.exists(staging.STAGING_JSON):
        os.remove(staging.STAGING_JSON)
    store.resetear_actual()


def test_crear_batch_detecta_observaciones():
    r = staging.crear_batch("prueba.csv", CSV)
    tipos = {o["tipo"] for o in r["observaciones"]}
    assert "precio_perdida" in tipos
    assert "sin_precio" in tipos
    assert "duplicado" in tipos
    assert "stock_outlier" in tipos
    # ordenadas por impacto en pesos desc
    impactos = [o["impacto_pesos"] for o in r["observaciones"]]
    assert impactos == sorted(impactos, reverse=True)


def test_resolver_set_margen_y_preview():
    r = staging.crear_batch("prueba.csv", CSV)
    bid = r["id"]
    staging.resolver(bid, "precio_perdida", "set_margen", {"margen": 30})
    staging.resolver(bid, "sin_precio", "set_margen", {"margen": 30})
    staging.resolver(bid, "duplicado", "unificar", {})
    staging.resolver(bid, "stock_outlier", "confirmar", {})
    p = staging.preview(bid)
    assert p["pendientes"] == []
    assert p["descartados"] == 1  # el duplicado no se integra


def test_integrar_agrega_al_inventario():
    antes = len(store.raw_actual())
    r = staging.crear_batch("prueba.csv", CSV)
    bid = r["id"]
    staging.resolver(bid, "duplicado", "unificar", {})
    res = staging.integrar(bid)
    assert res["nuevos"] == 3  # 4 filas - 1 duplicado
    assert len(store.raw_actual()) == antes + 3
    assert staging.listar() == []  # el batch se consumió


def test_descartar():
    r = staging.crear_batch("x.csv", CSV)
    staging.descartar(r["id"])
    assert staging.listar() == []

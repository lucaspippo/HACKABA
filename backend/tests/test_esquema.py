import os

import pytest

from core import esquema, staging, store

VENTAS_CSV = (
    "Fecha,Producto,Cantidad,Precio\n"
    "2026-06-01,MANTECA SANTA CLARA 200G (X30U),5,150\n"
    "2026-06-01,PRODUCTO QUE NO EXISTE XYZ,3,100\n"
)


@pytest.fixture(autouse=True)
def limpio():
    for f in (staging.STAGING_JSON, esquema.APARTADOS_JSON):
        if os.path.exists(f):
            os.remove(f)
    store.resetear_actual()
    yield
    for f in (staging.STAGING_JSON, esquema.APARTADOS_JSON):
        if os.path.exists(f):
            os.remove(f)
    store.resetear_actual()


def test_detecta_tipo_ventas():
    d = esquema.detectar_tipo(["Fecha", "Producto", "Cantidad", "Precio"])
    assert d["tipo"] == "venta"


def test_detecta_tipo_producto():
    d = esquema.detectar_tipo(["Codigo", "Producto", "Stock", "Costo", "PVP"])
    assert d["tipo"] == "producto"


def test_plan_relaciona_ventas_con_inventario():
    plan = esquema.plan_integracion("venta")
    assert plan["apartado_nuevo"] is True
    assert "producto" in plan["relaciona_con"]
    assert any("rotación" in a for a in plan["activa"])


def test_staging_ventas_detecta_huerfana():
    r = staging.crear_batch("ventas.csv", VENTAS_CSV)
    assert r["tipo"] == "venta"
    assert r["plan"]["relaciona_con"] == ["producto"]
    tipos = {o["tipo"] for o in r["observaciones"]}
    assert "producto_inexistente" in tipos
    assert r["observaciones"][0]["items"] == 1  # solo la huérfana


def test_integrar_ventas_crea_apartado():
    assert "venta" not in esquema.apartados_activos()
    r = staging.crear_batch("ventas.csv", VENTAS_CSV)
    staging.resolver(r["id"], "producto_inexistente", "unificar", {})  # descarta la huérfana
    res = staging.integrar(r["id"])
    assert res["tipo"] == "venta"
    assert res["nuevos"] == 1
    assert "venta" in esquema.apartados_activos()

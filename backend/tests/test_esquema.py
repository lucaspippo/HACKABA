import pytest

from core import esquema, staging, store
from tests.conftest import limpiar_tabla_tenant

VENTAS_CSV = (
    "Fecha,Producto,Cantidad,Precio\n"
    "2026-06-01,MANTECA SANTA CLARA 200G (X30U),5,150\n"
    "2026-06-01,PRODUCTO QUE NO EXISTE XYZ,3,100\n"
)


@pytest.fixture(autouse=True)
def limpio():
    limpiar_tabla_tenant("staging_batches")
    limpiar_tabla_tenant("data_sections")
    store.resetear_actual()
    yield
    limpiar_tabla_tenant("staging_batches")
    limpiar_tabla_tenant("data_sections")
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


def test_plan_integracion_orden_compra_usa_nombre_ordenes_compra():
    plan = esquema.plan_integracion("orden_compra")
    assert plan["nombre"] == "Órdenes de compra"
    assert plan["tipo"] == "orden_compra"


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


def test_upsert_filas_inserts_then_updates_by_source_id():
    esquema.upsert_filas("venta", [
        {"fecha": "2026-01-01", "producto": "A", "codigo": 1, "cantidad": 2,
         "precio": 10, "source": "odoo", "source_id": "L1"},
    ])
    assert len(esquema.filas("venta")) == 1
    esquema.upsert_filas("venta", [
        {"fecha": "2026-01-02", "producto": "A", "codigo": 1, "cantidad": 5,
         "precio": 10, "source": "odoo", "source_id": "L1"},
    ])
    filas = esquema.filas("venta")
    assert len(filas) == 1
    assert filas[0]["cantidad"] == 5
    assert filas[0]["fecha"] == "2026-01-02"


def test_delete_odoo_missing_keeps_csv_rows():
    esquema.reemplazar_filas("venta", [
        {"fecha": "2026-01-01", "producto": "CSV", "cantidad": 1, "precio": 1},
        {"fecha": "2026-01-01", "producto": "Odoo", "cantidad": 1, "precio": 1,
         "source": "odoo", "source_id": "L1"},
        {"fecha": "2026-01-01", "producto": "Gone", "cantidad": 1, "precio": 1,
         "source": "odoo", "source_id": "L2"},
    ])
    n = esquema.delete_odoo_missing("venta", {"L1"})
    assert n == 1
    ids = {f.get("source_id") for f in esquema.filas("venta")}
    assert ids == {None, "L1"}

import pytest

from core import staging, store
from tests.conftest import limpiar_tabla_tenant

CSV = (
    "Codigo,Producto,Stock,Costo,Precio\n"
    ",QUESO NUEVO A PERDIDA,10,200,100\n"          # costo > precio
    ",GALLETA SIN PRECIO,5,50,\n"                  # sin precio
    ",MANTECA SANTA CLARA 200G (X30U),3,100,150\n"  # duplicado de uno existente
    ",INSUMO LIMPIEZA,50000,10,20\n"               # stock outlier
)


@pytest.fixture(autouse=True)
def limpio():
    limpiar_tabla_tenant("staging_batches")
    store.resetear_actual()
    yield
    limpiar_tabla_tenant("staging_batches")
    store.resetear_actual()


def test_crear_batch_odoo_producto_nuevo_sin_observaciones_de_precio():
    store.resetear_actual()
    filas_odoo = [
        {"id": 501, "codigo": "ODOO-NEW-1", "nombre": "Producto Totalmente Nuevo",
         "categoria": "General", "precio": 999.0, "stock": 5.0},
    ]
    r = staging.crear_batch_odoo("producto", filas_odoo)
    assert r["tipo"] == "producto"
    assert r["total_filas"] == 1


def test_crear_batch_odoo_producto_detecta_duplicado_por_nombre():
    store.resetear_actual()
    existente = store.raw_actual()[0]
    filas_odoo = [
        {"id": 502, "codigo": "ODOO-DUP-1", "nombre": existente["descripcion"],
         "categoria": "General", "precio": 10.0, "stock": 1.0},
    ]
    r = staging.crear_batch_odoo("producto", filas_odoo)
    tipos = {o["tipo"] for o in r["observaciones"]}
    assert "duplicado" in tipos


def test_integrar_batch_odoo_usa_upsert_con_source():
    store.resetear_actual()
    filas_odoo = [
        {"id": 601, "codigo": "ODOO-INT-1", "nombre": "Producto Integrado Odoo",
         "categoria": "General", "precio": 42.0, "stock": 3.0},
    ]
    r = staging.crear_batch_odoo("producto", filas_odoo)
    res = staging.integrar(r["id"], actor="test")
    assert res["ok"] is True
    creado = next(d for d in store.raw_actual() if d.get("source_id") == "601")
    assert creado["source"] == "odoo"
    assert creado["sku"] == "ODOO-INT-1"


def test_crear_batch_odoo_proveedor_nuevo():
    r = staging.crear_batch_odoo("proveedor", [
        {"id": 801, "nombre": "Proveedor Staging Nuevo", "cuit": "30-2-2",
         "localidad": "Rosario", "telefono": "341-000", "email": "p@example.com"},
    ])
    assert r["tipo"] == "proveedor"
    assert r["total_filas"] == 1


def test_integrar_batch_odoo_proveedor():
    from core import proveedores
    r = staging.crear_batch_odoo("proveedor", [
        {"id": 802, "nombre": "Proveedor Integrado Odoo", "cuit": "30-3-3",
         "localidad": "", "telefono": "", "email": ""},
    ])
    res = staging.integrar(r["id"], actor="test")
    assert res["ok"] is True
    creado = next(p for p in proveedores.listar() if p.get("source_id") == "802")
    assert creado["nombre"] == "Proveedor Integrado Odoo"


def test_crear_batch_odoo_cliente_nuevo():
    r = staging.crear_batch_odoo("cliente", [
        {"id": 901, "nombre": "Cliente Staging Nuevo", "cuit": "20-4-4",
         "localidad": "CABA", "telefono": "11-000", "email": "cl@example.com"},
    ])
    assert r["tipo"] == "cliente"
    assert r["total_filas"] == 1


def test_integrar_batch_odoo_cliente():
    from core import cuentas
    r = staging.crear_batch_odoo("cliente", [
        {"id": 902, "nombre": "Cliente Integrado Odoo", "cuit": "20-5-5",
         "localidad": "", "telefono": "", "email": ""},
    ])
    res = staging.integrar(r["id"], actor="test")
    assert res["ok"] is True
    creado = next(c for c in cuentas.listar() if c.get("source_id") == "902")
    assert creado["nombre"] == "Cliente Integrado Odoo"
    assert creado["saldo"] == 0


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

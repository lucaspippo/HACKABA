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
    from core import esquema
    from core.db import blob_repo, tenant as _t
    limpiar_tabla_tenant("staging_batches")
    store.resetear_actual()
    esquema.reemplazar_filas("venta", [])
    blob_repo.save_blob("sales_validation", _t.current_tenant_id(), {"estado": "sin_datos"})
    yield
    limpiar_tabla_tenant("staging_batches")
    store.resetear_actual()
    esquema.reemplazar_filas("venta", [])


def test_crear_batch_odoo_producto_nuevo_sin_observaciones_de_precio():
    store.resetear_actual()
    filas_odoo = [
        {"id": 501, "codigo": "ODOO-NEW-1", "nombre": "Producto Totalmente Nuevo",
         "categoria": "General", "precio": 999.0, "stock": 5.0},
    ]
    r = staging.crear_batch_odoo("producto", filas_odoo)
    assert r["tipo"] == "producto"
    assert r["total_filas"] == 1
    tipos = {o["tipo"] for o in r["observaciones"]}
    assert "precio_a_perdida" not in tipos
    assert "sin_precio" not in tipos


def test_coerce_producto_odoo_emite_costo_y_omite_venta_x_peso():
    fila = staging.coerce_producto_odoo({
        "id": 1, "nombre": "X", "codigo": "SKU", "stock": 4, "precio": 10,
        "costo": 8, "free_qty": 3, "incoming_qty": 1, "outgoing_qty": 0, "activo": True,
    })
    assert fila["costo_iva"] == 8
    assert fila["free_qty"] == 3
    assert "venta_x_peso" not in fila
    assert fila["estado"] == "activo"


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


def test_crear_batch_odoo_orden_compra_nueva():
    r = staging.crear_batch_odoo("orden_compra", [
        {"id": 1001, "numero": "P00201", "proveedor": "Proveedor X", "estado": "confirmada",
         "fecha": "2026-08-20", "total": 500.0,
         "items": [{"producto": "Y", "cantidad": 2, "precio_unitario": 250.0}]},
    ])
    assert r["tipo"] == "orden_compra"
    assert r["total_filas"] == 1
    assert r["observaciones"] == []


def test_integrar_batch_odoo_orden_compra():
    from core.db import purchase_orders_repo, tenant as _tenant
    r = staging.crear_batch_odoo("orden_compra", [
        {"id": 1002, "numero": "P00202", "proveedor": "Proveedor Y", "estado": "cerrada",
         "fecha": "2026-08-15", "total": 300.0,
         "items": [{"producto": "Z", "cantidad": 1, "precio_unitario": 300.0}]},
    ])
    res = staging.integrar(r["id"], actor="test")
    assert res["ok"] is True
    creada = purchase_orders_repo.find_by_number(_tenant.current_tenant_id(), "P00202")
    assert creada["estado"] == "recibida"  # "cerrada" (Odoo) -> "recibida" (PolPilot)
    assert creada["source_status"] == "cerrada"


def test_crear_batch_odoo_venta_nueva():
    r = staging.crear_batch_odoo("venta", [
        {"id": 200, "nombre": "Laptop", "fecha": "2026-06-15 10:00:00",
         "cantidad": 2, "precio": 1200, "estado": "confirmada"},
    ])
    assert r["tipo"] == "venta"
    assert r["total_filas"] == 1


def test_integrar_batch_odoo_venta_auto_confirma_montos():
    from core import esquema, ventas
    r = staging.crear_batch_odoo("venta", [
        {"id": 201, "nombre": "Laptop", "fecha": "2026-06-15",
         "cantidad": 2, "precio": 100, "codigo": 1, "estado": "confirmada"},
    ])
    res = staging.integrar(r["id"], actor="test")
    assert res["ok"] is True
    filas = esquema.filas("venta")
    assert any(f.get("source_id") == "201" for f in filas)
    assert ventas.montos_confirmados() is True


def test_localizar_batch_odoo_cliente_usa_el_sustantivo_correcto():
    """The duplicate card is re-localized on read by (tipo, obs tipo); without
    a cliente-specific entry it would fall back to the products wording."""
    from core import cuentas
    existente = cuentas.listar()[0]
    r = staging.crear_batch_odoo("cliente", [
        {"id": 903, "nombre": existente["nombre"], "cuit": "", "localidad": "",
         "telefono": "", "email": ""},
    ])
    b = next(x for x in staging._load() if x["id"] == r["id"])
    obs = staging.localizar_batch(b, "en")["observaciones"][0]
    assert "customers" in obs["descripcion"]
    assert "products" not in obs["descripcion"]


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


def test_map_purchase_status():
    assert staging.map_purchase_status("draft", False) == "borrador"
    assert staging.map_purchase_status("confirmada", False) == "aprobada"
    assert staging.map_purchase_status("purchase", True) == "aprobada"
    assert staging.map_purchase_status("purchase", True, fully_received=True) == "recibida"
    assert staging.map_purchase_status(
        "purchase", True, fully_received=True, open_backorder=True) == "aprobada"
    assert staging.map_purchase_status("done", False) == "recibida"
    assert staging.map_purchase_status("cancel", False) == "cancelada"


def test_coerce_producto_odoo_needs_pricing_vs_wholesale():
    needs = staging.coerce_producto_odoo({
        "id": 4, "nombre": "Cable", "codigo": "product_unpriced_cable",
        "stock": 1, "precio": None, "precio_lista": 0, "pricing_status": "needs_pricing",
        "costo": 10, "activo": True,
    })
    assert needs["pvp"] is None
    assert needs["pricing_status"] == "needs_pricing"
    wholesale = staging.coerce_producto_odoo({
        "id": 3, "nombre": "Pallet", "codigo": "WH-001",
        "stock": 8, "precio": 8500, "precio_lista": 0, "pricing_status": "wholesale_only",
        "costo": 400, "activo": True,
    })
    assert wholesale["pvp"] == 8500
    assert wholesale["pricing_status"] == "wholesale_only"


def test_coerce_deposito_odoo_omite_counted_si_no_hay_conteo():
    fila = staging.coerce_deposito_odoo({
        "id": 30, "nombre": "X", "codigo": 1, "ubicacion": "WH/Stock",
        "lote": "L", "vencimiento": "2026-12-01", "cantidad": 5, "in_date": "2026-01-15",
    })
    assert "counted_qty" not in fila
    assert fila["source_id"] == "30"
    counted = staging.coerce_deposito_odoo({
        "id": 31, "nombre": "X", "codigo": 1, "ubicacion": "WH2",
        "lote": "", "vencimiento": "", "cantidad": 2, "in_date": "2025-01-01",
        "counted_qty": 1,
    })
    assert counted["counted_qty"] == 1


def test_coerce_recepcion_odoo():
    fila = staging.coerce_recepcion_odoo({
        "id": 500, "fecha": "2026-08-06 12:00:00", "nombre": "X", "codigo": 1,
        "proveedor": "Sur", "cantidad": 15, "deposito": "WH/Stock",
        "origen": "WH/IN/00012", "po_number": "P00010", "estado": "done",
    })
    assert fila["fecha"] == "2026-08-06"
    assert fila["po_number"] == "P00010"
    assert fila["source_id"] == "500"

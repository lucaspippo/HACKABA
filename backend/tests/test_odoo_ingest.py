import xmlrpc.client

import pytest

from core import odoo_ingest, store
from core.db import odoo_connections_repo, tenant as _tenant
from tests.conftest import limpiar_cuentas_db, limpiar_tabla_tenant


class _FakeCommon:
    def authenticate(self, db, user, pwd, ctx):
        return 7


class _FakeModels:
    def __init__(self):
        self.productos = [
            {"id": 1, "name": "Producto Ya Vinculado", "default_code": "SKU-1",
             "categ_id": [1, "General"], "list_price": 100.0, "qty_available": 50.0},
            {"id": 2, "name": "Producto Nuevo De Odoo", "default_code": "SKU-2",
             "categ_id": [1, "General"], "list_price": 200.0, "qty_available": 20.0},
        ]
        self.proveedores = [
            {"id": 3, "name": "Distribuidora del Sur", "vat": "30-11111111-1", "city": "Córdoba",
             "phone": "351-000-0000", "email": "ventas@distsur.example"},
            {"id": 4, "name": "Proveedor Genérico SRL", "vat": False, "city": False,
             "phone": False, "email": False},
        ]
        self.clientes = [
            {"id": 5, "name": "Cliente Ya Vinculado", "vat": "20-11111111-1", "city": "Rosario",
             "phone": "341-000-0000", "email": "cliente@example.com"},
            {"id": 6, "name": "Cliente Nuevo De Odoo", "vat": False, "city": False,
             "phone": False, "email": False},
        ]
        self.ordenes = [
            {"id": 10, "name": "P00010", "partner_id": [1, "Proveedor Ya Vinculado"],
             "state": "draft", "date_order": "2026-08-01", "amount_total": 100.0},
            {"id": 11, "name": "P00011", "partner_id": [1, "Proveedor Nuevo De Odoo"],
             "state": "purchase", "date_order": "2026-08-02", "amount_total": 200.0},
        ]
        self.lineas_orden = [
            {"id": 100, "order_id": [10, "P00010"], "product_id": [1, "Producto"],
             "name": "Producto", "product_qty": 1.0, "price_unit": 100.0},
            {"id": 101, "order_id": [11, "P00011"], "product_id": [1, "Producto"],
             "name": "Producto", "product_qty": 2.0, "price_unit": 100.0},
        ]

    def execute_kw(self, db, uid, pwd, model, method, args, kwargs):
        if model == "product.template":
            if method == "search":
                return [p["id"] for p in self.productos]
            if method == "read":
                return self.productos
        if model == "res.partner":
            if method == "search":
                domain = args[0]
                es_proveedores = any(d[0] == "supplier_rank" for d in domain)
                es_clientes = any(d[0] == "customer_rank" for d in domain)
                if es_proveedores:
                    return [p["id"] for p in self.proveedores]
                if es_clientes:
                    return [c["id"] for c in self.clientes]
                return []
            if method == "read":
                ids = set(args[0])
                if ids <= {p["id"] for p in self.proveedores}:
                    return self.proveedores
                return self.clientes
        if model == "purchase.order":
            if method == "search":
                return [o["id"] for o in self.ordenes]
            if method == "read":
                return self.ordenes
        if model == "purchase.order.line":
            if method == "search":
                return [l["id"] for l in self.lineas_orden]
            if method == "read":
                return self.lineas_orden
        raise NotImplementedError((model, method))


def _fake_server_proxy(url):
    return _FakeCommon() if url.endswith("/xmlrpc/2/common") else _FakeModels()


@pytest.fixture
def tenant_id():
    return _tenant.current_tenant_id()


@pytest.fixture(autouse=True)
def _setup(tenant_id, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    odoo_connections_repo.save(tenant_id, "https://x.odoo.com", "x", "admin", "good-key")
    store.resetear_actual()
    limpiar_cuentas_db()
    limpiar_tabla_tenant("purchase_orders")
    yield
    odoo_connections_repo.delete(tenant_id)
    store.resetear_actual()
    limpiar_cuentas_db()
    limpiar_tabla_tenant("purchase_orders")


def test_ingest_productos_primera_vez_todo_va_a_revision():
    r = odoo_ingest.ingest_productos(actor="test")
    assert r["actualizados"] == 0
    assert r["nuevos_para_revisar"] == 2
    assert r["batch_id"] is not None


def test_ingest_productos_segunda_vez_actualiza_sin_batch():
    r1 = odoo_ingest.ingest_productos(actor="test")
    from core import staging
    staging.integrar(r1["batch_id"], actor="test")

    r2 = odoo_ingest.ingest_productos(actor="test")
    assert r2["actualizados"] == 2
    assert r2["nuevos_para_revisar"] == 0
    assert r2["batch_id"] is None


def test_ingest_proveedores_primera_vez_todo_va_a_revision():
    r = odoo_ingest.ingest_proveedores(actor="test")
    assert r["nuevos_para_revisar"] >= 1
    assert r["batch_id"] is not None


def test_ingest_proveedores_segunda_vez_actualiza_sin_batch():
    r1 = odoo_ingest.ingest_proveedores(actor="test")
    from core import staging
    staging.integrar(r1["batch_id"], actor="test")

    r2 = odoo_ingest.ingest_proveedores(actor="test")
    assert r2["actualizados"] == 2
    assert r2["nuevos_para_revisar"] == 0
    assert r2["batch_id"] is None


def test_ingest_clientes_primera_vez_todo_va_a_revision():
    r = odoo_ingest.ingest_clientes(actor="test")
    assert r["nuevos_para_revisar"] >= 1
    assert r["batch_id"] is not None


def test_ingest_clientes_segunda_vez_actualiza_sin_batch():
    r1 = odoo_ingest.ingest_clientes(actor="test")
    from core import staging
    staging.integrar(r1["batch_id"], actor="test")

    r2 = odoo_ingest.ingest_clientes(actor="test")
    assert r2["actualizados"] == 2
    assert r2["nuevos_para_revisar"] == 0
    assert r2["batch_id"] is None


def test_ingest_ordenes_compra_primera_vez_todo_va_a_revision():
    r = odoo_ingest.ingest_ordenes_compra(actor="test")
    assert r["actualizados"] == 0
    assert r["nuevos_para_revisar"] == 2
    assert r["batch_id"] is not None


def test_ingest_ordenes_compra_segunda_vez_actualiza_sin_batch():
    r1 = odoo_ingest.ingest_ordenes_compra(actor="test")
    from core import staging
    staging.integrar(r1["batch_id"], actor="test")

    r2 = odoo_ingest.ingest_ordenes_compra(actor="test")
    assert r2["actualizados"] == 2
    assert r2["nuevos_para_revisar"] == 0
    assert r2["batch_id"] is None

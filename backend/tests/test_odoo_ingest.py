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


def _limpiar_proveedores() -> None:
    from core import esquema
    esquema.reemplazar_filas("proveedores", [])


@pytest.fixture(autouse=True)
def _setup(tenant_id, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    odoo_connections_repo.save(tenant_id, "https://x.odoo.com", "x", "admin", "good-key")
    store.resetear_actual()
    limpiar_cuentas_db()
    limpiar_tabla_tenant("purchase_orders")
    _limpiar_proveedores()
    yield
    odoo_connections_repo.delete(tenant_id)
    store.resetear_actual()
    limpiar_cuentas_db()
    limpiar_tabla_tenant("purchase_orders")
    _limpiar_proveedores()


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


def test_ingest_productos_mixto_actualiza_vinculado_y_stagea_nuevo():
    """One pulled row already linked, one brand new, in a single call — the
    two tiers are otherwise only exercised in separate calls."""
    store.upsert_desde_conector(
        {"descripcion": "Producto Ya Vinculado", "sku": "SKU-1", "stock": 1.0,
         "costo_iva": None, "pvp": 10.0, "source": "odoo", "source_id": "1"},
        actor="test")

    r = odoo_ingest.ingest_productos(actor="test")
    assert r["actualizados"] == 1
    assert r["nuevos_para_revisar"] == 1
    assert r["batch_id"] is not None
    vinculado = next(d for d in store.raw_actual() if d.get("source_id") == "1")
    assert vinculado["pvp"] == 100.0
    assert not any(d.get("source_id") == "2" for d in store.raw_actual())


def test_ingest_proveedores_primera_vez_todo_va_a_revision():
    r = odoo_ingest.ingest_proveedores(actor="test")
    assert r["actualizados"] == 0
    assert r["nuevos_para_revisar"] == 2
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
    assert r["actualizados"] == 0
    assert r["nuevos_para_revisar"] == 2
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


# --- C1: auto-upsert on re-sync must NOT overwrite dueño-edited,
# non-Odoo-owned fields (final whole-branch review, round 1) -----------------

def test_reingest_productos_no_pisa_costo_editado_por_el_dueño():
    """Repro: ingest -> integrate (link) -> dueño edits costo_iva -> re-sync
    the same linked product -> the dueño's cost must survive."""
    r1 = odoo_ingest.ingest_productos(actor="test")
    from core import staging
    staging.integrar(r1["batch_id"], actor="test")

    articulo = next(d for d in store.raw_actual() if d.get("source_id") == "1")
    store.actualizar_articulo(articulo["codigo"], {"costo_iva": 77.0}, actor="dueño")

    odoo_ingest.ingest_productos(actor="test")

    articulo = next(d for d in store.raw_actual() if d.get("source_id") == "1")
    assert articulo["costo_iva"] == 77.0
    # Odoo-owned fields still refresh normally.
    assert articulo["pvp"] == 100.0


def test_reingest_proveedores_no_pisa_contacto_y_notas_editados_por_el_dueño():
    """Repro: ingest -> integrate (link) -> dueño edits contacto/notas ->
    re-sync the same linked vendor -> the dueño's edits must survive."""
    from core import proveedores as proveedores_mod

    r1 = odoo_ingest.ingest_proveedores(actor="test")
    from core import staging
    staging.integrar(r1["batch_id"], actor="test")

    prov = next(p for p in proveedores_mod.listar() if p.get("source_id") == "3")
    proveedores_mod.actualizar(prov["id"], {"contacto": "Juan Pérez", "notas": "Paga a 30 días"},
                               actor="dueño")

    odoo_ingest.ingest_proveedores(actor="test")

    prov = next(p for p in proveedores_mod.listar() if p.get("source_id") == "3")
    assert prov["contacto"] == "Juan Pérez"
    assert prov["notas"] == "Paga a 30 días"
    # Odoo-owned fields still refresh normally.
    assert prov["cuit"] == "30-11111111-1"


def test_reingest_clientes_no_pisa_saldo_y_limite_editados_por_el_dueño(tenant_id):
    """Repro: ingest -> integrate (link) -> dueño edits balance/credit_limit
    (via the native write path, e.g. a payment) -> re-sync the same linked
    customer -> the dueño-owned accounting fields must survive."""
    from core import staging
    from core.db import customer_accounts_repo

    r1 = odoo_ingest.ingest_clientes(actor="test")
    staging.integrar(r1["batch_id"], actor="test")

    cuenta = next(c for c in customer_accounts_repo.list_accounts(tenant_id) if c["source_id"] == "5")
    cuenta["saldo"] = 1_234_000
    cuenta["limite_credito"] = 5_000_000
    customer_accounts_repo.upsert_account(tenant_id, cuenta)

    odoo_ingest.ingest_clientes(actor="test")

    cuenta = next(c for c in customer_accounts_repo.list_accounts(tenant_id) if c["source_id"] == "5")
    assert cuenta["saldo"] == 1_234_000
    assert cuenta["limite_credito"] == 5_000_000
    # Odoo-owned fields still refresh normally.
    assert cuenta["nombre"] == "Cliente Ya Vinculado"


# --- I2: PO ingestion writes must leave an audit trail -----------------------

def test_ingest_ordenes_compra_deja_rastro_de_auditoria():
    from core.audit import AuditLog

    r1 = odoo_ingest.ingest_ordenes_compra(actor="test")
    from core import staging
    staging.integrar(r1["batch_id"], actor="test")

    antes = len(AuditLog().list())
    odoo_ingest.ingest_ordenes_compra(actor="test")

    eventos = AuditLog().list()
    nuevos = eventos[antes:]
    conector = [e for e in nuevos if e["accion"] == "upsert_ordenes_compra_conector"]
    assert len(conector) == 1
    assert conector[0]["despues"]["actualizadas"] == 2
    assert sorted(conector[0]["despues"]["numeros"]) == ["P00010", "P00011"]


# --- I5: the auto-upsert tier must skip a row missing its required field,
# not write it through (same tolerance the staging tier already has) --------

def test_ingest_productos_omite_vinculado_sin_descripcion(monkeypatch):
    r1 = odoo_ingest.ingest_productos(actor="test")
    from core import staging
    staging.integrar(r1["batch_id"], actor="test")

    # Simulate the linked product losing its name in Odoo before the next
    # sync: a fresh fake whose "id": 1 row now carries an empty name.
    def _fake_server_proxy_sin_nombre(url):
        if url.endswith("/xmlrpc/2/common"):
            return _FakeCommon()
        fake = _FakeModels()
        fake.productos[0]["name"] = ""
        return fake

    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy_sin_nombre)

    r2 = odoo_ingest.ingest_productos(actor="test")
    assert r2["omitidos_malformados"] == 1
    # id 2 is also linked (from the first sync's staged batch) and unaffected
    # by the malformed row, so it still updates normally.
    assert r2["actualizados"] == 1
    articulo = next(d for d in store.raw_actual() if d.get("source_id") == "1")
    assert articulo["descripcion"] == "Producto Ya Vinculado"


def test_ingest_proveedores_omite_vinculado_sin_nombre(monkeypatch):
    from core import proveedores as proveedores_mod

    r1 = odoo_ingest.ingest_proveedores(actor="test")
    from core import staging
    staging.integrar(r1["batch_id"], actor="test")

    def _fake_server_proxy_sin_nombre(url):
        if url.endswith("/xmlrpc/2/common"):
            return _FakeCommon()
        fake = _FakeModels()
        fake.proveedores[0]["name"] = ""
        return fake

    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy_sin_nombre)

    r2 = odoo_ingest.ingest_proveedores(actor="test")
    assert r2["omitidos_malformados"] == 1
    assert r2["actualizados"] == 1
    prov = next(p for p in proveedores_mod.listar() if p.get("source_id") == "3")
    assert prov["nombre"] == "Distribuidora del Sur"


def test_ingest_clientes_omite_vinculado_sin_nombre(monkeypatch, tenant_id):
    from core.db import customer_accounts_repo

    r1 = odoo_ingest.ingest_clientes(actor="test")
    from core import staging
    staging.integrar(r1["batch_id"], actor="test")

    def _fake_server_proxy_sin_nombre(url):
        if url.endswith("/xmlrpc/2/common"):
            return _FakeCommon()
        fake = _FakeModels()
        fake.clientes[0]["name"] = ""
        return fake

    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy_sin_nombre)

    r2 = odoo_ingest.ingest_clientes(actor="test")
    assert r2["omitidos_malformados"] == 1
    assert r2["actualizados"] == 1
    cuenta = next(c for c in customer_accounts_repo.list_accounts(tenant_id) if c["source_id"] == "5")
    assert cuenta["nombre"] == "Cliente Ya Vinculado"


def test_ingest_ordenes_compra_omite_vinculada_sin_numero(monkeypatch, tenant_id):
    from core.db import purchase_orders_repo

    r1 = odoo_ingest.ingest_ordenes_compra(actor="test")
    from core import staging
    staging.integrar(r1["batch_id"], actor="test")

    def _fake_server_proxy_sin_numero(url):
        if url.endswith("/xmlrpc/2/common"):
            return _FakeCommon()
        fake = _FakeModels()
        fake.ordenes[0]["name"] = ""
        return fake

    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy_sin_numero)

    r2 = odoo_ingest.ingest_ordenes_compra(actor="test")
    assert r2["omitidos_malformados"] == 1
    assert r2["actualizados"] == 1
    orden = purchase_orders_repo.find_by_number(tenant_id, "P00010")
    assert orden is not None

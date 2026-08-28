import xmlrpc.client

import pytest

from core import odoo_ingest, store
from core.db import odoo_connections_repo, tenant as _tenant
from tests.conftest import limpiar_cuentas_db, limpiar_tabla_tenant
from tests.odoo_fakes import match_domain


class _FakeCommon:
    def authenticate(self, db, user, pwd, ctx):
        return 7


class _FakeModels:
    def __init__(self):
        self.productos = [
            {"id": 1, "name": "Producto Ya Vinculado", "default_code": "SKU-1",
             "categ_id": [1, "General"], "list_price": 100.0, "qty_available": 50.0,
             "standard_price": 80.0, "free_qty": 45.0, "incoming_qty": 5.0,
             "outgoing_qty": 0.0, "active": True},
            {"id": 2, "name": "Producto Nuevo De Odoo", "default_code": "SKU-2",
             "categ_id": [1, "General"], "list_price": 200.0, "qty_available": 20.0,
             "standard_price": 150.0, "free_qty": 20.0, "incoming_qty": 0.0,
             "outgoing_qty": 0.0, "active": True},
            {"id": 99, "name": "Fantasma Archivado", "default_code": "SKU-GHOST",
             "categ_id": [1, "General"], "list_price": 10.0, "qty_available": 3.0,
             "standard_price": 5.0, "free_qty": 3.0, "incoming_qty": 0.0,
             "outgoing_qty": 0.0, "active": False},
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
             "state": "draft", "date_order": "2026-08-01", "amount_total": 100.0,
             "currency_id": [1, "ARS"]},
            {"id": 11, "name": "P00011", "partner_id": [1, "Proveedor Nuevo De Odoo"],
             "state": "purchase", "date_order": "2026-08-02", "amount_total": 200.0,
             "currency_id": [1, "ARS"]},
        ]
        self.lineas_orden = [
            {"id": 100, "order_id": [10, "P00010"], "product_id": [1, "Producto"],
             "product_template_id": [1, "Producto Ya Vinculado"], "name": "Producto",
             "product_qty": 1.0, "price_unit": 100.0, "qty_received": 0.0},
            {"id": 101, "order_id": [11, "P00011"], "product_id": [1, "Producto"],
             "product_template_id": [1, "Producto Ya Vinculado"], "name": "Producto",
             "product_qty": 2.0, "price_unit": 100.0, "qty_received": 0.0},
        ]
        self.ordenes_venta = [
            {"id": 20, "name": "S00020", "partner_id": [1, "Cliente"],
             "state": "sale", "date_order": "2026-06-15 10:00:00", "amount_total": 200.0,
             "currency_id": [1, "ARS"], "pricelist_id": [10, "Minorista ARS"]},
            {"id": 21, "name": "S00021", "partner_id": [1, "Cliente"],
             "state": "draft", "date_order": "2026-06-20 09:00:00", "amount_total": 50.0,
             "currency_id": [1, "ARS"], "pricelist_id": [10, "Minorista ARS"]},
            {"id": 22, "name": "S00022", "partner_id": [1, "Cliente"],
             "state": "cancel", "date_order": "2026-05-01 09:00:00", "amount_total": 8.0,
             "currency_id": [1, "ARS"], "pricelist_id": [10, "Minorista ARS"]},
        ]
        self.lineas_venta = [
            {"id": 200, "order_id": [20, "S00020"], "product_id": [1, "Producto Ya Vinculado"],
             "product_template_id": [1, "Producto Ya Vinculado"], "name": "Producto Ya Vinculado",
             "product_uom_qty": 2.0, "price_unit": 100.0},
            {"id": 201, "order_id": [21, "S00021"], "product_id": [2, "Producto Nuevo De Odoo"],
             "product_template_id": [2, "Producto Nuevo De Odoo"], "name": "Producto Nuevo De Odoo",
             "product_uom_qty": 1.0, "price_unit": 50.0},
            {"id": 202, "order_id": [22, "S00022"], "product_id": [1, "Producto Ya Vinculado"],
             "product_template_id": [1, "Producto Ya Vinculado"], "name": "Producto Ya Vinculado",
             "product_uom_qty": 9.0, "price_unit": 8.0},
        ]
        self.variantes = [
            {"id": 1, "product_tmpl_id": [1, "Producto Ya Vinculado"], "free_qty": 45.0,
             "qty_available": 50.0, "incoming_qty": 5.0, "outgoing_qty": 0.0},
            {"id": 2, "product_tmpl_id": [2, "Producto Nuevo De Odoo"], "free_qty": 20.0,
             "qty_available": 20.0, "incoming_qty": 0.0, "outgoing_qty": 0.0},
            {"id": 99, "product_tmpl_id": [99, "Fantasma Archivado"], "free_qty": 3.0,
             "qty_available": 3.0, "incoming_qty": 0.0, "outgoing_qty": 0.0},
            {"id": 101, "product_tmpl_id": [1, "Producto Ya Vinculado"], "free_qty": 0.0,
             "qty_available": 0.0, "incoming_qty": 0.0, "outgoing_qty": 0.0},
        ]
        self.locations = [
            {"id": 8, "complete_name": "WH/Stock", "usage": "internal"},
            {"id": 9, "complete_name": "WH2/Stock", "usage": "internal"},
        ]
        self.lots = [
            {"id": 40, "name": "LOT-A", "expiration_date": "2026-12-01"},
        ]
        self.quants = [
            {"id": 30, "product_id": [101, "Producto Ya Vinculado"], "location_id": [8, "WH/Stock"],
             "quantity": 5.0, "lot_id": [40, "LOT-A"], "in_date": "2026-01-15 10:00:00",
             "inventory_quantity": 0, "inventory_quantity_set": False},
            {"id": 31, "product_id": [101, "Producto Ya Vinculado"], "location_id": [9, "WH2/Stock"],
             "quantity": 2.0, "lot_id": False, "in_date": "2025-01-01 10:00:00",
             "inventory_quantity": 1.0, "inventory_quantity_set": True},
            {"id": 32, "product_id": [101, "Producto Ya Vinculado"], "location_id": [8, "WH/Stock"],
             "quantity": 0.0, "lot_id": False, "in_date": "2026-02-01 10:00:00",
             "inventory_quantity": 0, "inventory_quantity_set": False},
        ]
        self.pickings = [
            {"id": 50, "name": "WH/IN/00012", "partner_id": [3, "Distribuidora del Sur"],
             "date_done": "2026-08-06 12:00:00", "scheduled_date": "2026-08-06 12:00:00",
             "origin": "P00011",
             "location_dest_id": [8, "WH/Stock"], "state": "done",
             "picking_type_code": "incoming", "backorder_id": False},
            {"id": 60, "name": "WH/OUT/00001", "partner_id": [5, "Cliente Ya Vinculado"],
             "date_done": "2026-06-16 12:00:00", "scheduled_date": "2026-06-16 12:00:00",
             "origin": "S00020", "location_dest_id": [8, "WH/Stock"], "state": "done",
             "picking_type_code": "outgoing", "backorder_id": False},
        ]
        self.moves = [
            {"id": 500, "picking_id": [50, "WH/IN/00012"],
             "product_id": [101, "Producto Ya Vinculado"], "quantity": 1.5,
             "product_uom_qty": 1.5,
             "location_dest_id": [8, "WH/Stock"],
             "purchase_line_id": [101, "P00011"], "sale_line_id": False, "state": "done"},
            {"id": 600, "picking_id": [60, "WH/OUT/00001"],
             "product_id": [1, "Producto Ya Vinculado"], "quantity": 2.0,
             "product_uom_qty": 2.0, "location_dest_id": [8, "WH/Stock"],
             "purchase_line_id": False, "sale_line_id": [200, "S00020"], "state": "done"},
        ]
        self.company = [{"id": 1, "name": "Demo", "currency_id": [1, "ARS"],
                         "country_id": [10, "Argentina"]}]
        self.rates = [
            {"id": 1, "name": "2024-08-01", "currency_id": [2, "USD"],
             "rate": 1 / 950, "inverse_company_rate": 950.0, "company_rate": 1 / 950},
            {"id": 2, "name": "2026-07-07", "currency_id": [2, "USD"],
             "rate": 1 / 1450, "inverse_company_rate": 1450.0, "company_rate": 1 / 1450},
        ]
        self.currencies = [{"id": 1, "name": "ARS", "symbol": "$"},
                           {"id": 2, "name": "USD", "symbol": "US$"}]
        self.pricelists = [
            {"id": 10, "name": "Minorista ARS", "currency_id": [1, "ARS"]},
            {"id": 11, "name": "Mayorista ARS", "currency_id": [1, "ARS"]},
        ]
        self.pl_items = []
        self.invoices = [
            {"id": 70, "name": "INV/2026/0001", "partner_id": [5, "Cliente Ya Vinculado"],
             "move_type": "out_invoice", "invoice_date": "2026-05-01",
             "invoice_date_due": "2026-05-15", "amount_total": 200.0,
             "amount_residual": 200.0, "amount_untaxed": 165.0,
             "payment_state": "not_paid", "currency_id": [1, "ARS"],
             "invoice_origin": "S00020", "state": "posted"},
            {"id": 71, "name": "BILL/2026/0001", "partner_id": [3, "Distribuidora del Sur"],
             "move_type": "in_invoice", "invoice_date": "2026-06-02",
             "invoice_date_due": "2026-06-16", "amount_total": 200.0,
             "amount_residual": 50.0, "amount_untaxed": 165.0,
             "payment_state": "partial", "currency_id": [1, "ARS"],
             "invoice_origin": "P00011", "state": "posted"},
        ]
        self.payments = [
            {"id": 80, "name": "PAY/2026/0001", "partner_id": [3, "Distribuidora del Sur"],
             "amount": 150.0, "date": "2026-06-10", "payment_type": "outbound",
             "partner_type": "supplier", "currency_id": [1, "ARS"],
             "ref": "BILL/2026/0001", "state": "posted"},
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
        if model == "sale.order":
            if method == "search":
                return [o["id"] for o in self.ordenes_venta]
            if method == "read":
                return self.ordenes_venta
        if model == "sale.order.line":
            if method == "search":
                return [l["id"] for l in self.lineas_venta]
            if method == "read":
                return self.lineas_venta
        if model == "stock.quant":
            if method == "search":
                return [q["id"] for q in self.quants if q["quantity"] != 0]
            if method == "read":
                want = set(args[0])
                return [q for q in self.quants if q["id"] in want]
        if model == "stock.location":
            if method == "read":
                want = set(args[0])
                return [x for x in self.locations if x["id"] in want]
        if model == "stock.lot":
            if method == "read":
                want = set(args[0])
                return [x for x in self.lots if x["id"] in want]
        if model == "product.product":
            if method == "search":
                domain = args[0] if args else []
                tmpl_in = None
                for term in domain:
                    if isinstance(term, (list, tuple)) and len(term) >= 3 and term[0] == "product_tmpl_id" and term[1] == "in":
                        tmpl_in = set(term[2])
                if tmpl_in is not None:
                    return [v["id"] for v in self.variantes if v["product_tmpl_id"][0] in tmpl_in]
                return [v["id"] for v in self.variantes]
            if method == "read":
                want = set(args[0])
                return [x for x in self.variantes if x["id"] in want]
        if model == "stock.picking":
            if method == "search":
                return [p["id"] for p in match_domain(self.pickings, args[0] if args else [])]
            if method == "read":
                want = set(args[0])
                return [p for p in self.pickings if p["id"] in want]
        if model == "stock.move":
            if method == "search":
                return [m["id"] for m in match_domain(self.moves, args[0] if args else [])]
            if method == "read":
                want = set(args[0])
                return [m for m in self.moves if m["id"] in want]
        if model == "res.company":
            if method == "search":
                return [c["id"] for c in self.company]
            if method == "read":
                return self.company
        if model == "res.currency.rate":
            if method == "search":
                return [r["id"] for r in self.rates]
            if method == "read":
                want = set(args[0])
                return [r for r in self.rates if r["id"] in want]
        if model == "res.currency":
            if method == "read":
                want = set(args[0])
                return [c for c in self.currencies if c["id"] in want]
        if model == "product.pricelist":
            if method == "search":
                return [p["id"] for p in self.pricelists]
            if method == "read":
                want = set(args[0])
                return [p for p in self.pricelists if p["id"] in want]
        if model == "product.pricelist.item":
            if method == "search":
                return [i["id"] for i in match_domain(self.pl_items, args[0] if args else [])]
            if method == "read":
                want = set(args[0])
                return [i for i in self.pl_items if i["id"] in want]
        if model == "account.move":
            if method == "search":
                return [m["id"] for m in match_domain(self.invoices, args[0] if args else [])]
            if method == "read":
                want = set(args[0])
                return [m for m in self.invoices if m["id"] in want]
        if model == "account.payment":
            if method == "search":
                return [p["id"] for p in match_domain(self.payments, args[0] if args else [])]
            if method == "read":
                want = set(args[0])
                return [p for p in self.payments if p["id"] in want]
        raise NotImplementedError((model, method))


def _fake_server_proxy(url):
    return _FakeCommon() if url.endswith("/xmlrpc/2/common") else _FakeModels()


@pytest.fixture
def tenant_id():
    return _tenant.current_tenant_id()


def _limpiar_proveedores() -> None:
    from core import esquema
    esquema.reemplazar_filas("proveedores", [])


def _limpiar_ventas() -> None:
    from core import esquema
    from core.db import blob_repo, tenant as _t
    esquema.reemplazar_filas("venta", [])
    blob_repo.save_blob("sales_validation", _t.current_tenant_id(), {"estado": "sin_datos"})


def _limpiar_deposito() -> None:
    from core import esquema
    esquema.reemplazar_filas("deposito", [])


def _limpiar_recepciones() -> None:
    from core import esquema
    esquema.reemplazar_filas("recepciones", [])


def _limpiar_contable() -> None:
    from core import esquema
    esquema.reemplazar_filas("entregas", [])
    esquema.reemplazar_filas("cuenta_corriente", [])
    esquema.reemplazar_filas("compras", [])
    esquema.reemplazar_filas("pagos", [])


@pytest.fixture(autouse=True)
def _setup(tenant_id, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    odoo_connections_repo.save(tenant_id, "https://x.odoo.com", "x", "admin", "good-key")
    store.resetear_actual()
    limpiar_cuentas_db()
    limpiar_tabla_tenant("purchase_orders")
    _limpiar_proveedores()
    _limpiar_ventas()
    _limpiar_deposito()
    _limpiar_recepciones()
    _limpiar_contable()
    yield
    odoo_connections_repo.delete(tenant_id)
    store.resetear_actual()
    limpiar_cuentas_db()
    limpiar_tabla_tenant("purchase_orders")
    _limpiar_proveedores()
    _limpiar_ventas()
    _limpiar_deposito()
    _limpiar_recepciones()
    _limpiar_contable()


def test_ingest_productos_primera_vez_todo_va_a_revision():
    r = odoo_ingest.ingest_productos(actor="test")
    assert r["actualizados"] == 0
    assert r["nuevos_para_revisar"] == 3
    assert r["batch_id"] is not None


def test_ingest_productos_segunda_vez_actualiza_sin_batch():
    r1 = odoo_ingest.ingest_productos(actor="test")
    from core import staging
    staging.integrar(r1["batch_id"], actor="test")

    r2 = odoo_ingest.ingest_productos(actor="test")
    assert r2["actualizados"] == 3
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
    assert r["nuevos_para_revisar"] == 2
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

def test_reingest_productos_odoo_pisa_costo_iva():
    """Odoo owns cost on linked products: a dueño edit of costo_iva is
    overwritten on the next sync with standard_price."""
    r1 = odoo_ingest.ingest_productos(actor="test")
    from core import staging
    staging.integrar(r1["batch_id"], actor="test")

    articulo = next(d for d in store.raw_actual() if d.get("source_id") == "1")
    store.actualizar_articulo(articulo["codigo"], {"costo_iva": 77.0}, actor="dueño")

    odoo_ingest.ingest_productos(actor="test")

    articulo = next(d for d in store.raw_actual() if d.get("source_id") == "1")
    assert articulo["costo_iva"] == 80.0
    assert articulo["pvp"] == 100.0
    assert articulo["free_qty"] == 45.0


def test_ingest_productos_archivado_con_stock_queda_anulado():
    r1 = odoo_ingest.ingest_productos(actor="test")
    from core import staging
    staging.integrar(r1["batch_id"], actor="test")
    ghost = next(d for d in store.raw_actual() if d.get("source_id") == "99")
    assert ghost["estado"] == "anulado"
    assert ghost["stock"] == 3.0


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
    # ids 2 and 99 are also linked (from the first sync's staged batch)
    assert r2["actualizados"] == 2
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


def test_ingest_ventas_primera_vez_solo_confirmadas_van_a_revision():
    r = odoo_ingest.ingest_ventas(actor="test")
    assert r["actualizados"] == 0
    assert r["nuevos_para_revisar"] == 1
    assert r["batch_id"] is not None


def test_ingest_ventas_segunda_vez_actualiza_y_confirma_montos():
    from core import staging, ventas, esquema
    r1 = odoo_ingest.ingest_ventas(actor="test")
    staging.integrar(r1["batch_id"], actor="test")
    assert ventas.montos_confirmados() is True
    filas = esquema.filas("venta")
    assert len(filas) == 1
    assert filas[0]["source_id"] == "200"
    assert filas[0]["cantidad"] == 2.0
    assert filas[0]["fecha"] == "2026-06-15"

    r2 = odoo_ingest.ingest_ventas(actor="test")
    assert r2["actualizados"] == 1
    assert r2["nuevos_para_revisar"] == 0
    assert r2["batch_id"] is None


def test_ingest_ventas_borra_linea_cancelada_y_conserva_csv(monkeypatch):
    from core import staging, esquema
    esquema.reemplazar_filas("venta", [
        {"fecha": "2026-01-01", "producto": "CSV", "cantidad": 1, "precio": 1},
    ])
    r1 = odoo_ingest.ingest_ventas(actor="test")
    staging.integrar(r1["batch_id"], actor="test")
    assert {f.get("source_id") for f in esquema.filas("venta")} == {None, "200"}

    def _fake_cancelada(url):
        if url.endswith("/xmlrpc/2/common"):
            return _FakeCommon()
        fake = _FakeModels()
        fake.ordenes_venta[0]["state"] = "cancel"
        return fake

    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_cancelada)
    odoo_ingest.ingest_ventas(actor="test")
    ids = {f.get("source_id") for f in esquema.filas("venta")}
    assert ids == {None}
    csv_row = next(f for f in esquema.filas("venta") if not f.get("source"))
    assert csv_row["producto"] == "CSV"


def _integrar_productos():
    from core import staging
    r = odoo_ingest.ingest_productos(actor="test")
    staging.integrar(r["batch_id"], actor="test")


def test_ingest_deposito_primera_vez_va_a_revision():
    _integrar_productos()
    r = odoo_ingest.ingest_deposito(actor="test")
    assert r["actualizados"] == 0
    assert r["nuevos_para_revisar"] == 2
    assert r["batch_id"] is not None


def test_ingest_deposito_segunda_vez_actualiza():
    from core import staging, esquema
    _integrar_productos()
    r1 = odoo_ingest.ingest_deposito(actor="test")
    staging.integrar(r1["batch_id"], actor="test")
    filas = esquema.filas("deposito")
    assert len(filas) == 2
    counted = next(f for f in filas if f["source_id"] == "31")
    assert counted["counted_qty"] == 1.0
    sin_conteo = next(f for f in filas if f["source_id"] == "30")
    assert "counted_qty" not in sin_conteo
    r2 = odoo_ingest.ingest_deposito(actor="test")
    assert r2["actualizados"] == 2
    assert r2["nuevos_para_revisar"] == 0


def test_ingest_recepciones_no_cambia_stock():
    from core import staging
    _integrar_productos()
    antes = {d["codigo"]: d.get("stock") for d in store.raw_actual()}
    r = odoo_ingest.ingest_recepciones(actor="test")
    staging.integrar(r["batch_id"], actor="test")
    despues = {d["codigo"]: d.get("stock") for d in store.raw_actual()}
    assert antes == despues


def test_ingest_recepciones_marca_po_recibida(tenant_id):
    from core import staging
    from core.db import purchase_orders_repo
    _integrar_productos()
    r_oc = odoo_ingest.ingest_ordenes_compra(actor="test")
    staging.integrar(r_oc["batch_id"], actor="test")
    po = purchase_orders_repo.find_by_number(tenant_id, "P00011")
    assert po["estado"] == "aprobada"
    r = odoo_ingest.ingest_recepciones(actor="test")
    staging.integrar(r["batch_id"], actor="test")
    po = purchase_orders_repo.find_by_number(tenant_id, "P00011")
    assert po["estado"] == "recibida"


def test_ingest_oc_purchase_parcial_queda_aprobada(monkeypatch, tenant_id):
    from core import staging
    from core.db import purchase_orders_repo

    def _fake_parcial(url):
        if url.endswith("/xmlrpc/2/common"):
            return _FakeCommon()
        fake = _FakeModels()
        fake.lineas_orden[1]["qty_received"] = 1.0
        return fake

    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_parcial)
    r = odoo_ingest.ingest_ordenes_compra(actor="test")
    staging.integrar(r["batch_id"], actor="test")
    po = purchase_orders_repo.find_by_number(tenant_id, "P00011")
    assert po["estado"] == "aprobada"
    po_draft = purchase_orders_repo.find_by_number(tenant_id, "P00010")
    assert po_draft["estado"] == "borrador"


def test_ingest_oc_purchase_fully_received_queda_recibida(monkeypatch, tenant_id):
    from core import staging
    from core.db import purchase_orders_repo

    def _fake_completa(url):
        if url.endswith("/xmlrpc/2/common"):
            return _FakeCommon()
        fake = _FakeModels()
        fake.lineas_orden[1]["qty_received"] = 2.0
        return fake

    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_completa)
    r = odoo_ingest.ingest_ordenes_compra(actor="test")
    staging.integrar(r["batch_id"], actor="test")
    po = purchase_orders_repo.find_by_number(tenant_id, "P00011")
    assert po["estado"] == "recibida"


def test_ingest_facturas_y_entregas(tenant_id):
    from core import esquema, staging
    r = odoo_ingest.ingest_facturas(actor="test")
    assert r["nuevos_para_revisar"] == 2
    staging.integrar(r["batch_id_facturas"], actor="test")
    staging.integrar(r["batch_id_compras"], actor="test")
    facturas = esquema.filas("cuenta_corriente")
    assert any(f["numero"] == "INV/2026/0001" and f["aging"] == "overdue" for f in facturas)
    bills = esquema.filas("compras")
    assert any(b["numero"] == "BILL/2026/0001" and b["residual"] == 50.0 for b in bills)
    r2 = odoo_ingest.ingest_entregas(actor="test")
    assert r2["nuevos_para_revisar"] == 1
    staging.integrar(r2["batch_id"], actor="test")
    entregas = esquema.filas("entregas")
    assert entregas[0]["so_number"] == "S00020"

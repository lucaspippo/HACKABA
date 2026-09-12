import xmlrpc.client

import pytest

from core import conectores
from core.db import odoo_connections_repo, tenant as _tenant
from tests.odoo_fakes import match_domain


class _FakeCommon:
    def authenticate(self, db, user, pwd, ctx):
        return False if pwd == "bad-key" else 7


class _FakeModels:
    def execute_kw(self, db, uid, pwd, model, method, args, kwargs):
        if model == "res.partner":
            domain = args[0] if method == "search" else None
            es_proveedores = domain is not None and any(d[0] == "supplier_rank" for d in domain)
            if method == "search":
                return [3, 4] if es_proveedores else [1, 2]
            if method == "read":
                ids = args[0]
                if 3 in ids or 4 in ids:
                    return [
                        {"id": 3, "name": "Distribuidora del Sur", "vat": "30-11111111-1", "city": "Córdoba",
                         "phone": "351-000-0000", "email": "ventas@distsur.example"},
                        {"id": 4, "name": "Proveedor Genérico SRL", "vat": False, "city": False,
                         "phone": False, "email": False},
                    ]
                return [
                    {"id": 1, "name": "Almacén Don Pérez", "vat": "20-12345678-9", "city": "Rosario",
                     "phone": "341-000-0000", "email": "perez@example.com",
                     "property_product_pricelist": [11, "Mayorista ARS"]},
                    {"id": 2, "name": "Kiosco La Esquina", "vat": False, "city": False,
                     "phone": False, "email": False,
                     "property_product_pricelist": [10, "Minorista ARS"]},
                ]
            raise NotImplementedError(method)
        if model == "product.template":
            if method == "search":
                return [1, 2, 3, 4]
            if method == "read":
                return [
                    {"id": 1, "name": "Laptop Pro 15\"", "default_code": "ELEC-001",
                     "categ_id": [4, "Electronics"], "list_price": 1200.0, "qty_available": 45.0,
                     "standard_price": 800.0, "free_qty": 40.0, "incoming_qty": 10.0,
                     "outgoing_qty": 5.0, "active": True},
                    {"id": 2, "name": "Standing Desk", "default_code": "FURN-002",
                     "categ_id": [5, "Furniture"], "list_price": 350.0, "qty_available": 0.0,
                     "standard_price": 200.0, "free_qty": 0.0, "incoming_qty": 0.0,
                     "outgoing_qty": 0.0, "active": True},
                    {"id": 3, "name": "Wholesale Pallet Wrap", "default_code": "WH-001",
                     "categ_id": [4, "Electronics"], "list_price": 0.0, "qty_available": 8.0,
                     "standard_price": 400.0, "free_qty": 8.0, "incoming_qty": 0.0,
                     "outgoing_qty": 0.0, "active": True},
                    {"id": 4, "name": "Unpriced Cable", "default_code": "product_unpriced_cable",
                     "categ_id": [4, "Electronics"], "list_price": 0.0, "qty_available": 1.0,
                     "standard_price": 10.0, "free_qty": 1.0, "incoming_qty": 0.0,
                     "outgoing_qty": 0.0, "active": True},
                ]
            raise NotImplementedError(method)
        if model == "purchase.order":
            if method == "search":
                return [10, 11, 12]
            if method == "read":
                return [
                    {"id": 10, "name": "P00010", "partner_id": [3, "Distribuidora del Sur"],
                     "state": "purchase", "date_order": "2026-08-05 10:00:00", "amount_total": 3800.0,
                     "currency_id": [1, "ARS"]},
                    {"id": 11, "name": "P00011", "partner_id": [4, "Proveedor Genérico SRL"],
                     "state": "draft", "date_order": "2026-08-20 09:00:00", "amount_total": 810.0,
                     "currency_id": [1, "ARS"]},
                    {"id": 12, "name": "P00012", "partner_id": [5, "Umbrella Supplies"],
                     "state": "purchase", "date_order": "2026-06-01 10:00:00", "amount_total": 100.0,
                     "currency_id": [2, "USD"]},
                ]
            raise NotImplementedError(method)
        if model == "purchase.order.line":
            if method == "search":
                return [100, 101, 102, 103]
            if method == "read":
                return [
                    {"id": 100, "order_id": [10, "P00010"], "product_id": [1, "Office Chair Ergo"],
                     "product_template_id": [1, "Office Chair Ergo"], "name": "Office Chair Ergo",
                     "product_qty": 20.0, "price_unit": 120.0, "qty_received": 15.0},
                    {"id": 101, "order_id": [10, "P00010"], "product_id": [2, "Filing Cabinet"],
                     "product_template_id": [2, "Filing Cabinet"], "name": "Filing Cabinet",
                     "product_qty": 10.0, "price_unit": 140.0, "qty_received": 0.0},
                    {"id": 102, "order_id": [11, "P00011"], "product_id": False,
                     "product_template_id": False, "name": "Printer Paper A4 (Box)",
                     "product_qty": 100.0, "price_unit": 6.5, "qty_received": 0.0},
                    {"id": 103, "order_id": [12, "P00012"], "product_id": [1, "Laptop Pro 15\""],
                     "product_template_id": [1, "Laptop Pro 15\""], "name": "Laptop Pro 15\"",
                     "product_qty": 1.0, "price_unit": 100.0, "qty_received": 0.0},
                ]
            raise NotImplementedError(method)
        if model == "sale.order":
            if method == "search":
                return [20, 21, 22]
            if method == "read":
                return [
                    {"id": 20, "name": "S00020", "partner_id": [1, "Almacén Don Pérez"],
                     "state": "sale", "date_order": "2026-06-15 10:00:00", "amount_total": 2500.0,
                     "currency_id": [2, "USD"], "pricelist_id": [12, "Minorista USD"]},
                    {"id": 21, "name": "S00021", "partner_id": [2, "Kiosco La Esquina"],
                     "state": "draft", "date_order": "2026-06-20 09:00:00", "amount_total": 25.0,
                     "currency_id": [1, "ARS"], "pricelist_id": [10, "Minorista ARS"]},
                    {"id": 22, "name": "S00022", "partner_id": [1, "Almacén Don Pérez"],
                     "state": "cancel", "date_order": "2026-05-01 09:00:00", "amount_total": 8.0,
                     "currency_id": [1, "ARS"], "pricelist_id": [11, "Mayorista ARS"]},
                ]
            raise NotImplementedError(method)
        if model == "sale.order.line":
            if method == "search":
                return [200, 201, 202]
            if method == "read":
                return [
                    {"id": 200, "order_id": [20, "S00020"], "product_id": [1, "Laptop Pro 15\""],
                     "product_template_id": [1, "Laptop Pro 15\""], "name": "Laptop Pro 15\"",
                     "product_uom_qty": 2.0, "price_unit": 1200.0, "qty_delivered": 1.0},
                    {"id": 201, "order_id": [21, "S00021"], "product_id": [2, "Wireless Mouse"],
                     "product_template_id": [2, "Wireless Mouse"], "name": "Wireless Mouse",
                     "product_uom_qty": 1.0, "price_unit": 25.0, "qty_delivered": 0.0},
                    {"id": 202, "order_id": [22, "S00022"], "product_id": [3, "Printer Paper A4 (Box)"],
                     "product_template_id": [3, "Printer Paper A4 (Box)"], "name": "Printer Paper A4 (Box)",
                     "product_uom_qty": 20.0, "price_unit": 8.0, "qty_delivered": 0.0},
                ]
            raise NotImplementedError(method)
        if model == "stock.quant":
            quants = [
                {"id": 30, "product_id": [101, "Laptop Pro 15\""], "location_id": [8, "WH/Stock"],
                 "quantity": 5.0, "lot_id": [40, "LOT-A"], "in_date": "2026-01-15 10:00:00",
                 "inventory_quantity": 0, "inventory_quantity_set": False},
                {"id": 31, "product_id": [101, "Laptop Pro 15\""], "location_id": [9, "WH2/Stock"],
                 "quantity": 2.0, "lot_id": False, "in_date": "2025-01-01 10:00:00",
                 "inventory_quantity": 1.0, "inventory_quantity_set": True},
                {"id": 32, "product_id": [101, "Laptop Pro 15\""], "location_id": [8, "WH/Stock"],
                 "quantity": 0.0, "lot_id": False, "in_date": "2026-02-01 10:00:00",
                 "inventory_quantity": 0, "inventory_quantity_set": False},
            ]
            if method == "search":
                return [q["id"] for q in quants if q["quantity"] != 0]
            if method == "read":
                want = set(args[0])
                return [q for q in quants if q["id"] in want]
            raise NotImplementedError(method)
        if model == "stock.location":
            if method == "read":
                locs = [
                    {"id": 8, "complete_name": "WH/Stock", "usage": "internal"},
                    {"id": 9, "complete_name": "WH2/Stock", "usage": "internal"},
                ]
                want = set(args[0])
                return [x for x in locs if x["id"] in want]
            raise NotImplementedError(method)
        if model == "stock.lot":
            if method == "read":
                return [{"id": 40, "name": "LOT-A", "expiration_date": "2026-12-01"}]
            raise NotImplementedError(method)
        if model == "product.product":
            variants = [
                {"id": 1, "product_tmpl_id": [1, "Laptop Pro 15\""], "free_qty": 40.0,
                 "qty_available": 45.0, "incoming_qty": 10.0, "outgoing_qty": 5.0},
                {"id": 2, "product_tmpl_id": [2, "Standing Desk"], "free_qty": 0.0,
                 "qty_available": 0.0, "incoming_qty": 0.0, "outgoing_qty": 0.0},
                {"id": 101, "product_tmpl_id": [1, "Laptop Pro 15\""], "free_qty": 0.0,
                 "qty_available": 0.0, "incoming_qty": 0.0, "outgoing_qty": 0.0},
                {"id": 3, "product_tmpl_id": [3, "Wholesale Pallet Wrap"], "free_qty": 8.0,
                 "qty_available": 8.0, "incoming_qty": 0.0, "outgoing_qty": 0.0},
                {"id": 4, "product_tmpl_id": [4, "Unpriced Cable"], "free_qty": 1.0,
                 "qty_available": 1.0, "incoming_qty": 0.0, "outgoing_qty": 0.0},
            ]
            if method == "search":
                domain = args[0] if args else []
                tmpl_in = None
                for term in domain:
                    if isinstance(term, (list, tuple)) and len(term) >= 3 and term[0] == "product_tmpl_id" and term[1] == "in":
                        tmpl_in = set(term[2])
                if tmpl_in is not None:
                    return [v["id"] for v in variants if v["product_tmpl_id"][0] in tmpl_in]
                return [v["id"] for v in variants]
            if method == "read":
                want = set(args[0])
                return [v for v in variants if v["id"] in want]
            raise NotImplementedError(method)
        if model == "stock.picking":
            pickings = [
                {"id": 50, "name": "WH/IN/00012",
                 "partner_id": [3, "Distribuidora del Sur"],
                 "date_done": "2026-08-06 12:00:00", "scheduled_date": "2026-08-06 12:00:00",
                 "origin": "P00010", "location_dest_id": [8, "WH/Stock"], "state": "done",
                 "picking_type_code": "incoming", "backorder_id": False},
                {"id": 51, "name": "WH/IN/00013",
                 "partner_id": [3, "Distribuidora del Sur"],
                 "date_done": False, "scheduled_date": "2026-08-10 12:00:00",
                 "origin": "P00010", "location_dest_id": [8, "WH/Stock"], "state": "assigned",
                 "picking_type_code": "incoming", "backorder_id": [50, "WH/IN/00012"]},
                {"id": 60, "name": "WH/OUT/00001",
                 "partner_id": [1, "Almacén Don Pérez"],
                 "date_done": "2026-06-16 12:00:00", "scheduled_date": "2026-06-16 12:00:00",
                 "origin": "S00020", "location_dest_id": [8, "WH/Stock"], "state": "done",
                 "picking_type_code": "outgoing", "backorder_id": False},
                {"id": 61, "name": "WH/OUT/00002",
                 "partner_id": [1, "Almacén Don Pérez"],
                 "date_done": False, "scheduled_date": "2026-06-20 12:00:00",
                 "origin": "S00020", "location_dest_id": [8, "WH/Stock"], "state": "assigned",
                 "picking_type_code": "outgoing", "backorder_id": [60, "WH/OUT/00001"]},
            ]
            if method == "search":
                return [p["id"] for p in match_domain(pickings, args[0] if args else [])]
            if method == "read":
                want = set(args[0])
                return [p for p in pickings if p["id"] in want]
            raise NotImplementedError(method)
        if model == "stock.move":
            moves = [
                {"id": 500, "picking_id": [50, "WH/IN/00012"],
                 "product_id": [101, "Laptop Pro 15\""], "quantity": 15.0, "product_uom_qty": 15.0,
                 "location_dest_id": [8, "WH/Stock"],
                 "purchase_line_id": [100, "P00010"], "sale_line_id": False, "state": "done"},
                {"id": 501, "picking_id": [51, "WH/IN/00013"],
                 "product_id": [101, "Laptop Pro 15\""], "quantity": 0.0, "product_uom_qty": 5.0,
                 "location_dest_id": [8, "WH/Stock"],
                 "purchase_line_id": [100, "P00010"], "sale_line_id": False, "state": "assigned"},
                {"id": 600, "picking_id": [60, "WH/OUT/00001"],
                 "product_id": [1, "Laptop Pro 15\""], "quantity": 1.0, "product_uom_qty": 1.0,
                 "location_dest_id": [8, "WH/Stock"],
                 "purchase_line_id": False, "sale_line_id": [200, "S00020"], "state": "done"},
                {"id": 601, "picking_id": [61, "WH/OUT/00002"],
                 "product_id": [1, "Laptop Pro 15\""], "quantity": 0.0, "product_uom_qty": 1.0,
                 "location_dest_id": [8, "WH/Stock"],
                 "purchase_line_id": False, "sale_line_id": [200, "S00020"], "state": "assigned"},
            ]
            if method == "search":
                return [m["id"] for m in match_domain(moves, args[0] if args else [])]
            if method == "read":
                want = set(args[0])
                return [m for m in moves if m["id"] in want]
            raise NotImplementedError(method)
        if model == "res.company":
            if method == "search":
                return [1]
            if method == "read":
                return [{"id": 1, "name": "Distribuidora del Litoral",
                         "currency_id": [1, "ARS"], "country_id": [10, "Argentina"]}]
        if model == "res.currency.rate":
            rates = [
                {"id": 1, "name": "2024-08-01", "currency_id": [2, "USD"],
                 "rate": 1 / 950, "inverse_company_rate": 950.0, "company_rate": 1 / 950},
                {"id": 2, "name": "2026-07-07", "currency_id": [2, "USD"],
                 "rate": 1 / 1450, "inverse_company_rate": 1450.0, "company_rate": 1 / 1450},
            ]
            if method == "search":
                return [r["id"] for r in rates]
            if method == "read":
                want = set(args[0])
                return [r for r in rates if r["id"] in want]
        if model == "res.currency":
            if method == "read":
                rows = [{"id": 1, "name": "ARS", "symbol": "$"},
                        {"id": 2, "name": "USD", "symbol": "US$"}]
                want = set(args[0])
                return [r for r in rows if r["id"] in want]
        if model == "product.pricelist":
            lists = [
                {"id": 10, "name": "Minorista ARS", "currency_id": [1, "ARS"]},
                {"id": 11, "name": "Mayorista ARS", "currency_id": [1, "ARS"]},
                {"id": 12, "name": "Minorista USD", "currency_id": [2, "USD"]},
                {"id": 13, "name": "Mayorista USD", "currency_id": [2, "USD"]},
            ]
            if method == "search":
                return [p["id"] for p in lists]
            if method == "read":
                want = set(args[0])
                return [p for p in lists if p["id"] in want]
        if model == "product.pricelist.item":
            items = [
                {"id": 100, "pricelist_id": [11, "Mayorista ARS"], "applied_on": "1_product",
                 "compute_price": "fixed", "fixed_price": 8500.0, "percent_price": 0,
                 "price_discount": 0, "categ_id": False,
                 "product_tmpl_id": [3, "Wholesale Pallet Wrap"], "product_id": False,
                 "min_quantity": 0},
                {"id": 101, "pricelist_id": [12, "Minorista USD"], "applied_on": "1_product",
                 "compute_price": "fixed", "fixed_price": 890.0, "percent_price": 0,
                 "price_discount": 0, "categ_id": False,
                 "product_tmpl_id": [1, "Laptop Pro 15\""], "product_id": False,
                 "min_quantity": 0},
                {"id": 102, "pricelist_id": [11, "Mayorista ARS"], "applied_on": "2_product_category",
                 "compute_price": "formula", "fixed_price": False, "percent_price": 0,
                 "price_discount": 15.0, "categ_id": [5, "Furniture"],
                 "product_tmpl_id": False, "product_id": False, "min_quantity": 0},
            ]
            if method == "search":
                return [i["id"] for i in match_domain(items, args[0] if args else [])]
            if method == "read":
                want = set(args[0])
                return [i for i in items if i["id"] in want]
        if model == "account.move":
            moves = [
                {"id": 70, "name": "INV/2026/0001", "partner_id": [1, "Almacén Don Pérez"],
                 "move_type": "out_invoice", "invoice_date": "2026-05-01",
                 "invoice_date_due": "2026-05-15", "amount_total": 2500.0,
                 "amount_residual": 0.0, "amount_untaxed": 2066.0,
                 "payment_state": "paid", "currency_id": [1, "ARS"],
                 "invoice_origin": "S00019", "state": "posted"},
                {"id": 71, "name": "INV/2026/0002", "partner_id": [1, "Almacén Don Pérez"],
                 "move_type": "out_invoice", "invoice_date": "2026-07-01",
                 "invoice_date_due": "2026-08-01", "amount_total": 890.0,
                 "amount_residual": 890.0, "amount_untaxed": 736.0,
                 "payment_state": "not_paid", "currency_id": [2, "USD"],
                 "invoice_origin": "S00020", "state": "posted"},
                {"id": 72, "name": "BILL/2026/0001", "partner_id": [5, "Umbrella Supplies"],
                 "move_type": "in_invoice", "invoice_date": "2026-06-02",
                 "invoice_date_due": "2026-06-16", "amount_total": 100.0,
                 "amount_residual": 40.0, "amount_untaxed": 82.0,
                 "payment_state": "partial", "currency_id": [2, "USD"],
                 "invoice_origin": "P00012", "state": "posted"},
            ]
            if method == "search":
                return [m["id"] for m in match_domain(moves, args[0] if args else [])]
            if method == "read":
                want = set(args[0])
                return [m for m in moves if m["id"] in want]
        if model == "account.payment":
            pays = [
                {"id": 80, "name": "PAY/2026/0001", "partner_id": [5, "Umbrella Supplies"],
                 "amount": 60.0, "date": "2026-06-10", "payment_type": "outbound",
                 "partner_type": "supplier", "currency_id": [2, "USD"],
                 "ref": "BILL/2026/0001", "state": "posted"},
            ]
            if method == "search":
                return [p["id"] for p in match_domain(pays, args[0] if args else [])]
            if method == "read":
                want = set(args[0])
                return [p for p in pays if p["id"] in want]
        raise NotImplementedError(model)


def _fake_server_proxy(url):
    return _FakeCommon() if url.endswith("/xmlrpc/2/common") else _FakeModels()


@pytest.fixture
def tenant_id():
    return _tenant.current_tenant_id()


@pytest.fixture(autouse=True)
def _sin_conexion_odoo(tenant_id):
    odoo_connections_repo.delete(tenant_id)
    yield
    odoo_connections_repo.delete(tenant_id)


def test_probar_conexion_ok(monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    conectores.probar_conexion_odoo("https://x.odoo.com", "x", "admin", "good-key")  # no lanza


def test_probar_conexion_credenciales_invalidas(monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    with pytest.raises(ValueError):
        conectores.probar_conexion_odoo("https://x.odoo.com", "x", "admin", "bad-key")


def test_disponibles_reporta_pendiente_sin_conexion(tenant_id):
    nombres = {c["nombre"]: c for c in conectores.disponibles(tenant_id)}
    assert nombres["odoo"]["estado"] == "pendiente"


def test_disponibles_reporta_activo_con_conexion(tenant_id):
    odoo_connections_repo.save(tenant_id, "https://x.odoo.com", "x", "admin", "good-key")
    nombres = {c["nombre"]: c for c in conectores.disponibles(tenant_id)}
    assert nombres["odoo"]["estado"] == "activo"


def test_pull_data_sin_conexion_configurada(tenant_id):
    with pytest.raises(ValueError):
        conectores.ConectorOdoo(tenant_id).pull_data()


def test_pull_data_trae_contactos_cliente(tenant_id, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    odoo_connections_repo.save(tenant_id, "https://x.odoo.com", "x", "admin", "good-key")
    r = conectores.ConectorOdoo(tenant_id).pull_data()
    assert r["origen"] == "odoo"
    assert r["modulo"] == "res.partner"
    assert r["total"] == 2
    assert r["clientes"][0]["nombre"] == "Almacén Don Pérez"
    assert r["clientes"][0]["cuit"] == "20-12345678-9"
    assert r["clientes"][0]["pricelist"] == "Mayorista ARS"
    # False (Odoo's "sin dato") nunca se filtra tal cual al frontend
    assert r["clientes"][1]["cuit"] == ""


def test_pull_data_credenciales_guardadas_invalidas(tenant_id, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    odoo_connections_repo.save(tenant_id, "https://x.odoo.com", "x", "admin", "bad-key")
    with pytest.raises(ValueError):
        conectores.ConectorOdoo(tenant_id).pull_data()


def test_push_action_es_solo_lectura(tenant_id):
    r = conectores.ConectorOdoo(tenant_id).push_action({})
    assert r["ok"] is False


def test_pull_productos_sin_conexion_configurada(tenant_id):
    with pytest.raises(ValueError):
        conectores.ConectorOdoo(tenant_id).pull_productos()


def test_pull_productos_trae_catalogo(tenant_id, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    odoo_connections_repo.save(tenant_id, "https://x.odoo.com", "x", "admin", "good-key")
    r = conectores.ConectorOdoo(tenant_id).pull_productos()
    assert r["origen"] == "odoo"
    assert r["modulo"] == "product.template"
    assert r["total"] == 4
    assert r["productos"][0]["codigo"] == "ELEC-001"
    assert r["productos"][0]["categoria"] == "Electronics"
    assert r["productos"][0]["stock"] == 45.0
    assert r["productos"][0]["costo"] == 800.0
    assert r["productos"][0]["free_qty"] == 40.0
    assert r["productos"][0]["incoming_qty"] == 10.0
    assert r["productos"][0]["outgoing_qty"] == 5.0
    assert r["productos"][0]["activo"] is True
    # sin stock (0) sigue siendo un número, no se pierde en el mapeo
    assert r["productos"][1]["stock"] == 0.0


def test_pull_productos_credenciales_guardadas_invalidas(tenant_id, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    odoo_connections_repo.save(tenant_id, "https://x.odoo.com", "x", "admin", "bad-key")
    with pytest.raises(ValueError):
        conectores.ConectorOdoo(tenant_id).pull_productos()


def test_pull_proveedores_sin_conexion_configurada(tenant_id):
    with pytest.raises(ValueError):
        conectores.ConectorOdoo(tenant_id).pull_proveedores()


def test_pull_proveedores_trae_contactos_proveedor(tenant_id, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    odoo_connections_repo.save(tenant_id, "https://x.odoo.com", "x", "admin", "good-key")
    r = conectores.ConectorOdoo(tenant_id).pull_proveedores()
    assert r["origen"] == "odoo"
    assert r["modulo"] == "res.partner"
    assert r["total"] == 2
    assert r["proveedores"][0]["nombre"] == "Distribuidora del Sur"
    assert r["proveedores"][0]["cuit"] == "30-11111111-1"
    assert r["proveedores"][1]["cuit"] == ""


def test_pull_proveedores_credenciales_guardadas_invalidas(tenant_id, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    odoo_connections_repo.save(tenant_id, "https://x.odoo.com", "x", "admin", "bad-key")
    with pytest.raises(ValueError):
        conectores.ConectorOdoo(tenant_id).pull_proveedores()


def test_pull_ordenes_compra_sin_conexion_configurada(tenant_id):
    with pytest.raises(ValueError):
        conectores.ConectorOdoo(tenant_id).pull_ordenes_compra()


def test_pull_ordenes_compra_trae_ordenes_con_items(tenant_id, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    odoo_connections_repo.save(tenant_id, "https://x.odoo.com", "x", "admin", "good-key")
    r = conectores.ConectorOdoo(tenant_id).pull_ordenes_compra()
    assert r["origen"] == "odoo"
    assert r["modulo"] == "purchase.order"
    assert r["total"] == 3
    orden_1 = next(o for o in r["ordenes"] if o["numero"] == "P00010")
    assert orden_1["proveedor"] == "Distribuidora del Sur"
    assert orden_1["estado"] == "confirmada"
    assert len(orden_1["items"]) == 2
    assert orden_1["items"][0]["producto"] == "Office Chair Ergo"
    orden_2 = next(o for o in r["ordenes"] if o["numero"] == "P00011")
    assert orden_2["estado"] == "borrador"
    # línea sin product_id resuelto (product_id=False) cae al nombre de la línea
    assert orden_2["items"][0]["producto"] == "Printer Paper A4 (Box)"


def test_pull_ordenes_compra_credenciales_guardadas_invalidas(tenant_id, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    odoo_connections_repo.save(tenant_id, "https://x.odoo.com", "x", "admin", "bad-key")
    with pytest.raises(ValueError):
        conectores.ConectorOdoo(tenant_id).pull_ordenes_compra()


def test_pull_ordenes_venta_sin_conexion_configurada(tenant_id):
    with pytest.raises(ValueError):
        conectores.ConectorOdoo(tenant_id).pull_ordenes_venta()


def test_pull_ordenes_venta_trae_ordenes_con_items(tenant_id, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    odoo_connections_repo.save(tenant_id, "https://x.odoo.com", "x", "admin", "good-key")
    r = conectores.ConectorOdoo(tenant_id).pull_ordenes_venta()
    assert r["origen"] == "odoo"
    assert r["modulo"] == "sale.order"
    assert r["total"] == 3
    confirmada = next(o for o in r["ordenes"] if o["numero"] == "S00020")
    assert confirmada["estado"] == "confirmada"
    assert confirmada["cliente"] == "Almacén Don Pérez"
    assert len(confirmada["items"]) == 1
    assert confirmada["items"][0]["id"] == 200
    assert confirmada["items"][0]["product_tmpl_id"] == 1
    assert confirmada["items"][0]["cantidad"] == 2.0
    borrador = next(o for o in r["ordenes"] if o["numero"] == "S00021")
    assert borrador["estado"] == "borrador"
    cancelada = next(o for o in r["ordenes"] if o["numero"] == "S00022")
    assert cancelada["estado"] == "cancelada"


def test_pull_deposito_omite_qty_cero_y_resuelve_lote(tenant_id, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    odoo_connections_repo.save(tenant_id, "https://x.odoo.com", "x", "admin", "good-key")
    r = conectores.ConectorOdoo(tenant_id).pull_deposito()
    assert r["modulo"] == "stock.quant"
    assert r["total"] == 2
    ids = {q["id"] for q in r["quants"]}
    assert ids == {30, 31}
    q30 = next(q for q in r["quants"] if q["id"] == 30)
    assert q30["ubicacion"] == "WH/Stock"
    assert q30["lote"] == "LOT-A"
    assert q30["vencimiento"] == "2026-12-01"
    assert q30["product_tmpl_id"] == 1
    assert "counted_qty" not in q30
    q31 = next(q for q in r["quants"] if q["id"] == 31)
    assert q31["counted_qty"] == 1.0
    assert q31["in_date"] == "2025-01-01"


def test_pull_recepciones_incluye_backorder_abierto(tenant_id, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    odoo_connections_repo.save(tenant_id, "https://x.odoo.com", "x", "admin", "good-key")
    r = conectores.ConectorOdoo(tenant_id).pull_recepciones()
    assert r["modulo"] == "stock.picking"
    assert r["total"] == 2
    rec = next(x for x in r["recepciones"] if x["id"] == 500)
    assert rec["origen"] == "WH/IN/00012"
    assert rec["po_number"] == "P00010"
    assert rec["cantidad"] == 15.0
    assert rec["product_tmpl_id"] == 1
    pending = next(x for x in r["recepciones"] if x["id"] == 501)
    assert pending["pendiente"] is True
    assert pending["open_backorder"] is True
    assert pending["es_backorder"] is True


def test_pull_productos_wholesale_only_vs_needs_pricing(tenant_id, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    odoo_connections_repo.save(tenant_id, "https://x.odoo.com", "x", "admin", "good-key")
    r = conectores.ConectorOdoo(tenant_id).pull_productos()
    by_code = {p["codigo"]: p for p in r["productos"]}
    wholesale = by_code["WH-001"]
    assert wholesale["pricing_status"] == "wholesale_only"
    assert wholesale["precio"] == 8500.0
    assert wholesale["precio_lista"] == 0.0
    unpriced = by_code["product_unpriced_cable"]
    assert unpriced["pricing_status"] == "needs_pricing"
    assert unpriced["precio"] is None
    laptop = by_code["ELEC-001"]
    usd = next(e for e in laptop["precios_pricelist"] if e["currency"] == "USD")
    assert usd["price"] == 890.0
    assert usd["origin"] == "fixed"
    assert usd["price"] != laptop["precio_lista"]


def test_pull_ordenes_honours_currency_and_dated_fx(tenant_id, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    odoo_connections_repo.save(tenant_id, "https://x.odoo.com", "x", "admin", "good-key")
    compras = conectores.ConectorOdoo(tenant_id).pull_ordenes_compra()
    usd_po = next(o for o in compras["ordenes"] if o["numero"] == "P00012")
    assert usd_po["currency"] == "USD"
    # 2026-06-01 uses the 950 ARS/USD point, not the later 1450.
    assert usd_po["total_company"] == 95000.0
    ars_po = next(o for o in compras["ordenes"] if o["numero"] == "P00010")
    assert ars_po["currency"] == "ARS"
    assert ars_po["total_company"] == 3800.0
    assert ars_po["open_backorder"] is True
    assert ars_po["fulfillment"] == "partial"

    ventas = conectores.ConectorOdoo(tenant_id).pull_ordenes_venta()
    usd_so = next(o for o in ventas["ordenes"] if o["numero"] == "S00020")
    assert usd_so["currency"] == "USD"
    assert usd_so["total_company"] == 2_375_000.0
    assert usd_so["items"][0]["precio_company"] == 1_140_000.0
    assert usd_so["open_backorder"] is True
    assert usd_so["fulfillment"] == "partial"


def test_pull_entregas_incluye_backorder_abierto(tenant_id, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    odoo_connections_repo.save(tenant_id, "https://x.odoo.com", "x", "admin", "good-key")
    r = conectores.ConectorOdoo(tenant_id).pull_entregas()
    assert r["total"] == 2
    pending = next(x for x in r["entregas"] if x["id"] == 601)
    assert pending["pendiente"] is True
    assert pending["open_backorder"] is True
    assert pending["cliente"] == "Almacén Don Pérez"


def test_pull_facturas_aging_and_residual(tenant_id, monkeypatch):
    monkeypatch.setenv("POLPILOT_DEMO_TODAY", "2026-07-07")
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    odoo_connections_repo.save(tenant_id, "https://x.odoo.com", "x", "admin", "good-key")
    r = conectores.ConectorOdoo(tenant_id).pull_facturas()
    assert r["as_of"] == "2026-07-20"
    by_num = {f["numero"]: f for f in r["facturas"]}
    assert by_num["INV/2026/0001"]["aging"] == "paid"
    assert by_num["INV/2026/0002"]["aging"] == "open"
    assert by_num["INV/2026/0002"]["currency"] == "USD"
    bill = by_num["BILL/2026/0001"]
    assert bill["aging"] == "overdue"
    assert bill["residual"] == 40.0
    assert bill["move_type"] == "in_invoice"


def test_pull_listas_y_monedas(tenant_id, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    odoo_connections_repo.save(tenant_id, "https://x.odoo.com", "x", "admin", "good-key")
    c = conectores.ConectorOdoo(tenant_id)
    listas = c.pull_listas_precios()
    assert listas["total"] == 4
    names = {pl["nombre"] for pl in listas["listas"]}
    assert names == {"Minorista ARS", "Mayorista ARS", "Minorista USD", "Mayorista USD"}
    fx = c.pull_monedas()
    assert fx["moneda_compania"] == "ARS"
    assert fx["total"] == 2
    assert fx["tipos_cambio"][0]["inverse_company_rate"] == 950.0
    assert fx["tipos_cambio"][-1]["inverse_company_rate"] == 1450.0


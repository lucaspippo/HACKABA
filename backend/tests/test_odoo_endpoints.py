import xmlrpc.client

import pytest
from fastapi.testclient import TestClient

import auth
import main
from core.db import odoo_connections_repo, tenant as _tenant
from tests.odoo_fakes import match_domain

client = TestClient(main.app)


class _FakeCommon:
    def authenticate(self, db, user, pwd, ctx):
        return False if pwd == "bad-key" else 7


def _by_id(rows, ids):
    want = set(ids)
    return [r for r in rows if r["id"] in want]


class _FakeModels:
    COMPANY = [{"id": 1, "name": "Distribuidora",
                "currency_id": [1, "ARS"], "country_id": [10, "Argentina"]}]
    RATES = [{"id": 1, "name": "2026-07-07", "currency_id": [2, "USD"],
              "rate": 1 / 1450, "inverse_company_rate": 1450.0, "company_rate": 1 / 1450}]
    CURRENCIES = [{"id": 1, "name": "ARS", "symbol": "$"},
                  {"id": 2, "name": "USD", "symbol": "US$"}]
    PRICELISTS = [{"id": 1, "name": "Minorista ARS", "currency_id": [1, "ARS"]}]
    PL_ITEMS = []
    PARTNERS = [{"id": 1, "name": "Cliente Odoo", "vat": "20-1-9", "city": "CABA",
                 "phone": "11-0000", "email": "c@example.com",
                 "customer_rank": 1, "supplier_rank": 1,
                 "property_product_pricelist": [1, "Minorista ARS"]}]
    PRODUCTS = [{"id": 1, "name": "Producto Odoo", "default_code": "X-1",
                 "categ_id": [1, "General"], "list_price": 10.0, "qty_available": 7.0,
                 "standard_price": 5.0, "active": True}]
    VARIANTS = [{"id": 1, "product_tmpl_id": [1, "Producto Odoo"], "free_qty": 7.0,
                 "qty_available": 7.0, "incoming_qty": 0.0, "outgoing_qty": 0.0}]
    POS = [{"id": 1, "name": "P00001", "partner_id": [1, "Proveedor Odoo"],
            "state": "purchase", "date_order": "2026-08-05 10:00:00",
            "amount_total": 500.0, "currency_id": [1, "ARS"]}]
    POLINES = [{"id": 1, "order_id": [1, "P00001"], "product_id": [1, "Producto Odoo"],
                "name": "Producto Odoo", "product_qty": 5.0, "price_unit": 100.0,
                "qty_received": 0.0}]
    SOS = [{"id": 1, "name": "S00001", "partner_id": [1, "Cliente Odoo"],
            "state": "sale", "date_order": "2026-06-15 10:00:00",
            "amount_total": 100.0, "currency_id": [1, "ARS"],
            "pricelist_id": [1, "Minorista ARS"]}]
    SOLINES = [{"id": 1, "order_id": [1, "S00001"], "product_id": [1, "Producto Odoo"],
                "product_template_id": [1, "Producto Odoo"], "name": "Producto Odoo",
                "product_uom_qty": 1.0, "price_unit": 100.0, "qty_delivered": 1.0}]
    QUANTS = [{"id": 1, "product_id": [1, "Producto Odoo"], "location_id": [8, "WH/Stock"],
               "quantity": 7.0, "lot_id": False, "in_date": "2026-01-15 10:00:00",
               "inventory_quantity": 0, "inventory_quantity_set": False}]
    LOCS = [{"id": 8, "complete_name": "WH/Stock", "usage": "internal"}]
    PICKINGS = [
        {"id": 1, "name": "WH/IN/00001", "partner_id": [1, "Proveedor Odoo"],
         "date_done": "2026-08-01 12:00:00", "scheduled_date": "2026-08-01 12:00:00",
         "origin": "P00001", "location_dest_id": [8, "WH/Stock"], "state": "done",
         "picking_type_code": "incoming", "backorder_id": False},
        {"id": 2, "name": "WH/OUT/00001", "partner_id": [1, "Cliente Odoo"],
         "date_done": "2026-06-16 12:00:00", "scheduled_date": "2026-06-16 12:00:00",
         "origin": "S00001", "location_dest_id": [8, "WH/Stock"], "state": "done",
         "picking_type_code": "outgoing", "backorder_id": False},
    ]
    MOVES = [
        {"id": 1, "picking_id": [1, "WH/IN/00001"], "product_id": [1, "Producto Odoo"],
         "quantity": 5.0, "product_uom_qty": 5.0, "location_dest_id": [8, "WH/Stock"],
         "purchase_line_id": [1, "P00001"], "sale_line_id": False, "state": "done"},
        {"id": 2, "picking_id": [2, "WH/OUT/00001"], "product_id": [1, "Producto Odoo"],
         "quantity": 1.0, "product_uom_qty": 1.0, "location_dest_id": [8, "WH/Stock"],
         "purchase_line_id": False, "sale_line_id": [1, "S00001"], "state": "done"},
    ]
    INVOICES = [
        {"id": 1, "name": "INV/2026/0001", "partner_id": [1, "Cliente Odoo"],
         "move_type": "out_invoice", "invoice_date": "2026-06-01",
         "invoice_date_due": "2026-08-01", "amount_total": 100.0,
         "amount_residual": 40.0, "amount_untaxed": 82.0,
         "payment_state": "partial", "currency_id": [1, "ARS"],
         "invoice_origin": "S00001", "state": "posted"},
    ]
    PAYMENTS = [
        {"id": 1, "name": "PAY/2026/0001", "partner_id": [1, "Cliente Odoo"],
         "amount": 60.0, "date": "2026-06-20", "payment_type": "inbound",
         "partner_type": "customer", "currency_id": [1, "ARS"],
         "ref": "INV/2026/0001", "state": "posted"},
    ]
    TABLES = {
        "res.company": COMPANY,
        "res.currency.rate": RATES,
        "res.currency": CURRENCIES,
        "product.pricelist": PRICELISTS,
        "product.pricelist.item": PL_ITEMS,
        "res.partner": PARTNERS,
        "product.template": PRODUCTS,
        "product.product": VARIANTS,
        "purchase.order": POS,
        "purchase.order.line": POLINES,
        "sale.order": SOS,
        "sale.order.line": SOLINES,
        "stock.quant": QUANTS,
        "stock.location": LOCS,
        "stock.lot": [],
        "stock.picking": PICKINGS,
        "stock.move": MOVES,
        "account.move": INVOICES,
        "account.payment": PAYMENTS,
    }

    def execute_kw(self, db, uid, pwd, model, method, args, kwargs):
        rows = self.TABLES.get(model)
        if rows is None:
            raise NotImplementedError(model)
        if method == "search":
            return [r["id"] for r in match_domain(rows, args[0] if args else [])]
        if method == "read":
            return _by_id(rows, args[0])
        raise NotImplementedError(method)


def _fake_server_proxy(url):
    return _FakeCommon() if url.endswith("/xmlrpc/2/common") else _FakeModels()


@pytest.fixture(scope="module")
def admin_token():
    creds = auth.cargar_o_generar_credenciales()
    return client.post("/api/login", json={"username": "emilio", "password": creds["emilio"]}).json()["token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(autouse=True)
def _sin_conexion_odoo():
    tid = _tenant.current_tenant_id()
    odoo_connections_repo.delete(tid)
    yield
    odoo_connections_repo.delete(tid)


def test_get_config_sin_conexion(admin_token):
    r = client.get("/api/conectores/odoo", headers=_h(admin_token))
    assert r.status_code == 200
    assert r.json() == {"conectado": False}


def test_put_config_credenciales_invalidas_no_guarda(admin_token, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    r = client.put("/api/conectores/odoo", headers=_h(admin_token),
                    json={"url": "https://x.odoo.com", "database": "x",
                          "username": "admin", "api_key": "bad-key"})
    assert r.status_code == 400
    assert client.get("/api/conectores/odoo", headers=_h(admin_token)).json() == {"conectado": False}


def test_put_luego_get_luego_delete(admin_token, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    r = client.put("/api/conectores/odoo", headers=_h(admin_token),
                    json={"url": "https://x.odoo.com", "database": "x",
                          "username": "admin", "api_key": "good-key"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}

    got = client.get("/api/conectores/odoo", headers=_h(admin_token)).json()
    assert got["conectado"] is True
    assert got["url"] == "https://x.odoo.com"
    assert "api_key" not in got  # nunca vuelve al frontend

    r = client.delete("/api/conectores/odoo", headers=_h(admin_token))
    assert r.status_code == 200
    assert client.get("/api/conectores/odoo", headers=_h(admin_token)).json() == {"conectado": False}


def test_sync_trae_contactos(admin_token, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    client.put("/api/conectores/odoo", headers=_h(admin_token),
               json={"url": "https://x.odoo.com", "database": "x",
                     "username": "admin", "api_key": "good-key"})
    r = client.post("/api/conectores/odoo/sync", headers=_h(admin_token))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["clientes"][0]["nombre"] == "Cliente Odoo"


def test_sync_sin_conexion_da_400(admin_token):
    r = client.post("/api/conectores/odoo/sync", headers=_h(admin_token))
    assert r.status_code == 400


def test_sync_productos_trae_catalogo(admin_token, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    client.put("/api/conectores/odoo", headers=_h(admin_token),
               json={"url": "https://x.odoo.com", "database": "x",
                     "username": "admin", "api_key": "good-key"})
    r = client.post("/api/conectores/odoo/sync-productos", headers=_h(admin_token))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["productos"][0]["codigo"] == "X-1"
    assert body["productos"][0]["stock"] == 7.0


def test_sync_productos_sin_conexion_da_400(admin_token):
    r = client.post("/api/conectores/odoo/sync-productos", headers=_h(admin_token))
    assert r.status_code == 400


def test_sync_proveedores_trae_contactos(admin_token, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    client.put("/api/conectores/odoo", headers=_h(admin_token),
               json={"url": "https://x.odoo.com", "database": "x",
                     "username": "admin", "api_key": "good-key"})
    r = client.post("/api/conectores/odoo/sync-proveedores", headers=_h(admin_token))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["proveedores"][0]["nombre"] == "Cliente Odoo"


def test_sync_proveedores_sin_conexion_da_400(admin_token):
    r = client.post("/api/conectores/odoo/sync-proveedores", headers=_h(admin_token))
    assert r.status_code == 400


def test_sync_ordenes_compra_trae_ordenes(admin_token, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    client.put("/api/conectores/odoo", headers=_h(admin_token),
               json={"url": "https://x.odoo.com", "database": "x",
                     "username": "admin", "api_key": "good-key"})
    r = client.post("/api/conectores/odoo/sync-ordenes-compra", headers=_h(admin_token))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["ordenes"][0]["numero"] == "P00001"
    assert body["ordenes"][0]["proveedor"] == "Proveedor Odoo"
    assert body["ordenes"][0]["estado"] == "confirmada"
    assert body["ordenes"][0]["items"][0]["producto"] == "Producto Odoo"


def test_sync_ordenes_compra_sin_conexion_da_400(admin_token):
    r = client.post("/api/conectores/odoo/sync-ordenes-compra", headers=_h(admin_token))
    assert r.status_code == 400


def test_ingest_productos_primera_vez_crea_batch(admin_token, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    client.put("/api/conectores/odoo", headers=_h(admin_token),
               json={"url": "https://x.odoo.com", "database": "x",
                     "username": "admin", "api_key": "good-key"})
    r = client.post("/api/conectores/odoo/ingest-productos", headers=_h(admin_token))
    assert r.status_code == 200
    body = r.json()
    assert body["nuevos_para_revisar"] == 1
    assert body["batch_id"] is not None


def test_ingest_productos_sin_conexion_da_400(admin_token):
    r = client.post("/api/conectores/odoo/ingest-productos", headers=_h(admin_token))
    assert r.status_code == 400


def test_ingest_proveedores_primera_vez_crea_batch(admin_token, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    client.put("/api/conectores/odoo", headers=_h(admin_token),
               json={"url": "https://x.odoo.com", "database": "x",
                     "username": "admin", "api_key": "good-key"})
    r = client.post("/api/conectores/odoo/ingest-proveedores", headers=_h(admin_token))
    assert r.status_code == 200
    body = r.json()
    assert body["nuevos_para_revisar"] == 1
    assert body["batch_id"] is not None


def test_ingest_proveedores_sin_conexion_da_400(admin_token):
    r = client.post("/api/conectores/odoo/ingest-proveedores", headers=_h(admin_token))
    assert r.status_code == 400


def test_ingest_contactos_primera_vez_crea_batch(admin_token, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    client.put("/api/conectores/odoo", headers=_h(admin_token),
               json={"url": "https://x.odoo.com", "database": "x",
                     "username": "admin", "api_key": "good-key"})
    r = client.post("/api/conectores/odoo/ingest-contactos", headers=_h(admin_token))
    assert r.status_code == 200
    body = r.json()
    assert body["nuevos_para_revisar"] == 1
    assert body["batch_id"] is not None


def test_ingest_contactos_sin_conexion_da_400(admin_token):
    r = client.post("/api/conectores/odoo/ingest-contactos", headers=_h(admin_token))
    assert r.status_code == 400


def test_ingest_ordenes_compra_primera_vez_crea_batch(admin_token, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    client.put("/api/conectores/odoo", headers=_h(admin_token),
               json={"url": "https://x.odoo.com", "database": "x",
                     "username": "admin", "api_key": "good-key"})
    r = client.post("/api/conectores/odoo/ingest-ordenes-compra", headers=_h(admin_token))
    assert r.status_code == 200
    body = r.json()
    assert body["nuevos_para_revisar"] == 1
    assert body["batch_id"] is not None


def test_ingest_ordenes_compra_sin_conexion_da_400(admin_token):
    r = client.post("/api/conectores/odoo/ingest-ordenes-compra", headers=_h(admin_token))
    assert r.status_code == 400


def test_sync_ventas_trae_ordenes(admin_token, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    client.put("/api/conectores/odoo", headers=_h(admin_token),
               json={"url": "https://x.odoo.com", "database": "x",
                     "username": "admin", "api_key": "good-key"})
    r = client.post("/api/conectores/odoo/sync-ventas", headers=_h(admin_token))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["ordenes"][0]["numero"] == "S00001"
    assert body["ordenes"][0]["estado"] == "confirmada"


def test_sync_ventas_sin_conexion_da_400(admin_token):
    r = client.post("/api/conectores/odoo/sync-ventas", headers=_h(admin_token))
    assert r.status_code == 400


def test_ingest_ventas_primera_vez_crea_batch(admin_token, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    client.put("/api/conectores/odoo", headers=_h(admin_token),
               json={"url": "https://x.odoo.com", "database": "x",
                     "username": "admin", "api_key": "good-key"})
    r = client.post("/api/conectores/odoo/ingest-ventas", headers=_h(admin_token))
    assert r.status_code == 200
    body = r.json()
    assert body["nuevos_para_revisar"] == 1
    assert body["batch_id"] is not None


def test_ingest_ventas_sin_conexion_da_400(admin_token):
    r = client.post("/api/conectores/odoo/ingest-ventas", headers=_h(admin_token))
    assert r.status_code == 400


def test_sync_deposito_trae_quants(admin_token, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    client.put("/api/conectores/odoo", headers=_h(admin_token),
               json={"url": "https://x.odoo.com", "database": "x",
                     "username": "admin", "api_key": "good-key"})
    r = client.post("/api/conectores/odoo/sync-deposito", headers=_h(admin_token))
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["quants"][0]["ubicacion"] == "WH/Stock"


def test_sync_recepciones_trae_movimientos(admin_token, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    client.put("/api/conectores/odoo", headers=_h(admin_token),
               json={"url": "https://x.odoo.com", "database": "x",
                     "username": "admin", "api_key": "good-key"})
    r = client.post("/api/conectores/odoo/sync-recepciones", headers=_h(admin_token))
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["recepciones"][0]["origen"] == "WH/IN/00001"


def test_forecast_vacio_200(admin_token):
    r = client.get("/api/forecast", headers=_h(admin_token))
    assert r.status_code == 200
    assert r.json()["available"] is False


def _conectar(admin_token, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    client.put("/api/conectores/odoo", headers=_h(admin_token),
               json={"url": "https://x.odoo.com", "database": "x",
                     "username": "admin", "api_key": "good-key"})


def test_sync_entregas_trae_salidas(admin_token, monkeypatch):
    _conectar(admin_token, monkeypatch)
    r = client.post("/api/conectores/odoo/sync-entregas", headers=_h(admin_token))
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["entregas"][0]["origen"] == "WH/OUT/00001"


def test_ingest_entregas_primera_vez_crea_batch(admin_token, monkeypatch):
    _conectar(admin_token, monkeypatch)
    r = client.post("/api/conectores/odoo/ingest-entregas", headers=_h(admin_token))
    assert r.status_code == 200
    assert r.json()["nuevos_para_revisar"] == 1
    assert r.json()["batch_id"] is not None


def test_sync_facturas_trae_comprobantes(admin_token, monkeypatch):
    _conectar(admin_token, monkeypatch)
    r = client.post("/api/conectores/odoo/sync-facturas", headers=_h(admin_token))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["facturas"][0]["payment_state"] == "partial"
    assert body["facturas"][0]["residual"] == 40.0


def test_ingest_facturas_primera_vez_crea_batch(admin_token, monkeypatch):
    _conectar(admin_token, monkeypatch)
    r = client.post("/api/conectores/odoo/ingest-facturas", headers=_h(admin_token))
    assert r.status_code == 200
    assert r.json()["nuevos_para_revisar"] == 1


def test_sync_pagos_trae_pagos(admin_token, monkeypatch):
    _conectar(admin_token, monkeypatch)
    r = client.post("/api/conectores/odoo/sync-pagos", headers=_h(admin_token))
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["pagos"][0]["numero"] == "PAY/2026/0001"


def test_sync_listas_y_monedas(admin_token, monkeypatch):
    _conectar(admin_token, monkeypatch)
    pl = client.post("/api/conectores/odoo/sync-listas-precios", headers=_h(admin_token))
    assert pl.status_code == 200
    assert pl.json()["total"] == 1
    fx = client.post("/api/conectores/odoo/sync-monedas", headers=_h(admin_token))
    assert fx.status_code == 200
    assert fx.json()["moneda_compania"] == "ARS"


def test_sync_entregas_sin_conexion_da_400(admin_token):
    r = client.post("/api/conectores/odoo/sync-entregas", headers=_h(admin_token))
    assert r.status_code == 400


def test_sync_facturas_sin_conexion_da_400(admin_token):
    r = client.post("/api/conectores/odoo/sync-facturas", headers=_h(admin_token))
    assert r.status_code == 400


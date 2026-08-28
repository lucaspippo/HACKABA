import xmlrpc.client

import pytest

from core import conectores
from core.db import odoo_connections_repo, tenant as _tenant


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
                     "phone": "341-000-0000", "email": "perez@example.com"},
                    {"id": 2, "name": "Kiosco La Esquina", "vat": False, "city": False,
                     "phone": False, "email": False},
                ]
            raise NotImplementedError(method)
        if model == "product.template":
            if method == "search":
                return [1, 2]
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
                ]
            raise NotImplementedError(method)
        if model == "purchase.order":
            if method == "search":
                return [10, 11]
            if method == "read":
                return [
                    {"id": 10, "name": "P00010", "partner_id": [3, "Distribuidora del Sur"],
                     "state": "purchase", "date_order": "2026-08-05 10:00:00", "amount_total": 3800.0},
                    {"id": 11, "name": "P00011", "partner_id": [4, "Proveedor Genérico SRL"],
                     "state": "draft", "date_order": "2026-08-20 09:00:00", "amount_total": 810.0},
                ]
            raise NotImplementedError(method)
        if model == "purchase.order.line":
            if method == "search":
                return [100, 101, 102]
            if method == "read":
                return [
                    {"id": 100, "order_id": [10, "P00010"], "product_id": [1, "Office Chair Ergo"],
                     "name": "Office Chair Ergo", "product_qty": 20.0, "price_unit": 120.0},
                    {"id": 101, "order_id": [10, "P00010"], "product_id": [2, "Filing Cabinet"],
                     "name": "Filing Cabinet", "product_qty": 10.0, "price_unit": 140.0},
                    {"id": 102, "order_id": [11, "P00011"], "product_id": False,
                     "name": "Printer Paper A4 (Box)", "product_qty": 100.0, "price_unit": 6.5},
                ]
            raise NotImplementedError(method)
        if model == "sale.order":
            if method == "search":
                return [20, 21, 22]
            if method == "read":
                return [
                    {"id": 20, "name": "S00020", "partner_id": [1, "Almacén Don Pérez"],
                     "state": "sale", "date_order": "2026-06-15 10:00:00", "amount_total": 2500.0},
                    {"id": 21, "name": "S00021", "partner_id": [2, "Kiosco La Esquina"],
                     "state": "draft", "date_order": "2026-06-20 09:00:00", "amount_total": 25.0},
                    {"id": 22, "name": "S00022", "partner_id": [1, "Almacén Don Pérez"],
                     "state": "cancel", "date_order": "2026-05-01 09:00:00", "amount_total": 8.0},
                ]
            raise NotImplementedError(method)
        if model == "sale.order.line":
            if method == "search":
                return [200, 201, 202]
            if method == "read":
                return [
                    {"id": 200, "order_id": [20, "S00020"], "product_id": [1, "Laptop Pro 15\""],
                     "product_template_id": [1, "Laptop Pro 15\""], "name": "Laptop Pro 15\"",
                     "product_uom_qty": 2.0, "price_unit": 1200.0},
                    {"id": 201, "order_id": [21, "S00021"], "product_id": [2, "Wireless Mouse"],
                     "product_template_id": [2, "Wireless Mouse"], "name": "Wireless Mouse",
                     "product_uom_qty": 1.0, "price_unit": 25.0},
                    {"id": 202, "order_id": [22, "S00022"], "product_id": [3, "Printer Paper A4 (Box)"],
                     "product_template_id": [3, "Printer Paper A4 (Box)"], "name": "Printer Paper A4 (Box)",
                     "product_uom_qty": 20.0, "price_unit": 8.0},
                ]
            raise NotImplementedError(method)
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
    assert r["total"] == 2
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
    assert r["total"] == 2
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

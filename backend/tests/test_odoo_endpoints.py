import xmlrpc.client

import pytest
from fastapi.testclient import TestClient

import auth
import main
from core.db import odoo_connections_repo, tenant as _tenant

client = TestClient(main.app)


class _FakeCommon:
    def authenticate(self, db, user, pwd, ctx):
        return False if pwd == "bad-key" else 7


class _FakeModels:
    def execute_kw(self, db, uid, pwd, model, method, args, kwargs):
        if method == "search":
            return [1]
        if method == "read":
            if model == "product.template":
                return [{"id": 1, "name": "Producto Odoo", "default_code": "X-1",
                          "categ_id": [1, "General"], "list_price": 10.0, "qty_available": 7.0}]
            if model == "purchase.order":
                return [{"id": 1, "name": "P00001", "partner_id": [1, "Proveedor Odoo"],
                          "state": "purchase", "date_order": "2026-08-05 10:00:00", "amount_total": 500.0}]
            if model == "purchase.order.line":
                return [{"id": 1, "order_id": [1, "P00001"], "product_id": [1, "Producto Odoo"],
                          "name": "Producto Odoo", "product_qty": 5.0, "price_unit": 100.0}]
            return [{"id": 1, "name": "Cliente Odoo", "vat": "20-1-9", "city": "CABA",
                      "phone": "11-0000", "email": "c@example.com"}]
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

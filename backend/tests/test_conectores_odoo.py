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
            if method == "search":
                return [1, 2]
            if method == "read":
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
                     "categ_id": [4, "Electronics"], "list_price": 1200.0, "qty_available": 45.0},
                    {"id": 2, "name": "Standing Desk", "default_code": "FURN-002",
                     "categ_id": [5, "Furniture"], "list_price": 350.0, "qty_available": 0.0},
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
    # sin stock (0) sigue siendo un número, no se pierde en el mapeo
    assert r["productos"][1]["stock"] == 0.0


def test_pull_productos_credenciales_guardadas_invalidas(tenant_id, monkeypatch):
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _fake_server_proxy)
    odoo_connections_repo.save(tenant_id, "https://x.odoo.com", "x", "admin", "bad-key")
    with pytest.raises(ValueError):
        conectores.ConectorOdoo(tenant_id).pull_productos()

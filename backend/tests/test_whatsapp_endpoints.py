"""main.py's /api/whatsapp-bot/* (tenant config + inbox) and
/api/webhooks/whatsapp (Meta Cloud API GET verify handshake + POST inbound,
HMAC-authenticated instead of a human session — same convention as the
Odoo connector endpoints, tests/test_odoo_endpoints.py)."""
import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

import auth
import main
import whatsapp_bot
from core.db import tenant as _tenant, whatsapp_repo

client = TestClient(main.app)


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {"display_phone_number": "+54 9", "verified_name": "Litoral"}
        self.text = text or json.dumps(self._payload)

    def json(self):
        return self._payload


@pytest.fixture(scope="module")
def admin_token():
    creds = auth.cargar_o_generar_credenciales()
    return client.post("/api/login", json={"username": "emilio", "password": creds["emilio"]}).json()["token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(autouse=True)
def _sin_canal():
    tid = _tenant.current_tenant_id()
    whatsapp_repo.delete_channel(tid)
    yield
    whatsapp_repo.delete_channel(tid)


def test_get_config_sin_conexion(admin_token):
    r = client.get("/api/whatsapp-bot/config", headers=_h(admin_token))
    assert r.status_code == 200
    assert r.json() == {"conectado": False}


def test_config_requiere_admin():
    r = client.get("/api/whatsapp-bot/config")
    assert r.status_code == 401


def test_put_config_credenciales_invalidas_no_guarda(admin_token, monkeypatch):
    monkeypatch.setattr("core.whatsapp_channel.httpx.get",
                         lambda *a, **k: _FakeResponse(401, text="rejected"))
    r = client.put("/api/whatsapp-bot/config", headers=_h(admin_token),
                    json={"phone_number_id": "123", "access_token": "bad", "app_secret": "s"})
    assert r.status_code == 400
    assert client.get("/api/whatsapp-bot/config", headers=_h(admin_token)).json() == {"conectado": False}


def test_put_luego_get_luego_delete(admin_token, monkeypatch):
    monkeypatch.setattr("core.whatsapp_channel.httpx.get", lambda *a, **k: _FakeResponse(200))
    r = client.put("/api/whatsapp-bot/config", headers=_h(admin_token),
                    json={"phone_number_id": "123", "access_token": "tok", "app_secret": "shh",
                          "greeting_message": "Hola!", "enabled": True})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["conectado"] is True
    assert "access_token" not in body and "app_secret" not in body

    got = client.get("/api/whatsapp-bot/config", headers=_h(admin_token)).json()
    assert got["conectado"] is True
    assert got["phone_number_id"] == "123"
    assert got["greeting_message"] == "Hola!"

    r = client.delete("/api/whatsapp-bot/config", headers=_h(admin_token))
    assert r.status_code == 200
    assert client.get("/api/whatsapp-bot/config", headers=_h(admin_token)).json() == {"conectado": False}


def test_conversaciones_vacio_sin_conexion(admin_token):
    r = client.get("/api/whatsapp-bot/conversaciones", headers=_h(admin_token))
    assert r.status_code == 200
    assert r.json() == {"conversaciones": []}


def test_conversaciones_lista_lo_que_hay(admin_token):
    tid = _tenant.current_tenant_id()
    conv = whatsapp_repo.get_or_create_conversation(tid, "+5491100000000", "Rosa")
    whatsapp_repo.add_message(tid, conv["id"], "in", "hola")
    r = client.get("/api/whatsapp-bot/conversaciones", headers=_h(admin_token))
    assert r.status_code == 200
    convs = r.json()["conversaciones"]
    assert len(convs) == 1 and convs[0]["customer_name"] == "Rosa"

    r = client.get(f"/api/whatsapp-bot/conversaciones/{conv['id']}/mensajes", headers=_h(admin_token))
    assert r.status_code == 200
    assert r.json()["mensajes"][0]["body"] == "hola"


# --- webhook: GET verify handshake -------------------------------------------

def _conectar(monkeypatch, admin_token, app_secret="app-secret-de-prueba"):
    monkeypatch.setattr("core.whatsapp_channel.httpx.get", lambda *a, **k: _FakeResponse(200))
    r = client.put("/api/whatsapp-bot/config", headers=_h(admin_token),
                    json={"phone_number_id": "123", "access_token": "tok",
                          "app_secret": app_secret, "enabled": True})
    assert r.status_code == 200, r.text
    tid = _tenant.current_tenant_id()
    return whatsapp_repo.get_channel(tid)["verify_token"]


def test_webhook_get_verifica_con_el_token_correcto(admin_token, monkeypatch):
    verify_token = _conectar(monkeypatch, admin_token)
    r = client.get("/api/webhooks/whatsapp", params={
        "hub.mode": "subscribe", "hub.verify_token": verify_token, "hub.challenge": "12345",
    })
    assert r.status_code == 200
    assert r.text == "12345"


def test_webhook_get_rechaza_token_incorrecto(admin_token, monkeypatch):
    _conectar(monkeypatch, admin_token)
    r = client.get("/api/webhooks/whatsapp", params={
        "hub.mode": "subscribe", "hub.verify_token": "no-es-el-token", "hub.challenge": "12345",
    })
    assert r.status_code == 403


def test_webhook_get_sin_canal_configurado_rechaza():
    r = client.get("/api/webhooks/whatsapp", params={
        "hub.mode": "subscribe", "hub.verify_token": "algo", "hub.challenge": "12345",
    })
    assert r.status_code == 403


# --- webhook: POST inbound (firma HMAC) --------------------------------------

def test_webhook_post_firma_valida_procesa(admin_token, monkeypatch):
    app_secret = "app-secret-de-prueba"
    _conectar(monkeypatch, admin_token, app_secret=app_secret)
    llamadas = []
    monkeypatch.setattr(whatsapp_bot, "procesar_webhook",
                         lambda tid, payload: llamadas.append((tid, payload)))
    payload = {"entry": [{"changes": [{"value": {"messages": []}}]}]}
    body = json.dumps(payload).encode("utf-8")
    firma = "sha256=" + hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    r = client.post("/api/webhooks/whatsapp", content=body,
                     headers={"x-hub-signature-256": firma, "content-type": "application/json"})
    assert r.status_code == 200
    assert len(llamadas) == 1
    assert llamadas[0][1] == payload


def test_webhook_post_firma_invalida_rechaza(admin_token, monkeypatch):
    _conectar(monkeypatch, admin_token, app_secret="app-secret-de-prueba")
    monkeypatch.setattr(whatsapp_bot, "procesar_webhook", lambda tid, payload: None)
    body = json.dumps({"entry": []}).encode("utf-8")
    r = client.post("/api/webhooks/whatsapp", content=body,
                     headers={"x-hub-signature-256": "sha256=deadbeef",
                              "content-type": "application/json"})
    assert r.status_code == 401


def test_webhook_post_sin_canal_configurado_no_falla():
    body = json.dumps({"entry": []}).encode("utf-8")
    r = client.post("/api/webhooks/whatsapp", content=body,
                     headers={"content-type": "application/json"})
    assert r.status_code == 200

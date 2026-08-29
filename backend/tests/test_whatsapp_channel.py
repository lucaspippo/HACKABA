"""core/whatsapp_channel.py — credential verification, webhook signature
checking, the customer-safe catalog search, and capturing pedido/presupuesto
as floor reports (core/piso.py)."""
from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from core import piso, whatsapp_channel


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text or json.dumps(self._payload)

    def json(self):
        return self._payload


# --- probar_credenciales / guardar_config / borrar_config -------------------

def test_probar_credenciales_ok(monkeypatch):
    monkeypatch.setattr(
        whatsapp_channel.httpx, "get",
        lambda *a, **k: _FakeResponse(200, {"display_phone_number": "+54 9 341 000-0000",
                                             "verified_name": "Distribuidora del Litoral"}),
    )
    info = whatsapp_channel.probar_credenciales("123", "tok")
    assert info["display_phone_number"] == "+54 9 341 000-0000"
    assert info["business_name"] == "Distribuidora del Litoral"


def test_probar_credenciales_rechazadas(monkeypatch):
    monkeypatch.setattr(whatsapp_channel.httpx, "get",
                         lambda *a, **k: _FakeResponse(401, text="Invalid OAuth access token"))
    with pytest.raises(ValueError):
        whatsapp_channel.probar_credenciales("123", "bad-token")


def test_probar_credenciales_requiere_ambos_campos():
    with pytest.raises(ValueError):
        whatsapp_channel.probar_credenciales("", "tok")
    with pytest.raises(ValueError):
        whatsapp_channel.probar_credenciales("123", "")


def test_guardar_config_valida_antes_de_persistir(db_tenant, monkeypatch):
    monkeypatch.setattr(whatsapp_channel.httpx, "get",
                         lambda *a, **k: _FakeResponse(401, text="rejected"))
    with pytest.raises(ValueError):
        whatsapp_channel.guardar_config(
            db_tenant, phone_number_id="123", access_token="bad",
            app_secret="secret", greeting_message="", enabled=True,
        )
    assert whatsapp_channel.obtener_config(db_tenant) is None


def test_guardar_config_luego_obtener_no_expone_secretos(db_tenant, monkeypatch):
    monkeypatch.setattr(
        whatsapp_channel.httpx, "get",
        lambda *a, **k: _FakeResponse(200, {"display_phone_number": "+54 9", "verified_name": "Litoral"}),
    )
    whatsapp_channel.guardar_config(
        db_tenant, phone_number_id="123", access_token="tok-real",
        app_secret="secret-real", greeting_message="Hola!", enabled=True,
    )
    cfg = whatsapp_channel.obtener_config(db_tenant)
    assert cfg["phone_number_id"] == "123"
    assert cfg["greeting_message"] == "Hola!"
    assert "access_token" not in cfg
    assert "app_secret" not in cfg

    con_secretos = whatsapp_channel.config_con_secretos(db_tenant)
    assert con_secretos["access_token"] == "tok-real"
    assert con_secretos["app_secret"] == "secret-real"


def test_borrar_config(db_tenant, monkeypatch):
    monkeypatch.setattr(
        whatsapp_channel.httpx, "get",
        lambda *a, **k: _FakeResponse(200, {"display_phone_number": "+54 9", "verified_name": "Litoral"}),
    )
    whatsapp_channel.guardar_config(
        db_tenant, phone_number_id="123", access_token="tok",
        app_secret="secret", greeting_message="", enabled=True,
    )
    whatsapp_channel.borrar_config(db_tenant)
    assert whatsapp_channel.obtener_config(db_tenant) is None


# --- firma del webhook (HMAC) ------------------------------------------------

def test_verificar_firma_correcta():
    secret = "app-secret"
    body = b'{"entry": []}'
    firma = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert whatsapp_channel.verificar_firma(secret, body, firma) is True


def test_verificar_firma_incorrecta():
    body = b'{"entry": []}'
    assert whatsapp_channel.verificar_firma("app-secret", body, "sha256=deadbeef") is False


def test_verificar_firma_sin_header():
    assert whatsapp_channel.verificar_firma("app-secret", b"{}", None) is False


def test_verificar_firma_formato_invalido():
    assert whatsapp_channel.verificar_firma("app-secret", b"{}", "not-sha256=abc") is False


# --- catálogo seguro para el cliente -----------------------------------------

def test_buscar_catalogo_nunca_expone_costo_ni_inmovilizado():
    from core import store
    art = next(a for a in store.raw_actual() if a.get("pvp") and a.get("costo_iva"))
    resultados = whatsapp_channel.buscar_catalogo(art["descripcion"][:6])
    assert resultados
    hit = resultados[0]
    assert set(hit) == {"codigo", "nombre", "precio", "disponible"}
    assert "costo_iva" not in hit and "inmovilizado" not in hit


def test_buscar_catalogo_omite_productos_sin_precio_de_venta(monkeypatch):
    import data_store as ds
    monkeypatch.setattr(ds, "buscar_productos",
                         lambda texto, limit=25: [{"codigo": 1, "descripcion": "Sin precio",
                                                    "pvp": None, "stock": 5}])
    assert whatsapp_channel.buscar_catalogo("sin precio") == []


# --- capturar pedido / presupuesto (core/piso.py) ----------------------------

@pytest.fixture(autouse=True)
def _limpio():
    from tests.conftest import limpiar_tabla_tenant
    limpiar_tabla_tenant("floor_reports")
    yield
    limpiar_tabla_tenant("floor_reports")


def test_registrar_pedido_queda_como_reporte_de_piso_canal_whatsapp():
    r = whatsapp_channel.registrar_pedido(
        telefono="+5491111111111", cliente_nombre="Rosa",
        items=[{"producto": "Aceite", "cantidad": "3 unidades"}], nota="Entregar mañana",
    )
    assert r["tipo"] == "pedido"
    assert r["actor"] == "Ángela (WhatsApp)"
    assert r["datos"]["canal"] == "whatsapp"
    assert r["datos"]["cliente"] == "Rosa"
    assert r["datos"]["telefono"] == "+5491111111111"
    assert r["datos"]["items"][0]["producto"] == "Aceite"
    assert r["estado"] == "nuevo"


def test_registrar_pedido_sin_nombre_usa_el_telefono_como_cliente():
    r = whatsapp_channel.registrar_pedido(
        telefono="+5492222222222", cliente_nombre="", items=[{"producto": "Harina"}],
    )
    assert r["datos"]["cliente"] == "+5492222222222"


def test_registrar_presupuesto_queda_como_reporte_de_piso():
    r = whatsapp_channel.registrar_presupuesto(
        telefono="+5493333333333", cliente_nombre="Marcos",
        items=[{"producto": "Manteca", "cantidad": "10 kg"}], nota="",
    )
    assert r["tipo"] == "presupuesto"
    assert r["datos"]["canal"] == "whatsapp"
    listado = piso.listar(tipo="presupuesto")
    assert any(x["id"] == r["id"] for x in listado)


def test_presupuesto_requiere_cliente_e_items():
    with pytest.raises(ValueError):
        piso.reportar("presupuesto", "x", {"items": [{"producto": "a"}]})  # sin cliente
    with pytest.raises(ValueError):
        piso.reportar("presupuesto", "x", {"cliente": "Juan"})  # sin items


def test_pedido_y_presupuesto_no_se_confunden_al_listar():
    whatsapp_channel.registrar_pedido(telefono="+541", cliente_nombre="A",
                                       items=[{"producto": "x"}])
    whatsapp_channel.registrar_presupuesto(telefono="+542", cliente_nombre="B",
                                            items=[{"producto": "y"}])
    assert len(piso.listar(tipo="pedido")) == 1
    assert len(piso.listar(tipo="presupuesto")) == 1

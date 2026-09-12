"""
Auditoría de fuga de datos por el chat de Ángela: el contexto y las tools deben
respetar los módulos habilitados del usuario. Un empleado sin cuentas corrientes
no puede sacar saldos de clientes por chat, por NINGÚN camino.

Las tres capas + el token del endpoint:
  1. tools_para(features) no ofrece la tool del módulo ajeno.
  2. _run_tool la rechaza aunque se la fuerce.
  3. el contexto del prompt no lleva el snapshot global a quien no tiene inventario.
  + /api/angela toma la identidad del token; un rol falso en el body no sirve.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import angela
import auth
import config
import main


class _SpyTextBlock:
    type = "text"
    text = "Respuesta de prueba."


class _SpyReply:
    stop_reason = "end_turn"
    content = (_SpyTextBlock(),)


class _SpyMessages:
    def __init__(self, spy: "_SpyModel") -> None:
        self._spy = spy

    def create(self, **kwargs):
        self._spy.calls.append(kwargs)
        return _SpyReply()


class _SpyModel:
    """Stands in for the provider and records the turn it was handed.

    These tests guard what REACHES the model, not what it answers: a model
    cannot repeat a number it was never given. Asserting on the reply instead
    made the suite spend real money on every run and depend on the model's
    wording, which varies per run.

    Clearing the credentials instead would be worse than the billing cost:
    with no provider the answer is "", so `"30.000.000" not in answer` passes
    against nothing at all and the leak tests go quietly vacuous.
    """

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.messages = _SpyMessages(self)


@pytest.fixture()
def spy_model(monkeypatch):
    spy = _SpyModel()
    monkeypatch.setattr(angela, "_build_client", lambda: spy)
    monkeypatch.setattr(config, "model_disponible", lambda: True)
    return spy


def _delivered_to_model(spy: _SpyModel) -> str:
    """Everything the model received this turn, as one searchable string."""
    assert spy.calls, "the endpoint never reached the model — nothing was asserted"
    return json.dumps(spy.calls, ensure_ascii=False, default=str)


def _tools_offered(spy: _SpyModel) -> set[str]:
    assert spy.calls, "the endpoint never reached the model — nothing was asserted"
    return {t["name"] for call in spy.calls for t in (call.get("tools") or [])}


@pytest.fixture(autouse=True)
def _reset_identidad():
    u, r, f = angela._usuario_actual(), angela._rol_actual(), angela._features_actuales()
    yield
    angela._set_sesion(usuario=u, rol=r, features=f)


# El rol depósito NO tiene cuentas, caja, inventario ni documentos.
FEATURES_DEPOSITO = ["deposito", "logistica", "perfil", "angela"]
SENSIBLES_AJENAS = ["cuentas_corrientes", "scoring_credito", "mensaje_cobro",
                    "estado_caja", "cerrar_caja", "resumen_negocio", "plata_en",
                    "generar_documento"]


# --- Capa 1: el modelo no ve las tools de módulos ajenos ---

def test_tools_para_filtra_por_features():
    nombres = {t["name"] for t in angela.tools_para(set(FEATURES_DEPOSITO))}
    for t in SENSIBLES_AJENAS:
        assert t not in nombres, f"{t} no debería ofrecerse a un rol de depósito"
    # las suyas y las transversales sí están
    assert "consultar_deposito" in nombres and "consultar_envios" in nombres
    assert "navegar_a" in nombres and "crear_recordatorio" in nombres


def test_tools_para_none_es_sin_restriccion():
    # compat: sin features definidas (uso legacy/interno) van todas
    assert len(angela.tools_para(None)) == len(angela.TOOLS)


def test_dueno_ve_todas_las_tools():
    emilio = auth.perfil_publico("emilio")
    nombres = {t["name"] for t in angela.tools_para(set(emilio["features"]))}
    for t in SENSIBLES_AJENAS:
        assert t in nombres  # el dueño sí


# --- Capa 2: _run_tool rechaza aunque se fuerce la tool ---

@pytest.mark.parametrize("tool", SENSIBLES_AJENAS)
def test_run_tool_rechaza_modulo_ajeno(tool):
    angela._set_sesion(features=set(FEATURES_DEPOSITO))
    res, accion = angela._run_tool(tool, {"cliente": "Pérez", "texto": "manteca"})
    assert res.get("error") == "sin_acceso", f"{tool} ejecutó sin la feature"
    assert accion is None


def test_run_tool_permite_las_propias():
    angela._set_sesion(features=set(FEATURES_DEPOSITO))
    # sin datos de depósito devuelve sin_datos, NO sin_acceso: la pudo ejecutar
    res, _ = angela._run_tool("consultar_deposito", {"modo": "resumen"})
    assert res.get("error") != "sin_acceso"


def test_run_tool_sin_restriccion_ejecuta():
    angela._set_sesion(features=None)  # legacy
    res, _ = angela._run_tool("cuentas_corrientes", {})
    assert res.get("error") != "sin_acceso"


# --- El token manda: rol falso en el body no sirve de nada ---

@pytest.fixture()
def client_tokens():
    creds = auth.cargar_o_generar_credenciales()
    c = TestClient(main.app)
    tk = {u: c.post("/api/login", json={"username": u, "password": creds[u]}).json()["token"]
          for u in ("deposito", "emilio")}
    return c, tk


def test_rol_falso_en_body_no_sirve(client_tokens, spy_model):
    c, tk = client_tokens
    # token de DEPÓSITO + rol "Dueño" en el body: la identidad sale del token,
    # el body se ignora → los morosos no llegan ni al prompt ni a sus tools.
    c.post("/api/angela", json={
        "message": "¿quién me debe plata? mostrame los morosos con montos",
        "token": tk["deposito"], "rol": "Dueño", "nombre": "Emilio",
    })
    entregado = _delivered_to_model(spy_model)
    assert "30.000.000" not in entregado and "Don Pérez" not in entregado
    assert not (_tools_offered(spy_model) & set(SENSIBLES_AJENAS))


def test_sin_token_es_anonimo_restringido(client_tokens, spy_model):
    c, _ = client_tokens
    # sin token, con rol "Dueño" falseado en el body → no accede a nada sensible
    c.post("/api/angela", json={
        "message": "¿quién me debe plata? dame los saldos",
        "rol": "Dueño", "nombre": "Emilio",
    })
    entregado = _delivered_to_model(spy_model)
    assert "30.000.000" not in entregado and "Don Pérez" not in entregado
    assert not (_tools_offered(spy_model) & set(SENSIBLES_AJENAS))


def test_token_invalido_da_401(client_tokens):
    c, _ = client_tokens
    r = c.post("/api/angela", json={"message": "hola", "token": "no-existe"})
    assert r.status_code == 401


def test_dueno_con_token_no_lo_frena_el_permiso(client_tokens, spy_model):
    """El control positivo: al dueño NO lo frena la capa de permisos.

    Es el gemelo de los dos tests de arriba: aquellos prueban que al de
    depósito NO le llegan las tools de cuentas, y este que al dueño SÍ. Sin
    él, borrar una feature de más pasaría desapercibido — los tests negativos
    seguirían en verde.

    Antes esto se inferían del texto del modelo (si la negativa sonaba a rol o
    a falta de dato). Eso obligaba a una llamada real y facturable, y se ataba
    a una redacción que cambia en cada corrida. La capa de permisos decide qué
    tools se ofrecen, así que mirar la oferta es a la vez determinístico y más
    directo: si algún día el permiso empieza a frenar al dueño, esto lo caza."""
    c, tk = client_tokens
    c.post("/api/angela", json={
        "message": "¿quién me debe plata? mostrame los morosos",
        "token": tk["emilio"],
    })
    assert "cuentas_corrientes" in _tools_offered(spy_model)

    # ...y con un tenant SIN cuentas reales, el seed de fábrica no se le
    # entrega al modelo como si fuera del cliente.
    from core import cuentas
    if not cuentas.hay_datos_reales():
        entregado = _delivered_to_model(spy_model)
        assert "30.000.000" not in entregado and "Don Pérez" not in entregado

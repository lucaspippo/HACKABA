"""
Autorización por endpoint: la identidad sale del TOKEN, nunca del body.
Por cada endpoint sensible, los 4 casos del pedido:
  (a) sin token → 401
  (b) token del rol correcto → funciona
  (c) token de rol equivocado → 403
  (d) rol="Dueño" en el body pero token de rol menor → 403 (el body no escala)
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import auth
import main

client = TestClient(main.app)


@pytest.fixture(scope="module")
def tokens():
    creds = auth.cargar_o_generar_credenciales()
    return {u: client.post("/api/login", json={"username": u, "password": creds[u]}).json()["token"]
            for u in ("emilio", "paula", "vendedor", "deposito")}


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


# Cada caso: (nombre, método, ruta, rol_con_permiso, rol_sin_permiso).
# vendedor sólo tiene cobranzas/perfil/angela → es el "rol menor" para casi todo.
CASOS = [
    ("cuentas_listar", "GET", "/api/cuentas", "paula", "deposito"),
    ("cuentas_cobro", "POST", "/api/cuentas/perez/cobro", "paula", "deposito"),
    ("caja_estado", "GET", "/api/caja", "paula", "deposito"),
    ("caja_cerrar", "POST", "/api/caja/cerrar", "paula", "deposito"),
    ("inventario", "GET", "/api/inventario", "emilio", "vendedor"),
    ("calidad", "GET", "/api/calidad", "paula", "deposito"),
    ("saneamiento_aplicar", "POST", "/api/saneamiento/aplicar/balanza", "paula", "deposito"),
    ("anomalias_aplicar", "POST", "/api/anomalias/aplicar", "paula", "deposito"),
    ("documentos", "GET", "/api/documentos/resumen_ejecutivo", "emilio", "deposito"),
    ("deposito", "GET", "/api/deposito", "deposito", "vendedor"),
    ("logistica", "GET", "/api/logistica", "deposito", "vendedor"),
    ("evolucion", "GET", "/api/evolucion", "emilio", "vendedor"),
    ("staging_listar", "GET", "/api/staging", "emilio", "vendedor"),
    ("contexto", "GET", "/api/contexto", None, "vendedor"),   # sólo polpilot (admin_contexto)
    ("versiones", "GET", "/api/versiones", "paula", "deposito"),
]

# Sólo el dueño (require_admin).
CASOS_ADMIN = [
    ("audit", "GET", "/api/audit"),
    ("sync_delta", "GET", "/api/sync/delta"),
    ("sync_config", "GET", "/api/sync/config"),
    ("conectores", "GET", "/api/conectores"),
]


def _call(metodo, ruta, headers=None, json=None):
    fn = client.get if metodo == "GET" else client.post
    kw = {"headers": headers or {}}
    if metodo == "POST":
        kw["json"] = json if json is not None else {}
    return fn(ruta, **kw)


@pytest.mark.parametrize("nombre,metodo,ruta,rol_ok,rol_no", CASOS)
def test_endpoint_rechaza_sin_token(nombre, metodo, ruta, rol_ok, rol_no):
    r = _call(metodo, ruta)
    assert r.status_code == 401, f"{nombre} dejó pasar sin token ({r.status_code})"


@pytest.mark.parametrize("nombre,metodo,ruta,rol_ok,rol_no", CASOS)
def test_endpoint_rol_equivocado_da_403(nombre, metodo, ruta, rol_ok, rol_no, tokens):
    r = _call(metodo, ruta, headers=_h(tokens[rol_no]))
    assert r.status_code == 403, f"{nombre} dejó pasar a {rol_no} ({r.status_code})"


@pytest.mark.parametrize("nombre,metodo,ruta,rol_ok,rol_no", CASOS)
def test_endpoint_rol_correcto_funciona(nombre, metodo, ruta, rol_ok, rol_no, tokens):
    if rol_ok is None:
        pytest.skip("sin rol de prueba con esta feature (contexto = polpilot interno)")
    r = _call(metodo, ruta, headers=_h(tokens[rol_ok]))
    # 200 o un 4xx de negocio (400/404), pero NUNCA 401/403 de auth
    assert r.status_code not in (401, 403), f"{nombre} bloqueó al rol correcto {rol_ok} ({r.status_code})"


@pytest.mark.parametrize("nombre,metodo,ruta,rol_ok,rol_no", CASOS)
def test_endpoint_body_role_no_escala(nombre, metodo, ruta, rol_ok, rol_no, tokens):
    # rol="Dueño"/actor="emilio" en el body + token de rol menor → sigue 403.
    if metodo != "POST":
        pytest.skip("el escalado por body sólo aplica a POST con cuerpo")
    r = _call(metodo, ruta, headers=_h(tokens[rol_no]),
              json={"rol": "Dueño", "actor": "emilio", "es_admin": True,
                    "monto": 1, "declarado": 0, "tipo": "x", "accion": "y"})
    assert r.status_code == 403, f"{nombre}: el body escaló a {rol_no} ({r.status_code})"


# --- require_admin: sólo el dueño ---

@pytest.mark.parametrize("nombre,metodo,ruta", CASOS_ADMIN)
def test_admin_rechaza_sin_token(nombre, metodo, ruta):
    assert _call(metodo, ruta).status_code == 401


@pytest.mark.parametrize("nombre,metodo,ruta", CASOS_ADMIN)
def test_admin_rechaza_no_dueno(nombre, metodo, ruta, tokens):
    # paula es rol válido pero NO es dueño → 403
    assert _call(metodo, ruta, headers=_h(tokens["paula"])).status_code == 403


@pytest.mark.parametrize("nombre,metodo,ruta", CASOS_ADMIN)
def test_admin_dueno_funciona(nombre, metodo, ruta, tokens):
    r = _call(metodo, ruta, headers=_h(tokens["emilio"]))
    assert r.status_code not in (401, 403)


# --- El header y la query se aceptan; token inválido/vacío no ---

def test_token_invalido_da_401(tokens):
    assert client.get("/api/caja", headers=_h("no-existe")).status_code == 401


def test_token_por_query_tambien_funciona(tokens):
    # compat con las llamadas viejas que mandaban ?token=
    r = client.get(f"/api/caja?token={tokens['paula']}")
    assert r.status_code not in (401, 403)


# --- Excepciones públicas documentadas: siguen abiertas a propósito ---

def test_publicos_no_exigen_token():
    assert client.get("/api/health").status_code == 200
    # login es público (emite el token)
    creds = auth.cargar_o_generar_credenciales()
    assert client.post("/api/login", json={"username": "emilio", "password": creds["emilio"]}).status_code == 200


# --- P9·C3 (M5): el vendedor del piloto puede hacer su trabajo declarado ---

def test_vendedor_piloto_tiene_cuentas():
    """Su trabajo es cobrar: sin `cuentas` no ve deudores (los datos viven
    detrás de require_feature("cuentas")), como ya pasaba con diego/lucia
    en el demo."""
    feats = auth.USUARIOS["vendedor"]["features"]
    assert "cobranzas" in feats and "cuentas" in feats


# --- P9·C6 (M10): TTL de tokens + login en tiempo constante ---

def test_token_vencido_es_token_inexistente(monkeypatch):
    creds = auth.cargar_o_generar_credenciales()
    s = auth.login("emilio", creds["emilio"])
    assert auth.usuario_por_token(s["token"])["username"] == "emilio"
    # se vence el token: adelantamos el reloj más allá del TTL (capturando la
    # función real ANTES de patchear — auth.time ES el módulo time)
    import time as _time
    reloj_real = _time.time
    monkeypatch.setattr(auth.time, "time",
                        lambda: reloj_real() + auth.TOKEN_TTL_SEGUNDOS + 1)
    assert auth.usuario_por_token(s["token"]) is None
    # y quedó purgado de la tabla de sesiones
    assert s["token"] not in auth._SESIONES


def test_login_no_distingue_usuario_inexistente_de_password_mala():
    """Sin return temprano: ambas fallas responden lo mismo (None). El tiempo
    constante es por construcción (compare_digest contra hash señuelo)."""
    assert auth.login("noexiste", "loquesea") is None
    assert auth.login("emilio", "password-mala") is None

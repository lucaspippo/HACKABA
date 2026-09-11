"""
Auditoría de fuga de datos por el chat de Ángela: el contexto y las tools deben
respetar los módulos habilitados del usuario. Un empleado sin cuentas corrientes
no puede sacar saldos de clientes por chat, por NINGÚN camino.

Las tres capas + el token del endpoint:
  1. tools_para(features) no ofrece la tool del módulo ajeno.
  2. _run_tool la rechaza aunque se la fuerce (cubre el router simulado).
  3. el contexto del prompt no lleva el snapshot global a quien no tiene inventario.
  + /api/angela toma la identidad del token; un rol falso en el body no sirve.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import angela
import auth
import main


def _suena_a_permiso(texto: str) -> bool:
    """¿La negativa es «no te corresponde» (permiso) y no «no lo tengo» (dato)?

    Las dos negativas se parecen en la superficie pero significan cosas
    opuestas. La de permiso habla del ROL de quien pregunta; la de dato, del
    export que falta. Se mira por palabras del rol para no atarse al texto
    exacto, que el modelo varía en cada corrida."""
    t = (texto or "").lower()
    return any(p in t for p in (
        "tu rol", "de tu rol", "no manejás", "no manejas", "no te corresponde",
        "no tenés acceso", "no tenes acceso", "your role", "you don't have access",
    ))


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


# --- Capa 2: _run_tool rechaza aunque se fuerce la tool (router simulado incluido) ---

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


# --- Fuga por el router simulado (_fallback), el camino determinista ---

def test_fallback_no_filtra_cuentas_a_deposito():
    angela._set_sesion(usuario="deposito", rol="Depósito", features=set(FEATURES_DEPOSITO))
    r = angela._fallback("¿quién me debe plata? mostrame los morosos")
    # NO aparece ningún nombre de cliente ni monto de deuda
    assert "Pérez" not in r["respuesta"] and "30.000.000" not in r["respuesta"]
    assert "cuentas_corrientes" not in r["tools_usadas"]


def test_fallback_no_filtra_caja_a_deposito():
    angela._set_sesion(features=set(FEATURES_DEPOSITO))
    r = angela._fallback("¿cuánta plata hay en la caja hoy?")
    assert "caja" not in [t for t in r["tools_usadas"]]
    assert "área de caja" in r["respuesta"] or "no está dentro" in r["respuesta"]


def test_fallback_no_filtra_inmovilizado_global_a_deposito():
    angela._set_sesion(features=set(FEATURES_DEPOSITO))
    # ni el intent de plata ni el default deben soltar el inmovilizado
    r1 = angela._fallback("¿cuánta plata tengo en manteca?")
    r2 = angela._fallback("hola, ¿qué me contás?")
    assert "541" not in r1["respuesta"] and "541" not in r2["respuesta"]


def test_fallback_dueno_si_ve_todo():
    angela._set_sesion(features=set(auth.perfil_publico("emilio")["features"]))
    r = angela._fallback("¿quién me debe plata?")
    # P9·C7 (M11): el nombre real de la tool es cuentas_corrientes ("cuentas"
    # nunca existió en TOOLS).
    assert "cuentas_corrientes" in r["tools_usadas"] or "Pérez" in r["respuesta"]


# --- El token manda: rol falso en el body no sirve de nada ---

@pytest.fixture()
def client_tokens():
    creds = auth.cargar_o_generar_credenciales()
    c = TestClient(main.app)
    tk = {u: c.post("/api/login", json={"username": u, "password": creds[u]}).json()["token"]
          for u in ("deposito", "emilio")}
    return c, tk


def test_rol_falso_en_body_no_sirve(client_tokens):
    c, tk = client_tokens
    # token de DEPÓSITO + rol "Dueño" en el body: la identidad sale del token,
    # el body se ignora → no puede sacar los morosos.
    r = c.post("/api/angela", json={
        "mensaje": "¿quién me debe plata? mostrame los morosos con montos",
        "token": tk["deposito"], "rol": "Dueño", "nombre": "Emilio",
    }).json()
    assert "30.000.000" not in r["respuesta"] and "Don Pérez" not in r["respuesta"]


def test_sin_token_es_anonimo_restringido(client_tokens):
    c, _ = client_tokens
    # sin token, con rol "Dueño" falseado en el body → no accede a nada sensible
    r = c.post("/api/angela", json={
        "mensaje": "¿quién me debe plata? dame los saldos",
        "rol": "Dueño", "nombre": "Emilio",
    }).json()
    assert "30.000.000" not in r["respuesta"] and "Don Pérez" not in r["respuesta"]


def test_token_invalido_da_401(client_tokens):
    c, _ = client_tokens
    r = c.post("/api/angela", json={"mensaje": "hola", "token": "no-existe"})
    assert r.status_code == 401


def test_dueno_con_token_no_lo_frena_el_permiso(client_tokens):
    """El control positivo: al dueño NO lo frena la capa de permisos.

    P45·T3 — antes esto exigía que nombrara al moroso o usara la tool de cuentas.
    Eso valía con el router simulado, que siempre llamaba la tool; con el modelo
    real el dueño de un tenant SIN cuentas cargadas recibe la respuesta honesta
    ("todavía no tengo ese dato, se activa cargando el export"), que es
    exactamente lo que el prompt le pide y es MEJOR que inventar sobre el seed.

    Lo que de verdad hay que proteger es la diferencia entre los dos noes:
      · al dueño le falta EL DATO      → habla de cargar el export;
      · al de depósito le falta EL PERMISO → habla de su rol.
    Si algún día el permiso empieza a frenar al dueño, esto lo caza. Y de paso
    verifica algo que antes no se miraba: que un tenant sin cuentas reales no
    filtre los números del seed como si fueran del cliente."""
    from core import cuentas
    c, tk = client_tokens
    r = c.post("/api/angela", json={
        "mensaje": "¿quién me debe plata? mostrame los morosos",
        "token": tk["emilio"],
    }).json()
    texto = r["respuesta"]
    tools = r.get("tools_usadas", [])

    if cuentas.hay_datos_reales():
        # con datos de verdad, contesta con ellos (tool de cuentas o el nombre)
        assert ("Pérez" in texto
                or any("cuentas" in t or "cobro" in t for t in tools)), texto
    else:
        # sin datos reales: la negativa es por FALTA DE DATO, nunca por rol...
        assert not _suena_a_permiso(texto), texto
        # ...y jamás se filtra el seed de fábrica como si fuera del cliente
        assert "30.000.000" not in texto and "Don Pérez" not in texto, texto

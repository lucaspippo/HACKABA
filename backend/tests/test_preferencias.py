"""
P19·A — Memoria de preferencias: Ángela recuerda cómo te gusta ver tu negocio.

Cubre: el catálogo estructurado (validación), las tools recordar_preferencia /
leer_preferencias, que crear_widget respete sin_torta (nunca más una torta),
los endpoints de transparencia (/api/preferencias: listar, escribir, borrar),
la paridad del router simulado, y que la preferencia SOBREVIVA (persistencia
en memoria.json, no en el navegador).
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

import angela
import auth
import main
from core import memoria


@pytest.fixture(autouse=True)
def limpio():
    backup = None
    if os.path.exists(memoria.MEMORIA_JSON):
        backup = open(memoria.MEMORIA_JSON, encoding="utf-8").read()
        os.remove(memoria.MEMORIA_JSON)
    usuario, rol = angela._usuario_actual(), angela._rol_actual()
    yield
    angela._set_sesion(usuario=usuario, rol=rol)
    if os.path.exists(memoria.MEMORIA_JSON):
        os.remove(memoria.MEMORIA_JSON)
    if backup is not None:
        open(memoria.MEMORIA_JSON, "w", encoding="utf-8").write(backup)


@pytest.fixture()
def cliente_dueno():
    creds = auth.cargar_o_generar_credenciales()
    c = TestClient(main.app)
    dueno = next(u for u, v in auth.USUARIOS.items()
                 if v.get("es_admin") and not v.get("interno"))
    r = c.post("/api/login", json={"username": dueno, "password": creds[dueno]})
    assert r.status_code == 200
    return c, r.json()["token"], dueno


# --- El catálogo estructurado valida (nada de memoria con basura) ---

def test_set_vista_catalogo():
    v = memoria.set_vista("emilio", "sin_torta", True)
    assert v["sin_torta"] is True
    v = memoria.set_vista("emilio", "margen_pin_umbral", 18)
    assert v["margen_pin_umbral"] == 18


def test_set_vista_clave_desconocida():
    with pytest.raises(ValueError):
        memoria.set_vista("emilio", "color_favorito", "azul")


def test_set_vista_umbral_invalido():
    with pytest.raises(ValueError):
        memoria.set_vista("emilio", "margen_pin_umbral", 150)


def test_orden_home_valida_permutacion():
    orden = list(reversed(memoria.BLOQUES_HOME))
    assert memoria.set_vista("emilio", "orden_home", orden)["orden_home"] == orden
    with pytest.raises(ValueError):
        memoria.set_vista("emilio", "orden_home", ["cards", "inventado"])


def test_borrar_vista():
    memoria.set_vista("emilio", "sin_torta", True)
    assert memoria.borrar_vista("emilio", "sin_torta") is True
    assert "sin_torta" not in memoria.vista("emilio")
    assert memoria.borrar_vista("emilio", "sin_torta") is False


# --- Las tools de Ángela (mismo espacio, con validación) ---

def test_tool_recordar_preferencia_y_leer():
    angela._set_sesion(usuario="emilio", rol="dueño")
    result, accion = angela._run_tool("recordar_preferencia",
                                      {"clave": "sin_torta", "valor": True})
    assert result["ok"] and accion["type"] == "preferencia"
    assert accion["vista"]["sin_torta"] is True
    prefs, _ = angela._run_tool("leer_preferencias", {})
    assert prefs["vista"]["sin_torta"] is True


def test_tool_preferencia_invalida_honesta():
    angela._set_sesion(usuario="emilio", rol="dueño")
    result, accion = angela._run_tool("recordar_preferencia",
                                      {"clave": "lo_que_sea", "valor": 1})
    assert result["ok"] is False and accion is None


# --- "I don't like pie charts" → nunca más una torta ---

def test_crear_widget_respeta_sin_torta():
    angela._set_sesion(usuario="emilio", rol="dueño")
    memoria.set_vista("emilio", "sin_torta", True)
    result, accion = angela._run_tool("crear_widget", {
        "tipo": "donut", "datos_fuente": "estado_catalogo", "seccion_destino": "inicio",
    })
    assert result["ok"] and result["widget"]["tipo"] == "barras"
    assert "tipo_ajustado" in result  # Ángela puede mencionarlo con gracia
    assert accion["widget"]["tipo"] == "barras"


def test_crear_widget_sin_pref_permite_donut():
    angela._set_sesion(usuario="emilio", rol="dueño")
    result, _ = angela._run_tool("crear_widget", {
        "tipo": "donut", "datos_fuente": "estado_catalogo", "seccion_destino": "inicio",
    })
    assert result["widget"]["tipo"] == "donut"


def test_widget_persiste_en_servidor():
    """P19·C: el widget pedido por chat queda en memoria.json (no solo browser)."""
    angela._set_sesion(usuario="emilio", rol="dueño")
    result, _ = angela._run_tool("crear_widget", {
        "tipo": "barras", "datos_fuente": "estado_catalogo", "seccion_destino": "inicio",
    })
    wid = result["widget"]["id"]
    guardados = memoria.vista("emilio").get("widgets", {}).get("inicio", [])
    assert any(w["id"] == wid for w in guardados)


# --- Transparencia total por API (Mi perfil lista y borra) ---

def test_api_preferencias_ciclo_completo(cliente_dueno):
    c, token, dueno = cliente_dueno
    h = {"Authorization": f"Bearer {token}"}
    r = c.post("/api/preferencias", json={"clave": "sin_torta", "valor": True}, headers=h)
    assert r.status_code == 200
    r = c.get("/api/preferencias", headers=h)
    assert r.json()["vista"]["sin_torta"] is True
    r = c.delete("/api/preferencias/sin_torta", headers=h)
    assert r.status_code == 200 and "sin_torta" not in r.json()["vista"]
    assert c.delete("/api/preferencias/sin_torta", headers=h).status_code == 404


def test_api_preferencias_valida(cliente_dueno):
    c, token, _ = cliente_dueno
    h = {"Authorization": f"Bearer {token}"}
    r = c.post("/api/preferencias", json={"clave": "margen_pin_umbral", "valor": 150}, headers=h)
    assert r.status_code == 400


# --- Paridad del router simulado (sin API key el flujo existe igual) ---

def test_fallback_sin_torta_es():
    angela._set_sesion(usuario="emilio", rol="dueño", idioma="es")
    r = angela._fallback("no me gustan los gráficos de torta")
    assert "recordar_preferencia" in r["tools_usadas"]
    assert memoria.vista("emilio").get("sin_torta") is True
    assert "torta" in r["respuesta"].lower()


def test_fallback_pie_charts_en():
    angela._set_sesion(usuario="emilio", rol="dueño", idioma="en")
    r = angela._fallback("I don't like pie charts")
    assert memoria.vista("emilio").get("sin_torta") is True
    assert "pie chart" in r["respuesta"].lower()


def test_fallback_margen_pin():
    angela._set_sesion(usuario="emilio", rol="dueño", idioma="es")
    r = angela._fallback("todo lo que tenga margen menor a 18 lo quiero fijado arriba")
    assert memoria.vista("emilio").get("margen_pin_umbral") == 18
    assert "18" in r["respuesta"]


def test_fallback_que_recordas():
    angela._set_sesion(usuario="emilio", rol="dueño", idioma="es")
    memoria.set_vista("emilio", "sin_torta", True)
    r = angela._fallback("¿qué recordás de mí?")
    assert "torta" in r["respuesta"].lower()


# --- P19·B — el Home se reordena por chat y queda persistido ---

def test_tool_reordenar_inicio():
    angela._set_sesion(usuario="emilio", rol="dueño")
    orden = ["oportunidades", "cards", "decisiones", "feed", "metricas", "plata"]
    result, accion = angela._run_tool("reordenar_inicio", {"orden": orden})
    assert result["ok"] and accion["type"] == "orden_home" and accion["orden"] == orden
    assert memoria.vista("emilio")["orden_home"] == orden


def test_tool_reordenar_invalido_honesto():
    angela._set_sesion(usuario="emilio", rol="dueño")
    result, accion = angela._run_tool("reordenar_inicio", {"orden": ["cards", "sidebar"]})
    assert result["ok"] is False and accion is None
    assert "bloques_validos" in result  # Ángela puede decir qué SÍ se mueve


def test_tool_reordenar_reset():
    angela._set_sesion(usuario="emilio", rol="dueño")
    angela._run_tool("reordenar_inicio",
                     {"orden": ["plata", "cards", "decisiones", "oportunidades", "feed", "metricas"]})
    result, accion = angela._run_tool("reordenar_inicio", {"reset": True})
    assert result["ok"] and accion["orden"] is None
    assert "orden_home" not in memoria.vista("emilio")


def test_fallback_oportunidades_arriba_de_decisiones():
    angela._set_sesion(usuario="emilio", rol="dueño", idioma="es")
    r = angela._fallback("poné las oportunidades de hoy arriba de lo que necesita mi decisión")
    orden = memoria.vista("emilio").get("orden_home")
    assert orden is not None
    assert orden.index("oportunidades") < orden.index("decisiones")
    assert "reordenar_inicio" in r["tools_usadas"]


def test_fallback_volver_a_como_estaba():
    angela._set_sesion(usuario="emilio", rol="dueño", idioma="es")
    angela._fallback("poné las oportunidades arriba de las decisiones")
    r = angela._fallback("volvé a como estaba el inicio")
    assert "orden_home" not in memoria.vista("emilio")
    assert "reordenar_inicio" in r["tools_usadas"]


# --- P19·C — estadísticas a pedido que persisten ---

def _hay_ventas():
    from core import analisis
    return analisis.plata_parada_mas_de(120).get("disponible", False)


def test_widget_plata_parada_o_guard_honesto():
    """Con ventas validadas la card se crea con dias+posicion; sin ventas el
    resultado es ok:False con motivo y alternativa (JAMÁS una card vacía)."""
    angela._set_sesion(usuario="emilio", rol="dueño")
    result, accion = angela._run_tool("crear_widget", {
        "tipo": "card", "datos_fuente": "plata_parada_dias", "dias": 120,
        "seccion_destino": "inicio", "posicion": "top",
    })
    if _hay_ventas():
        assert result["ok"] and result["widget"]["dias"] == 120
        assert result["widget"]["posicion"] == "top"
        assert accion["type"] == "create_widget"
    else:
        assert result["ok"] is False and result["error"] == "sin_ventas"
        assert result["alternativa"]  # Ángela ofrece la más cercana
        assert accion is None


def test_gestionar_widget_cambiar_y_quitar():
    angela._set_sesion(usuario="emilio", rol="dueño")
    angela._run_tool("crear_widget", {
        "tipo": "barras", "datos_fuente": "estado_catalogo",
        "seccion_destino": "inicio", "titulo": "Mi catálogo",
    })
    result, accion = angela._run_tool("gestionar_widget",
                                      {"que": "cambiar_tipo", "titulo": "catálogo", "tipo": "tabla"})
    assert result["ok"] and result["widget"]["tipo"] == "tabla"
    assert accion["type"] == "preferencia"
    guardado = memoria.vista("emilio")["widgets"]["inicio"][0]
    assert guardado["tipo"] == "tabla"  # persiste en el server
    result, _ = angela._run_tool("gestionar_widget", {"que": "quitar", "titulo": "catálogo"})
    assert result["ok"]
    assert memoria.vista("emilio")["widgets"]["inicio"] == []


def test_gestionar_widget_no_encontrado_honesto():
    angela._set_sesion(usuario="emilio", rol="dueño")
    result, accion = angela._run_tool("gestionar_widget", {"que": "quitar", "titulo": "inexistente"})
    assert result["ok"] is False and accion is None


def test_gestionar_widget_respeta_sin_torta():
    angela._set_sesion(usuario="emilio", rol="dueño")
    memoria.set_vista("emilio", "sin_torta", True)
    angela._run_tool("crear_widget", {
        "tipo": "barras", "datos_fuente": "estado_catalogo",
        "seccion_destino": "inicio", "titulo": "Mi catálogo",
    })
    result, _ = angela._run_tool("gestionar_widget",
                                 {"que": "cambiar_tipo", "titulo": "catálogo", "tipo": "donut"})
    assert result["ok"] is False  # ni por la puerta de atrás entra una torta


def test_api_widget_plata_parada(cliente_dueno):
    c, token, _ = cliente_dueno
    r = c.get("/api/widget-datos/plata-parada?dias=120",
              headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    d = r.json()
    if d.get("disponible"):
        assert d["dias_min"] == 120 and "monto" in d and "top" in d
    else:
        assert d.get("motivo")  # honesto: dice por qué no hay dato

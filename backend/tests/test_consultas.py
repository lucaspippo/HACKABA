"""
P21 — Estadísticas generativas: Ángela construye lo que le pidan, no ofrece menú.

Cubre el contrato de core/consultas.py (whitelists, rechazos limpios, verdad
literal) y los 7 casos de aceptación del prompt vía la tool consultar_serie
(el mismo camino que usa el modelo real) + la paridad del router simulado.

La suite corre con el tenant PILOTO (sin ventas cargadas): los casos que
necesitan ventas usan una fixture sintética con los productos reales del demo
(monkeypatch de la lectura — el CONTRATO es lo que se testea), y el caso
literal que destapó el bug corre además en subprocess contra el dataset demo
REAL. Todo LECTURA: el hash del dataset no se mueve ni un byte.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

import pytest

import angela
from core import consultas, memoria, store


def _hash_dataset() -> str:
    return hashlib.sha256(
        json.dumps(store.raw_actual(), sort_keys=True).encode()).hexdigest()


@pytest.fixture(autouse=True)
def limpio():
    if os.path.exists(memoria.MEMORIA_JSON):
        os.remove(memoria.MEMORIA_JSON)
    usuario, rol = angela._usuario_actual(), angela._rol_actual()
    antes = _hash_dataset()
    yield
    # regla 1 del prompt: esto es LECTURA — nada puede modificar datos
    assert _hash_dataset() == antes, "una consulta MUTÓ el dataset"
    angela._set_sesion(usuario=usuario, rol=rol)
    if os.path.exists(memoria.MEMORIA_JSON):
        os.remove(memoria.MEMORIA_JSON)


# --- fixture de ventas: los productos REALES del demo, 24 meses ----------------

_PRODUCTOS = [
    ("VINO TINTO LA RIBERA 750CC (X6U)", "bebidas", 800, 9500.0),
    ("GASEOSA COLA COSTA DULCE 2.25L (X6U)", "bebidas", 1200, 3800.0),
    ("JUGO EN POLVO COSTA DULCE (X20S)", "bebidas", 2000, 950.0),
    ("LECHE ENTERA CAMPO ALEGRE 1L (X12U)", "lácteos", 3000, 1450.0),
]


def _filas_sinteticas() -> list[dict]:
    filas = []
    for i in range(24):  # 2024-07 .. 2026-06
        anio, mes = divmod(6 + i, 12)
        clave = f"{2024 + anio}-{mes + 1:02d}"
        for j, (prod, cat, base_u, precio) in enumerate(_PRODUCTOS):
            filas.append({"fecha": f"{clave}-15", "producto": prod, "codigo": 9000 + j,
                          "categoria": cat, "cantidad": float(base_u + i * 10),
                          "precio": precio * (1.03 ** i), "boca": "Casa Central"})
    return filas


@pytest.fixture()
def ventas(monkeypatch):
    filas = _filas_sinteticas()
    monkeypatch.setattr(consultas, "_filas_ventas", lambda: filas)
    indices = {f["fecha"][:7]: 100.0 * (1.028 ** i)
               for i, f in enumerate(filas[::len(_PRODUCTOS)])}
    monkeypatch.setattr(consultas.macro, "ipc_serie",
                        lambda: {"disponible": True, "indices": indices})
    return filas


# --- A · el contrato: whitelists y rechazos limpios ---------------------------

def test_fuente_fuera_de_whitelist():
    r = consultas.consultar({"fuente": "sql; drop table"}, "es")
    assert r["ok"] is False and "sugerencias" in r


def test_metrica_invalida_para_fuente():
    r = consultas.consultar({"fuente": "cuentas", "metrica": "pesos_reales"}, "es")
    assert r["ok"] is False


def test_deflactar_unidades_rechazado():
    r = consultas.consultar({"fuente": "ventas", "metrica": "unidades",
                             "deflactar": True}, "es")
    assert r["ok"] is False and "unidades" in r["motivo"]


def test_producto_inexistente_error_claro(ventas):
    r = consultas.consultar({"fuente": "ventas", "producto": "criptomoneda lunar"}, "es")
    assert r["ok"] is False and "criptomoneda lunar" in r["motivo"]


def test_fecha_invalida():
    r = consultas.consultar({"fuente": "ventas", "desde": "hace un tiempo"}, "es")
    assert r["ok"] is False


def test_sin_ventas_honesto():
    """El piloto no tiene ventas: la consulta lo DICE, no devuelve una serie vacía."""
    r = consultas.consultar({"fuente": "ventas", "agrupar": "mes"}, "es")
    assert r["ok"] is False and "ventas" in r["motivo"].lower()


def test_tope_de_puntos_y_series(ventas):
    r = consultas.consultar({"fuente": "ventas", "metrica": "pesos", "agrupar": "mes"}, "es")
    assert r["ok"] and len(r["series"][0]["puntos"]) <= consultas.MAX_PUNTOS
    assert len(r["series"]) <= consultas.MAX_SERIES


def test_pesos_reales_con_base_declarada(ventas):
    r = consultas.consultar({"fuente": "ventas", "metrica": "pesos_reales",
                             "agrupar": "anio"}, "en")
    assert r["ok"] and r["meta"]["deflactado"] and r["meta"]["base_ipc"]
    assert "constant" in r["meta"]["unidad"]


def test_pesos_reales_sin_ipc_rechazado(ventas, monkeypatch):
    monkeypatch.setattr(consultas.macro, "ipc_serie", lambda: {"disponible": False})
    r = consultas.consultar({"fuente": "ventas", "metrica": "pesos_reales"}, "es")
    assert r["ok"] is False and r["alternativa"] == "pesos"


# --- D · los 7 casos de aceptación, literales ---------------------------------

def test_caso1_vino_tinto_la_ribera_fijado_en_trend(ventas):
    """El caso que destapó el bug: gráfico del producto, creado y FIJADO en
    Trend — sin menú de consuelo. El widget persiste en el server."""
    angela._set_sesion(usuario="emilio", rol="dueño")
    result, accion = angela._run_tool("consultar_serie", {
        "fuente": "ventas", "metrica": "unidades", "agrupar": "mes",
        "producto": "vino tinto la ribera", "desde": "2024-07",
        "fijar_en": "trend", "tipo": "linea",
    })
    assert result["ok"] and result["fijado"]
    assert "VINO TINTO LA RIBERA" in result["series"][0]["nombre"]
    assert accion["type"] == "create_widget" and accion["section"] == "evolucion"
    w = accion["widget"]
    assert w["datos_fuente"] == "consulta" and w["tipo"] == "linea"
    assert w["subtitulo"]  # la metadata honesta viaja con el widget
    # persiste: recargar lo re-ejecuta desde la consulta guardada
    guardados = memoria.vista("emilio")["widgets"]["evolucion"]
    assert any(x["id"] == w["id"] and x["consulta"]["producto"] == "vino tinto la ribera"
               for x in guardados)
    # y la consulta guardada devuelve el dato recalculado
    r2 = consultas.consultar(w["consulta"], "en")
    assert r2["ok"] and len(r2["series"][0]["puntos"]) == 24


def test_caso2_analisis_vertical_de_bebidas(ventas):
    r = consultas.consultar({"fuente": "ventas", "metrica": "pesos",
                             "agrupar": "producto", "categoria": "bebidas",
                             "composicion": True}, "es")
    assert r["ok"] and r["meta"]["unidad"] == "%" and r["meta"]["composicion"]
    total_pct = sum(p["y"] for p in r["series"][0]["puntos"])
    assert 99 < total_pct <= 100.5  # los 3 productos de bebidas suman el 100%


def test_caso3_comparar_leche_vs_gaseosa(ventas):
    r = consultas.consultar({"fuente": "ventas", "metrica": "unidades", "agrupar": "mes",
                             "producto": "leche entera", "comparar_producto": "gaseosa cola",
                             "desde": "2024-07"}, "en")
    assert r["ok"] and len(r["series"]) == 2
    assert all(len(s["puntos"]) == 24 for s in r["series"])
    assert "LECHE ENTERA" in r["series"][0]["nombre"]
    assert "GASEOSA COLA" in r["series"][1]["nombre"]


def test_caso4_margen_por_categoria_de_peor_a_mejor():
    # inventario del PILOTO alcanza: la métrica sale de los artículos cargados
    r = consultas.consultar({"fuente": "inventario", "metrica": "margen_teorico",
                             "agrupar": "categoria", "orden": "asc"}, "es")
    assert r["ok"]
    ys = [p["y"] for p in r["series"][0]["puntos"]]
    assert ys == sorted(ys)  # de peor a mejor
    assert r["meta"]["unidad"] == "%"


def test_caso5_ventas_por_dia_honesto(ventas):
    angela._set_sesion(usuario="emilio", rol="dueño")
    result, accion = angela._run_tool("consultar_serie",
                                      {"fuente": "ventas", "agrupar": "dia"})
    assert result["ok"] is False and accion is None
    assert result["alternativa"] == "mes"  # lo más cercano que SÍ existe


def test_caso6_sin_torta_activo_no_hay_torta(ventas):
    angela._set_sesion(usuario="emilio", rol="dueño")
    memoria.set_vista("emilio", "sin_torta", True)
    result, accion = angela._run_tool("consultar_serie", {
        "fuente": "ventas", "metrica": "pesos", "agrupar": "categoria",
        "composicion": True, "fijar_en": "inicio", "tipo": "donut",
    })
    assert result["ok"] and result["widget"]["tipo"] == "barras"
    assert "tipo_ajustado" in result  # Ángela puede mencionar que lo recordó
    assert accion["widget"]["tipo"] == "barras"


def test_caso7a_fallback_vino_es(ventas):
    angela._set_sesion(usuario="emilio", rol="dueño", idioma="es")
    r = angela._fallback("haceme un gráfico en trend de ventas mes a mes de vino tinto la ribera")
    assert "consultar_serie" in r["tools_usadas"]
    assert any(a["type"] == "create_widget" for a in r["acciones"])
    assert "VINO TINTO LA RIBERA" in r["respuesta"]
    assert memoria.vista("emilio")["widgets"]["evolucion"]  # quedó fijo


def test_caso7b_fallback_por_dia_en(ventas):
    angela._set_sesion(usuario="emilio", rol="dueño", idioma="en")
    r = angela._fallback("make me a chart of sales by day")
    assert "by month" in r["respuesta"]
    assert r["opciones"]  # ofrece lo más cercano, no un menú de gráficos genéricos


def test_caso1_contra_demo_real():
    """El caso literal, contra el dataset demo CANÓNICO (subprocess, como
    test_kpis): 24 puntos reales del vino, sin tocar nada."""
    backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_demo = os.path.join(os.path.dirname(backend), "data-demo")
    env = {**os.environ, "POLPILOT_TENANT": "demo", "POLPILOT_DATA_DIR": data_demo,
           "POLPILOT_DEMO_TODAY": "2026-07-07", "PYTHONIOENCODING": "utf-8"}
    env.pop("ANTHROPIC_API_KEY", None)
    codigo = (
        "import json; from core import consultas;"
        "r = consultas.consultar({'fuente':'ventas','metrica':'unidades','agrupar':'mes',"
        "'producto':'vino tinto la ribera','desde':'2024-07'}, 'en');"
        "print(json.dumps({'ok': r['ok'], 'nombre': r['series'][0]['nombre'],"
        "'n': len(r['series'][0]['puntos'])}))"
    )
    r = subprocess.run([sys.executable, "-c", codigo], cwd=backend, env=env,
                       capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr[-500:]
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["ok"] and out["n"] == 24
    assert "VINO TINTO LA RIBERA" in out["nombre"]


# --- gates y endpoint ----------------------------------------------------------

def test_gate_por_fuente():
    """Un rol sin 'cuentas' no consulta cuentas ni con la tool genérica."""
    angela._set_sesion(usuario="deposito", rol="depósito", features={"deposito"})
    result, _ = angela._run_tool("consultar_serie", {"fuente": "cuentas"})
    assert result.get("error") == "sin_acceso"


def test_api_consulta_serie():
    import auth
    import main
    from fastapi.testclient import TestClient
    creds = auth.cargar_o_generar_credenciales()
    c = TestClient(main.app)
    dueno = next(u for u, v in auth.USUARIOS.items()
                 if v.get("es_admin") and not v.get("interno"))
    tok = c.post("/api/login", json={"username": dueno, "password": creds[dueno]}).json()["token"]
    # inventario existe en cualquier tenant: el endpoint responde el contrato
    r = c.post("/api/consulta-serie",
               json={"consulta": {"fuente": "inventario", "metrica": "inmovilizado",
                                  "agrupar": "categoria"}},
               headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200 and r.json()["ok"]
    # y una consulta inválida rechaza limpio, no 500
    r2 = c.post("/api/consulta-serie", json={"consulta": {"fuente": "sql"}},
                headers={"Authorization": f"Bearer {tok}"})
    assert r2.status_code == 200 and r2.json()["ok"] is False

"""
P34·2 — el agregador de actividad de equipo cuenta el trabajo REAL (slugs de
audit correctos), lista a TODOS los empleados (los inactivos también) y NUNCA
expone texto de conversaciones (solo temas = tools).
"""
from __future__ import annotations

import os
import subprocess
import sys

import main


def test_familia_evento_slugs_reales():
    # cargas: los slugs que EFECTIVAMENTE graba el audit (antes contaba nombres
    # muertos "confirmar_*" y subcontaba el trabajo real)
    for acc in ("cargar_remito", "cargar_factura", "cargar_recibo",
                "cargar_orden_compra", "integrar_staging", "crear_apartado"):
        assert main._familia_evento(acc) == "carga", acc
    # correcciones: saneamiento por prefijo + las explícitas
    for acc in ("sanear_fantasma", "sanear_balanza", "sanear_costo_viejo",
                "sanear_fantasma_custom", "aplicar_lista_precios",
                "corregir_precio_perdida"):
        assert main._familia_evento(acc) == "correccion", acc
    assert main._familia_evento("consulta_angela") == "consulta"
    # lo que NO es trabajo del negocio no cuenta
    for acc in ("restaurar_version", "cambiar_idioma", "editar_descripcion_perfil",
                "confirmar_remito", ""):
        assert main._familia_evento(acc) is None, acc


def test_demo_equipo_actividad_estructura_y_verdad():
    backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_demo = os.path.join(os.path.dirname(backend), "data-demo")
    env = {**os.environ, "POLPILOT_TENANT": "demo", "POLPILOT_DATA_DIR": data_demo,
           "POLPILOT_DEMO_TODAY": "2026-07-07", "POLPILOT_DEMO_AUTOLOGIN": "1",
           "PYTHONIOENCODING": "utf-8"}
    env.pop("ANTHROPIC_API_KEY", None)
    code = r"""
from fastapi.testclient import TestClient
import main
c = TestClient(main.app)
tok = c.post("/api/demo/autologin").json()["token"]
d = c.get("/api/equipo/actividad", headers={"Authorization": "Bearer " + tok}).json()

filas = d["actividad"]
# TODOS los empleados no-admin (los inactivos también): el demo tiene 12
assert len(filas) >= 10, ("pocos empleados", len(filas))
por_nombre = {f["nombre"]: f for f in filas}

# el fix de slugs: Marta (integrar_staging x2 + cargar_factura + cargar_recibo)
# y Nahuel (cargar_remito x2) — que antes NO se contaban — ahora sí
assert por_nombre["Marta"]["cargas"] >= 4, ("Marta cargas", por_nombre["Marta"])
assert por_nombre["Nahuel"]["cargas"] >= 2, ("Nahuel cargas", por_nombre["Nahuel"])

# hay empleados SIN actividad, mostrados honestamente (no rellenados)
sin = [f for f in filas if f["consultas"] + f["acciones"] == 0]
assert len(sin) >= 1, "el demo debe tener inactivos reales"
assert all(f["dias_desde"] is None for f in sin), "inactivo no tiene recencia"

# recencia con clamp: nunca negativa
assert all(f["dias_desde"] is None or f["dias_desde"] >= 0 for f in filas)

# resumen del equipo, todo derivado
r = d["resumen"]
for k in ("personas", "activos_semana", "acciones_total", "objetivos_en_curso", "objetivos_listos"):
    assert k in r, k
assert r["acciones_total"] >= 6

# NUNCA texto de conversaciones: los "temas" son slugs de tools, cortos y sin
# espacios de frase; jamás el mensaje del usuario
for f in filas:
    for tema, n in f["temas_top"]:
        assert isinstance(tema, str) and " " not in tema, ("tema con espacios?", tema)
print("OK")
"""
    r = subprocess.run([sys.executable, "-c", code], cwd=backend, env=env,
                       capture_output=True, text=True, timeout=180)
    assert r.returncode == 0 and "OK" in r.stdout, (r.stdout[-900:], r.stderr[-900:])

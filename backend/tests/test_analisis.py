"""
P7 · Los cruces de análisis dan números CORRECTOS y coherentes con el dataset
(no inventados), y sin datos se dice (anti-alucinación).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAIZ = os.path.dirname(BACKEND)
DATA_DEMO = os.path.join(RAIZ, "data-demo")


def _en_demo(codigo: str) -> str:
    env = {**os.environ, "POLPILOT_TENANT": "demo", "POLPILOT_DATA_DIR": DATA_DEMO,
           "PYTHONIOENCODING": "utf-8"}
    env.pop("ANTHROPIC_API_KEY", None)
    r = subprocess.run([sys.executable, "-c", codigo], cwd=BACKEND, env=env,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-800:]
    return r.stdout


def test_rotacion_cruza_stock_con_ventas_reales():
    out = _en_demo("""
import json
from core import analisis
r = analisis.rotacion()
print(json.dumps({"disp": r["disponible"], "total": r["inmovilizado_total"],
                  "dias": r["dias_promedio"], "pct_dormido": r["pct_dormido"],
                  "top": r["dormidos_top"][0] if r["dormidos_top"] else None}))
""")
    r = json.loads(out)
    assert r["disp"]
    # empresa SANA: rotación promedio razonable y poco dormido
    assert 15 <= r["dias"] <= 45
    assert r["pct_dormido"] < 30
    # el inmovilizado del análisis cierra con el inventario (misma fuente)
    arts = json.load(open(os.path.join(DATA_DEMO, "inventory.json"), encoding="utf-8"))["articulos"]
    inv = sum(a["inmovilizado"] for a in arts if a["estado"] == "activo" and a.get("costo_iva"))
    assert abs(r["total"] - inv) / inv < 0.02  # activos con costo: mismo número


def test_estacionalidad_decenal_detecta_los_picos_del_dataset():
    out = _en_demo("""
import json
from core import analisis
e = analisis.estacionalidad()
beb = e["categorias"]["bebidas"]
fia = e["categorias"]["fiambres y quesos (balanza)"]
print(json.dumps({"anios": e["anios_analizados"], "beb_pico": beb["pico_max"],
                  "beb_idx": beb["idx_max"], "fia_pico": fia["pico_max"]}))
""")
    e = json.loads(out)
    assert e["anios"] >= 8                      # historia decenal real
    assert e["beb_pico"] == 12 and e["beb_idx"] > 1.4   # el diseño del dataset: fiestas
    assert e["fia_pico"] == 12


def test_push_pull_tiene_fundamento_numerico():
    out = _en_demo("""
import json
from core import analisis
pp = analisis.push_pull()
print(json.dumps({"push": len(pp["push"]), "pull": len(pp["pull"]),
                  "push_motivos": all("%" in x["motivo"] or "temporada" in x["motivo"] for x in pp["push"]),
                  "pull_rapidos": all(x["dias_rotacion"] <= 20 for x in pp["pull"])}))
""")
    pp = json.loads(out)
    assert pp["push"] >= 3 and pp["pull"] >= 3
    assert pp["push_motivos"] and pp["pull_rapidos"]


def test_objetivos_salen_de_los_datos():
    out = _en_demo("""
import json
from core import analisis, cuentas
o = analisis.objetivos()["objetivos"]
al = cuentas.alertas()
cobrar = next((x for x in o if x["id"] == "cobrar_morosos"), None)
print(json.dumps({"n": len(o), "ids": [x["id"] for x in o],
                  "monto_ok": cobrar and cobrar["monto"] == al["impacto_pesos"]}))
""")
    o = json.loads(out)
    assert o["n"] >= 3
    assert "liquidar_dormido" in o["ids"] and "crecimiento" in o["ids"]
    assert o["monto_ok"]  # el monto del objetivo ES el de cuentas corrientes


def test_sin_ventas_no_se_inventa_nada():
    """En el PILOTO (sin ventas cargadas) el análisis lo dice, no inventa."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    env.pop("POLPILOT_TENANT", None)
    env.pop("POLPILOT_DATA_DIR", None)
    env.pop("ANTHROPIC_API_KEY", None)
    r = subprocess.run([sys.executable, "-c", """
from core import analisis, ventas
if ventas.hay_datos():
    print("con_datos")           # si algún día el piloto carga ventas, el test no aplica
else:
    r = analisis.rotacion()
    assert r["disponible"] is False and "ventas" in r["motivo"].lower()
    print("honesto")
"""], cwd=BACKEND, env=env, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-500:]
    assert r.stdout.strip() in ("honesto", "con_datos")

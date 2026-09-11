import json
import os
import subprocess
import sys

import pytest

from core import fase, store, memoria

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAIZ = os.path.dirname(BACKEND)
DATA_DEMO = os.path.join(RAIZ, "data-demo")


@pytest.fixture(autouse=True)
def estado_limpio():
    store.resetear_actual()
    if os.path.exists(memoria.MEMORIA_JSON):
        os.remove(memoria.MEMORIA_JSON)
    yield
    store.resetear_actual()


def test_fase_carga_inicial_con_issues():
    f = fase.actual()
    assert f["fase"] == "carga_inicial"
    assert f["foco"] == "saneamiento"
    assert set(f) == {"fase", "titulo", "foco", "mensaje", "datos"}
    assert f["mensaje"]


def test_piloto_sin_ventas_reales_ni_cuentas_reales():
    """P11·B3: el piloto sigue pidiendo lo que falta — sus ventas no están y
    sus cuentas son el seed de fábrica, no el Excel real."""
    d = fase.datos_presentes()
    assert d["ventas"] is False
    assert d["cuentas"] is False   # seed de Horizonte ≠ datos reales


def _en_demo(codigo: str) -> str:
    env = {**os.environ, "POLPILOT_TENANT": "demo", "POLPILOT_DATA_DIR": DATA_DEMO,
           "POLPILOT_DEMO_TODAY": "2026-07-07", "PYTHONIOENCODING": "utf-8"}
    env.pop("ANTHROPIC_API_KEY", None)
    r = subprocess.run([sys.executable, "-c", codigo], cwd=BACKEND, env=env,
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stderr[-800:]
    return r.stdout


def test_demo_esta_en_operacion_y_entra_por_inicio():
    """P11·B3+B7: con 10 años de ventas validadas, el demo está EN OPERACIÓN
    y el foco es el panel — el dueño entra por Inicio, no por Datos a corregir."""
    out = _en_demo("""
import json
from core import fase
f = fase.actual()
print(json.dumps({"fase": f["fase"], "foco": f["foco"], "datos": f["datos"]}))
""")
    r = json.loads(out)
    assert r["fase"] == "operacion"
    assert r["foco"] == "panel"
    d = r["datos"]
    assert d["ventas"] and d["cuentas"] and d["deposito"] and d["logistica"]


def test_demo_no_pide_datos_que_ya_estan():
    """P11·B3: ninguna tarjeta pendiente de Oportunidades pide las ventas que
    ya están cargadas, y el snapshot del prompt de Ángela dice que están."""
    out = _en_demo("""
import json
import data_store as ds
import angela
ops = ds.oportunidades()
print(json.dumps({
    "pend": [p["id"] for p in ops["pendientes"]],
    "snapshot": angela._resumen_para_prompt(),
}, ensure_ascii=False))
""")
    r = json.loads(out)
    assert "rotacion" not in r["pend"]
    assert "ventas históricas validadas: SÍ" in r["snapshot"]
    assert "cuentas corrientes: SÍ" in r["snapshot"]


def test_piloto_mantiene_su_tarjeta_de_rotacion_pendiente():
    """En el piloto (sin ventas) la tarjeta 'rotacion' sigue pidiendo el export,
    como corresponde."""
    import data_store as ds
    ops = ds.oportunidades()
    assert "rotacion" in [p["id"] for p in ops["pendientes"]]

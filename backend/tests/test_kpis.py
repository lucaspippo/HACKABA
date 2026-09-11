"""
P18·A — Los KPIs del dueño (analisis.kpis): derivados SOLO de datos existentes,
cada uno presente únicamente si su dato lo sostiene. Los valores del demo son
los números canónicos del guion — si esto se mueve, el guion se entera acá.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from core import analisis


def test_kpis_piloto_solo_los_sostenibles():
    k = analisis.kpis()
    # El tenant de la suite no tiene ventas validadas → los KPIs de ventas
    # CAEN (honesto).
    assert "crecimiento_pct" not in k
    assert "rotacion_dias" not in k
    assert "dormido" not in k
    # El margen teórico SÍ está: el catálogo sintético cubre PVP+costo muy por
    # arriba del guard de cobertura (≥80%), así que el agregado es defendible.
    assert "margen_teorico" in k
    # Días de cobro sí: las cuentas (seed) tienen comportamiento por cliente.
    assert k["cobro_dias"] > 0


def test_kpis_demo_valores_canonicos():
    backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_demo = os.path.join(os.path.dirname(backend), "data-demo")
    env = {**os.environ, "POLPILOT_TENANT": "demo", "POLPILOT_DATA_DIR": data_demo,
           "POLPILOT_DEMO_TODAY": "2026-07-07", "PYTHONIOENCODING": "utf-8"}
    env.pop("ANTHROPIC_API_KEY", None)
    r = subprocess.run(
        [sys.executable, "-c",
         "import json; from core import analisis; print(json.dumps(analisis.kpis('en')))"],
        cwd=backend, env=env, capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr[-500:]
    k = json.loads(r.stdout.strip().splitlines()[-1])
    assert k["crecimiento_pct"] == 3.9
    assert k["rotacion_dias"] == 30
    assert k["dormido"]["pct"] == 15.5
    assert round(k["dormido"]["monto"]) == 68927214
    assert k["margen_teorico"] == {"pct": 17.7, "sin_pvp": 8}
    assert k["cobro_dias"] == 25

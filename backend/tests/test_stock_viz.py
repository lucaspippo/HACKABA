"""Stock visualizations — every figure is a cut of an existing core derivation.

The piloto scratch has a catalog and no sales: the pack must lock, not invent
zeros. The demo tenant (subprocess) is where the charts have numbers.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from core import stock_viz

_PACK_KEYS = (
    "excess_by_category",
    "rotation",
    "expiry_horizon",
    "seasonality",
    "gmroi",
    "aging",
    "lead_truth",
)


def _demo_script(code: str):
    backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_demo = os.path.join(os.path.dirname(backend), "data-demo")
    env = {**os.environ, "POLPILOT_TENANT": "demo", "POLPILOT_DATA_DIR": data_demo,
           "POLPILOT_DEMO_TODAY": "2026-07-07", "PYTHONIOENCODING": "utf-8"}
    env.pop("ANTHROPIC_API_KEY", None)
    r = subprocess.run(
        [sys.executable, "-c", code],
        cwd=backend, env=env, capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr[-800:]
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_piloto_pack_locks_without_sales():
    pack = stock_viz.pack("es")
    assert set(pack) == set(_PACK_KEYS)
    for k in ("excess_by_category", "rotation", "seasonality", "gmroi"):
        assert pack[k]["disponible"] is False
        assert pack[k].get("motivo")
    for k in ("aging", "lead_truth", "expiry_horizon"):
        if not pack[k].get("disponible"):
            assert pack[k].get("motivo")


def test_piloto_burn_unknown_sku():
    r = stock_viz.product_burn(999_999_999, "es")
    assert r["disponible"] is False
    assert r.get("motivo")


def test_demo_pack_burn_and_reponer_puntos():
    out = _demo_script("""
import json
from core import stock_viz, reponer
pack = stock_viz.pack("es")
codigo = next(p["codigo"] for p in pack["rotation"]["puntos"] if not p.get("sin_venta"))
print(json.dumps({
    "pack": pack,
    "burn": stock_viz.product_burn(codigo, "es"),
    "reponer": reponer.analizar(),
}))
""")
    pack = out["pack"]
    assert set(pack) == set(_PACK_KEYS)

    excess = pack["excess_by_category"]
    assert excess["disponible"] is True
    assert excess["categorias"]
    assert excess["total_excedente"] > 0
    assert excess["total_necesario"] > 0
    for c in excess["categorias"]:
        assert c["necesario"] >= 0 and c["excedente"] >= 0

    rot = pack["rotation"]
    assert rot["disponible"] is True
    assert rot["puntos"]
    assert rot["cortes"]["sano"] == 35 and rot["cortes"]["atencion"] == 60
    for p in rot["puntos"][:20]:
        assert p["codigo"] and p["producto"]
        assert p["inmovilizado"] >= 0
        assert p["estado"] in ("sano", "atencion", "dormido")

    gmroi = pack["gmroi"]
    assert gmroi["disponible"] is True
    assert gmroi["grupos"]
    ratios = [g["gmroi"] for g in gmroi["grupos"]]
    assert ratios == sorted(ratios, reverse=True)
    for g in gmroi["grupos"]:
        assert g["inmovilizado"] > 0
        esperado = round(g["ganancia_12m"] / g["inmovilizado"], 2)
        assert abs(g["gmroi"] - esperado) < 0.011

    season = pack["seasonality"]
    assert season["disponible"] is True
    assert season["featured"]
    assert len(season["indice"]) == 12

    venc = pack["expiry_horizon"]
    if venc.get("disponible") and venc.get("total_en_riesgo", 0) > 0:
        assert venc["weeks"]
        assert abs(sum(w["monto"] for w in venc["weeks"]) - venc["total_en_riesgo"]) < 1

    aging = pack["aging"]
    if aging.get("disponible"):
        ids = [b["id"] for b in aging["buckets"]]
        assert ids == ["0_30", "31_90", "91_180", "181_365", "365_plus"]
        assert 0 <= aging["cubierto_pct"] <= 100

    r = out["reponer"]
    assert r["disponible"] is True
    assert r["puntos"]
    assert len(r["puntos"]) <= min(80, r["total_en_zona"])

    burn = out["burn"]
    assert burn["disponible"] is True
    assert burn["dias"] == list(range(0, 61, 7))
    assert len(burn["sin_camion"]) == len(burn["dias"])
    assert burn["sin_camion"] == sorted(burn["sin_camion"], reverse=True)
    if burn["incoming_qty"] > 0:
        landed = next(i for i, d in enumerate(burn["dias"]) if d >= burn["lead_dias"])
        assert burn["con_camion"][landed] >= burn["sin_camion"][landed]
    if burn["stockout_day"] is not None:
        assert burn["stockout_day"] in burn["dias"]
        idx = burn["dias"].index(burn["stockout_day"])
        assert burn["sin_camion"][idx] == 0

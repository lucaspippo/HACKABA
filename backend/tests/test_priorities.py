"""Prioridades inbox: merge duplicates, rank act vs watch, role filter.

Synthetic tests do not need the demo dataset. Canonical merge on DEMO runs
in a subprocess (same pattern as test_p27 / test_p45).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from core import oportunidades_neg as opn
from core import priorities


def _item(id_, *, monto=0, band=None, tono="salvia", naturaleza=None, **extra):
    it = {
        "id": id_,
        "monto": monto,
        "tono": tono,
        "chip": id_,
        "titulo": id_,
        "resumen": id_,
        "origen": extra.pop("origen", [f"synthetic:{id_}"]),
        "modulos": extra.pop("modulos", ("oportunidades",)),
        "drill": extra.pop("drill", {"porque": [], "grafico": None,
                                     "involucrados": [], "supuestos": []}),
    }
    if band:
        it["band"] = band
    if naturaleza:
        it["naturaleza"] = naturaleza
    it.update(extra)
    return it


def test_merge_drops_alert_twins_when_opportunity_exists():
    items = [
        _item("cobrar_morosos", monto=100, origen=["oportunidad:cobrar_morosos"]),
        _item("morosos", monto=100, tono="rojo", origen=["alerta:morosos"]),
        _item("moroso_atraso", monto=40, tono="rojo", origen=["alerta:moroso_atraso"]),
        _item("quiebre_inminente", monto=1, origen=["oportunidad:quiebre_inminente"]),
        _item("quiebre", cifra_texto="12", origen=["alerta:quiebre"]),
        _item("pre_pico", monto=50, origen=["oportunidad:pre_pico"]),
        _item("pico", origen=["alerta:pico"]),
        _item("despertar_dormido", monto=80),
    ]
    merged = priorities.merge_duplicates(items)
    ids = [i["id"] for i in merged]
    assert ids.count("cobrar_morosos") == 1
    assert "morosos" not in ids and "moroso_atraso" not in ids
    assert "quiebre" not in ids and "pico" not in ids
    cob = next(i for i in merged if i["id"] == "cobrar_morosos")
    assert cob["tono"] == "rojo"
    assert "alerta:morosos" in cob["origen"]
    assert "oportunidad:cobrar_morosos" in cob["origen"]


def test_merge_keeps_alert_when_opportunity_absent():
    items = [
        _item("morosos", monto=12, tono="rojo", origen=["alerta:morosos"]),
        _item("quiebre", cifra_texto="3", origen=["alerta:quiebre"]),
    ]
    merged = priorities.merge_duplicates(items)
    ids = {i["id"] for i in merged}
    assert ids == {"morosos", "quiebre"}


def test_solicitud_pendiente_is_dropped():
    items = [
        _item("solicitud_pendiente", origen=["alerta:solicitud_pendiente"]),
        _item("despertar_dormido", monto=10),
    ]
    merged = priorities.merge_duplicates(items)
    assert [i["id"] for i in merged] == ["despertar_dormido"]


def test_rank_puts_leak_today_before_large_dormant_money():
    items = [
        _item("despertar_dormido", monto=68_000_000, tono="salvia"),
        _item("quiebre_inminente", cifra_texto="4 días", tono="rojo"),
        _item("cobrar_morosos", monto=85_000_000, tono="rojo"),
    ]
    act, watch = priorities.split_and_rank(items)
    assert [i["id"] for i in act] == ["cobrar_morosos", "quiebre_inminente",
                                      "despertar_dormido"]
    assert watch == []


def test_concentracion_and_cheques_go_to_watch():
    items = [
        _item("concentracion", monto=470_000_000, naturaleza="riesgo", tono="oro"),
        _item("cheques", monto=2_000_000, tono="azul"),
        _item("caja_inusual", monto=400_000, tono="oro"),
        _item("ventana_compra", monto=1_700_000, tono="salvia"),
    ]
    act, watch = priorities.split_and_rank(items)
    assert [i["id"] for i in act] == ["ventana_compra"]
    assert [i["id"] for i in watch] == ["concentracion", "cheques", "caja_inusual"]


def test_badge_is_len_act():
    inbox = {
        "act": [_item("a"), _item("b")],
        "watch": [_item("c")],
    }
    assert priorities.badge_of(inbox) == 2


def test_visibles_para_hides_cobranza_from_warehouse():
    items = [
        _item("cobrar_morosos", modulos=("cuentas",)),
        _item("quiebre_inminente", modulos=("inventario",)),
    ]
    vistos = priorities.visibles_para(items, ["inventario", "deposito"])
    assert [i["id"] for i in vistos] == ["quiebre_inminente"]


def test_visibles_para_none_keeps_all():
    items = [
        _item("cobrar_morosos", modulos=("cuentas",)),
        _item("quiebre_inminente", modulos=("inventario",)),
    ]
    assert [i["id"] for i in priorities.visibles_para(items, None)] == [
        "cobrar_morosos", "quiebre_inminente"]


def _en_demo(expr: str):
    backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_demo = os.path.join(os.path.dirname(backend), "data-demo")
    env = {**os.environ, "POLPILOT_TENANT": "demo", "POLPILOT_DATA_DIR": data_demo,
           "POLPILOT_DEMO_TODAY": "2026-07-07", "PYTHONIOENCODING": "utf-8"}
    env.pop("ANTHROPIC_API_KEY", None)
    r = subprocess.run(
        [sys.executable, "-c", f"import json; print(json.dumps({expr}))"],
        cwd=backend, env=env, capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr[-800:]
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_demo_inbox_has_no_duplicate_twins():
    d = _en_demo(
        "__import__('core.priorities', fromlist=['x']).inbox('es', "
        "['alertas','oportunidades','cuentas','inventario','deposito',"
        "'finanzas','caja','evolucion'])")
    ids = [i["id"] for i in d["act"]] + [i["id"] for i in d["watch"]]
    assert "morosos" not in ids and "moroso_atraso" not in ids
    assert "quiebre" not in ids
    assert "pico" not in ids
    assert "solicitud_pendiente" not in ids
    assert d["badge"] == len(d["act"])
    for w in d["watch"]:
        assert w["id"] not in {i["id"] for i in d["act"]}
    # leak-today (mora) ranks above dormant stock even if dormido is huge
    act_ids = [i["id"] for i in d["act"]]
    if "cobrar_morosos" in act_ids and "despertar_dormido" in act_ids:
        assert act_ids.index("cobrar_morosos") < act_ids.index("despertar_dormido")


def test_item_tipo_prefers_action_map_over_opportunity():
    it = priorities._item(
        id="quiebre", tono="rojo", chip="x", titulo="x", resumen="",
        origen=[], modulos=("inventario",), tipo="comprar")
    assert it["tipo"] == "reponer"


def test_item_tipo_keeps_opportunity_verb():
    it = priorities._item(
        id="despertar_dormido", tono="salvia", chip="x", titulo="x", resumen="",
        origen=[], modulos=("oportunidades",), tipo="liquidar")
    assert it["tipo"] == "liquidar"


def test_demo_warehouse_does_not_see_debtors():
    d = _en_demo(
        "__import__('core.priorities', fromlist=['x']).inbox('es', "
        "['inventario','deposito'])")
    ids = {i["id"] for i in d["act"]} | {i["id"] for i in d["watch"]}
    assert "cobrar_morosos" not in ids
    assert "concentracion" not in ids
    assert "quiebre_inminente" in ids


def test_demo_recuperable_matches_canonical_sum_for_full_role():
    d = _en_demo(
        "__import__('core.priorities', fromlist=['x']).inbox('es', "
        "['alertas','oportunidades','cuentas','inventario','deposito',"
        "'finanzas','caja','evolucion'])")
    canon = _en_demo(
        "__import__('core.oportunidades_neg', fromlist=['x']).recuperable(lang='es')")
    assert d["recuperable"]["disponible"] is True
    assert d["recuperable"]["total"] == canon["total"]
    assert {c["id"] for c in d["recuperable"]["componentes"]} == \
        {c["id"] for c in canon["componentes"]}


def test_demo_recuperable_hides_warehouse_exposure():
    d = _en_demo(
        "__import__('core.priorities', fromlist=['x']).inbox('es', "
        "['inventario','deposito'])")
    ids = {c["id"] for c in d["recuperable"]["componentes"]}
    assert "cobrar_morosos" not in ids

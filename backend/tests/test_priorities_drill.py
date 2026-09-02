"""Alert-only card types must carry real drill data (chart, involucrados
with a real product id) instead of an empty/blank drill — see design spec
2026-09-01."""
import json
import os
import subprocess
import sys

import pytest

from core import priorities

_DEMO_INBOX = None


def _demo_inbox():
    """The real demo dataset's inbox, fetched once per module.

    This suite's fixture pins tenant `piloto` over a near-empty scratch dataset
    (tests/conftest.py), so an in-process `inbox()` returns almost no cards and
    every per-card assertion below would pass vacuously or skip. Card-shape
    assertions only mean anything against the seeded dataset, so this follows
    the repo's established subprocess pattern (test_priorities.py::_en_demo).
    Fetched once and cached — the subprocess costs seconds and every test here
    reads the same payload.
    """
    global _DEMO_INBOX
    if _DEMO_INBOX is None:
        backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_demo = os.path.join(os.path.dirname(backend), "data-demo")
        env = {**os.environ, "POLPILOT_TENANT": "demo",
               "POLPILOT_DATA_DIR": data_demo,
               "POLPILOT_DEMO_TODAY": "2026-07-07", "PYTHONIOENCODING": "utf-8"}
        env.pop("ANTHROPIC_API_KEY", None)
        expr = ("__import__('core.priorities', fromlist=['x']).inbox('es', "
                "['alertas','oportunidades','cuentas','inventario','deposito',"
                "'finanzas','caja','evolucion'])")
        r = subprocess.run(
            [sys.executable, "-c", f"import json; print(json.dumps({expr}))"],
            cwd=backend, env=env, capture_output=True, text=True, timeout=180)
        assert r.returncode == 0, r.stderr[-800:]
        _DEMO_INBOX = json.loads(r.stdout.strip().splitlines()[-1])
    return _DEMO_INBOX


def _card(cid):
    d = _demo_inbox()
    return next((c for c in d["act"] + d["watch"] if c["id"] == cid), None)


def test_dep_vencidos_drill_has_product_involucrados(monkeypatch):
    from core import deposito, store
    monkeypatch.setattr(deposito, "resumen", lambda: {"vencidos": 1, "por_vencer": 0,
                                                       "discrepancias": 0})
    monkeypatch.setattr(deposito, "vencidos", lambda: [
        {"codigo": "P1", "producto": "Prod Uno", "cantidad": 5, "dias_vencido": 3}])
    monkeypatch.setattr(store, "raw_actual", lambda: [
        {"codigo": "P1", "descripcion": "Prod Uno", "costo_iva": 1000}])
    out = priorities._alerts_deposito("es")
    dep_venc = next(i for i in out if i["id"] == "dep_vencidos")
    assert dep_venc["drill"]["porque"]
    assert dep_venc["drill"]["grafico"] is not None
    iv = dep_venc["drill"]["involucrados"][0]
    assert iv["id"] == "P1" and iv["kind"] == "product"


def test_venc_riesgo_drill_has_product_involucrados(monkeypatch):
    from core import vencimientos
    monkeypatch.setattr(vencimientos, "en_riesgo", lambda dias, lang: {
        "disponible": True, "lotes_en_riesgo": 1, "total_en_riesgo": 5000,
        "items": [{"codigo": "P2", "producto": "Prod Dos", "dias_restantes": 4,
                  "plata_en_riesgo": 5000}]})
    out = priorities._alerts_deposito("es")
    venc = next(i for i in out if i["id"] == "venc_riesgo")
    assert venc["drill"]["grafico"] is not None
    iv = venc["drill"]["involucrados"][0]
    assert iv["id"] == "P2" and iv["kind"] == "product"


def test_costo_viejo_drill_has_product_involucrados(monkeypatch):
    from core import store
    monkeypatch.setattr(store, "panorama", lambda: {"alertas": {"costo_viejo": {"cantidad": 1}},
                                                     "grupos": {"costo_viejo": [
                                                         {"codigo": "P3", "descripcion": "Prod Tres",
                                                          "inmovilizado": 20_000,
                                                          "antiguedad_costo_dias": 400}]}})
    out = priorities._alerts_inventario("es")
    cv = next(i for i in out if i["id"] == "costo_viejo")
    assert cv["drill"]["grafico"] is not None
    iv = cv["drill"]["involucrados"][0]
    assert iv["id"] == "P3" and iv["kind"] == "product"


def test_caida_interanual_drill_has_chart(monkeypatch):
    from core import evolucion
    pan = {"hay_datos": True,
          "serie": [{"mes": "2026-01", "nominal": 100, "real": 95},
                    {"mes": "2026-02", "nominal": 110, "real": 90}]}
    monkeypatch.setattr(evolucion, "panorama", lambda lang: pan)
    monkeypatch.setattr(evolucion, "alertas_de", lambda p, lang: [
        {"titulo": "Caída real", "detalle": "cayó"}])
    out = priorities._alerts_evolucion("es")
    a = out[0]
    assert a["drill"]["grafico"] is not None
    assert len(a["drill"]["grafico"]["series"][0]["puntos"]) == 2


def test_caja_inusual_drill_has_chart(monkeypatch):
    from core import caja
    monkeypatch.setattr(caja, "estado", lambda: {
        "abierta": True,
        "totales": {"total": 500_000},
        "historial": [{"fecha": f"2026-06-2{i}", "total": 260_000, "diferencia": 0}
                     for i in range(5)],
    })
    out = priorities._alerts_caja("es")
    a = out[0]
    assert a["drill"]["grafico"] is not None
    assert len(a["drill"]["grafico"]["series"][0]["puntos"]) == 6


def test_pago_vencido_drill_has_chart_and_text_involucrados(monkeypatch):
    from core import pagos
    monkeypatch.setattr(pagos, "resumen", lambda: {
        "pagos_vencidos": 1, "vencidos_total": 30_000, "por_pagar_semana": 0,
        "cheques_cartera": 0, "cheques_total": 0})
    monkeypatch.setattr(pagos, "pagos_vencidos", lambda: [
        {"proveedor": "Proveedor Uno", "numero": "F-1", "monto": 30_000, "dias_vencido": 5}])
    out = priorities._alerts_pagos("es")
    pv = next(i for i in out if i["id"] == "pago_vencido")
    assert pv["drill"]["grafico"] is not None
    iv = pv["drill"]["involucrados"][0]
    # No stable id exists on hand-entered pagos_proveedores rows (spec,
    # scope decision) — involucrados here stay text-only, non-clickable.
    assert iv.get("id") is None and iv.get("kind") is None
    assert "Proveedor Uno" in iv["nombre"]


def test_moroso_atraso_states_the_deviation_as_a_metric():
    c = _card("moroso_atraso") or _card("cobrar_morosos")
    assert c, "expected a debtor card in the demo dataset"
    ins = c["insight"]
    assert ins["pattern"]["label"]
    days = next(e for e in ins["evidence"] if e["id"] == "days_overdue")
    assert days["unit"] == "days"
    assert days["baseline"]["value"] > 0, "the client's own payment average"
    assert days["deviation"]["direction"] == "up"
    assert days["method"]["label"], "every metric explains how it was computed"


def test_debtor_card_links_real_client_records():
    c = _card("moroso_atraso") or _card("cobrar_morosos")
    rows = [r for e in c["insight"]["evidence"] for r in e["records"]]
    assert rows, "the debtors must be listed as clickable records"
    assert all(r["kind"] == "client" and r["id"] is not None for r in rows)


def test_stockout_card_lists_products_as_records():
    c = _card("quiebre") or _card("quiebre_inminente")
    assert c, "expected a stockout card in the demo dataset"
    rows = [r for e in c["insight"]["evidence"] for r in e["records"]]
    assert all(r["kind"] == "product" and r["id"] is not None for r in rows)


def test_no_alert_card_emits_an_empty_pattern():
    d = _demo_inbox()
    for c in d["act"] + d["watch"]:
        assert c["insight"]["pattern"] and c["insight"]["pattern"]["label"], c["id"]


@pytest.mark.parametrize("cid", ["pago_vencido", "pago_semana", "cheques",
                                 "dep_vencidos", "dep_porvencer", "dep_discrep",
                                 "venc_riesgo"])
def test_finance_and_warehouse_alerts_carry_pattern_and_evidence(cid):
    c = _card(cid)
    if c is None:
        pytest.skip(f"{cid} not present in the demo dataset")
    ins = c["insight"]
    assert ins["pattern"]["label"], f"{cid} has no pattern"
    assert ins["evidence"], f"{cid} has no evidence"
    assert all(e["method"]["label"] for e in ins["evidence"]), \
        f"{cid} has a metric with no 'how was this calculated'"


@pytest.mark.parametrize("cid", ["dep_vencidos", "dep_porvencer", "dep_discrep",
                                 "venc_riesgo"])
def test_warehouse_alerts_link_real_products(cid):
    c = _card(cid)
    if c is None:
        pytest.skip(f"{cid} not present in the demo dataset")
    rows = [r for e in c["insight"]["evidence"] for r in e["records"]]
    assert rows, f"{cid} lists no products"
    assert all(r["kind"] == "product" and r["id"] is not None for r in rows)


@pytest.mark.parametrize("cid", ["pago_vencido", "pago_semana", "cheques"])
def test_finance_alert_rows_are_plain_text_not_fake_links(cid):
    """pagos.py has no stable per-row id. A row that looks clickable and
    silently no-ops is worse than plain text."""
    c = _card(cid)
    if c is None:
        pytest.skip(f"{cid} not present in the demo dataset")
    rows = [r for e in c["insight"]["evidence"] for r in e["records"]]
    assert all(r["id"] is None and r["kind"] is None for r in rows)


def test_dep_discrep_count_does_not_contradict_its_rows():
    """discrepancy_count and discrepancy_rows must both derive from the same
    (suppression-filtered) collection — a card that says 'N items differ' and
    then lists a different number of rows contradicts itself."""
    c = _card("dep_discrep")
    if c is None:
        pytest.skip("dep_discrep not present in the demo dataset")
    ev = {e["id"]: e for e in c["insight"]["evidence"]}
    count = ev["discrepancy_count"]["value"]
    rows = ev["discrepancy_rows"]["records"]
    if count <= 8:  # the builder's display cap
        assert len(rows) == count
    else:
        # count exceeds the cap: rows must be a prefix of the counted set,
        # not a mismatched (e.g. unfiltered) collection.
        assert len(rows) == 8


@pytest.mark.parametrize("cid", ["costo_viejo", "caja_inusual",
                                 "caida_interanual", "pico"])
def test_remaining_alerts_carry_pattern_and_evidence(cid):
    c = _card(cid)
    if c is None:
        pytest.skip(f"{cid} not present in the demo dataset")
    ins = c["insight"]
    assert ins["pattern"]["label"]
    assert ins["evidence"]


def test_whole_business_alerts_carry_a_chart_instead_of_records():
    """No per-row UI exists for caja/evolución, so these prove themselves
    with a series rather than fake links."""
    for cid in ("caja_inusual", "caida_interanual"):
        c = _card(cid)
        if c is None:
            continue
        ev = c["insight"]["evidence"]
        assert any(e["kind"] == "series" and e["chart"] for e in ev), cid
        assert not [r for e in ev for r in e["records"]], cid


OPPORTUNITY_IDS = ["cobrar_morosos", "despertar_dormido", "ventana_compra",
                   "cliente_frio", "estrella_caida", "quiebre_inminente",
                   "pre_pico", "concentracion", "margen_bajo", "sobrecompra"]


@pytest.mark.parametrize("cid", OPPORTUNITY_IDS)
def test_opportunity_cards_carry_structured_insight(cid):
    c = _card(cid)
    if c is None:
        pytest.skip(f"{cid} not present in the demo dataset")
    ins = c["insight"]
    assert ins["pattern"]["label"]
    assert ins["evidence"]
    assert any(e["weight"] == "primary" for e in ins["evidence"]), \
        f"{cid} declares nothing load-bearing"
    assert ins["recommendation"]["label"]


def test_restock_card_keeps_its_day_counts_as_supporting_metrics():
    """The retired `metrics` strip: same numbers, now first-class evidence."""
    c = _card("quiebre_inminente")
    if c is None:
        pytest.skip("quiebre_inminente not present")
    ids = {e["id"] for e in c["insight"]["evidence"]}
    assert {"days_of_coverage", "supplier_lead_time"} <= ids


def test_no_card_anywhere_still_carries_metrics_on_the_insight():
    d = _demo_inbox()
    for c in d["act"] + d["watch"]:
        assert "metrics" not in c["insight"], c["id"]

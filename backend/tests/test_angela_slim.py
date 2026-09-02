"""angela._slim — a projection, never a second computation."""
from core import insight as ins

import angela


def _card():
    chart = {"ok": True, "series": [{"nombre": "s", "puntos": [{"x": 1, "y": 2}]}],
             "meta": {}}
    return {
        "id": "cobrar_morosos", "chip": "Cobrar", "titulo": "t", "resumen": "r",
        "monto": 85700000, "cifra_texto": None, "tono": "rojo", "band": "act",
        "insight": ins.build(
            pattern=ins.pattern("3 clientes concentran la mora"),
            hypothesis=ins.hypothesis("cambió el comportamiento de pago"),
            evidence=[
                ins.metric("overdue_total", label="$85.700.000", value=85700000,
                           unit="ars", weight="primary",
                           baseline={"value": 40000000, "label": "mes pasado"},
                           method={"key": "k", "label": "Suma de saldos vencidos"},
                           records=[ins.record(kind="client", id=i, name=f"c{i}")
                                    for i in range(9)]),
                ins.series("hist", label="serie", chart=chart,
                           method={"key": "k", "label": "l"}, weight="supporting"),
            ],
            assumptions=[ins.assumption("sin pagos en efectivo", if_wrong="menor")],
            risk=ins.risk("capital en la calle", exposure=85700000),
        ) | {"confidence": {"data": {"level": "high", "reason": "r", "signals": {"x": 1}},
                            "hypothesis": {"level": "low", "reason": "r", "signals": {}}},
             "owner": {"suggested": "Marina", "role": "Cobranzas", "reason": "cuentas"},
             "deadline": {"date": "2026-07-14", "basis": "b", "urgency": "this_week"}},
    }


def test_only_primary_evidence_reaches_the_model():
    s = angela._slim(_card())
    assert [e["id"] for e in s["insight"]["evidence"]] == ["overdue_total"]


def test_charts_are_dropped():
    """Series points are for rendering, not reasoning."""
    s = angela._slim(_card())
    assert all("chart" not in e for e in s["insight"]["evidence"])


def test_records_are_capped_but_the_total_is_reported():
    s = angela._slim(_card())
    ev = s["insight"]["evidence"][0]
    assert len(ev["records"]) == 3
    assert ev["records_total"] == 9


def test_values_are_passed_through_untouched_never_reformatted():
    """The deterministic invariant: the projection selects, it does not
    compute or format. A pesos string here would be Angela's number, not
    core's."""
    card = _card()
    s = angela._slim(card)
    src = card["insight"]["evidence"][0]
    out = s["insight"]["evidence"][0]
    assert out["value"] == src["value"] and out["value"] == 85700000
    assert out["baseline"] == src["baseline"]
    assert out["deviation"] == src["deviation"]


def test_confidence_levels_survive_but_signals_do_not():
    s = angela._slim(_card())["insight"]["confidence"]
    assert s["data"] == "high" and s["hypothesis"] == "low"


def test_envelope_keys_are_unchanged():
    s = angela._slim(_card())
    for k in ("id", "chip", "titulo", "resumen", "monto", "cifra_texto", "tono", "band"):
        assert k in s

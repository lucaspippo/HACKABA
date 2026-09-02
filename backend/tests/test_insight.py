"""core/insight.py — the constructor vocabulary every card builder uses."""
import pytest

from core import insight


def test_metric_derives_deviation_from_baseline():
    m = insight.metric(
        "days_overdue", label="66 días contra 31", value=66, unit="days",
        baseline={"value": 31, "label": "promedio histórico"},
        method={"key": "core.method.dias_mora", "label": "Días desde la última cobranza"},
    )
    assert m["deviation"] == {"pct": 113, "direction": "up"}


def test_metric_deviation_direction_is_down_when_below_baseline():
    m = insight.metric(
        "margin", label="12% contra 20%", value=12, unit="pct",
        baseline={"value": 20, "label": "margen objetivo"},
        method={"key": "core.method.margen", "label": "Margen sobre costo"},
    )
    assert m["deviation"] == {"pct": 40, "direction": "down"}


@pytest.mark.parametrize("baseline", [None, {"value": 0, "label": "cero"}])
def test_metric_deviation_is_none_without_a_usable_baseline(baseline):
    """No baseline, or a zero baseline: no meaningful percentage exists."""
    m = insight.metric(
        "count", label="3 clientes", value=3, unit="clients", baseline=baseline,
        method={"key": "core.method.conteo", "label": "Conteo"},
    )
    assert m["deviation"] is None


def test_evidence_weight_defaults_to_supporting():
    """A builder must OPT IN to claiming an item is load-bearing."""
    m = insight.metric("x", label="x", value=1, unit="u",
                       method={"key": "k", "label": "l"})
    assert m["weight"] == "supporting"


def test_build_fills_every_contract_key():
    i = insight.build(pattern=insight.pattern("3 clientes concentran la mora"))
    assert set(i) == {
        "pattern", "hypothesis", "evidence", "assumptions", "alternatives",
        "falsifiers", "risk", "recommendation", "owner", "deadline", "confidence",
    }
    assert i["hypothesis"] is None
    assert i["evidence"] == []
    assert i["owner"] is None          # derived later, in _compose
    assert i["confidence"] is None     # derived later, in _compose


def test_records_carries_rows_and_kind():
    r = insight.records(
        "debtors", label="Clientes en mora",
        rows=[insight.record(kind="client", id="c-142", name="Doña Elsa", amount=1000)],
        method={"key": "k", "label": "l"}, weight="primary",
    )
    assert r["kind"] == "records"
    assert r["records"][0] == {"kind": "client", "id": "c-142",
                              "name": "Doña Elsa", "amount": 1000, "detail": None}


def test_blank_is_a_fresh_object_each_call():
    """Shared mutable default would leak evidence between cards."""
    a, b = insight.blank(), insight.blank()
    a["evidence"].append({"id": "x"})
    assert b["evidence"] == []

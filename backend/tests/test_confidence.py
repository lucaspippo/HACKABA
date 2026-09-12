"""core/confidence.py — the two axes must move independently."""
from core import confidence
from core import insight


def _chart(points: int) -> dict:
    return {"ok": True,
            "series": [{"nombre": "s", "puntos": [{"x": i, "y": i} for i in range(points)]}],
            "meta": {}}


def _insight(*, points=0, records=0, assumptions=0, alternatives=0):
    ev = []
    if points:
        ev.append(insight.series("s", label="l", chart=_chart(points),
                                 method={"key": "k", "label": "l"}))
    if records:
        ev.append(insight.records(
            "r", label="l",
            rows=[insight.record(kind="client", id=i, name=str(i)) for i in range(records)],
            method={"key": "k", "label": "l"}))
    return insight.build(
        pattern=insight.pattern("p"),
        evidence=ev,
        assumptions=[insight.assumption(f"a{i}") for i in range(assumptions)],
        alternatives=[insight.caveat(f"c{i}") for i in range(alternatives)],
    )


def test_rich_data_and_many_assumptions_disagree():
    """The assertion that was impossible before the split."""
    c = confidence.split_for(_insight(points=12, assumptions=3))
    assert c["data"]["level"] == "high"
    assert c["hypothesis"]["level"] == "low"


def test_thin_data_and_no_assumptions_disagree_the_other_way():
    c = confidence.split_for(_insight(points=0, assumptions=0))
    assert c["data"]["level"] == "low"
    assert c["hypothesis"]["level"] == "high"


def test_records_count_toward_data_confidence_without_a_chart():
    """An alert with no chart but eight real rows is not low-data."""
    c = confidence.split_for(_insight(points=0, records=8))
    assert c["data"]["level"] == "medium"


def test_declared_alternatives_lower_hypothesis_confidence():
    """More competing explanations means LESS certainty, not more."""
    few = confidence.split_for(_insight(points=6, alternatives=0))
    many = confidence.split_for(_insight(points=6, alternatives=3))
    order = {"low": 0, "medium": 1, "high": 2}
    assert order[many["hypothesis"]["level"]] < order[few["hypothesis"]["level"]]


def test_signals_are_exposed_for_the_ui():
    c = confidence.split_for(_insight(points=12, records=3, assumptions=1))
    assert c["data"]["signals"]["chart_points"] == 12
    assert c["data"]["signals"]["record_count"] == 3
    assert c["hypothesis"]["signals"]["assumptions"] == 1


def test_both_axes_always_carry_a_reason_string():
    c = confidence.split_for(_insight())
    assert c["data"]["reason"] and c["hypothesis"]["reason"]

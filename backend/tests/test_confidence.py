"""core/confidence.py — the two axes must move independently."""
from core import confidence
from core import insight


def _chart(points: int) -> dict:
    return {"ok": True,
            "series": [{"nombre": "s", "puntos": [{"x": i, "y": i} for i in range(points)]}],
            "meta": {}}


def _insight(*, points=0, records=0, assumptions=0, alternatives=0, knowledge=()):
    ev = []
    if points:
        ev.append(insight.series("s", label="l", chart=_chart(points),
                                 method={"key": "k", "label": "l"}))
    if records:
        ev.append(insight.records(
            "r", label="l",
            rows=[insight.record(kind="client", id=i, name=str(i)) for i in range(records)],
            method={"key": "k", "label": "l"}))
    for k in knowledge:
        ev.append(k)
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


def _knowledge_evidence(*, fresh: bool) -> dict:
    """A hand-built knowledge-kind evidence item, bypassing insight.knowledge()
    (which needs a real DB-backed piece) — confidence.py only needs the
    evidence dict's shape, not a live piece."""
    return {"id": "k01", "kind": "knowledge", "label": "x", "value": None,
            "unit": None, "baseline": None, "deviation": None, "weight": "supporting",
            "method": {"source": "conocimiento", "tipo": "regla"}, "records": [], "chart": None,
            "origen": {}, "freshness": "fresco" if fresh else "revisar",
            "needs_review": not fresh}


def test_knowledge_evidence_counts_toward_data_confidence():
    c = confidence.split_for(_insight(knowledge=[_knowledge_evidence(fresh=True),
                                                 _knowledge_evidence(fresh=True)]))
    assert c["data"]["level"] == "medium"  # 2 knowledge items == DATA_MEDIUM_RECORDS
    assert c["data"]["signals"]["record_count"] == 2


def test_knowledge_evidence_never_affects_hypothesis_confidence():
    c = confidence.split_for(_insight(knowledge=[_knowledge_evidence(fresh=True)]))
    assert c["hypothesis"]["level"] == "high"  # no assumptions/alternatives declared


def test_sources_stale_true_when_any_cited_knowledge_needs_review():
    c = confidence.split_for(_insight(
        knowledge=[_knowledge_evidence(fresh=True), _knowledge_evidence(fresh=False)]))
    assert c["data"]["signals"]["sources_stale"] is True


def test_sources_stale_false_with_no_stale_knowledge():
    c = confidence.split_for(_insight(knowledge=[_knowledge_evidence(fresh=True)]))
    assert c["data"]["signals"]["sources_stale"] is False


def test_sources_stale_false_with_no_knowledge_evidence_at_all():
    c = confidence.split_for(_insight(points=12))
    assert c["data"]["signals"]["sources_stale"] is False

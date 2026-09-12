"""Shared confidence signal: generic, not per-card-type (see design spec
2026-09-01). Signals: chart data points (sample size proxy) and number of
declared assumptions."""
from core import confidence


def _drill(points=0, assumptions=0):
    grafico = None
    if points:
        grafico = {"ok": True, "series": [{"nombre": "x",
                   "puntos": [{"x": i, "y": i} for i in range(points)]}],
                   "meta": {}}
    return {"grafico": grafico, "supuestos": ["a"] * assumptions}


def test_high_confidence_needs_enough_points_and_no_assumptions():
    out = confidence.level_for(_drill(points=6, assumptions=0), "en")
    assert out["level"] == "high"
    assert "6" in out["reason"]


def test_medium_confidence_with_some_points_or_one_assumption():
    assert confidence.level_for(_drill(points=3, assumptions=0), "en")["level"] == "medium"
    assert confidence.level_for(_drill(points=1, assumptions=1), "en")["level"] == "medium"


def test_low_confidence_with_little_data_and_multiple_assumptions():
    out = confidence.level_for(_drill(points=1, assumptions=2), "en")
    assert out["level"] == "low"


def test_no_chart_and_no_assumptions_is_still_low():
    """A finding with nothing behind it (no chart, no declared assumptions)
    must not read as confident by default — absence of assumptions is not
    evidence of confidence."""
    out = confidence.level_for(_drill(points=0, assumptions=0), "en")
    assert out["level"] == "low"


def test_reason_is_translated():
    out_es = confidence.level_for(_drill(points=6, assumptions=0), "es")
    out_en = confidence.level_for(_drill(points=6, assumptions=0), "en")
    assert out_es["reason"] != out_en["reason"]

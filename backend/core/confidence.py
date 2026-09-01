"""Shared confidence signal for every Prioridades card, computed from
generic signals already present on any drill (backend/core/priorities.py
composes it, per card, once — no per-card-type confidence logic).

The rule of thumb: a finding backed by a real chart with several data
points and no undeclared leaps of assumption reads as high confidence; a
finding with a thin chart or several assumptions reads as low. This is
intentionally coarse — it is a reading aid, not a statistical model."""
from __future__ import annotations

HIGH_POINTS = 6
MEDIUM_POINTS = 3
MEDIUM_MAX_ASSUMPTIONS = 1


def _chart_points(grafico: dict | None) -> int:
    if not grafico or not grafico.get("series"):
        return 0
    return max((len(s.get("puntos") or []) for s in grafico["series"]), default=0)


def level_for(drill: dict, lang: str | None = None) -> dict:
    import i18n
    points = _chart_points(drill.get("grafico"))
    assumptions = len(drill.get("supuestos") or [])
    if points >= HIGH_POINTS and assumptions == 0:
        level = "high"
        reason = i18n.t("core.confidence.reason_high", lang, points=points)
    elif points >= MEDIUM_POINTS or (points > 0 and assumptions <= MEDIUM_MAX_ASSUMPTIONS):
        level = "medium"
        reason = i18n.t("core.confidence.reason_medium", lang, points=points,
                        assumptions=assumptions)
    else:
        level = "low"
        reason = i18n.t("core.confidence.reason_low", lang, points=points,
                        assumptions=assumptions)
    return {"level": level, "reason": reason}


"""Confidence for a Prioridades card, split along the seam that matters.

Two questions the owner asks separately, and that a single level cannot
answer:

  data       — how much evidence is behind this? (chart points, real
               records, freshness)
  hypothesis — how big is the interpretive leap? (declared assumptions,
               competing explanations)

They can disagree, and when they do that IS the information: twelve months
of clean history read through three assumptions is high-data,
low-hypothesis, and the owner should see both.

Deliberately coarse — a reading aid, not a statistical model. Computed once
per card, centrally, in priorities._compose; no per-card-type logic.
"""

DATA_HIGH_POINTS = 6
DATA_MEDIUM_POINTS = 3
DATA_MEDIUM_RECORDS = 2


def _insight_chart_points(insight: dict) -> int:
    """Longest series across every piece of evidence carrying a chart."""
    best = 0
    for ev in insight.get("evidence") or []:
        chart = ev.get("chart")
        if not chart or not chart.get("series"):
            continue
        best = max(best, max((len(s.get("puntos") or [])
                              for s in chart["series"]), default=0))
    return best


def _insight_record_count(insight: dict) -> int:
    return sum(len(ev.get("records") or []) for ev in insight.get("evidence") or [])


def _data_level(points: int, records: int) -> str:
    """Records give breadth; only a series gives history. A card with many
    rows and no chart tops out at medium — breadth alone is not depth."""
    if points >= DATA_HIGH_POINTS:
        return "high"
    if points >= DATA_MEDIUM_POINTS or records >= DATA_MEDIUM_RECORDS:
        return "medium"
    return "low"


def _hypothesis_level(assumptions: int, alternatives: int) -> str:
    """Both signals push the same way: every declared assumption and every
    competing explanation is a reason to trust the reading less. Declaring
    them is honest, and honesty should show as lower confidence, not
    higher."""
    leaps = assumptions + alternatives
    if leaps == 0:
        return "high"
    if leaps <= 2:
        return "medium"
    return "low"


def split_for(insight: dict, lang: str | None = None) -> dict:
    """Confidence in the data behind an insight, and confidence in the
    hypothesis drawn from it, as two independent axes."""
    import i18n
    points = _insight_chart_points(insight)
    records = _insight_record_count(insight)
    assumptions = len(insight.get("assumptions") or [])
    alternatives = len(insight.get("alternatives") or [])

    data_level = _data_level(points, records)
    hyp_level = _hypothesis_level(assumptions, alternatives)
    hyp_key = {"high": "hyp_high", "medium": "hyp_medium", "low": "hyp_low"}[hyp_level]

    return {
        "data": {
            "level": data_level,
            "reason": i18n.t(f"core.confidence.data_{data_level}", lang,
                             points=points, records=records),
            "signals": {"chart_points": points, "record_count": records,
                        "sources_stale": False, "missing": []},
        },
        "hypothesis": {
            "level": hyp_level,
            "reason": i18n.t(f"core.confidence.{hyp_key}", lang,
                             assumptions=assumptions, alternatives=alternatives),
            "signals": {"assumptions": assumptions, "alternatives": alternatives},
        },
    }

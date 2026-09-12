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
from __future__ import annotations

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
    """Real rows give breadth; a cited knowledge piece is as much "a real
    thing behind this" as a database row, so it counts the same way."""
    from_records = sum(len(ev.get("records") or []) for ev in insight.get("evidence") or [])
    from_knowledge = sum(1 for ev in insight.get("evidence") or [] if ev.get("kind") == "knowledge")
    return from_records + from_knowledge


def _sources_stale(insight: dict) -> bool:
    """True when ANY cited knowledge evidence is due for review — errs
    toward surfacing the caveat, same "declare it and let confidence show
    it" philosophy as _hypothesis_level."""
    return any(ev.get("needs_review") for ev in insight.get("evidence") or []
              if ev.get("kind") == "knowledge")


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
                        "sources_stale": _sources_stale(insight), "missing": []},
        },
        "hypothesis": {
            "level": hyp_level,
            "reason": i18n.t(f"core.confidence.{hyp_key}", lang,
                             assumptions=assumptions, alternatives=alternatives),
            "signals": {"assumptions": assumptions, "alternatives": alternatives},
        },
    }

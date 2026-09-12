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

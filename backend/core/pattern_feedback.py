"""Shared feedback-and-memory mechanism for any core/*.py finding that
carries an `id` + `fingerprint` — used identically by core/patrones.py's
learned patterns and core/oportunidades_neg.py's fixed rule set. Feedback
lands in the SAME table (core/db/pattern_feedback_repo.py) no matter which
module produced the finding: `pattern_id` there is just the finding's own
`id`, and nothing about the storage assumes it came from a learned pattern
rather than a hand-coded rule.

The two detection philosophies stay separate modules on purpose (a fixed,
closed, heavily-tested rule set vs. an open-ended statistical one) — this
module is only the part that both can safely share: "the owner already
reacted to this exact instance, don't show it again."
"""
from __future__ import annotations

from typing import Callable


def feedback_key(finding_id: str, fingerprint: str | None) -> str:
    return f"{finding_id}:{fingerprint}"


def drop_handled(findings: list[dict]) -> list[dict]:
    """Drop any finding the owner already reacted to (accepted / dismissed /
    already knew) — same "no dato, no card" spirit as a detector's own
    thresholds, just triggered by the owner's word instead of a statistic.
    A genuinely different instance (a different fingerprint) still shows up
    normally. Fails open: a lookup error must never hide every finding."""
    from core.db import pattern_feedback_repo
    from core.db import tenant as _tenant
    try:
        handled = pattern_feedback_repo.latest_by_fingerprint(_tenant.current_tenant_id())
    except Exception:  # noqa: BLE001
        return findings
    return [f for f in findings if feedback_key(f["id"], f.get("fingerprint")) not in handled]


def record(compute_current: Callable[[], list[dict]], finding_id: str, action: str, *,
          actor: str, note: str | None = None) -> dict:
    """Record the owner's reaction to the CURRENTLY live finding `finding_id`
    (recomputed via `compute_current`, e.g. `lambda: patrones.cards(lang)`),
    snapshotting its display text so a later history view can still show
    what it was about after it stops firing. Raises KeyError if that finding
    isn't live right now (a stale request against an outdated inbox, or
    feedback already given on this exact instance)."""
    from core.db import pattern_feedback_repo
    from core.db import tenant as _tenant
    from . import analisis_cache
    current = next((f for f in compute_current() if f["id"] == finding_id), None)
    if not current or not current.get("fingerprint"):
        raise KeyError(f"no live finding for id={finding_id!r}")
    snapshot = {"titulo": current.get("titulo"), "resumen": current.get("resumen"),
               "monto": current.get("monto"), "monto_label": current.get("monto_label")}
    row = pattern_feedback_repo.create(
        _tenant.current_tenant_id(), pattern_id=finding_id,
        fingerprint=current["fingerprint"], action=action, actor=actor,
        snapshot=snapshot, note=note)
    # Both /api/oportunidades and priorities.inbox() cache their compose
    # (core/analisis_cache.py) — without this, a just-recorded reaction
    # wouldn't hide its finding until something ELSE happened to bust the
    # cache first (bumping the shared generation clears every cached key).
    analisis_cache.datos_cambiaron()
    return row


def history(limit: int = 50) -> list[dict]:
    """Every feedback event this tenant has given, across every source,
    most recent first — the owner's own record of what Ángela flagged and
    what came of it."""
    from core.db import pattern_feedback_repo
    from core.db import tenant as _tenant
    return pattern_feedback_repo.history(_tenant.current_tenant_id(), limit)

"""The structured insight every Prioridades card carries.

One fixed shape for every finding, so cards are comparable and the UI,
Ángela and the tests all read the same thing:

    Pattern → Hypothesis → Evidence → Assumptions → Risk
            → Recommended action → Owner → Deadline

This module is pure vocabulary: constructors that validate shape and derive
what can be derived locally (a deviation from a value and its baseline).
It performs no I/O, resolves no tenant and reads no dataset — builders in
priorities.py / oportunidades_neg.py / patrones.py / piso.py supply the
domain values, and core/priorities.py::_compose fills the fields that can
only be derived once the whole insight exists (owner, confidence, risk
level, deadline urgency).

Per the deterministic-core invariant (repo CLAUDE.md), every value that
lands here was calculated upstream. Nothing in this file invents a number.
"""
from __future__ import annotations

WEIGHTS = ("primary", "supporting")


def blank() -> dict:
    """An insight with no content. A fresh object every call — a shared
    default would leak evidence from one card into the next."""
    return build(pattern=None)


def build(*, pattern=None, hypothesis=None, evidence=(), assumptions=(),
          alternatives=(), falsifiers=(), risk=None, recommendation=None,
          deadline=None) -> dict:
    """Assemble one card's insight.

    `owner`, `confidence` and the derived halves of `risk`/`deadline` are
    left for _compose: they need the finished insight (and, for owner, the
    tenant's team) and cannot be known here.
    """
    return {
        "pattern": pattern,
        "hypothesis": hypothesis,
        "evidence": list(evidence),
        "assumptions": list(assumptions),
        "alternatives": list(alternatives),
        "falsifiers": list(falsifiers),
        "risk": risk,
        "recommendation": recommendation,
        "owner": None,
        "deadline": deadline,
        "confidence": None,
    }


def pattern(label: str, *, since: str | None = None,
            scope: dict | None = None) -> dict:
    """The observation, with no interpretation in it."""
    return {"label": label, "since": since, "scope": scope}


def hypothesis(label: str) -> dict:
    """The interpretive leap, kept separate from the observation."""
    return {"label": label}


def _deviation(value, baseline: dict | None) -> dict | None:
    """Percentage gap between a value and its baseline.

    None when there is no baseline, or the baseline is zero — no meaningful
    percentage exists, and a divide-by-zero guard that returned 0 or inf
    would be a made-up number on a card that promises calculated ones.
    """
    if not baseline:
        return None
    base = baseline.get("value")
    if not base:  # None or 0
        return None
    delta = (float(value) - float(base)) / abs(float(base))
    return {"pct": round(abs(delta) * 100), "direction": "up" if delta >= 0 else "down"}


def _evidence(id, kind, *, label, method, weight, value=None, unit=None,
              baseline=None, deviation=None, records=(), chart=None) -> dict:
    if weight not in WEIGHTS:
        raise ValueError(f"weight must be one of {WEIGHTS}, got {weight!r}")
    return {
        "id": id, "kind": kind, "label": label,
        "value": value, "unit": unit, "baseline": baseline,
        "deviation": deviation, "weight": weight, "method": method,
        "records": list(records), "chart": chart,
    }


def metric(id: str, *, label: str, value, unit: str, method: dict,
           baseline: dict | None = None, weight: str = "supporting",
           records=(), chart=None) -> dict:
    """One number that supports the conclusion, with how it was computed.

    `weight` defaults to "supporting": a builder must opt in to calling an
    item load-bearing, which is what the UI expands and what Ángela sees.
    """
    return _evidence(id, "metric", label=label, method=method, weight=weight,
                     value=value, unit=unit, baseline=baseline,
                     deviation=_deviation(value, baseline),
                     records=records, chart=chart)


def records(id: str, *, label: str, rows, method: dict,
            weight: str = "supporting") -> dict:
    """The real rows behind a claim — the owner can click through to them."""
    return _evidence(id, "records", label=label, method=method, weight=weight,
                     records=rows)


def series(id: str, *, label: str, chart: dict, method: dict,
           weight: str = "supporting") -> dict:
    """A Contract P21 chart as evidence for a claim."""
    return _evidence(id, "series", label=label, method=method, weight=weight,
                     chart=chart)


def record(*, kind: str, id, name: str, amount=None, detail: str | None = None) -> dict:
    """One clickable row. `kind` drives navigation ("client" → cuentas,
    "product" → inventario); an id with no kind has nowhere to land."""
    return {"kind": kind, "id": id, "name": name, "amount": amount, "detail": detail}


def assumption(label: str, *, if_wrong: str | None = None) -> dict:
    """A declared leap, and what it would mean for the finding to be wrong."""
    return {"label": label, "if_wrong": if_wrong}


def caveat(label: str) -> dict:
    """One alternative explanation, or one thing that would falsify this."""
    return {"label": label}


def risk(label: str, *, exposure=None) -> dict:
    """`exposure` is the money at stake if nothing is done — not always the
    card's `monto` (for dep_porvencer, monto is total lot value while only a
    fraction actually expires). `level` is derived in _compose."""
    return {"level": None, "label": label, "exposure": exposure}


def recommendation(label: str | None = None, *, detail: str | None = None,
                   proposal=None, navigate: str | None = None,
                   chat: str | None = None) -> dict:
    """The move. Consolidates what the card envelope scatters across
    titulo/chip/propuesta/navegar/accion_chat.

    `label` is OPTIONAL and belongs here only when the move is genuinely
    different from the card's own title: every card's `titulo` is already
    the move stated in the owner's language, and passing it again printed
    the same sentence twice in one panel (once as the heading, once as the
    recommendation). When it is absent the UI falls back to `titulo`.
    """
    return {"label": label, "detail": detail, "proposal": proposal,
            "navigate": navigate, "chat": chat}


def deadline(date: str, *, basis: str) -> dict:
    """`basis` says WHY this is the date (supplier lead time, lot expiry,
    ageing curve). `urgency` is derived in _compose against the dataset's
    today."""
    return {"date": date, "basis": basis, "urgency": None}

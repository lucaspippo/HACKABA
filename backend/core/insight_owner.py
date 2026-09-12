"""Suggest who on the team should own a Prioridades card.

A suggestion, never an assignment: the card says "Marina" because Marina is
the only person whose access covers cuentas corrientes, not because anybody
decided. Assignment (and overriding this) belongs to the deferred action-
workflow spec.

Returns None readily and on purpose. A tenant with no team, one person, or
two equally-plausible candidates gets no suggestion, and the UI says "sin
dueño sugerido" — which is honest, and better than a name nobody chose.
"""
from __future__ import annotations

NO_DOMAIN = "__sin_dominio__"


def suggest(modulos) -> dict | None:
    """The one non-admin teammate whose access covers every module this card
    needs, or None when that person is not unique."""
    needed = {m for m in (modulos or ()) if m != NO_DOMAIN}
    if not needed:
        return None
    try:
        from . import perfiles
        matriz = perfiles.matriz()
    except Exception:  # noqa: BLE001 — a lookup failure must not kill the inbox
        return None

    candidates = [
        row for row in matriz
        if not row.get("es_admin")
        and needed <= {m for m, has in (row.get("modulos") or {}).items() if has}
    ]
    if len(candidates) != 1:
        # Zero: nobody covers it. More than one: a coin flip, so say nothing.
        return None
    row = candidates[0]
    return {"suggested": row["nombre"], "role": row.get("rol") or "",
            "reason": sorted(needed)[0]}

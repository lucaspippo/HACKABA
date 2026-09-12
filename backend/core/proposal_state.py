"""Has this proposal already been executed?

Ángela leaves an action assembled and waits for a human yes (see
core/autonomia.py: stock, plata and permisos are pinned to `pide_ok` and no
setting loosens them). Once someone approves, the card must say so — to that
person on reload, and to every other user, so nobody acts on it twice.

That fact is DERIVED, never stored: each proposal type declares how to find
the real record it produces, and the domain table stays the single source of
truth. Nothing is mirrored here, so nothing can drift out of sync with it.

Adding a proposal type means adding one resolver that calls that type's own
core/ module — this file never touches a repo or a tenant id.
"""
from __future__ import annotations


def _find_order(origen: str, codigo):
    """Indirection so tests can substitute the lookup without a database."""
    from . import ordenes
    return ordenes.find_for_origin(origen=origen, codigo=codigo)


def _resolve_purchase_order(proposal: dict, origin_id: str) -> dict | None:
    orden = _find_order(origin_id, proposal.get("codigo"))
    if not orden:
        return None
    return {
        "type": "orden_compra",
        "label": orden["numero"],
        # The human who pressed approve. `preparada_por` is always "Ángela",
        # so using it here would credit the agent for the person's decision.
        "actor": orden.get("aprobada_por") or "",
        "date": orden.get("preparada") or "",
        "status": orden.get("estado") or "",
        "navigate": "ordenes_compra",
    }


RESOLVERS = {"orden_compra": _resolve_purchase_order}


def for_proposal(proposal: dict | None, origin_id: str) -> dict | None:
    """The executed action for this proposal, or None if it hasn't run yet.

    Never raises: a card whose resolver fails renders as not-yet-acted-on,
    which is the safe direction — the worst case is showing the proposal
    again, and preparar() is idempotent per (origen, codigo).
    """
    if not proposal:
        return None
    resolver = RESOLVERS.get(proposal.get("tipo"))
    if not resolver:
        return None
    try:
        return resolver(proposal, origin_id)
    except Exception:  # noqa: BLE001 — a lookup failure must not blank the inbox
        return None

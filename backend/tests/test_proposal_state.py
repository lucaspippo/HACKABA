"""Resolving whether a card's proposal was already executed."""
from __future__ import annotations

from core import proposal_state


def test_unknown_proposal_type_returns_none_without_raising():
    assert proposal_state.for_proposal({"tipo": "no_such_type"}, "whatever") is None


def test_missing_proposal_returns_none():
    assert proposal_state.for_proposal(None, "quiebre_inminente") is None


def test_purchase_order_proposal_resolves_to_the_order(monkeypatch):
    monkeypatch.setattr(
        proposal_state, "_find_order",
        lambda origen, codigo: {
            "numero": "OC-2026-0901", "estado": "borrador",
            "aprobada_por": "Aldo", "preparada_por": "Ángela",
            "preparada": "2026-07-07T09:14:02",
        })
    got = proposal_state.for_proposal(
        {"tipo": "orden_compra", "codigo": 7}, "quiebre_inminente")
    assert got == {
        "type": "orden_compra",
        "label": "OC-2026-0901",
        "actor": "Aldo",
        "date": "2026-07-07T09:14:02",
        "status": "borrador",
        "navigate": "ordenes_compra",
    }


def test_purchase_order_proposal_none_when_no_order(monkeypatch):
    monkeypatch.setattr(proposal_state, "_find_order", lambda origen, codigo: None)
    assert proposal_state.for_proposal(
        {"tipo": "orden_compra", "codigo": 7}, "quiebre_inminente") is None


def test_resolver_failure_is_swallowed(monkeypatch):
    def boom(origen, codigo):
        raise RuntimeError("db down")
    monkeypatch.setattr(proposal_state, "_find_order", boom)
    assert proposal_state.for_proposal(
        {"tipo": "orden_compra", "codigo": 7}, "quiebre_inminente") is None

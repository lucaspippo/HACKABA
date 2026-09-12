"""core/oportunidades_neg.py sharing core/pattern_feedback.py with
core/patrones.py (see tests/test_patrones.py for the mechanism itself) —
the closed rule set stays closed and hand-coded, only "don't show me this
exact instance again" is shared.
"""
from __future__ import annotations

from core import oportunidades_neg


def _patch_tenant(monkeypatch, tenant_id):
    from core.db import tenant as tenant_module
    monkeypatch.setattr(tenant_module, "current_tenant_id", lambda: tenant_id)


def _moroso(nombre, dias_sin_pagar, saldo):
    return {"id": nombre.lower().replace(" ", "-"), "nombre": nombre, "en_mora": True,
            "dias_sin_pagar": dias_sin_pagar, "saldo": saldo, "promedio_pago_dias": 30,
            "movimientos": []}


def test_feedback_hides_the_exact_customer_it_was_given_on(monkeypatch, db_tenant):
    from core import cuentas
    _patch_tenant(monkeypatch, db_tenant)
    monkeypatch.setattr(cuentas, "listar",
                        lambda: [_moroso("Cliente Uno", 90, 50_000)])

    before = oportunidades_neg.cards("es")
    assert "cobrar_morosos" in [c["id"] for c in before]

    oportunidades_neg.record_feedback("cobrar_morosos", "dismissed", actor="aldo", lang="es")

    after = oportunidades_neg.cards("es")
    assert "cobrar_morosos" not in [c["id"] for c in after]


def test_feedback_does_not_hide_a_different_worst_debtor(monkeypatch, db_tenant):
    """Dismissing today's worst debtor shouldn't silence a LATER, genuinely
    different customer who becomes the worst — the fingerprint is the
    customer's name, not the card id."""
    from core import cuentas
    _patch_tenant(monkeypatch, db_tenant)
    monkeypatch.setattr(cuentas, "listar",
                        lambda: [_moroso("Cliente Uno", 90, 50_000)])
    oportunidades_neg.record_feedback("cobrar_morosos", "dismissed", actor="aldo", lang="es")
    assert "cobrar_morosos" not in [c["id"] for c in oportunidades_neg.cards("es")]

    monkeypatch.setattr(cuentas, "listar",
                        lambda: [_moroso("Cliente Dos", 120, 80_000)])
    assert "cobrar_morosos" in [c["id"] for c in oportunidades_neg.cards("es")]


def test_feedback_on_a_card_that_is_not_live_raises(monkeypatch, db_tenant):
    import pytest
    from core import cuentas
    _patch_tenant(monkeypatch, db_tenant)
    monkeypatch.setattr(cuentas, "listar", lambda: [])
    with pytest.raises(KeyError):
        oportunidades_neg.record_feedback("cobrar_morosos", "dismissed", actor="aldo", lang="es")


def test_feedback_survives_a_second_lookup_via_the_shared_history(monkeypatch, db_tenant):
    from core import cuentas, pattern_feedback
    _patch_tenant(monkeypatch, db_tenant)
    monkeypatch.setattr(cuentas, "listar",
                        lambda: [_moroso("Cliente Tres", 45, 12_000)])
    recorded = oportunidades_neg.record_feedback(
        "cobrar_morosos", "already_knew", actor="aldo", note="acuerdo de pago", lang="es")
    assert recorded["pattern_id"] == "cobrar_morosos"
    assert "Cliente Tres" in recorded["snapshot"]["resumen"]

    hist = pattern_feedback.history()
    assert any(h["id"] == recorded["id"] for h in hist)


def test_all_ten_cards_declare_a_fingerprint():
    """Every card in the closed set needs one — otherwise it can never be
    fed back on, silently. Sliced by source line ranges (sorted by
    definition order, not _SET's order) so this doesn't depend on _SET
    listing the builders in file order."""
    import inspect
    lines = inspect.getsource(oportunidades_neg).splitlines()
    pairs = sorted((b.__code__.co_firstlineno - 1, b) for b in oportunidades_neg._SET)
    for idx, (start, builder) in enumerate(pairs):
        end = pairs[idx + 1][0] if idx + 1 < len(pairs) else len(lines)
        body = "\n".join(lines[start:end])
        assert '"fingerprint"' in body, f"{builder.__name__} has no fingerprint"

"""/api/patrones/feedback and /api/patrones/historial — the API surface for
closing the loop on a core/patrones.py finding (see tests/test_patrones.py
for the underlying core.patrones.record_feedback logic)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import auth
import main

client = TestClient(main.app)


@pytest.fixture(scope="module")
def tokens():
    creds = auth.cargar_o_generar_credenciales()
    return {u: client.post("/api/login", json={"username": u, "password": creds[u]}).json()["token"]
            for u in ("emilio", "paula", "vendedor", "deposito")}


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(autouse=True)
def _clear_pattern_feedback():
    """Every test in this file shares piloto's real tenant row (same
    reasoning as test_authz.py) — clear feedback before each test so one
    test's dismissal doesn't suppress the finding another test needs live."""
    from sqlalchemy import text
    from core.db import tenant as tenant_module
    from core.db.engine import tenant_connection
    tid = tenant_module.current_tenant_id()
    with tenant_connection(tid) as conn:
        conn.execute(text("DELETE FROM pattern_feedback WHERE tenant_id = :tid"), {"tid": tid})
    yield


def _seed_combo(monkeypatch):
    from core import ventas_cliente
    from tests.test_patrones import _combo_orders
    monkeypatch.setattr(ventas_cliente, "all_orders",
                        lambda: _combo_orders(n_both=8, n_anchor_only=2, n_partner_only=3))


def _seed_moroso(monkeypatch):
    from core import cuentas
    monkeypatch.setattr(cuentas, "listar", lambda: [
        {"id": "cliente-uno", "nombre": "Cliente Uno", "en_mora": True, "dias_sin_pagar": 90,
         "saldo": 50_000, "promedio_pago_dias": 30, "movimientos": []}])


def test_no_token_is_rejected():
    r = client.post("/api/patrones/feedback", json={"card_id": "combo_no_percibido", "action": "dismissed"})
    assert r.status_code == 401


def test_owner_can_give_feedback_and_it_shows_up_in_history(tokens, monkeypatch):
    _seed_combo(monkeypatch)
    r = client.post("/api/patrones/feedback", headers=_h(tokens["emilio"]),
                    json={"card_id": "combo_no_percibido", "action": "dismissed", "note": "ya lo vimos"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pattern_id"] == "combo_no_percibido"
    assert body["action"] == "dismissed"
    assert body["note"] == "ya lo vimos"

    r = client.get("/api/patrones/historial", headers=_h(tokens["emilio"]))
    assert r.status_code == 200
    assert any(h["id"] == body["id"] for h in r.json()["historial"])


def test_role_missing_the_pattern_domain_is_rejected(tokens, monkeypatch):
    _seed_combo(monkeypatch)
    # paula has "caja" but not "oportunidades": combo_no_percibido needs both
    # cuentas+oportunidades, so she can't give feedback on this specific finding.
    r = client.post("/api/patrones/feedback", headers=_h(tokens["paula"]),
                    json={"card_id": "combo_no_percibido", "action": "dismissed"})
    assert r.status_code == 403


def test_role_with_no_relevant_module_is_rejected(tokens, monkeypatch):
    _seed_combo(monkeypatch)
    r = client.post("/api/patrones/feedback", headers=_h(tokens["vendedor"]),
                    json={"card_id": "combo_no_percibido", "action": "dismissed"})
    assert r.status_code == 403


def test_unknown_action_is_a_400(tokens, monkeypatch):
    _seed_combo(monkeypatch)
    r = client.post("/api/patrones/feedback", headers=_h(tokens["emilio"]),
                    json={"card_id": "combo_no_percibido", "action": "not_a_real_action"})
    assert r.status_code == 400


def test_feedback_on_a_card_that_is_not_live_is_a_404(tokens, monkeypatch):
    from core import ventas_cliente
    monkeypatch.setattr(ventas_cliente, "all_orders", lambda: [])
    r = client.post("/api/patrones/feedback", headers=_h(tokens["emilio"]),
                    json={"card_id": "combo_no_percibido", "action": "dismissed"})
    assert r.status_code == 404


# --- the same endpoint also dispatches to core/oportunidades_neg.py --------------

def test_owner_can_give_feedback_on_an_oportunidad_card(tokens, monkeypatch):
    _seed_moroso(monkeypatch)
    r = client.post("/api/patrones/feedback", headers=_h(tokens["emilio"]),
                    json={"card_id": "cobrar_morosos", "action": "already_knew"})
    assert r.status_code == 200, r.text
    assert r.json()["pattern_id"] == "cobrar_morosos"

    r = client.get("/api/patrones/historial", headers=_h(tokens["emilio"]))
    assert any(h["pattern_id"] == "cobrar_morosos" for h in r.json()["historial"])


def test_role_missing_the_oportunidad_domain_is_rejected(tokens, monkeypatch):
    _seed_moroso(monkeypatch)
    # deposito has neither "cuentas" nor "oportunidades": cobrar_morosos needs "cuentas".
    r = client.post("/api/patrones/feedback", headers=_h(tokens["deposito"]),
                    json={"card_id": "cobrar_morosos", "action": "dismissed"})
    assert r.status_code == 403


def test_unknown_card_id_is_a_404(tokens):
    r = client.post("/api/patrones/feedback", headers=_h(tokens["emilio"]),
                    json={"card_id": "no_existe_este_hallazgo", "action": "dismissed"})
    assert r.status_code == 404

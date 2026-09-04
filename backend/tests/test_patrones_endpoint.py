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


# --- /api/patrones/aprender ("Enseñar a Ángela") --------------------------------

@pytest.fixture(autouse=True)
def _clear_business_knowledge():
    from tests.conftest import limpiar_tabla_tenant
    limpiar_tabla_tenant("business_knowledge_pieces")
    yield
    limpiar_tabla_tenant("business_knowledge_pieces")


def _aprender_payload(**kw):
    base = dict(card_id="combo_no_percibido", tipo="contexto", ambito="global",
               nodo="ventas", efecto="contexto_para_angela")
    base.update(kw)
    return base


def test_owner_can_teach_angela_from_a_live_finding(tokens, monkeypatch):
    _seed_combo(monkeypatch)
    r = client.post("/api/patrones/aprender", headers=_h(tokens["emilio"]),
                    json=_aprender_payload())
    assert r.status_code == 200, r.text
    pieza = r.json()["pieza"]
    assert pieza["tipo"] == "contexto"
    assert pieza["efecto"] == "contexto_para_angela"
    assert pieza["origen"]["hallazgo_id"] == "combo_no_percibido"

    r = client.get("/api/conocimiento", headers=_h(tokens["emilio"]))
    assert any(p["id"] == pieza["id"] for p in r.json()["piezas"])


def test_non_admin_cannot_teach_angela(tokens, monkeypatch):
    _seed_combo(monkeypatch)
    r = client.post("/api/patrones/aprender", headers=_h(tokens["paula"]),
                    json=_aprender_payload())
    assert r.status_code == 403


def test_invalid_efecto_is_a_400(tokens, monkeypatch):
    _seed_combo(monkeypatch)
    r = client.post("/api/patrones/aprender", headers=_h(tokens["emilio"]),
                    json=_aprender_payload(efecto="not_a_real_effect"))
    assert r.status_code == 400


def test_teaching_from_a_card_that_is_not_live_is_a_404(tokens, monkeypatch):
    from core import ventas_cliente
    monkeypatch.setattr(ventas_cliente, "all_orders", lambda: [])
    r = client.post("/api/patrones/aprender", headers=_h(tokens["emilio"]),
                    json=_aprender_payload())
    assert r.status_code == 404


def test_teach_angela_on_an_oportunidad_card(tokens, monkeypatch):
    _seed_moroso(monkeypatch)
    r = client.post("/api/patrones/aprender", headers=_h(tokens["emilio"]),
                    json=_aprender_payload(card_id="cobrar_morosos", ambito="cliente",
                                          nodo="clientes", entidad="Cliente Uno",
                                          efecto="requiere_aprobacion"))
    assert r.status_code == 200, r.text
    assert r.json()["pieza"]["nodo"] == "clientes"


# --- the same endpoint also dispatches to core/oportunidades_neg.py --------------

def test_owner_can_give_feedback_on_an_oportunidad_card(tokens, monkeypatch):
    _seed_moroso(monkeypatch)
    r = client.post("/api/patrones/feedback", headers=_h(tokens["emilio"]),
                    json={"card_id": "cobrar_morosos", "action": "already_knew"})
    assert r.status_code == 200, r.text
    assert r.json()["pattern_id"] == "cobrar_morosos"

    r = client.get("/api/patrones/historial", headers=_h(tokens["emilio"]))
    assert any(h["pattern_id"] == "cobrar_morosos" for h in r.json()["historial"])


def test_dismissing_a_card_is_narrated_into_the_next_turn(tokens, monkeypatch):
    """The decision, not the data: `core/` recalculates every figure, so what
    Ángela could not otherwise know is that Emilio reacted to this finding."""
    import angela
    from core import app_events
    _seed_moroso(monkeypatch)
    r = client.post("/api/patrones/feedback", headers=_h(tokens["emilio"]),
                    json={"card_id": "cobrar_morosos", "action": "dismissed"})
    assert r.status_code == 200, r.text

    try:
        _s, _m, _t, messages = angela._prepare_turn(
            "¿y los morosos?", [], "dueño", "emilio", None, "es")
    finally:
        angela._set_sesion()
    note = messages[-1]["content"][0]["text"]
    assert app_events.LABEL in note
    assert "descartó" in note


def test_a_rejected_feedback_call_narrates_nothing(tokens, monkeypatch):
    """403 and 404 paths must not queue an event: the sentence is a record of
    something that happened."""
    from core import app_events
    _seed_moroso(monkeypatch)
    client.post("/api/patrones/feedback", headers=_h(tokens["deposito"]),
                json={"card_id": "cobrar_morosos", "action": "dismissed"})
    client.post("/api/patrones/feedback", headers=_h(tokens["emilio"]),
                json={"card_id": "no_existe_este_hallazgo", "action": "dismissed"})
    assert app_events.pending("deposito") == 0
    assert app_events.pending("emilio") == 0


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

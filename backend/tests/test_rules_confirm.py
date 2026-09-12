import pytest
from fastapi.testclient import TestClient

import auth
import main
from core import rules
from tests.conftest import limpiar_tabla_tenant

client = TestClient(main.app)

PROPOSAL = {
    "description": "always require confirmation over $5000",
    "condition": {"field": "amount", "operator": "gt", "value": 5000},
    "action": [{"type": "require_human_confirmation"}],
    "node": "ventas",
    "scope": "global",
}


@pytest.fixture(autouse=True)
def limpio():
    limpiar_tabla_tenant("business_rules")
    yield
    limpiar_tabla_tenant("business_rules")


@pytest.fixture(scope="module")
def tokens():
    creds = auth.cargar_o_generar_credenciales()
    return {u: client.post("/api/login", json={"username": u, "password": creds[u]}).json()["token"]
            for u in ("emilio", "deposito", "vendedor")}


def _confirm(tok, **overrides):
    body = {**PROPOSAL, **overrides}
    return client.post("/api/rules/confirm", json=body,
                       headers={"Authorization": f"Bearer {tok}"})


def test_owner_confirmation_lands_active(tokens):
    r = _confirm(tokens["emilio"])
    assert r.status_code == 200
    assert r.json()["state"] == "active"
    assert rules.list_rules()[0]["description"] == PROPOSAL["description"]


def test_employee_confirming_a_scoped_rule_in_their_own_node_lands_active(tokens, monkeypatch):
    from core import proveedores
    monkeypatch.setattr(proveedores, "listar", lambda: [{"id": "p1", "nombre": "Supplier Y"}])
    r = _confirm(tokens["deposito"], node="deposito", scope="proveedor",
                entity_name="Supplier Y", entity_type="proveedor",
                condition={"op": "all", "clauses": [
                    {"field": "supplier_id", "operator": "eq", "value": "$entity"},
                    {"field": "damage_reported", "operator": "eq", "value": True}]},
                action=[{"type": "mark_receipt_partial"}])
    assert r.json()["state"] == "active"


def test_employee_confirming_a_global_rule_lands_pending(tokens):
    r = _confirm(tokens["deposito"])
    assert r.json()["state"] == "pending"
    assert rules.list_rules(status="active") == []


def test_confirming_the_same_chip_twice_yields_one_rule(tokens):
    """The chip survives a page reload and can be tapped twice; two identical
    active rules would double every action evaluate() returns."""
    first = _confirm(tokens["emilio"])
    assert first.json()["already_existed"] is False
    second = _confirm(tokens["emilio"])
    assert second.status_code == 200
    assert second.json()["already_existed"] is True
    assert second.json()["rule"]["id"] == first.json()["rule"]["id"]
    assert len(rules.list_rules()) == 1


def test_confirm_rejects_a_malformed_condition(tokens):
    assert _confirm(tokens["emilio"], condition={}).status_code == 400
    assert rules.list_rules() == []


def test_confirm_rejects_a_bad_node(tokens):
    assert _confirm(tokens["emilio"], node="marketing").status_code == 400


def test_confirm_needs_a_session():
    assert client.post("/api/rules/confirm", json=PROPOSAL).status_code in (401, 403)


def test_ambiguous_entity_lands_pending(tokens, monkeypatch):
    from core import proveedores
    monkeypatch.setattr(proveedores, "listar", lambda: [
        {"id": "p1", "nombre": "Supplier Y North"}, {"id": "p2", "nombre": "Supplier Y South"}])
    r = _confirm(tokens["emilio"], node="deposito", scope="proveedor",
                entity_name="Supplier Y", entity_type="proveedor",
                condition={"op": "all", "clauses": [
                    {"field": "supplier_id", "operator": "eq", "value": "$entity"},
                    {"field": "damage_reported", "operator": "eq", "value": True}]},
                action=[{"type": "mark_receipt_partial"}])
    assert r.json()["state"] == "pending"

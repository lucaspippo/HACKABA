import pytest

from core import rules
from tests.conftest import limpiar_tabla_tenant


@pytest.fixture(autouse=True)
def limpio():
    limpiar_tabla_tenant("business_rules")
    yield
    limpiar_tabla_tenant("business_rules")


def _use_tenant(db_tenant, monkeypatch):
    from core.db import tenant as tenant_module
    monkeypatch.setattr(tenant_module, "current_tenant_id", lambda: db_tenant)


ORIGIN = {"author": "aldo", "created_at": "2026-09-11", "source": "conversation"}


# --- Reference case 1: discount by client + quantity --------------------------

def test_case1_discount_by_client_and_quantity(db_tenant, monkeypatch):
    _use_tenant(db_tenant, monkeypatch)
    from core import cuentas
    monkeypatch.setattr(cuentas, "listar", lambda: [{"id": "c1", "nombre": "Client X"}])
    rules.create(
        description="5% off orders over 100 units for Client X",
        condition={"op": "all", "clauses": [
            {"field": "client_id", "operator": "eq", "value": "$entity"},
            {"field": "quantity", "operator": "gt", "value": 100}]},
        action=[{"type": "apply_discount", "params": {"percent": 5}}],
        node="ventas", scope="cliente", entity_name="Client X",
        entity_type="cliente", origin=ORIGIN)

    matching = rules.evaluate({"client_id": "c1", "quantity": 150})
    assert len(matching) == 1
    assert matching[0]["actions"] == [{"type": "apply_discount", "params": {"percent": 5}}]

    assert rules.evaluate({"client_id": "c1", "quantity": 50}) == []
    assert rules.evaluate({"client_id": "c2", "quantity": 150}) == []


# --- Reference case 2: receiving tolerance by supplier + damage report --------

def test_case2_receiving_tolerance_by_supplier_and_damage(db_tenant, monkeypatch):
    _use_tenant(db_tenant, monkeypatch)
    from core import proveedores
    monkeypatch.setattr(proveedores, "listar", lambda: [{"id": "p1", "nombre": "Supplier Y"}])
    rules.create(
        description="Mark partial and notify purchasing on damage from Supplier Y",
        condition={"op": "all", "clauses": [
            {"field": "supplier_id", "operator": "eq", "value": "$entity"},
            {"field": "damage_reported", "operator": "eq", "value": True}]},
        action=[{"type": "mark_receipt_partial", "params": {}},
                {"type": "notify", "params": {"target": "purchasing"}}],
        node="proveedores", scope="proveedor", entity_name="Supplier Y",
        entity_type="proveedor", origin=ORIGIN)

    matching = rules.evaluate({"supplier_id": "p1", "damage_reported": True})
    assert len(matching) == 1
    assert matching[0]["actions"] == [
        {"type": "mark_receipt_partial", "params": {}},
        {"type": "notify", "params": {"target": "purchasing"}}]

    assert rules.evaluate({"supplier_id": "p1", "damage_reported": False}) == []
    assert rules.evaluate({"supplier_id": "p2", "damage_reported": True}) == []


# --- Reference case 3: escalate to a human on either condition ----------------

def test_case3_escalation_on_new_product_or_high_amount(db_tenant, monkeypatch):
    _use_tenant(db_tenant, monkeypatch)
    from core import cuentas
    monkeypatch.setattr(cuentas, "listar", lambda: [{"id": "c1", "nombre": "Client Z"}])
    rules.create(
        description="Ask a human before auto-executing for Client Z on a new "
                    "product or a large amount",
        condition={"op": "all", "clauses": [
            {"field": "client_id", "operator": "eq", "value": "$entity"},
            {"op": "any", "clauses": [
                {"field": "product_seen_before", "operator": "eq", "value": False},
                {"field": "amount", "operator": "gt", "value": 5000}]}]},
        action=[{"type": "require_human_confirmation", "params": {}}],
        node="ventas", scope="cliente", entity_name="Client Z",
        entity_type="cliente", origin=ORIGIN)

    # arm 1: new product, low amount
    assert len(rules.evaluate({"client_id": "c1", "product_seen_before": False,
                               "amount": 100})) == 1
    # arm 2: known product, high amount
    assert len(rules.evaluate({"client_id": "c1", "product_seen_before": True,
                               "amount": 9000})) == 1
    # neither arm
    assert rules.evaluate({"client_id": "c1", "product_seen_before": True,
                           "amount": 100}) == []


# --- verify(): replay a rule's own test cases ---------------------------------

def test_verify_matches_expected_action(db_tenant, monkeypatch):
    _use_tenant(db_tenant, monkeypatch)
    from core import cuentas
    monkeypatch.setattr(cuentas, "listar", lambda: [{"id": "c1", "nombre": "Client X"}])
    rule = rules.create(
        description="5% off", condition={"op": "all", "clauses": [
            {"field": "client_id", "operator": "eq", "value": "$entity"},
            {"field": "quantity", "operator": "gt", "value": 100}]},
        action=[{"type": "apply_discount", "params": {"percent": 5}}],
        node="ventas", scope="cliente", entity_name="Client X",
        entity_type="cliente", origin=ORIGIN,
        test_cases=[
            {"facts": {"client_id": "c1", "quantity": 150},
             "expected_action": [{"type": "apply_discount", "params": {"percent": 5}}]},
            {"facts": {"client_id": "c1", "quantity": 50}, "expected_action": []},
        ])
    result = rules.verify(rule["id"])
    assert result["ok"] is True
    assert all(r["ok"] for r in result["results"])


def test_verify_catches_a_mismatch_after_editing_the_action(db_tenant, monkeypatch):
    _use_tenant(db_tenant, monkeypatch)
    from core import cuentas
    from core.db import tenant as _tenant
    monkeypatch.setattr(cuentas, "listar", lambda: [{"id": "c1", "nombre": "Client X"}])
    rule = rules.create(
        description="5% off", condition={"op": "all", "clauses": [
            {"field": "client_id", "operator": "eq", "value": "$entity"},
            {"field": "quantity", "operator": "gt", "value": 100}]},
        action=[{"type": "apply_discount", "params": {"percent": 5}}],
        node="ventas", scope="cliente", entity_name="Client X",
        entity_type="cliente", origin=ORIGIN,
        test_cases=[{"facts": {"client_id": "c1", "quantity": 150},
                    "expected_action": [{"type": "apply_discount", "params": {"percent": 5}}]}])
    # simulate an edit that changed the discount without updating the test case
    from core.db.engine import tenant_connection
    from sqlalchemy import text
    import json
    with tenant_connection(_tenant.current_tenant_id()) as conn:
        conn.execute(text("UPDATE business_rules SET action = :action WHERE id = :id"),
                    {"action": json.dumps([{"type": "apply_discount", "params": {"percent": 10}}]),
                     "id": rule["id"]})
    result = rules.verify(rule["id"])
    assert result["ok"] is False
    assert result["results"][0]["ok"] is False
    assert result["results"][0]["actual"] == [{"type": "apply_discount", "params": {"percent": 10}}]

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


CLIENT_CONDITION = {"op": "all", "clauses": [
    {"field": "client_id", "operator": "eq", "value": "$entity"},
    {"field": "quantity", "operator": "gt", "value": 100},
]}
DISCOUNT_ACTION = [{"type": "apply_discount", "params": {"percent": 5}}]
ORIGIN = {"author": "aldo", "created_at": "2026-09-11", "source": "conversation"}


def test_validate_proposal_resolves_a_unique_match(db_tenant, monkeypatch):
    _use_tenant(db_tenant, monkeypatch)
    from core import cuentas
    monkeypatch.setattr(cuentas, "listar", lambda: [{"id": "c1", "nombre": "Client X"}])
    proposal = rules.validate_proposal(
        description="5% off for Client X", condition=CLIENT_CONDITION,
        action=DISCOUNT_ACTION, node="ventas", scope="cliente",
        entity_name="Client X", entity_type="cliente")
    assert proposal["entity_id"] == "c1"
    assert proposal["status"] == "active"
    assert proposal["condition"]["clauses"][0]["value"] == "c1"
    assert rules.list_rules() == []  # nothing persisted


def test_validate_proposal_writes_nothing_and_is_pending_when_ambiguous(db_tenant, monkeypatch):
    _use_tenant(db_tenant, monkeypatch)
    from core import cuentas
    monkeypatch.setattr(cuentas, "listar", lambda: [
        {"id": "c1", "nombre": "Client X North"}, {"id": "c2", "nombre": "Client X South"}])
    proposal = rules.validate_proposal(
        description="5% off for Client X", condition=CLIENT_CONDITION,
        action=DISCOUNT_ACTION, node="ventas", scope="cliente",
        entity_name="Client X", entity_type="cliente")
    assert proposal["entity_id"] is None
    assert proposal["status"] == "pending"


def test_non_global_condition_must_reference_entity_placeholder(db_tenant, monkeypatch):
    _use_tenant(db_tenant, monkeypatch)
    with pytest.raises(rules.RulesInvalid):
        rules.validate_proposal(
            description="x", condition={"field": "quantity", "operator": "gt", "value": 100},
            action=DISCOUNT_ACTION, node="ventas", scope="cliente",
            entity_name="Client X", entity_type="cliente")


def test_global_scope_needs_no_entity(db_tenant, monkeypatch):
    _use_tenant(db_tenant, monkeypatch)
    proposal = rules.validate_proposal(
        description="always require confirmation over $5000",
        condition={"field": "amount", "operator": "gt", "value": 5000},
        action=[{"type": "require_human_confirmation"}],
        node="ventas", scope="global")
    assert proposal["entity_id"] is None
    assert proposal["status"] == "active"


def test_create_persists_and_supersede_links_versions(db_tenant, monkeypatch):
    _use_tenant(db_tenant, monkeypatch)
    from core import cuentas
    monkeypatch.setattr(cuentas, "listar", lambda: [{"id": "c1", "nombre": "Client X"}])
    old = rules.create(description="v1", condition=CLIENT_CONDITION, action=DISCOUNT_ACTION,
                       node="ventas", scope="cliente", entity_name="Client X",
                       entity_type="cliente", origin=ORIGIN)
    new = rules.create(description="v2", condition=CLIENT_CONDITION,
                       action=[{"type": "apply_discount", "params": {"percent": 10}}],
                       node="ventas", scope="cliente", entity_name="Client X",
                       entity_type="cliente", origin=ORIGIN)
    result = rules.supersede(old["id"], replacement_id=new["id"], actor="aldo")
    assert result["status"] == "superseded"
    assert result["superseded_by"] == new["id"]
    assert rules.get(new["id"])["status"] == "active"


def test_pause_and_activate(db_tenant, monkeypatch):
    _use_tenant(db_tenant, monkeypatch)
    rule = rules.create(description="x", condition={"field": "amount", "operator": "gt", "value": 1},
                        action=[{"type": "require_human_confirmation"}], node="ventas",
                        scope="global", origin=ORIGIN)
    assert rules.pause(rule["id"])["status"] == "paused"
    assert rules.activate(rule["id"])["status"] == "active"


def test_archive_is_audited(db_tenant, monkeypatch):
    _use_tenant(db_tenant, monkeypatch)
    rule = rules.create(description="x", condition={"field": "amount", "operator": "gt", "value": 1},
                        action=[{"type": "require_human_confirmation"}], node="ventas",
                        scope="global", origin=ORIGIN)
    result = rules.archive(rule["id"], actor="aldo")
    assert result["status"] == "archived"
    from core.audit import AuditLog
    events = [e for e in AuditLog().list_for(rule["id"])]
    assert any(e["accion"] == "archive_rule" for e in events)

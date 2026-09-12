import pytest

import angela
from core import rules
from tests.conftest import limpiar_tabla_tenant


@pytest.fixture(autouse=True)
def limpio():
    limpiar_tabla_tenant("business_rules")
    usuario, rol = angela._usuario_actual(), angela._rol_actual()
    yield
    angela._set_sesion(usuario=usuario, rol=rol)
    limpiar_tabla_tenant("business_rules")


def _use_tenant(db_tenant, monkeypatch):
    from core.db import tenant as tenant_module
    monkeypatch.setattr(tenant_module, "current_tenant_id", lambda: db_tenant)


def test_propose_rule_validates_and_saves_nothing(db_tenant, monkeypatch):
    _use_tenant(db_tenant, monkeypatch)
    angela._set_sesion(usuario="emilio", rol="dueño")
    result, action = angela._run_tool("propose_rule", {
        "description": "always require confirmation over $5000",
        "condition": {"field": "amount", "operator": "gt", "value": 5000},
        "action": [{"type": "require_human_confirmation"}],
        "node": "ventas", "scope": "global",
    })
    assert result["ok"] is True
    assert action is None
    assert result["proposal"]["status"] == "active"
    assert rules.list_rules() == []


def test_propose_rule_reports_invalid_shape(db_tenant, monkeypatch):
    _use_tenant(db_tenant, monkeypatch)
    angela._set_sesion(usuario="emilio", rol="dueño")
    result, _ = angela._run_tool("propose_rule", {
        "description": "x", "condition": {"field": "amount", "operator": "gt", "value": 1},
        "action": [{"type": "levitate"}], "node": "ventas", "scope": "global",
    })
    assert result["ok"] is False
    assert "motivo" in result


def test_evaluate_rule_for_relays_matches(db_tenant, monkeypatch):
    _use_tenant(db_tenant, monkeypatch)
    rules.create(description="x", condition={"field": "amount", "operator": "gt", "value": 1000},
                action=[{"type": "require_human_confirmation"}], node="ventas",
                scope="global", origin={"author": "aldo", "created_at": "2026-09-11",
                                        "source": "conversation"})
    angela._set_sesion(usuario="emilio", rol="dueño")
    result, action = angela._run_tool("evaluate_rule_for", {"facts": {"amount": 5000}})
    assert action is None
    assert len(result["matches"]) == 1
    assert result["matches"][0]["actions"] == [{"type": "require_human_confirmation"}]


def test_evaluate_rule_for_withholds_text_of_rules_the_user_cannot_list(db_tenant, monkeypatch):
    """A rule a vendedor cannot list still fires for them — the product needs
    that — but its description must not leak through the match."""
    _use_tenant(db_tenant, monkeypatch)
    from core import cuentas
    monkeypatch.setattr(cuentas, "listar", lambda: [{"id": "c1", "nombre": "Client X"}])
    rules.create(description="secret 5% deal with Client X",
                condition={"op": "all", "clauses": [
                    {"field": "client_id", "operator": "eq", "value": "$entity"},
                    {"field": "quantity", "operator": "gt", "value": 100}]},
                action=[{"type": "apply_discount", "params": {"percent": 5}}],
                node="caja", scope="cliente", entity_name="Client X",
                entity_type="cliente", origin={"author": "aldo",
                                               "created_at": "2026-09-11",
                                               "source": "conversation"})
    angela._set_sesion(usuario="vendedor", rol="mostrador", features={"cuentas"})
    result, _ = angela._run_tool("evaluate_rule_for",
                                 {"facts": {"client_id": "c1", "quantity": 150}})
    assert len(result["matches"]) == 1
    match = result["matches"][0]
    assert match["actions"] == [{"type": "apply_discount", "params": {"percent": 5}}]
    assert "rule_id" in match
    assert "description" not in match

    angela._set_sesion(usuario="emilio", rol="dueño")
    owner_result, _ = angela._run_tool("evaluate_rule_for",
                                       {"facts": {"client_id": "c1", "quantity": 150}})
    assert owner_result["matches"][0]["description"] == "secret 5% deal with Client X"


def test_list_rules_tool_respects_role_scope(db_tenant, monkeypatch):
    _use_tenant(db_tenant, monkeypatch)
    rules.create(description="global rule",
                condition={"field": "amount", "operator": "gt", "value": 1},
                action=[{"type": "require_human_confirmation"}], node="ventas",
                scope="global", origin={"author": "aldo", "created_at": "2026-09-11",
                                        "source": "conversation"})
    angela._set_sesion(usuario="vendedor", rol="mostrador", features={"cuentas"})
    result, action = angela._run_tool("list_rules", {})
    assert action is None
    assert len(result["rules"]) == 1  # global rules are visible to everyone

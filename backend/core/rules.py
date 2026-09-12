"""Structured business rules — the deterministic IF/THEN sibling of
core/conocimiento.py's free-text memory. See
docs/superpowers/specs/2026-09-11-structured-business-rules-design.md.
"""
from __future__ import annotations

ACTION_TYPES = {"apply_discount", "mark_receipt_partial", "notify",
                "require_human_confirmation"}

# Entity types _resolve_entity actually knows how to resolve. AMBITOS (imported
# from conocimiento) also allows "categoria" and "empleado" scopes, but this
# plan builds no resolver for those yet — _prepare rejects them explicitly
# rather than letting the request fall through to _resolve_entity's generic
# "unknown entity_type" error.
ENTITY_TYPES = {"cliente", "proveedor", "producto"}

_ENTITY_PLACEHOLDER = "$entity"

_OPERATORS = {
    "eq": lambda a, v: a == v,
    "ne": lambda a, v: a != v,
    "gt": lambda a, v: a > v,
    "gte": lambda a, v: a >= v,
    "lt": lambda a, v: a < v,
    "lte": lambda a, v: a <= v,
    "in": lambda a, v: a in v,
    "not_in": lambda a, v: a not in v,
}


class RulesInvalid(ValueError):
    pass


def _matches(condition: dict, facts: dict) -> bool:
    if "clauses" in condition:
        results = (_matches(c, facts) for c in condition["clauses"])
        return any(results) if condition.get("op") == "any" else all(results)
    field, operator = condition["field"], condition["operator"]
    if operator not in _OPERATORS:
        raise RulesInvalid(f"unknown operator: {operator!r}")
    if field not in facts:
        return False
    return _OPERATORS[operator](facts[field], condition.get("value"))


def _validate_action(action) -> None:
    if not isinstance(action, list) or not action:
        raise RulesInvalid("action must be a non-empty list")
    for step in action:
        if not isinstance(step, dict) or "type" not in step:
            raise RulesInvalid(f"invalid action step: {step!r}")
        if step["type"] not in ACTION_TYPES:
            raise RulesInvalid(f"unknown action type: {step['type']!r}")


def _condition_has_entity_placeholder(condition: dict) -> bool:
    if "clauses" in condition:
        return any(_condition_has_entity_placeholder(c) for c in condition["clauses"])
    return condition.get("value") == _ENTITY_PLACEHOLDER


def _substitute_entity(condition: dict, entity_id: str) -> dict:
    if "clauses" in condition:
        return {**condition, "clauses": [_substitute_entity(c, entity_id)
                                         for c in condition["clauses"]]}
    if condition.get("value") == _ENTITY_PLACEHOLDER:
        return {**condition, "value": entity_id}
    return dict(condition)


def _resolve_entity(entity_type: str, entity_name: str) -> str | None:
    from . import cuentas, proveedores, ventas_cliente

    def _norm(s):
        return (s or "").strip().lower()

    def _fuzzy_match_one(name, candidates, name_key="nombre", id_key="id"):
        n = _norm(name)
        matches = [c for c in candidates
                  if n in _norm(c[name_key]) or _norm(c[name_key]) in n]
        return matches[0][id_key] if len(matches) == 1 else None

    if entity_type == "cliente":
        return _fuzzy_match_one(entity_name, cuentas.listar())
    if entity_type == "proveedor":
        return _fuzzy_match_one(entity_name, proveedores.listar())
    if entity_type == "producto":
        codes = ventas_cliente.buscar_producto(entity_name)
        return str(codes[0]) if len(codes) == 1 else None
    raise RulesInvalid(f"unknown entity_type: {entity_type!r}")


def _prepare(*, description: str, condition: dict, action, node: str, scope: str,
            entity_name: str | None = None, entity_type: str | None = None) -> dict:
    from . import conocimiento
    if not (description or "").strip():
        raise RulesInvalid("description cannot be empty")
    if node not in conocimiento.NODOS:
        raise RulesInvalid(f"unknown node: {node!r}")
    if scope not in conocimiento.AMBITOS:
        raise RulesInvalid(f"unknown scope: {scope!r}")
    _validate_action(action)

    entity_name = (entity_name or "").strip() or None
    entity_id = None
    if scope != "global":
        if not entity_name:
            raise RulesInvalid("a non-global rule needs a concrete entity")
        if not entity_type:
            raise RulesInvalid("a non-global rule needs entity_type")
        if entity_type not in ENTITY_TYPES:
            raise RulesInvalid(
                f"unsupported entity_type {entity_type!r} "
                f"(supported: {', '.join(sorted(ENTITY_TYPES))})")
        if not _condition_has_entity_placeholder(condition):
            raise RulesInvalid("condition must reference '$entity' for a non-global rule")
        entity_id = _resolve_entity(entity_type, entity_name)
        if entity_id:
            condition = _substitute_entity(condition, entity_id)
    else:
        entity_type = None

    status = "pending" if (scope != "global" and entity_id is None) else "active"
    return {"description": description.strip(), "condition": condition, "action": action,
            "node": node, "scope": scope, "entity_name": entity_name,
            "entity_type": entity_type, "entity_id": entity_id, "status": status}


def validate_proposal(*, description: str, condition: dict, action, node: str,
                      scope: str, entity_name: str | None = None,
                      entity_type: str | None = None) -> dict:
    return _prepare(description=description, condition=condition, action=action,
                    node=node, scope=scope, entity_name=entity_name,
                    entity_type=entity_type)


def create(*, description: str, condition: dict, action, node: str, scope: str,
          entity_name: str | None = None, entity_type: str | None = None,
          origin: dict, knowledge_piece_id: str | None = None,
          test_cases: list | None = None) -> dict:
    import secrets

    prepared = _prepare(description=description, condition=condition, action=action,
                        node=node, scope=scope, entity_name=entity_name,
                        entity_type=entity_type)
    from core.db import business_rules_repo
    from core.db import tenant as _tenant
    rule = business_rules_repo.create(
        _tenant.current_tenant_id(), id="r" + secrets.token_hex(4),
        description=prepared["description"], condition=prepared["condition"],
        action=prepared["action"], node=prepared["node"], scope=prepared["scope"],
        entity_name=prepared["entity_name"], entity_type=prepared["entity_type"],
        entity_id=prepared["entity_id"], origin=origin,
        knowledge_piece_id=knowledge_piece_id, status=prepared["status"],
        test_cases=test_cases or [])
    from core.audit import AuditLog
    AuditLog().record(origin.get("author", ""), "create_rule", None,
                      {"id": rule["id"], "node": rule["node"]})
    return rule


def list_rules(node: str | None = None, scope: str | None = None,
              status: str | None = None) -> list[dict]:
    from core.db import business_rules_repo
    from core.db import tenant as _tenant
    out = business_rules_repo.list_rules(_tenant.current_tenant_id())
    if node:
        out = [r for r in out if r["node"] == node]
    if scope:
        out = [r for r in out if r["scope"] == scope]
    if status:
        out = [r for r in out if r["status"] == status]
    return out


def get(rule_id: str) -> dict | None:
    from core.db import business_rules_repo
    from core.db import tenant as _tenant
    return business_rules_repo.get(_tenant.current_tenant_id(), rule_id)


def pause(rule_id: str) -> dict | None:
    from core.db import business_rules_repo
    from core.db import tenant as _tenant
    return business_rules_repo.set_status(_tenant.current_tenant_id(), rule_id, "paused")


def activate(rule_id: str) -> dict | None:
    from core.db import business_rules_repo
    from core.db import tenant as _tenant
    rule = business_rules_repo.get(_tenant.current_tenant_id(), rule_id)
    if rule is None:
        return None
    if rule["scope"] != "global" and rule["entity_id"] is None:
        raise RulesInvalid(
            f"rule {rule_id!r} was never bound to a concrete entity "
            "and must be resolved before it can be activated")
    return business_rules_repo.set_status(_tenant.current_tenant_id(), rule_id, "active")


def archive(rule_id: str, *, actor: str) -> dict | None:
    from core.db import business_rules_repo
    from core.db import tenant as _tenant
    rule = business_rules_repo.set_status(_tenant.current_tenant_id(), rule_id, "archived")
    if rule:
        from core.audit import AuditLog
        AuditLog().record(actor, "archive_rule", None, {"id": rule["id"], "node": rule["node"]})
    return rule


def supersede(rule_id: str, *, replacement_id: str, actor: str) -> dict | None:
    from core.db import business_rules_repo
    from core.db import tenant as _tenant
    rule = business_rules_repo.set_superseded_by(
        _tenant.current_tenant_id(), rule_id, superseded_by=replacement_id)
    if rule:
        from core.audit import AuditLog
        AuditLog().record(actor, "supersede_rule", None,
                          {"id": rule["id"], "superseded_by": replacement_id})
    return rule


def visible_to(user: dict, rules_list: list[dict] | None = None) -> list[dict]:
    from . import conocimiento, perfiles
    rules_list = list_rules() if rules_list is None else rules_list
    if user.get("es_admin"):
        return list(rules_list)
    username = user.get("username")
    feats = set(perfiles.features_efectivas(username))
    out = []
    for r in rules_list:
        if r["scope"] == "global":
            out.append(r)
        elif r["scope"] == "empleado" and (r.get("entity_name") or "").strip().lower() == (username or "").lower():
            out.append(r)
        elif conocimiento.NODO_FEATURE.get(r["node"]) in feats:
            out.append(r)
    return out

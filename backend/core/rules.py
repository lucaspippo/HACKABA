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


# A condition tree is authored by an LLM, so its depth is untrusted input:
# without a cap a deeply nested tree would escape this module as a
# RecursionError instead of a RulesInvalid.
_MAX_CONDITION_DEPTH = 12


class RulesInvalid(ValueError):
    pass


def _is_branch(condition: dict) -> bool:
    return "clauses" in condition or "op" in condition


def _matches(condition: dict, facts: dict) -> bool:
    if not isinstance(condition, dict):
        raise RulesInvalid(f"condition node must be an object: {condition!r}")
    if _is_branch(condition):
        clauses = condition.get("clauses")
        if not isinstance(clauses, list):
            raise RulesInvalid(f"'clauses' must be a list: {clauses!r}")
        results = (_matches(c, facts) for c in clauses)
        return any(results) if condition.get("op") == "any" else all(results)
    if "field" not in condition or "operator" not in condition:
        raise RulesInvalid(f"condition clause needs 'field' and 'operator': {condition!r}")
    field, operator = condition["field"], condition["operator"]
    if operator not in _OPERATORS:
        raise RulesInvalid(f"unknown operator: {operator!r}")
    if field not in facts:
        return False
    value = condition.get("value")
    try:
        return _OPERATORS[operator](facts[field], value)
    except TypeError as e:
        # Validation cannot prevent this: the stored value is well-formed and
        # the incoming fact simply carries an incompatible type. Surfacing it
        # beats a silent False, which would make the rule never fire.
        raise RulesInvalid(
            f"cannot compare field {field!r} ({facts[field]!r}) with {value!r} "
            f"using operator {operator!r}") from e


def _validate_condition(condition, *, _path: str = "condition", _depth: int = 0) -> None:
    if _depth > _MAX_CONDITION_DEPTH:
        raise RulesInvalid(f"condition nests deeper than {_MAX_CONDITION_DEPTH} levels")
    if not isinstance(condition, dict):
        raise RulesInvalid(f"{_path} must be an object, got {type(condition).__name__}")
    if _is_branch(condition):
        op = condition.get("op")
        if op not in ("all", "any"):
            raise RulesInvalid(f"{_path}: 'op' must be 'all' or 'any', got {op!r}")
        clauses = condition.get("clauses")
        if not isinstance(clauses, list) or not clauses:
            raise RulesInvalid(f"{_path}: 'clauses' must be a non-empty list")
        for i, clause in enumerate(clauses):
            _validate_condition(clause, _path=f"{_path}.clauses[{i}]", _depth=_depth + 1)
        return
    field = condition.get("field")
    if not isinstance(field, str) or not field.strip():
        raise RulesInvalid(f"{_path}: 'field' must be a non-empty string, got {field!r}")
    operator = condition.get("operator")
    if operator not in _OPERATORS:
        raise RulesInvalid(
            f"{_path}: unknown operator {operator!r} "
            f"(supported: {', '.join(sorted(_OPERATORS))})")
    if "value" not in condition:
        raise RulesInvalid(f"{_path}: 'value' is required")


def _validate_action(action) -> None:
    if not isinstance(action, list) or not action:
        raise RulesInvalid("action must be a non-empty list")
    for step in action:
        if not isinstance(step, dict) or "type" not in step:
            raise RulesInvalid(f"invalid action step: {step!r}")
        if step["type"] not in ACTION_TYPES:
            raise RulesInvalid(f"unknown action type: {step['type']!r}")


def _condition_has_entity_placeholder(condition: dict) -> bool:
    """True only when a '$entity' clause is guaranteed to be evaluated.

    A placeholder under an 'any' branch is bypassed whenever a sibling arm
    matches, so the rule would fire for entities it was never bound to.
    """
    if _is_branch(condition):
        if condition.get("op") == "any":
            return False
        return any(_condition_has_entity_placeholder(c) for c in condition["clauses"])
    return condition.get("value") == _ENTITY_PLACEHOLDER


def _substitute_entity(condition: dict, entity_id) -> dict:
    if _is_branch(condition):
        return {**condition, "clauses": [_substitute_entity(c, entity_id)
                                         for c in condition["clauses"]]}
    if condition.get("value") == _ENTITY_PLACEHOLDER:
        return {**condition, "value": entity_id}
    return dict(condition)


def _resolve_entity(entity_type: str, entity_name: str):
    """The resolved id in the type the facts will carry — a product code stays
    an int, so an 'eq' clause against a real fact can actually match."""
    from . import cuentas, proveedores, ventas_cliente

    def _norm(s):
        return (s or "").strip().lower()

    def _fuzzy_match_one(name, candidates, name_key="nombre", id_key="id"):
        n = _norm(name)
        if not n:
            return None
        matches = [c for c in candidates
                  if _norm(c[name_key]) and (n in _norm(c[name_key]) or _norm(c[name_key]) in n)]
        return matches[0][id_key] if len(matches) == 1 else None

    if entity_type == "cliente":
        return _fuzzy_match_one(entity_name, cuentas.listar())
    if entity_type == "proveedor":
        return _fuzzy_match_one(entity_name, proveedores.listar())
    if entity_type == "producto":
        codes = ventas_cliente.buscar_producto(entity_name)
        return codes[0] if len(codes) == 1 else None
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
    _validate_condition(condition)
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
        if entity_id is not None:
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

    author = ((origin or {}).get("author") or "").strip()
    if not author:
        raise RulesInvalid("origin.author is required")
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
        entity_id=None if prepared["entity_id"] is None else str(prepared["entity_id"]),
        origin=origin,
        knowledge_piece_id=knowledge_piece_id, status=prepared["status"],
        test_cases=test_cases or [])
    from core.audit import AuditLog
    AuditLog().record(author, "create_rule", None,
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


def find_duplicate(*, condition: dict, action, node: str, scope: str,
                   entity_name: str | None = None) -> dict | None:
    """An existing live rule with the same condition/action about the same
    target, or None. Confirming is idempotent through this: the tool-call part
    stays in the thread after a reload, so the same chip can be tapped twice,
    and two identical active rules would double every action evaluate() hands
    back. Compare against a prepared condition — a stored one has already had
    '$entity' substituted."""
    target = (entity_name or "").strip().lower()
    for r in list_rules():
        if r["status"] in ("archived", "superseded"):
            continue
        if (r["node"] == node and r["scope"] == scope
                and (r["entity_name"] or "").strip().lower() == target
                and r["condition"] == condition and r["action"] == action):
            return r
    return None


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
    """Link both directions of the version chain: the old rule points forward
    through superseded_by, the replacement points back through supersedes and
    carries the next version number."""
    from core.db import business_rules_repo
    from core.db import tenant as _tenant
    tenant_id = _tenant.current_tenant_id()
    old = business_rules_repo.get(tenant_id, rule_id)
    if old is None:
        return None
    replacement = business_rules_repo.get(tenant_id, replacement_id)
    if replacement is None:
        raise RulesInvalid(f"no such replacement rule: {replacement_id!r}")
    business_rules_repo.set_supersedes(
        tenant_id, replacement_id, supersedes=rule_id,
        version=(old.get("version") or 1) + 1)
    rule = business_rules_repo.set_superseded_by(
        tenant_id, rule_id, superseded_by=replacement_id)
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


def evaluate(facts: dict) -> list[dict]:
    matches = []
    for rule in list_rules(status="active"):
        try:
            hit = _matches(rule["condition"], facts)
        except RulesInvalid as e:
            raise RulesInvalid(f"rule {rule['id']!r}: {e}") from e
        if hit:
            matches.append({"rule_id": rule["id"], "description": rule["description"],
                            "actions": rule["action"]})
    return matches


def verify(rule_id: str) -> dict:
    """Replay a rule's test cases against its current condition and action.

    Returns {ok: bool, cases: int, results: list}. cases == 0 means no test
    cases were recorded — ok: True in that case means "nothing failed", not
    "something passed".
    """
    rule = get(rule_id)
    if not rule:
        raise RulesInvalid(f"no such rule: {rule_id!r}")
    results = []
    for case in rule["test_cases"]:
        actual = rule["action"] if _matches(rule["condition"], case["facts"]) else []
        expected = case.get("expected_action")
        ok = True if expected is None else actual == expected
        results.append({"case": case, "expected": expected, "actual": actual, "ok": ok})
    return {"ok": all(r["ok"] for r in results), "cases": len(results), "results": results}

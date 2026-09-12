"""Structured business rules — the deterministic SI/ENTONCES sibling of
core/conocimiento.py's free-text memory. See
docs/superpowers/specs/2026-09-11-structured-business-rules-design.md.
"""
from __future__ import annotations

ACTION_TYPES = {"apply_discount", "mark_receipt_partial", "notify",
                "require_human_confirmation"}

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

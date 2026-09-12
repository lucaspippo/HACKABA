import pytest

from core import rules


def test_eq_matches():
    condition = {"field": "client_id", "operator": "eq", "value": "c1"}
    assert rules._matches(condition, {"client_id": "c1"}) is True
    assert rules._matches(condition, {"client_id": "c2"}) is False


def test_missing_field_never_matches():
    condition = {"field": "quantity", "operator": "gt", "value": 100}
    assert rules._matches(condition, {}) is False


def test_all_requires_every_clause():
    condition = {"op": "all", "clauses": [
        {"field": "client_id", "operator": "eq", "value": "c1"},
        {"field": "quantity", "operator": "gt", "value": 100},
    ]}
    assert rules._matches(condition, {"client_id": "c1", "quantity": 150}) is True
    assert rules._matches(condition, {"client_id": "c1", "quantity": 50}) is False


def test_any_requires_one_clause():
    condition = {"op": "any", "clauses": [
        {"field": "product_seen_before", "operator": "eq", "value": False},
        {"field": "amount", "operator": "gt", "value": 5000},
    ]}
    assert rules._matches(condition, {"product_seen_before": False, "amount": 100}) is True
    assert rules._matches(condition, {"product_seen_before": True, "amount": 9000}) is True
    assert rules._matches(condition, {"product_seen_before": True, "amount": 100}) is False


def test_nested_any_inside_all():
    condition = {"op": "all", "clauses": [
        {"field": "client_id", "operator": "eq", "value": "c1"},
        {"op": "any", "clauses": [
            {"field": "product_seen_before", "operator": "eq", "value": False},
            {"field": "amount", "operator": "gt", "value": 5000},
        ]},
    ]}
    assert rules._matches(condition, {"client_id": "c1", "product_seen_before": False,
                                      "amount": 0}) is True
    assert rules._matches(condition, {"client_id": "c2", "product_seen_before": False,
                                      "amount": 0}) is False


@pytest.mark.parametrize("operator,value,fact,expected", [
    ("ne", "c1", "c2", True), ("ne", "c1", "c1", False),
    ("gte", 100, 100, True), ("gte", 100, 99, False),
    ("lt", 100, 50, True), ("lt", 100, 150, False),
    ("lte", 100, 100, True), ("lte", 100, 101, False),
    ("in", ["a", "b"], "a", True), ("in", ["a", "b"], "c", False),
    ("not_in", ["a", "b"], "c", True), ("not_in", ["a", "b"], "a", False),
])
def test_every_operator(operator, value, fact, expected):
    condition = {"field": "x", "operator": operator, "value": value}
    assert rules._matches(condition, {"x": fact}) is expected


def test_unknown_operator_raises():
    with pytest.raises(rules.RulesInvalid):
        rules._matches({"field": "x", "operator": "wat", "value": 1}, {"x": 1})


def test_validate_action_accepts_known_types():
    rules._validate_action([{"type": "apply_discount", "params": {"percent": 5}}])


def test_validate_action_rejects_unknown_type():
    with pytest.raises(rules.RulesInvalid):
        rules._validate_action([{"type": "levitate", "params": {}}])


def test_validate_action_rejects_non_list():
    with pytest.raises(rules.RulesInvalid):
        rules._validate_action({"type": "apply_discount"})


def test_condition_has_entity_placeholder():
    yes = {"op": "all", "clauses": [{"field": "client_id", "operator": "eq", "value": "$entity"},
                                     {"field": "quantity", "operator": "gt", "value": 100}]}
    no = {"field": "quantity", "operator": "gt", "value": 100}
    assert rules._condition_has_entity_placeholder(yes) is True
    assert rules._condition_has_entity_placeholder(no) is False


def test_substitute_entity_replaces_placeholder_only():
    condition = {"op": "all", "clauses": [
        {"field": "client_id", "operator": "eq", "value": "$entity"},
        {"field": "quantity", "operator": "gt", "value": 100},
    ]}
    resolved = rules._substitute_entity(condition, "c1")
    assert resolved["clauses"][0]["value"] == "c1"
    assert resolved["clauses"][1]["value"] == 100
    # original untouched
    assert condition["clauses"][0]["value"] == "$entity"

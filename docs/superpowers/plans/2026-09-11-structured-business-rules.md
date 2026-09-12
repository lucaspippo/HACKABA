# Structured Business Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic SI/ENTONCES rules engine (`core/rules.py`) alongside the existing free-text `core/conocimiento.py` memory, so a class of business rules with a precise condition and action is evaluated the same way every time instead of being re-narrated by an LLM.

**Architecture:** A new Postgres table `business_rules` (one row per rule, RLS-scoped like `business_knowledge_pieces`) backs a small condition/action DSL. `core/rules.py` resolves a rule's target entity (client/supplier/product) to a real ID once, at creation time, then matches/evaluates purely against that stored condition — no fuzzy re-matching at evaluation time. Three new Ángela tools (`propose_rule`, `evaluate_rule_for`, `list_rules`) plug it into chat, following the existing propose→chip→confirm pattern from `proponer_conocimiento`.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy Core + Alembic, Postgres (JSONB columns), pytest.

**Spec:** `docs/superpowers/specs/2026-09-11-structured-business-rules-design.md`

## Global Constraints

- All new identifiers (table/column names, module/function/variable names, comments, new Ángela tool names) are English. Comments only where the *why* isn't obvious from the code — default to none.
- Exception, per the spec: the stored **values** of `node` and `scope` reuse `core/conocimiento.py`'s existing Spanish catalog (`NODOS`, `AMBITOS`) verbatim — import them from there, never redefine.
- Every tenant-scoped query goes through `tenant_connection()`, never `get_admin_engine()`.
- No side effects, no order/receiving flow integration, no frontend panel — engine + Ángela chat tools + tests only, per spec's non-goals.
- Run the backend test suite with `../.venv/Scripts/python.exe -m pytest` from `backend/` (never bare `python` — see root `CLAUDE.md`).

---

### Task 1: Migration for `business_rules` + RLS test

**Files:**
- Create: `backend/migrations/versions/0048_business_rules.py`
- Modify: `backend/core/db/tenant_tables.py`
- Test: `backend/tests/test_migrations.py`

**Interfaces:**
- Produces: table `business_rules` with columns `id, tenant_id, description, condition (jsonb), action (jsonb), node, scope, entity_name, entity_type, entity_id, origin (jsonb), knowledge_piece_id, status, supersedes, superseded_by, version, test_cases (jsonb), created_at`. PK `(tenant_id, id)`. RLS enabled + forced + `tenant_isolation` policy.

- [ ] **Step 1: Write the failing RLS test**

Add to `backend/tests/test_migrations.py`, right after `test_business_knowledge_pieces_table_has_rls_enabled` (around line 202):

```python
def test_business_rules_table_has_rls_enabled():
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT relname, relrowsecurity, relforcerowsecurity "
            "FROM pg_class WHERE relname = 'business_rules'"
        )).mappings().all()
        assert len(rows) == 1
        assert rows[0]["relrowsecurity"] and rows[0]["relforcerowsecurity"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_migrations.py::test_business_rules_table_has_rls_enabled -v`
Expected: FAIL — `assert len(rows) == 1` fails (0 rows), because the table doesn't exist yet.

- [ ] **Step 3: Write the migration**

Create `backend/migrations/versions/0048_business_rules.py`:

```python
"""structured business rules: a deterministic condition/action engine
alongside core/conocimiento.py's free-text memory

Revision ID: 0048
Revises: 0047
Create Date: 2026-09-11

New table, no data migration: this is a sibling of business_knowledge_pieces
(0039), not a replacement for anything. See
docs/superpowers/specs/2026-09-11-structured-business-rules-design.md.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

revision = "0048"
down_revision = "0047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "business_rules",
        sa.Column("id", sa.Text, nullable=False),
        sa.Column("tenant_id", psql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("condition", psql.JSONB, nullable=False),
        sa.Column("action", psql.JSONB, nullable=False),
        sa.Column("node", sa.Text, nullable=False),
        sa.Column("scope", sa.Text, nullable=False),
        sa.Column("entity_name", sa.Text, nullable=True),
        sa.Column("entity_type", sa.Text, nullable=True),
        sa.Column("entity_id", sa.Text, nullable=True),
        sa.Column("origin", psql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("knowledge_piece_id", sa.Text, nullable=True),
        sa.Column("status", sa.Text, nullable=False, server_default="active"),
        sa.Column("supersedes", sa.Text, nullable=True),
        sa.Column("superseded_by", sa.Text, nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("test_cases", psql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("tenant_id", "id"),
        sa.CheckConstraint(
            "node IN ('ventas', 'inventario', 'deposito', 'proveedores', "
            "'clientes', 'caja', 'equipo', 'contexto')",
            name="business_rules_node_check"),
        sa.CheckConstraint(
            "scope IN ('cliente', 'proveedor', 'categoria', 'empleado', 'global')",
            name="business_rules_scope_check"),
        sa.CheckConstraint(
            "status IN ('active', 'paused', 'pending', 'archived', 'superseded')",
            name="business_rules_status_check"),
    )
    op.create_index("ix_business_rules_tenant_id", "business_rules", ["tenant_id"])

    op.execute("ALTER TABLE business_rules ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE business_rules FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON business_rules
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_table("business_rules")
```

- [ ] **Step 4: Add the table to `tenant_tables.py`**

In `backend/core/db/tenant_tables.py`, add `"business_rules"` to `BUSINESS_DATA_TABLES` (anywhere in the tuple, e.g. right after `"business_knowledge_pieces"`):

```python
    "collection_actions", "expiry_actions", "business_knowledge_pieces",
    "business_rules", "data_sections",
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_migrations.py::test_business_rules_table_has_rls_enabled -v`
Expected: PASS (the test suite's `dbsetup.py` runs `alembic upgrade head` against the test database automatically before tests run).

- [ ] **Step 6: Commit**

```bash
git add backend/migrations/versions/0048_business_rules.py backend/core/db/tenant_tables.py backend/tests/test_migrations.py
git commit -m "feat: add business_rules table with RLS"
```

---

### Task 2: `core/db/business_rules_repo.py`

**Files:**
- Create: `backend/core/db/business_rules_repo.py`
- Test: `backend/tests/test_business_rules_repo.py`

**Interfaces:**
- Consumes: `core.db.engine.tenant_connection(tenant_id)` (context manager yielding a SQLAlchemy connection).
- Produces:
  - `create(tenant_id, *, id, description, condition, action, node, scope, entity_name=None, entity_type=None, entity_id=None, origin=None, knowledge_piece_id=None, status="active", supersedes=None, version=1, test_cases=None) -> dict`
  - `list_rules(tenant_id) -> list[dict]`
  - `get(tenant_id, rule_id) -> dict | None`
  - `set_status(tenant_id, rule_id, status) -> dict | None`
  - `set_superseded_by(tenant_id, rule_id, *, superseded_by) -> dict | None` (also sets `status="superseded"`)
  - Every dict has keys: `id, description, condition, action, node, scope, entity_name, entity_type, entity_id, origin, knowledge_piece_id, status, supersedes, superseded_by, version, test_cases, created_at` (created_at as ISO string).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_business_rules_repo.py`:

```python
from core.db import business_rules_repo


def _rule(**kw):
    base = dict(
        id="rtest1", description="5% off orders over 100 units for client X",
        condition={"op": "all", "clauses": [
            {"field": "client_id", "operator": "eq", "value": "c1"},
            {"field": "quantity", "operator": "gt", "value": 100},
        ]},
        action=[{"type": "apply_discount", "params": {"percent": 5}}],
        node="ventas", scope="cliente", entity_name="Client X",
        entity_type="cliente", entity_id="c1",
        origin={"author": "aldo", "created_at": "2026-09-11", "source": "conversation"},
    )
    base.update(kw)
    return base


def test_create_then_list(db_tenant):
    row = business_rules_repo.create(db_tenant, **_rule())
    assert row["id"] == "rtest1"
    assert row["status"] == "active"
    assert row["version"] == 1
    assert row["test_cases"] == []
    assert row["condition"]["clauses"][0]["value"] == "c1"

    rows = business_rules_repo.list_rules(db_tenant)
    assert len(rows) == 1
    assert rows[0]["id"] == "rtest1"


def test_get_missing_returns_none(db_tenant):
    assert business_rules_repo.get(db_tenant, "no-existe") is None


def test_set_status(db_tenant):
    business_rules_repo.create(db_tenant, **_rule())
    updated = business_rules_repo.set_status(db_tenant, "rtest1", "paused")
    assert updated["status"] == "paused"
    assert business_rules_repo.get(db_tenant, "rtest1")["status"] == "paused"


def test_set_superseded_by(db_tenant):
    business_rules_repo.create(db_tenant, **_rule())
    business_rules_repo.create(db_tenant, **_rule(id="rtest2"))
    updated = business_rules_repo.set_superseded_by(db_tenant, "rtest1", superseded_by="rtest2")
    assert updated["status"] == "superseded"
    assert updated["superseded_by"] == "rtest2"


def test_test_cases_round_trip(db_tenant):
    cases = [{"facts": {"client_id": "c1", "quantity": 150},
              "expected_action": [{"type": "apply_discount", "params": {"percent": 5}}]}]
    row = business_rules_repo.create(db_tenant, **_rule(test_cases=cases))
    assert row["test_cases"] == cases


def test_tenants_never_see_each_others_rules(db_tenant):
    business_rules_repo.create(db_tenant, **_rule())
    from core.db.engine import get_admin_engine
    from sqlalchemy import text
    import uuid as _uuid
    engine = get_admin_engine()
    with engine.begin() as conn:
        other_id = conn.execute(text(
            "INSERT INTO tenants (slug, name, short_name, source) "
            "VALUES (:slug, 'Other', 'Other', 'test') RETURNING id"
        ), {"slug": f"test-other-{_uuid.uuid4().hex[:8]}"}).scalar_one()
    try:
        assert business_rules_repo.list_rules(str(other_id)) == []
    finally:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM tenants WHERE id = :id"), {"id": other_id})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_business_rules_repo.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.db.business_rules_repo'`.

- [ ] **Step 3: Write the repo module**

Create `backend/core/db/business_rules_repo.py`:

```python
"""One row per structured business rule — core/rules.py's storage. See
migration 0048 and docs/superpowers/specs/2026-09-11-structured-business-rules-design.md."""
from __future__ import annotations

import json

from sqlalchemy import text

from core.db.engine import tenant_connection

_COLS = ("id", "description", "condition", "action", "node", "scope",
         "entity_name", "entity_type", "entity_id", "origin",
         "knowledge_piece_id", "status", "supersedes", "superseded_by",
         "version", "test_cases", "created_at")


def _to_rule(row) -> dict:
    return {
        "id": row["id"],
        "description": row["description"],
        "condition": row["condition"],
        "action": row["action"],
        "node": row["node"],
        "scope": row["scope"],
        "entity_name": row["entity_name"],
        "entity_type": row["entity_type"],
        "entity_id": row["entity_id"],
        "origin": row["origin"] or {},
        "knowledge_piece_id": row["knowledge_piece_id"],
        "status": row["status"],
        "supersedes": row["supersedes"],
        "superseded_by": row["superseded_by"],
        "version": row["version"],
        "test_cases": row["test_cases"] or [],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


def list_rules(tenant_id: str) -> list[dict]:
    with tenant_connection(tenant_id) as conn:
        rows = conn.execute(
            text(f"SELECT {', '.join(_COLS)} FROM business_rules ORDER BY created_at")
        ).mappings().all()
    return [_to_rule(r) for r in rows]


def get(tenant_id: str, rule_id: str) -> dict | None:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(f"SELECT {', '.join(_COLS)} FROM business_rules WHERE id = :id"),
            {"id": rule_id},
        ).mappings().one_or_none()
    return _to_rule(row) if row else None


def create(tenant_id: str, *, id: str, description: str, condition: dict,
          action: list, node: str, scope: str, entity_name: str | None = None,
          entity_type: str | None = None, entity_id: str | None = None,
          origin: dict | None = None, knowledge_piece_id: str | None = None,
          status: str = "active", supersedes: str | None = None,
          version: int = 1, test_cases: list | None = None) -> dict:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                "INSERT INTO business_rules "
                "(id, tenant_id, description, condition, action, node, scope, "
                " entity_name, entity_type, entity_id, origin, knowledge_piece_id, "
                " status, supersedes, version, test_cases) "
                "VALUES (:id, :tid, :description, :condition, :action, :node, :scope, "
                " :entity_name, :entity_type, :entity_id, :origin, :knowledge_piece_id, "
                " :status, :supersedes, :version, :test_cases) "
                f"RETURNING {', '.join(_COLS)}"
            ),
            {"id": id, "tid": tenant_id, "description": description,
             "condition": json.dumps(condition), "action": json.dumps(action),
             "node": node, "scope": scope, "entity_name": entity_name,
             "entity_type": entity_type, "entity_id": entity_id,
             "origin": json.dumps(origin or {}), "knowledge_piece_id": knowledge_piece_id,
             "status": status, "supersedes": supersedes, "version": version,
             "test_cases": json.dumps(test_cases or [])},
        ).mappings().one()
    return _to_rule(row)


def set_status(tenant_id: str, rule_id: str, status: str) -> dict | None:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                "UPDATE business_rules SET status = :status "
                f"WHERE id = :id RETURNING {', '.join(_COLS)}"
            ),
            {"status": status, "id": rule_id},
        ).mappings().one_or_none()
    return _to_rule(row) if row else None


def set_superseded_by(tenant_id: str, rule_id: str, *, superseded_by: str) -> dict | None:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                "UPDATE business_rules SET status = 'superseded', superseded_by = :sup_by "
                f"WHERE id = :id RETURNING {', '.join(_COLS)}"
            ),
            {"sup_by": superseded_by, "id": rule_id},
        ).mappings().one_or_none()
    return _to_rule(row) if row else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_business_rules_repo.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/core/db/business_rules_repo.py backend/tests/test_business_rules_repo.py
git commit -m "feat: add business_rules_repo storage layer"
```

---

### Task 3: Condition matcher + action validation (pure logic, no DB)

**Files:**
- Create: `backend/core/rules.py`
- Test: `backend/tests/test_rules_matching.py`

**Interfaces:**
- Produces (module-private but used by Task 4/5):
  - `RulesInvalid(ValueError)` exception class.
  - `ACTION_TYPES = {"apply_discount", "mark_receipt_partial", "notify", "require_human_confirmation"}`
  - `_matches(condition: dict, facts: dict) -> bool`
  - `_validate_action(action: list) -> None` (raises `RulesInvalid` on a bad shape)
  - `_condition_has_entity_placeholder(condition: dict) -> bool`
  - `_substitute_entity(condition: dict, entity_id: str) -> dict` (returns a new dict, does not mutate the input)

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_rules_matching.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_rules_matching.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.rules'`.

- [ ] **Step 3: Write the implementation**

Create `backend/core/rules.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_rules_matching.py -v`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add backend/core/rules.py backend/tests/test_rules_matching.py
git commit -m "feat: add condition matcher and action validation for business rules"
```

---

### Task 4: Entity resolution + CRUD lifecycle

**Files:**
- Modify: `backend/core/rules.py`
- Test: `backend/tests/test_rules_lifecycle.py`

**Interfaces:**
- Consumes: `core.rules.RulesInvalid`, `core.rules._matches`, `core.rules._validate_action`, `core.rules._condition_has_entity_placeholder`, `core.rules._substitute_entity` (Task 3); `core.db.business_rules_repo.create/list_rules/get/set_status/set_superseded_by` (Task 2); `core.conocimiento.NODOS`, `core.conocimiento.NODO_FEATURE`, `core.conocimiento.AMBITOS` (existing).
- Produces:
  - `validate_proposal(*, description, condition, action, node, scope, entity_name=None, entity_type=None) -> dict` — returns `{description, condition, action, node, scope, entity_name, entity_type, entity_id, status}`, writes nothing. Raises `RulesInvalid` on a bad shape.
  - `create(*, description, condition, action, node, scope, entity_name=None, entity_type=None, origin, knowledge_piece_id=None, test_cases=None) -> dict` — persists, returns the stored row.
  - `list_rules(node=None, scope=None, status=None) -> list[dict]`
  - `get(rule_id) -> dict | None`
  - `pause(rule_id) -> dict | None`
  - `activate(rule_id) -> dict | None`
  - `archive(rule_id, *, actor) -> dict | None`
  - `supersede(rule_id, *, replacement_id, actor) -> dict | None`
  - `visible_to(user: dict, rules: list[dict] | None = None) -> list[dict]` — same role-scoping semantics as `conocimiento.visibles_para`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_rules_lifecycle.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_rules_lifecycle.py -v`
Expected: FAIL with `AttributeError: module 'core.rules' has no attribute 'validate_proposal'`.

- [ ] **Step 3: Extend the implementation**

Append to `backend/core/rules.py` (after the code from Task 3):

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_rules_lifecycle.py -v`
Expected: PASS (all tests).

- [ ] **Step 5: Register the new audit actions**

`test_p42.py`'s audit-classification scan (see `backend/tests/test_p42.py` around line 109-117) will fail once `core/rules.py` emits `"create_rule"`, `"archive_rule"`, and `"supersede_rule"` through `AuditLog().record(...)` unless they're declared. In `backend/core/auditoria.py`, add near the existing `*_conocimiento` entries (around line 71-77):

```python
    "create_rule":    {"clase": "datos", "gate": "propia"},
    "archive_rule":   {"clase": "datos", "gate": "propia"},
    "supersede_rule": {"clase": "datos", "gate": "propia"},
```

In `backend/i18n.py`, add near the existing `audit.acc.*_conocimiento` entries (around line 3419-3426):

```python
    "audit.acc.create_rule": {"es": "Creó una regla estructurada del negocio",
                              "en": "Created a structured business rule"},
    "audit.acc.archive_rule": {"es": "Archivó una regla estructurada del negocio",
                               "en": "Archived a structured business rule"},
    "audit.acc.supersede_rule": {"es": "Reemplazó una regla estructurada del negocio",
                                 "en": "Replaced a structured business rule"},
```

- [ ] **Step 6: Run the audit-classification and bilingual-text tests**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_p42.py -v`
Expected: PASS — in particular the scan that fails on undeclared audit slugs and the bilingual-text check.

- [ ] **Step 7: Commit**

```bash
git add backend/core/rules.py backend/tests/test_rules_lifecycle.py backend/core/auditoria.py backend/i18n.py
git commit -m "feat: add entity resolution and CRUD lifecycle to core/rules.py"
```

---

### Task 5: `evaluate()` + `verify()` — the 3 reference use cases

**Files:**
- Modify: `backend/core/rules.py`
- Test: `backend/tests/test_rules_evaluate.py`

**Interfaces:**
- Consumes: everything from Tasks 3-4.
- Produces:
  - `evaluate(facts: dict) -> list[dict]` — each item `{rule_id, description, actions}`.
  - `verify(rule_id: str) -> dict` — `{ok: bool, results: [{case, expected, actual, ok}]}`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_rules_evaluate.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_rules_evaluate.py -v`
Expected: FAIL with `AttributeError: module 'core.rules' has no attribute 'evaluate'`.

- [ ] **Step 3: Add `evaluate()` and `verify()`**

Append to `backend/core/rules.py`:

```python
def evaluate(facts: dict) -> list[dict]:
    matches = []
    for rule in list_rules(status="active"):
        if _matches(rule["condition"], facts):
            matches.append({"rule_id": rule["id"], "description": rule["description"],
                            "actions": rule["action"]})
    return matches


def verify(rule_id: str) -> dict:
    rule = get(rule_id)
    if not rule:
        raise RulesInvalid(f"no such rule: {rule_id!r}")
    results = []
    for case in rule["test_cases"]:
        actual = rule["action"] if _matches(rule["condition"], case["facts"]) else []
        expected = case.get("expected_action")
        ok = True if expected is None else actual == expected
        results.append({"case": case, "expected": expected, "actual": actual, "ok": ok})
    return {"ok": all(r["ok"] for r in results), "results": results}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_rules_evaluate.py -v`
Expected: PASS (all tests, covering the 3 reference use cases plus `verify`).

- [ ] **Step 5: Commit**

```bash
git add backend/core/rules.py backend/tests/test_rules_evaluate.py
git commit -m "feat: add evaluate() and verify() to core/rules.py"
```

---

### Task 6: Ángela chat tools (`propose_rule`, `evaluate_rule_for`, `list_rules`)

**Files:**
- Modify: `backend/angela.py`
- Test: `backend/tests/test_rules_tools.py`

**Interfaces:**
- Consumes: `core.rules.validate_proposal`, `core.rules.evaluate`, `core.rules.list_rules`, `core.rules.visible_to`, `core.rules.RulesInvalid` (Tasks 4-5); `angela._usuario_para_manual()`, `angela._run_tool` dispatch pattern (existing).
- Produces: three entries in `angela.TOOLS`, three `if name == ...` branches in `angela._run_tool`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_rules_tools.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_rules_tools.py -v`
Expected: FAIL — `angela._run_tool` returns `{"error": "herramienta desconocida: propose_rule"}`.

- [ ] **Step 3: Add the tool definitions**

In `backend/angela.py`, insert before the closing `]` of `TOOLS` (currently line 1400, right after the `objetivos_negocio` entry):

```python
    {
        "name": "propose_rule",
        "description": "Propose a structured, deterministic SI/ENTONCES business rule "
        "(a precise condition and a precise action, e.g. 'if this client orders more than "
        "100 units, apply a 5% discount') that should always be evaluated the same way — "
        "unlike proponer_conocimiento's free-text memory, which is narrated, not computed. "
        "Use this instead of proponer_conocimiento when the conversation states an exact "
        "condition and an exact action, not just context. This SAVES NOTHING on its own — "
        "it returns a validated proposal for a chip the person taps to confirm.",
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "human-readable summary of the rule"},
                "condition": {"type": "object", "description":
                    "a boolean tree: {\"op\": \"all\"|\"any\", \"clauses\": [...]}, where each "
                    "clause is either {\"field\", \"operator\", \"value\"} (operator one of "
                    "eq/ne/gt/gte/lt/lte/in/not_in) or another nested {op, clauses} node. "
                    "When scope is not 'global', exactly the clause(s) that pin the rule to "
                    "its entity must use the literal string \"$entity\" as their value — it "
                    "gets resolved to the real entity ID automatically."},
                "action": {"type": "array", "description":
                    "a list of {\"type\", \"params\"} steps. type is one of: apply_discount "
                    "(params: percent), mark_receipt_partial, notify (params: target), "
                    "require_human_confirmation."},
                "node": {"type": "string", "enum": ["ventas", "inventario", "deposito", "proveedores",
                                                    "clientes", "caja", "equipo", "contexto"]},
                "scope": {"type": "string", "enum": ["cliente", "proveedor", "categoria", "empleado", "global"]},
                "entity_name": {"type": "string", "description": "the specific customer/supplier/product this rule targets, if scope isn't global"},
                "entity_type": {"type": "string", "enum": ["cliente", "proveedor", "producto"]},
            },
            "required": ["description", "condition", "action", "node", "scope"],
        },
    },
    {
        "name": "evaluate_rule_for",
        "description": "Hand the deterministic rules engine a structured fact you built from "
        "the conversation (e.g. {\"client_id\": \"...\", \"quantity\": 150}) and get back which "
        "active rules match and what they resolve to. NEVER compute a discount, a decision, "
        "or an action yourself — always relay exactly what this returns.",
        "input_schema": {
            "type": "object",
            "properties": {
                "facts": {"type": "object", "description": "field -> value, matched against active rules' conditions"},
            },
            "required": ["facts"],
        },
    },
    {
        "name": "list_rules",
        "description": "List the structured business rules already taught to Ángela "
        "(read-only) — what this user is allowed to see, same scoping as business knowledge.",
        "input_schema": {
            "type": "object",
            "properties": {
                "node": {"type": "string", "enum": ["ventas", "inventario", "deposito",
                                                    "proveedores", "clientes", "caja",
                                                    "equipo", "contexto"]},
            },
        },
    },
]
```

- [ ] **Step 4: Add the `_run_tool` handlers**

In `backend/angela.py`, insert right after the existing `if name == "proponer_conocimiento": ... return result, None` block (ends around line 1894, right before `if name == "reordenar_inicio":`):

```python
    if name == "propose_rule":
        from core import rules
        try:
            proposal = rules.validate_proposal(
                description=args.get("description", ""), condition=args.get("condition", {}),
                action=args.get("action", []), node=args.get("node", ""),
                scope=args.get("scope", ""), entity_name=args.get("entity_name"),
                entity_type=args.get("entity_type"))
        except rules.RulesInvalid as e:
            return {"ok": False, "motivo": str(e)}, None
        return {"ok": True, "proposal": proposal}, None
    if name == "evaluate_rule_for":
        from core import rules
        matches = rules.evaluate(args.get("facts", {}))
        return {"matches": matches}, None
    if name == "list_rules":
        from core import rules
        matched = rules.list_rules(node=args.get("node"), status="active")
        matched = rules.visible_to(_usuario_para_manual(), matched)
        return {"rules": matched}, None
```

- [ ] **Step 5: Add the system-prompt guidance**

In `backend/angela.py`, right after the existing "CUANDO TE PIDEN QUE TE ACUERDES DE ALGO" block (ends around line 576, just before "NORMALIZACIÓN AUTOMÁTICA"), add:

```
CUANDO LA REGLA ES UNA CONDICIÓN Y UNA ACCIÓN EXACTAS:
- Si lo que te dicen tiene una condición precisa y una acción precisa ("si el cliente X pide
más de 100 unidades, aplicale 5% de descuento"; "si hay reporte de daño de tal proveedor, marcá
la recepción como parcial y avisale a compras"), no es texto libre: usá 'propose_rule', no
'proponer_conocimiento'. La diferencia es que esto lo tiene que aplicar un motor determinístico
siempre igual, no vos narrándolo de memoria cada vez.
- 'propose_rule' tampoco guarda nada por sí solo: mismo patrón del chip a confirmar.
- Para aplicar una regla ya guardada a un pedido o hecho concreto, usá 'evaluate_rule_for' con
los datos como hecho estructurado. Nunca calcules vos vos el descuento o la decisión: contá
exactamente lo que te devuelve el motor.
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_rules_tools.py -v`
Expected: PASS (all tests).

- [ ] **Step 7: Commit**

```bash
git add backend/angela.py backend/tests/test_rules_tools.py
git commit -m "feat: add propose_rule, evaluate_rule_for, and list_rules Angela tools"
```

---

### Task 7: Confirm endpoint (`POST /api/rules/confirm`)

**Files:**
- Modify: `backend/main.py`
- Test: `backend/tests/test_rules_confirm.py`

**Interfaces:**
- Consumes: `core.rules.validate_proposal`, `core.rules.create`, `core.rules.RulesInvalid`, `core.conocimiento.NODO_FEATURE` (existing); `usuario_actual`, `_lang` (existing FastAPI dependencies in `main.py`).
- Produces: `POST /api/rules/confirm` — same response shape as `POST /api/conocimiento/confirm`: `{"ok": True, "rule": <dict>, "state": <status>}`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_rules_confirm.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_rules_confirm.py -v`
Expected: FAIL with 404 (route doesn't exist).

- [ ] **Step 3: Add the endpoint**

In `backend/main.py`, add near the existing `/api/conocimiento/*` routes (after `conocimiento_borrar`, e.g. right after line 3635's closing of that function):

```python
class RuleProposal(BaseModel):
    description: str
    condition: dict
    action: list
    node: str
    scope: str
    entity_name: str | None = None
    entity_type: str | None = None


def _can_activate_rule(u: dict, node: str, scope: str) -> bool:
    if u.get("es_admin"):
        return True
    if scope == "global":
        return False
    from core import conocimiento, perfiles
    return conocimiento.NODO_FEATURE.get(node) in set(perfiles.features_efectivas(u["username"]))


@app.post("/api/rules/confirm")
def rules_confirm(req: RuleProposal, u: dict = Depends(usuario_actual)):
    from core import fechas, rules
    try:
        proposal = rules.validate_proposal(
            description=req.description, condition=req.condition, action=req.action,
            node=req.node, scope=req.scope, entity_name=req.entity_name,
            entity_type=req.entity_type)
    except rules.RulesInvalid as e:
        raise HTTPException(status_code=400, detail=str(e))

    rule = rules.create(
        description=proposal["description"], condition=proposal["condition"],
        action=proposal["action"], node=proposal["node"], scope=proposal["scope"],
        entity_name=proposal["entity_name"], entity_type=proposal["entity_type"],
        origin={"author": u["username"], "created_at": fechas.hoy().isoformat(),
               "source": "conversation"})

    # rules.create() already resolved active/pending from entity resolution
    # alone; downgrade further when the confirming user lacks the authority
    # to activate this rule outright (mirrors conocimiento_confirm's
    # _can_activate). core/rules.py exposes no "set to pending" verb of its
    # own (pending only ever happens as a side effect of creation), so this
    # one case goes straight through the repo.
    if rule["status"] == "active" and not _can_activate_rule(u, rule["node"], rule["scope"]):
        from core.db import business_rules_repo
        from core.db import tenant as _tenant
        rule = business_rules_repo.set_status(_tenant.current_tenant_id(), rule["id"], "pending")
    return {"ok": True, "rule": rule, "state": rule["status"]}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_rules_confirm.py -v`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/tests/test_rules_confirm.py
git commit -m "feat: add POST /api/rules/confirm endpoint"
```

---

### Task 8: Full-suite regression check

**Files:** none (verification only).

- [ ] **Step 1: Run the full backend suite twice, as two separate invocations**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest -q`
Run again as a fresh invocation: `cd backend && ../.venv/Scripts/python.exe -m pytest -q`
Expected: PASS both times (per `core/db/MIGRATING_A_MODULE.md`'s warning, a second, separate run catches cross-run leftover-row leakage that a single run — or the same run twice in one process — cannot).

- [ ] **Step 2: Restore any mutated demo/piloto seed files**

Run: `cd .. && git checkout -- data-demo/`
Expected: clean `git status` for `data-demo/`.

- [ ] **Step 3: Final review commit (if anything needs squashing/cleanup), otherwise done**

No commit needed if Task 1-7 commits already stand alone cleanly.

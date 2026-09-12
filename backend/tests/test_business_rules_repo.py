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

from core.db import pattern_feedback_repo


def test_create_then_history(db_tenant):
    row = pattern_feedback_repo.create(
        db_tenant, pattern_id="combo_no_percibido", fingerprint="1:2",
        action="dismissed", actor="aldo", snapshot={"titulo": "x"})
    assert row["pattern_id"] == "combo_no_percibido"
    assert row["fingerprint"] == "1:2"
    assert row["action"] == "dismissed"
    assert row["snapshot"] == {"titulo": "x"}

    hist = pattern_feedback_repo.history(db_tenant)
    assert len(hist) == 1
    assert hist[0]["id"] == row["id"]


def test_unknown_action_rejected(db_tenant):
    import pytest
    with pytest.raises(ValueError):
        pattern_feedback_repo.create(
            db_tenant, pattern_id="combo_no_percibido", fingerprint="1:2",
            action="not_a_real_action", actor="aldo", snapshot={})


def test_latest_by_fingerprint_keeps_only_the_most_recent_per_pair(db_tenant):
    pattern_feedback_repo.create(
        db_tenant, pattern_id="faltante_caja_patron", fingerprint="weekday:5",
        action="dismissed", actor="aldo", snapshot={"titulo": "first"})
    second = pattern_feedback_repo.create(
        db_tenant, pattern_id="faltante_caja_patron", fingerprint="weekday:5",
        action="already_knew", actor="aldo", snapshot={"titulo": "second"})
    latest = pattern_feedback_repo.latest_by_fingerprint(db_tenant)
    assert set(latest) == {"faltante_caja_patron:weekday:5"}
    assert latest["faltante_caja_patron:weekday:5"]["id"] == second["id"]
    assert latest["faltante_caja_patron:weekday:5"]["action"] == "already_knew"


def test_latest_by_fingerprint_keeps_different_fingerprints_separate(db_tenant):
    pattern_feedback_repo.create(
        db_tenant, pattern_id="combo_no_percibido", fingerprint="1:2",
        action="dismissed", actor="aldo", snapshot={})
    pattern_feedback_repo.create(
        db_tenant, pattern_id="combo_no_percibido", fingerprint="3:4",
        action="accepted", actor="aldo", snapshot={})
    latest = pattern_feedback_repo.latest_by_fingerprint(db_tenant)
    assert set(latest) == {"combo_no_percibido:1:2", "combo_no_percibido:3:4"}


def test_tenants_never_see_each_others_feedback(db_tenant):
    pattern_feedback_repo.create(
        db_tenant, pattern_id="combo_no_percibido", fingerprint="1:2",
        action="dismissed", actor="aldo", snapshot={})
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
        assert pattern_feedback_repo.history(str(other_id)) == []
        assert pattern_feedback_repo.latest_by_fingerprint(str(other_id)) == {}
    finally:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM tenants WHERE id = :id"), {"id": other_id})

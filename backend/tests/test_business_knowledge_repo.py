from core.db import business_knowledge_repo


def _piece(**kw):
    base = dict(id="ktest1", texto="Tolerale 45 días a Doña Elsa.", tipo="regla",
               ambito="cliente", entidad="Despensa Doña Elsa", nodo="clientes",
               efecto="ajusta_umbral")
    base.update(kw)
    return base


def test_create_then_list(db_tenant):
    row = business_knowledge_repo.create(db_tenant, **_piece())
    assert row["id"] == "ktest1"
    assert row["estado"] == "activo"
    assert row["veces_aplicada"] == 0
    assert row["efecto_profundo"] is False

    rows = business_knowledge_repo.list_pieces(db_tenant)
    assert len(rows) == 1
    assert rows[0]["id"] == "ktest1"


def test_get_missing_returns_none(db_tenant):
    assert business_knowledge_repo.get(db_tenant, "no-existe") is None


def test_set_status(db_tenant):
    business_knowledge_repo.create(db_tenant, **_piece())
    updated = business_knowledge_repo.set_status(db_tenant, "ktest1", "pausado")
    assert updated["estado"] == "pausado"
    assert business_knowledge_repo.get(db_tenant, "ktest1")["estado"] == "pausado"


def test_increment_applied(db_tenant):
    business_knowledge_repo.create(db_tenant, **_piece())
    business_knowledge_repo.increment_applied(db_tenant, "ktest1")
    row = business_knowledge_repo.increment_applied(db_tenant, "ktest1", 2)
    assert row["veces_aplicada"] == 3


def test_delete(db_tenant):
    business_knowledge_repo.create(db_tenant, **_piece())
    assert business_knowledge_repo.delete(db_tenant, "ktest1") is True
    assert business_knowledge_repo.get(db_tenant, "ktest1") is None
    assert business_knowledge_repo.delete(db_tenant, "ktest1") is False


def test_seed_if_empty_only_seeds_once(db_tenant):
    seed = {"piezas": [_piece(id="k01"), _piece(id="k02", entidad="Otro Cliente")]}
    business_knowledge_repo.seed_if_empty(db_tenant, seed)
    assert len(business_knowledge_repo.list_pieces(db_tenant)) == 2

    business_knowledge_repo.set_status(db_tenant, "k01", "pausado")
    business_knowledge_repo.seed_if_empty(db_tenant, seed)  # no-op: table isn't empty
    assert business_knowledge_repo.get(db_tenant, "k01")["estado"] == "pausado"


def test_tenants_never_see_each_others_pieces(db_tenant):
    business_knowledge_repo.create(db_tenant, **_piece())
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
        assert business_knowledge_repo.list_pieces(str(other_id)) == []
    finally:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM tenants WHERE id = :id"), {"id": other_id})

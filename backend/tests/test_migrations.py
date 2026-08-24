from sqlalchemy import text

from core.db.engine import get_engine


def test_tenants_table_exists():
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'tenants' ORDER BY column_name"
        )).scalars().all()
        assert set(row) == {
            "created_at", "default_lang", "id", "logo_url",
            "name", "short_name", "slug", "source",
        }


def test_auth_tables_have_rls_enabled():
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT relname, relrowsecurity, relforcerowsecurity "
            "FROM pg_class WHERE relname IN ('auth_credentials', 'sessions')"
        )).mappings().all()
        by_name = {r["relname"]: r for r in rows}
        assert by_name["auth_credentials"]["relrowsecurity"] is True
        assert by_name["auth_credentials"]["relforcerowsecurity"] is True
        assert by_name["sessions"]["relrowsecurity"] is True
        assert by_name["sessions"]["relforcerowsecurity"] is True


def test_rls_blocks_cross_tenant_reads():
    from core.db.engine import get_admin_engine, tenant_connection

    admin = get_admin_engine()
    with admin.begin() as conn:
        t1 = conn.execute(text(
            "INSERT INTO tenants (slug, name, short_name, source) "
            "VALUES ('rls-test-1', 'T1', 'T1', 'test') RETURNING id"
        )).scalar_one()
        t2 = conn.execute(text(
            "INSERT INTO tenants (slug, name, short_name, source) "
            "VALUES ('rls-test-2', 'T2', 'T2', 'test') RETURNING id"
        )).scalar_one()

    with tenant_connection(str(t1)) as conn:
        conn.execute(text(
            "INSERT INTO auth_credentials (tenant_id, username, password_hash) "
            "VALUES (:tid, 'alice', 'hash')"
        ), {"tid": str(t1)})

    with tenant_connection(str(t2)) as conn:
        rows = conn.execute(text("SELECT * FROM auth_credentials")).mappings().all()
        assert rows == []  # t2's session variable can't see t1's row

    with admin.begin() as conn:
        conn.execute(text("DELETE FROM tenants WHERE id IN (:a, :b)"), {"a": t1, "b": t2})


def test_customer_accounts_tables_have_rls_enabled():
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT relname, relrowsecurity, relforcerowsecurity "
            "FROM pg_class WHERE relname IN ('customer_accounts', 'account_movements')"
        )).mappings().all()
        assert len(rows) == 2
        assert all(r["relrowsecurity"] and r["relforcerowsecurity"] for r in rows)


def test_audit_events_table_has_rls_enabled():
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT relname, relrowsecurity, relforcerowsecurity "
            "FROM pg_class WHERE relname = 'audit_events'"
        )).mappings().all()
        assert len(rows) == 1
        assert rows[0]["relrowsecurity"] and rows[0]["relforcerowsecurity"]


def test_data_versions_table_has_rls_enabled():
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT relname, relrowsecurity, relforcerowsecurity "
            "FROM pg_class WHERE relname = 'data_versions'"
        )).mappings().all()
        assert len(rows) == 1
        assert rows[0]["relrowsecurity"] and rows[0]["relforcerowsecurity"]


def test_inventory_working_table_has_rls_enabled():
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT relname, relrowsecurity, relforcerowsecurity "
            "FROM pg_class WHERE relname = 'inventory_working'"
        )).mappings().all()
        assert len(rows) == 1
        assert rows[0]["relrowsecurity"] and rows[0]["relforcerowsecurity"]


def test_caja_state_table_has_rls_enabled():
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT relname, relrowsecurity, relforcerowsecurity "
            "FROM pg_class WHERE relname = 'caja_state'"
        )).mappings().all()
        assert len(rows) == 1
        assert rows[0]["relrowsecurity"] and rows[0]["relforcerowsecurity"]


def test_organization_config_table_has_rls_enabled():
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT relname, relrowsecurity, relforcerowsecurity "
            "FROM pg_class WHERE relname = 'organization_config'"
        )).mappings().all()
        assert len(rows) == 1
        assert rows[0]["relrowsecurity"] and rows[0]["relforcerowsecurity"]


def test_purchase_orders_table_has_rls_enabled():
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT relname, relrowsecurity, relforcerowsecurity "
            "FROM pg_class WHERE relname = 'purchase_orders'"
        )).mappings().all()
        assert len(rows) == 1
        assert rows[0]["relrowsecurity"] and rows[0]["relforcerowsecurity"]


def test_team_goals_table_has_rls_enabled():
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT relname, relrowsecurity, relforcerowsecurity "
            "FROM pg_class WHERE relname = 'team_goals'"
        )).mappings().all()
        assert len(rows) == 1
        assert rows[0]["relrowsecurity"] and rows[0]["relforcerowsecurity"]


def test_supplier_conditions_table_has_rls_enabled():
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT relname, relrowsecurity, relforcerowsecurity "
            "FROM pg_class WHERE relname = 'supplier_conditions'"
        )).mappings().all()
        assert len(rows) == 1
        assert rows[0]["relrowsecurity"] and rows[0]["relforcerowsecurity"]

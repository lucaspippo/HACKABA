import os

from sqlalchemy import text

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://polpilot:polpilot@localhost:5432/polpilot")
os.environ.setdefault("APP_DATABASE_URL", "postgresql+psycopg://polpilot_app:polpilot_app@localhost:5432/polpilot")


def test_get_engine_connects():
    from core.db.engine import get_engine

    engine = get_engine()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar_one() == 1


def test_get_admin_engine_connects():
    from core.db.engine import get_admin_engine

    engine = get_admin_engine()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar_one() == 1


def test_app_role_is_not_superuser_and_has_no_bypassrls():
    """The whole point of the two-engine split: if this ever comes back
    True, Row-Level Security silently stops applying to every tenant-scoped
    query — see the Task 4 correction note in the plan."""
    from core.db.engine import get_engine

    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
        )).mappings().one()
        assert row["rolsuper"] is False
        assert row["rolbypassrls"] is False


def test_tenant_connection_sets_session_variable():
    from core.db.engine import tenant_connection

    with tenant_connection("11111111-1111-1111-1111-111111111111") as conn:
        val = conn.execute(text("SELECT current_setting('app.tenant_id', true)")).scalar_one()
        assert val == "11111111-1111-1111-1111-111111111111"

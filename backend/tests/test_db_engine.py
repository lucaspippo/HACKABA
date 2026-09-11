import os

import pytest
from sqlalchemy import text


def test_get_engine_connects():
    os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://polpilot:polpilot@localhost:5432/polpilot")
    from core.db.engine import get_engine

    engine = get_engine()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar_one() == 1


def test_tenant_connection_sets_session_variable():
    from core.db.engine import tenant_connection

    with tenant_connection("11111111-1111-1111-1111-111111111111") as conn:
        val = conn.execute(text("SELECT current_setting('app.tenant_id', true)")).scalar_one()
        assert val == "11111111-1111-1111-1111-111111111111"

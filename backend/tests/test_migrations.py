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

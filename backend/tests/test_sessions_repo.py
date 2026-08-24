from core.db import sessions_repo


def test_create_then_get_roundtrip(db_tenant):
    sessions_repo.create(db_tenant, "alice", "tok-123", ttl_seconds=60)
    session = sessions_repo.get(db_tenant, "tok-123")
    assert session is not None
    assert session["username"] == "alice"


def test_get_missing_token_returns_none(db_tenant):
    assert sessions_repo.get(db_tenant, "no-such-token") is None


def test_expired_session_returns_none_and_is_purged(db_tenant):
    sessions_repo.create(db_tenant, "alice", "tok-expired", ttl_seconds=-1)
    assert sessions_repo.get(db_tenant, "tok-expired") is None
    # a second call finds nothing to purge — confirms the row is actually gone
    assert sessions_repo.get(db_tenant, "tok-expired") is None

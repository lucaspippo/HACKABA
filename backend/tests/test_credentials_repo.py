from core.db import credentials_repo


def test_set_then_get_roundtrip(db_tenant):
    credentials_repo.set(db_tenant, "alice", "some-hash")
    assert credentials_repo.get(db_tenant, "alice") == "some-hash"


def test_get_missing_returns_none(db_tenant):
    assert credentials_repo.get(db_tenant, "nobody") is None


def test_set_is_idempotent_upsert(db_tenant):
    credentials_repo.set(db_tenant, "alice", "hash-1")
    credentials_repo.set(db_tenant, "alice", "hash-2")
    assert credentials_repo.get(db_tenant, "alice") == "hash-2"

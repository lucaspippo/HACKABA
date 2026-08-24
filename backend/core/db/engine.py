"""
The one module that knows how to open a Postgres connection. Every domain
repo module (core/db/*_repo.py) goes through tenant_connection() — never
through get_engine() directly — so tenant isolation (RLS) is never optional.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"))
except ImportError:
    pass  # sin python-dotenv, DATABASE_URL puede venir del entorno igual

_ENGINE: Engine | None = None


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        url = os.environ["DATABASE_URL"]
        _ENGINE = create_engine(url, pool_pre_ping=True)
    return _ENGINE


@contextmanager
def tenant_connection(tenant_id: str) -> Iterator[Connection]:
    """A connection scoped to one tenant for the duration of one transaction.
    SET LOCAL only lasts for the transaction, so it can never leak onto a
    pooled connection reused by a different tenant afterward."""
    # Postgres's SET/SET LOCAL don't accept bind parameters — set_config() does,
    # and its third argument (is_local=true) gives the same transaction-only
    # scoping SET LOCAL would.
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": tenant_id})
        yield conn

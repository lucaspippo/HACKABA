"""
The one module that knows how to open a Postgres connection.

Two engines, two roles, on purpose:
  - get_admin_engine() connects as DATABASE_URL (an elevated/owner role —
    superuser locally). Used only for schema-level or non-tenant-scoped work:
    Alembic (migrations/env.py builds its own engine, doesn't use this one),
    looking up/creating rows in `tenants` itself, and one-off admin scripts.
  - get_engine() / tenant_connection() connect as APP_DATABASE_URL, a role
    WITHOUT BYPASSRLS or superuser. Every core/db/*_repo.py module goes
    through tenant_connection() — never get_admin_engine() — so tenant
    isolation (Row-Level Security) is never optional. Superuser and
    BYPASSRLS roles silently skip RLS policies regardless of
    FORCE ROW LEVEL SECURITY, so using the admin engine here would make the
    isolation guarantee a no-op without any visible error.
"""
from __future__ import annotations

import datetime
import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from core.db.url import normalize_driver

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"))
except ImportError:
    pass  # sin python-dotenv, las URLs pueden venir del entorno igual

_ENGINE: Engine | None = None
_ADMIN_ENGINE: Engine | None = None


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        url = normalize_driver(os.environ["APP_DATABASE_URL"])
        _ENGINE = create_engine(url, pool_pre_ping=True)
    return _ENGINE


def get_admin_engine() -> Engine:
    global _ADMIN_ENGINE
    if _ADMIN_ENGINE is None:
        url = normalize_driver(os.environ["DATABASE_URL"])
        _ADMIN_ENGINE = create_engine(url, pool_pre_ping=True)
    return _ADMIN_ENGINE


def to_local_iso(dt: datetime.datetime, timespec: str = "seconds") -> str:
    """Formats a timezone-aware Postgres timestamp (always UTC internally,
    regardless of session timezone) as the naive local-time ISO string
    `datetime.datetime.now().isoformat()` would have produced — the format
    every core/*.py module used before its timestamps moved to Postgres.

    Why this matters: `now()`-generated columns are correct UTC instants,
    but core/fechas.py's hoy() (and anything comparing a `[:10]` date
    prefix against it) uses naive *local* time. Near a UTC midnight
    boundary — routine for any timezone behind UTC, Argentina's UTC-3
    included — the UTC date and the local date differ, so leaving a
    timestamp in UTC breaks those comparisons. Convert on the way out,
    not by changing what "today" means everywhere else."""
    return dt.astimezone().replace(tzinfo=None).isoformat(timespec=timespec)


@contextmanager
def tenant_connection(tenant_id: str) -> Iterator[Connection]:
    """A connection scoped to one tenant for the duration of one transaction,
    on the RLS-restricted app role. Postgres's SET/SET LOCAL don't accept
    bind parameters — set_config() does, and its third argument (is_local=
    true) gives the same transaction-only scoping SET LOCAL would."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": tenant_id})
        yield conn

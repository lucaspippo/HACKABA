"""Normalizes a Postgres URL to the driver this project actually installs.

requirements.txt ships `psycopg[binary]` (v3) and nothing else, but
SQLAlchemy maps a bare `postgresql://` (and the `postgres://` alias managed
providers still emit) to the *psycopg2* dialect. A URL copied from a hosting
dashboard therefore fails at the first query with ModuleNotFoundError rather
than at startup, which is a slow and confusing way to find out.

An explicitly requested driver (`postgresql+asyncpg://`) is respected: this
exists to fill in an omission, not to override a decision.
"""
from __future__ import annotations

_TARGET = "postgresql+psycopg://"
_BARE_PREFIXES = ("postgresql://", "postgres://")


def normalize_driver(url: str) -> str:
    if not url:
        return url
    for prefix in _BARE_PREFIXES:
        if url.startswith(prefix):
            return _TARGET + url[len(prefix):]
    return url

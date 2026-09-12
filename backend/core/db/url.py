"""Normalizes a Postgres URL to the driver this project actually installs.

SQLAlchemy maps a bare `postgresql://` (and the `postgres://` alias managed
providers still emit) to *psycopg2*, but requirements.txt ships only
`psycopg` v3 — so a URL copied from a hosting dashboard fails at the first
query rather than at startup. An explicit driver is left alone: this fills in
an omission, it does not override a choice.
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

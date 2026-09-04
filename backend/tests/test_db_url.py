"""Postgres URL normalization (core/db/url.py).

Managed providers hand out `postgresql://…`, which SQLAlchemy maps to the
psycopg2 dialect — and only psycopg v3 is installed (requirements.txt).
Without normalization the first query against such a URL dies with
ModuleNotFoundError, so this is the guard for that whole class of outage.
"""
from __future__ import annotations

import pytest

from core.db.url import normalize_driver


@pytest.mark.parametrize("given", [
    "postgresql://u:p@host:5432/db",
    "postgres://u:p@host:5432/db",
    "postgresql+psycopg://u:p@host:5432/db",
])
def test_every_postgres_spelling_lands_on_psycopg(given):
    assert normalize_driver(given).startswith("postgresql+psycopg://")


def test_the_rest_of_the_url_is_untouched():
    got = normalize_driver("postgres://u:p@host:6543/db?sslmode=require")
    assert got == "postgresql+psycopg://u:p@host:6543/db?sslmode=require"


def test_an_explicit_other_driver_is_left_alone():
    # Someone who deliberately asked for a different driver gets it: this
    # normalizer exists to fix an omission, not to override a choice.
    given = "postgresql+asyncpg://u:p@host:5432/db"
    assert normalize_driver(given) == given


def test_a_non_postgres_url_is_left_alone():
    given = "sqlite:///tmp/x.db"
    assert normalize_driver(given) == given


def test_an_empty_url_is_passed_through_unchanged():
    # engine.py raises its own KeyError for a missing variable; this helper
    # must not turn that into a confusing parse error.
    assert normalize_driver("") == ""

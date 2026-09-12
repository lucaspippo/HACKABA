"""core/insight_owner.py — a suggestion, or an honest None."""
from unittest.mock import patch

from core import insight_owner


def _row(username, nombre, rol, modulos, es_admin=False):
    return {"username": username, "nombre": nombre, "rol": rol,
            "es_admin": es_admin, "modulos": modulos}


def test_suggests_the_single_person_who_covers_the_modules():
    matriz = [
        _row("marina", "Marina", "Cobranzas", {"cuentas": True, "inventario": False}),
        _row("beto", "Beto", "Depósito", {"cuentas": False, "inventario": True}),
    ]
    with patch("core.perfiles.matriz", return_value=matriz):
        assert insight_owner.suggest(("cuentas",)) == {
            "suggested": "Marina", "role": "Cobranzas", "reason": "cuentas"}


def test_none_when_two_people_both_cover_the_modules():
    """Ambiguous is not a coin flip — the UI says 'sin dueño sugerido'."""
    matriz = [
        _row("marina", "Marina", "Cobranzas", {"cuentas": True}),
        _row("ana", "Ana", "Administración", {"cuentas": True}),
    ]
    with patch("core.perfiles.matriz", return_value=matriz):
        assert insight_owner.suggest(("cuentas",)) is None


def test_none_when_nobody_covers_the_modules():
    matriz = [_row("beto", "Beto", "Depósito", {"cuentas": False, "inventario": True})]
    with patch("core.perfiles.matriz", return_value=matriz):
        assert insight_owner.suggest(("cuentas",)) is None


def test_none_for_an_empty_team():
    """A fresh DB-backed tenant may have nobody assigned yet."""
    with patch("core.perfiles.matriz", return_value=[]):
        assert insight_owner.suggest(("cuentas",)) is None


def test_admins_are_excluded_from_the_candidate_set():
    """The owner sees every module; counting them would make every card
    ambiguous and no card would ever get a suggestion."""
    matriz = [
        _row("aldo", "Aldo", "Dueño", {"cuentas": True}, es_admin=True),
        _row("marina", "Marina", "Cobranzas", {"cuentas": True}),
    ]
    with patch("core.perfiles.matriz", return_value=matriz):
        assert insight_owner.suggest(("cuentas",))["suggested"] == "Marina"


def test_requires_every_module_not_just_one():
    matriz = [
        _row("marina", "Marina", "Cobranzas", {"cuentas": True, "inventario": False}),
    ]
    with patch("core.perfiles.matriz", return_value=matriz):
        assert insight_owner.suggest(("cuentas", "inventario")) is None


def test_none_for_the_no_domain_sentinel():
    """`__sin_dominio__` means the card declared no module — not that
    everyone owns it."""
    matriz = [_row("marina", "Marina", "Cobranzas", {"cuentas": True})]
    with patch("core.perfiles.matriz", return_value=matriz):
        assert insight_owner.suggest(("__sin_dominio__",)) is None


def test_a_perfiles_failure_yields_none_not_an_exception():
    """One broken lookup must not take down the whole inbox."""
    with patch("core.perfiles.matriz", side_effect=RuntimeError("db down")):
        assert insight_owner.suggest(("cuentas",)) is None

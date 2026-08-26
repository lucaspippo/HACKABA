"""core/db/users_repo.py — CRUD against a throwaway tenant, isolated from
the shared piloto roster auth.py's own tests exercise."""
from __future__ import annotations

from core.db import users_repo


def _usuario(username: str, **overrides) -> dict:
    base = {"username": username, "nombre": "Nombre", "rol": "Rol",
            "es_admin": False, "color": "#123456", "features": ["perfil"]}
    base.update(overrides)
    return base


def test_create_and_get(db_tenant):
    users_repo.create(db_tenant, _usuario("ana"))
    u = users_repo.get(db_tenant, "ana")
    assert u["username"] == "ana"
    assert u["nombre"] == "Nombre"
    assert u["activo"] is True
    assert u["features"] == ["perfil"]


def test_list_all_excludes_inactive_by_default(db_tenant):
    users_repo.create(db_tenant, _usuario("ana"))
    users_repo.create(db_tenant, _usuario("beto"))
    users_repo.set_active(db_tenant, "beto", False)

    activos = users_repo.list_all(db_tenant)
    assert {u["username"] for u in activos} == {"ana"}

    todos = users_repo.list_all(db_tenant, include_inactive=True)
    assert {u["username"] for u in todos} == {"ana", "beto"}


def test_update_only_touches_given_fields(db_tenant):
    users_repo.create(db_tenant, _usuario("ana", rol="QA"))
    users_repo.update(db_tenant, "ana", {"rol": "QA Senior"})
    u = users_repo.get(db_tenant, "ana")
    assert u["rol"] == "QA Senior"
    assert u["nombre"] == "Nombre"  # untouched


def test_puesto_and_ingreso_round_trip(db_tenant):
    users_repo.create(db_tenant, _usuario(
        "ana", ingreso="2026-01-15",
        puesto={"sector": "Depósito", "mentor": "beto"},
    ))
    u = users_repo.get(db_tenant, "ana")
    assert u["ingreso"] == "2026-01-15"
    assert u["puesto"] == {"sector": "Depósito", "mentor": "beto"}

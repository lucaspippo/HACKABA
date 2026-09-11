"""POST /api/admin/usuarios, PATCH /api/admin/usuarios/{usuario},
POST /api/admin/usuarios/{usuario}/desactivar|reactivar — admin
provisioning of the tenant's user roster, on top of the new Postgres-backed
auth.USUARIOS (see auth.py / core/db/users_repo.py)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import auth
import main
from core.db import tenant as _tenant
from core.db.engine import tenant_connection


def _borrar_test_users(*usernames: str) -> None:
    tid = _tenant.current_tenant_id()
    with tenant_connection(tid) as conn:
        for u in usernames:
            conn.execute(text("DELETE FROM users WHERE username = :u"), {"u": u})
            conn.execute(text("DELETE FROM auth_credentials WHERE username = :u"), {"u": u})
            conn.execute(text("DELETE FROM sessions WHERE username = :u"), {"u": u})
    for u in usernames:
        auth._GENERADAS_ESTE_PROCESO.pop(u, None)
    auth.reload_usuarios()


@pytest.fixture(autouse=True)
def _limpio():
    yield
    _borrar_test_users("nueva1")


@pytest.fixture()
def tokens():
    creds = auth.cargar_o_generar_credenciales()
    c = TestClient(main.app)
    t = {}
    for u in ("deposito", "emilio"):
        r = c.post("/api/login", json={"username": u, "password": creds[u]})
        assert r.status_code == 200
        t[u] = r.json()["token"]
    return c, t


def test_no_admin_no_puede_crear_usuario(tokens):
    c, t = tokens
    r = c.post("/api/admin/usuarios",
               json={"token": t["deposito"], "username": "nueva1",
                     "nombre": "Nueva", "rol": "QA"})
    assert r.status_code == 403
    assert "nueva1" not in auth.USUARIOS


def test_admin_crea_edita_desactiva_reactiva_usuario(tokens):
    c, t = tokens

    r = c.post("/api/admin/usuarios",
               json={"token": t["emilio"], "username": "nueva1",
                     "nombre": "Nueva", "rol": "QA", "features": ["perfil", "angela"]})
    assert r.status_code == 200
    body = r.json()
    assert body["usuario"]["username"] == "nueva1"
    assert body["usuario"]["activo"] is True
    assert body["password_inicial"]  # una contraseña inicial viajó una vez
    assert "nueva1" in auth.USUARIOS

    r = c.patch(f"/api/admin/usuarios/nueva1",
               json={"token": t["emilio"], "rol": "QA Senior"})
    assert r.status_code == 200
    assert r.json()["rol"] == "QA Senior"

    r = c.post("/api/admin/usuarios/nueva1/desactivar", json={"token": t["emilio"]})
    assert r.status_code == 200
    assert r.json()["activo"] is False
    assert "nueva1" not in auth.USUARIOS

    r = c.post("/api/admin/usuarios/nueva1/reactivar", json={"token": t["emilio"]})
    assert r.status_code == 200
    assert r.json()["activo"] is True
    assert "nueva1" in auth.USUARIOS


def test_crear_usuario_duplicado_es_400(tokens):
    c, t = tokens
    r1 = c.post("/api/admin/usuarios",
               json={"token": t["emilio"], "username": "nueva1", "nombre": "Nueva", "rol": "QA"})
    assert r1.status_code == 200
    r2 = c.post("/api/admin/usuarios",
               json={"token": t["emilio"], "username": "nueva1", "nombre": "Otra", "rol": "QA"})
    assert r2.status_code == 400


def test_editar_usuario_inexistente_es_404(tokens):
    c, t = tokens
    r = c.patch("/api/admin/usuarios/no-existe", json={"token": t["emilio"], "nombre": "X"})
    assert r.status_code == 404


def test_no_se_puede_desactivar_al_dueno_via_api(tokens):
    c, t = tokens
    r = c.post("/api/admin/usuarios/emilio/desactivar", json={"token": t["emilio"]})
    assert r.status_code == 400
    assert "emilio" in auth.USUARIOS

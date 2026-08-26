"""auth.USUARIOS is now Postgres-backed (core/db/users_repo.py) instead of a
hardcoded dict, and auth.py exposes admin provisioning
(crear_usuario/editar_usuario/desactivar_usuario/reactivar_usuario). This
covers: the lazy seed-once-from-the-hardcoded-roster behavior, full
create/edit/deactivate/reactivate round trips, that a deactivated user
disappears from auth.USUARIOS and can't log in, that their live sessions
get purged, and that the owner can't deactivate themselves.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

import auth
from core.db.engine import tenant_connection
from core.db import tenant as _tenant


def _borrar_test_users(*usernames: str) -> None:
    tid = _tenant.current_tenant_id()
    with tenant_connection(tid) as conn:
        for u in usernames:
            conn.execute(text("DELETE FROM users WHERE username = :u"), {"u": u})
            conn.execute(text("DELETE FROM auth_credentials WHERE username = :u"), {"u": u})
            conn.execute(text("DELETE FROM sessions WHERE username = :u"), {"u": u})
    # auth._GENERADAS_ESTE_PROCESO caches plaintext per-process across calls
    # (same reasoning as the historical cargar_o_generar_credenciales() bug
    # documented in the migration playbook): without clearing it here, the
    # NEXT test's cargar_o_generar_credenciales() would skip regenerating a
    # credential row for a since-deleted user and hand back a stale plaintext
    # that no longer matches any hash in Postgres.
    for u in usernames:
        auth._GENERADAS_ESTE_PROCESO.pop(u, None)
    auth.reload_usuarios()


@pytest.fixture(autouse=True)
def _limpio():
    yield
    _borrar_test_users("testuser1")
    auth.reload_usuarios()


def test_usuarios_lazy_seeds_from_horizonte_roster():
    u = auth.USUARIOS
    assert set(u) == {"emilio", "paula", "vendedor", "deposito", "polpilot"}
    assert u["emilio"]["es_admin"] is True
    assert u["emilio"]["rol"] == "Dueño"


def test_crear_usuario_aparece_en_usuarios():
    antes = len(auth.USUARIOS)
    u = auth.crear_usuario(username="testuser1", nombre="Test User", rol="QA",
                            features=["perfil", "angela"])
    assert u["username"] == "testuser1"
    assert u["activo"] is True
    assert len(auth.USUARIOS) == antes + 1
    assert "testuser1" in auth.USUARIOS


def test_crear_usuario_duplicado_falla():
    auth.crear_usuario(username="testuser1", nombre="Test User", rol="QA")
    with pytest.raises(auth.UsuarioInvalido):
        auth.crear_usuario(username="testuser1", nombre="Otro Nombre", rol="QA")


def test_editar_usuario_cambia_campos():
    auth.crear_usuario(username="testuser1", nombre="Test User", rol="QA")
    editado = auth.editar_usuario("testuser1", {"nombre": "Editado", "rol": "QA Senior"})
    assert editado["nombre"] == "Editado"
    assert editado["rol"] == "QA Senior"
    assert auth.USUARIOS["testuser1"]["nombre"] == "Editado"


def test_desactivar_usuario_lo_saca_de_usuarios_y_bloquea_login():
    auth.crear_usuario(username="testuser1", nombre="Test User", rol="QA")
    creds = auth.cargar_o_generar_credenciales()
    pw = creds["testuser1"]

    assert auth.login("testuser1", pw) is not None

    auth.desactivar_usuario("testuser1")
    assert "testuser1" not in auth.USUARIOS
    assert auth.login("testuser1", pw) is None


def test_desactivar_purga_las_sesiones_vivas():
    auth.crear_usuario(username="testuser1", nombre="Test User", rol="QA")
    creds = auth.cargar_o_generar_credenciales()
    sesion = auth.login("testuser1", creds["testuser1"])
    assert auth.usuario_por_token(sesion["token"]) is not None

    auth.desactivar_usuario("testuser1")
    assert auth.usuario_por_token(sesion["token"]) is None


def test_reactivar_usuario_lo_devuelve_a_usuarios():
    auth.crear_usuario(username="testuser1", nombre="Test User", rol="QA")
    auth.desactivar_usuario("testuser1")
    assert "testuser1" not in auth.USUARIOS
    auth.reactivar_usuario("testuser1")
    assert "testuser1" in auth.USUARIOS


def test_no_se_puede_desactivar_al_dueno():
    with pytest.raises(auth.UsuarioInvalido):
        auth.desactivar_usuario("emilio")
    assert "emilio" in auth.USUARIOS

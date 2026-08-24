"""
Perfiles autoadministrados: el empleado describe → Ángela propone → el dueño
aprueba. Cubre sugerencias, flujo solicitud→aprobación, permisos (nadie se
autoaprueba por ningún camino) y el evento de notificación con WhatsApp inactivo.
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

import angela
import auth
import main
from core import perfiles, notificaciones


@pytest.fixture(autouse=True)
def limpio():
    files = [perfiles.PERFILES_JSON, notificaciones.NOTIFICACIONES_JSON]
    backup = {}
    for f in files:
        if os.path.exists(f):
            backup[f] = open(f, encoding="utf-8").read()
            os.remove(f)
    # los tests de Ángela mutan los globals de sesión: restaurarlos siempre
    usuario, rol = angela._usuario_actual(), angela._rol_actual()
    yield
    angela._set_sesion(usuario=usuario, rol=rol)
    for f in files:
        if os.path.exists(f):
            os.remove(f)
        if f in backup:
            open(f, "w", encoding="utf-8").write(backup[f])


@pytest.fixture()
def tokens():
    """Login real de deposito y emilio (los guards usan el token, no el body)."""
    creds = auth.cargar_o_generar_credenciales()
    c = TestClient(main.app)
    t = {}
    for u in ("deposito", "emilio"):
        r = c.post("/api/login", json={"username": u, "password": creds[u]})
        assert r.status_code == 200
        t[u] = r.json()["token"]
    return c, t


# --- Fase C · propuesta de módulos ---

def test_sugerencias_desde_la_descripcion():
    r = perfiles.set_descripcion(
        "deposito", "me encargo de cobrarle a los clientes y seguir las deudas")
    modulos = {s["modulo"] for s in r["sugerencias"]}
    assert "cuentas" in modulos          # cobranzas y deudas → Cuentas corrientes
    assert all(m in auth.MODULOS for m in modulos)  # nunca inventa módulos
    # no sugiere lo que ya tiene (deposito tiene 'deposito' y 'logistica')
    assert "deposito" not in modulos and "logistica" not in modulos
    # cada sugerencia trae el porqué en una línea
    assert all(s["motivo"] for s in r["sugerencias"])


# --- Fase D · solicitud → notificación → aprobación/rechazo ---

def test_flujo_solicitud_aprobacion_y_rechazo():
    s1 = perfiles.crear_solicitud("deposito", "cuentas", "motivo test")
    s2 = perfiles.crear_solicitud("deposito", "alertas", "motivo test")

    # El dueño recibe la notificación emitida por el SISTEMA (no por el empleado)
    notifs = notificaciones.listar("emilio", solo_no_leidas=True)
    assert len(notifs) == 2 and notifs[0]["tipo"] == "solicitud_modulo"
    assert "Ángela sugiere" in notifs[0]["cuerpo"] or "pide" in notifs[0]["titulo"]

    perfiles.resolver_solicitud(s1["id"], aprobar=True, actor="emilio")
    perfiles.resolver_solicitud(s2["id"], aprobar=False, actor="emilio", motivo="todavía no")

    feats = perfiles.features_efectivas("deposito")
    assert "cuentas" in feats and "alertas" not in feats
    # el merge llega al perfil público (lo que ve el frontend)
    assert "cuentas" in auth.perfil_publico("deposito")["features"]

    # el empleado recibe las dos respuestas, la rechazada con el motivo
    respuestas = notificaciones.listar("deposito")
    assert len(respuestas) == 2
    rechazo = next(n for n in respuestas if "rechaz" in n["titulo"] + n["cuerpo"])
    assert "todavía no" in rechazo["cuerpo"]

    # una solicitud resuelta no se puede volver a resolver
    with pytest.raises(ValueError):
        perfiles.resolver_solicitud(s1["id"], aprobar=True, actor="emilio")


def test_solicitud_de_modulo_inexistente_o_duplicada():
    with pytest.raises(ValueError):
        perfiles.crear_solicitud("deposito", "modulo_inventado")
    perfiles.crear_solicitud("deposito", "cuentas")
    with pytest.raises(ValueError):
        perfiles.crear_solicitud("deposito", "cuentas")  # ya hay una pendiente


# --- Permisos: el empleado NO puede autoaprobar por ningún camino ---

def test_empleado_no_puede_autoaprobar_por_api(tokens):
    c, t = tokens
    s = perfiles.crear_solicitud("deposito", "cuentas")
    # resolver su propia solicitud → 403
    r = c.post(f"/api/solicitudes/{s['id']}/resolver",
               json={"token": t["deposito"], "aprobar": True})
    assert r.status_code == 403
    # habilitarse un módulo directo → 403
    r = c.post("/api/admin/feature",
               json={"token": t["deposito"], "usuario": "deposito",
                     "modulo": "caja", "habilitar": True})
    assert r.status_code == 403
    # la matriz del dueño tampoco es suya
    assert c.get(f"/api/admin/matriz?token={t['deposito']}").status_code == 403
    # y nada quedó habilitado
    assert "cuentas" not in perfiles.features_efectivas("deposito")
    assert "caja" not in perfiles.features_efectivas("deposito")


def test_empleado_via_angela_genera_solicitud_no_habilita():
    angela._set_sesion(usuario="Encargado de depósito", rol="Depósito")
    res, _ = angela._run_tool("gestionar_modulo",
                              {"usuario": "deposito", "modulo": "caja", "habilitar": True})
    assert res.get("solicitud_creada") is True
    assert "caja" not in perfiles.features_efectivas("deposito")  # NO se habilitó
    # y no puede tocarle módulos a OTRO empleado
    res, _ = angela._run_tool("gestionar_modulo",
                              {"usuario": "paula", "modulo": "caja", "habilitar": True})
    assert "error" in res


def test_dueno_via_angela_aplica_y_audita():
    angela._set_sesion(usuario="emilio", rol="Dueño")
    res, accion = angela._run_tool("gestionar_modulo",
                                   {"usuario": "paula", "modulo": "deposito", "habilitar": True})
    assert res.get("ok") is True
    assert "deposito" in perfiles.features_efectivas("paula")
    from core import store
    assert any(e["accion"] == "cambiar_modulo_empleado" for e in store.audit.list())
    # y paula recibió la notificación
    assert any(n["tipo"] == "modulo_cambiado" for n in notificaciones.listar("paula"))


def test_no_dueno_no_puede_editar_perfil_ajeno(tokens):
    c, t = tokens
    r = c.post("/api/perfil/paula/descripcion",
               json={"token": t["deposito"], "texto": "hackeo"})
    assert r.status_code == 403


# --- Notificaciones: evento con múltiples destinos, WhatsApp inactivo ---

def test_notificacion_evento_y_destino_whatsapp_inactivo():
    destinos = {d["nombre"]: d["activo"] for d in notificaciones.destinos_registrados()}
    assert destinos == {"panel": True, "whatsapp": False}  # registrado pero APAGADO
    # emitir usa solo los activos: no explota aunque whatsapp esté registrado
    n = notificaciones.emitir("paula", "Prueba", "cuerpo", tipo="general")
    assert notificaciones.listar("paula")[0]["id"] == n["id"]
    # el slot inactivo mantiene el patrón del ConectorMCP
    with pytest.raises(NotImplementedError):
        notificaciones._destino_whatsapp(n)
    # marcar leída
    notificaciones.marcar_leida(n["id"])
    assert notificaciones.listar("paula", solo_no_leidas=True) == []


# --- P9·C1 (M1): las notificaciones nombran al dueño REAL del tenant, en el
# --- idioma del destinatario — nada de "Emilio" hardcodeado cross-tenant.

def test_notificaciones_con_dueno_real_e_idioma_del_destinatario():
    assert auth.nombre_dueno() == "Emilio"  # piloto: el dueño real ES Emilio
    s = perfiles.crear_solicitud("deposito", "cuentas", "motivo test")
    perfiles.set_idioma("deposito", "en")  # el destinatario elige inglés
    perfiles.resolver_solicitud(s["id"], aprobar=True, actor="emilio")
    n = next(x for x in notificaciones.listar("deposito")
             if x["tipo"] == "solicitud_resuelta")
    # sale en el idioma del destinatario y con el nombre que da auth.nombre_dueno()
    assert "approved" in n["titulo"] or "approved" in n["cuerpo"]
    assert auth.nombre_dueno() in n["cuerpo"]

    perfiles.set_idioma("deposito", "es")
    perfiles.set_feature("deposito", "caja", True, actor="emilio")
    m = next(x for x in notificaciones.listar("deposito")
             if x["tipo"] == "modulo_cambiado")
    assert auth.nombre_dueno() in m["cuerpo"] and "habilitó" in m["cuerpo"]

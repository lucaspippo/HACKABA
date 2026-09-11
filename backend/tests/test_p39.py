"""
P39 · Parte 1 — el panel de Equipo, consistente:

  1. La NÓMINA ES UNA SOLA: "Ver como", "Lo que pasó con tu equipo" y "Quién ve
     qué" hablan de las mismas personas (antes: 7 / 12 / 13).
  2. Solicitudes ES el canal del empleado: pide con SUS palabras, el dueño
     aprueba, y aprobar TILDA la celda en la matriz (el sistema de permisos que
     ya existía — no se recrea nada).
  3. "Qué resolvió esta semana": lo concreto de los últimos 7 días, sacado de la
     auditoría real y agrupado por acción. Un empleado sin trabajo registrado
     queda vacío — nunca relleno.
"""
from __future__ import annotations

import os
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

import auth
import main
from core import perfiles, notificaciones


@pytest.fixture(autouse=True)
def limpio():
    """Las solicitudes/notificaciones se persisten: backup y restore siempre."""
    files = [perfiles.PERFILES_JSON, notificaciones.NOTIFICACIONES_JSON]
    backup = {}
    for f in files:
        if os.path.exists(f):
            backup[f] = open(f, encoding="utf-8").read()
            os.remove(f)
    yield
    for f in files:
        if os.path.exists(f):
            os.remove(f)
        if f in backup:
            open(f, "w", encoding="utf-8").write(backup[f])


@pytest.fixture()
def cliente_tokens():
    creds = auth.cargar_o_generar_credenciales()
    c = TestClient(main.app)
    empleado = next(u for u, v in auth.USUARIOS.items()
                    if not v.get("es_admin") and not v.get("interno"))
    dueno = auth.dueno()["username"]
    t = {}
    for u in (empleado, dueno):
        r = c.post("/api/login", json={"username": u, "password": creds[u]})
        assert r.status_code == 200, r.text
        t[u] = r.json()["token"]
    return c, t, empleado, dueno


# --- 1 · una sola nómina --------------------------------------------------------

def test_actividad_incluye_al_dueno_y_no_a_los_internos():
    """El bucket de actividad se arma con TODAS las personas del tenant menos
    los usuarios internos de PolPilot: la misma regla que perfiles.matriz()."""
    esperados = {u for u, v in auth.USUARIOS.items() if not v.get("interno")}
    de_la_matriz = {f["username"] for f in perfiles.matriz()}
    assert de_la_matriz == esperados
    # el dueño está en la matriz → tiene que estar también en la actividad
    assert auth.dueno()["username"] in esperados


def test_es_trabajo_cubre_carga_correccion_y_piso():
    for acc in ("cargar_remito", "integrar_staging", "sanear_balanza",
                "corregir_precio_perdida"):
        assert main._es_trabajo(acc), acc
    # lo del piso (Parte 3) y lo que no cae en familias pero SÍ es trabajo
    for acc in ("validacion_montos_ventas", "preparar_orden_compra",
                "reportar_faltante", "marcar_conteo", "confirmar_entrega",
                "cerrar_tarea_piso", "pedir_reposicion"):
        assert main._es_trabajo(acc), acc
    # lo administrativo puro NO es trabajo del negocio
    for acc in ("cambiar_idioma", "cambiar_foto_perfil", "consulta_angela",
                "editar_descripcion_perfil", "restaurar_version", ""):
        assert not main._es_trabajo(acc), acc


# --- 2 · el canal: pedir con el porqué, aprobar tilda la matriz ------------------

def test_solicitud_guarda_el_motivo_del_empleado(cliente_tokens):
    c, t, empleado, dueno = cliente_tokens
    falta = next(m for m in auth.MODULOS
                 if m not in perfiles.features_efectivas(empleado)
                 and m not in main._MODULOS_NO_PEDIBLES)
    r = c.post("/api/solicitudes", json={
        "token": t[empleado], "modulos": [falta],
        "motivo": "Visito clientes y necesito ver la cuenta antes del pedido."})
    assert r.status_code == 200, r.text
    creada = r.json()["creadas"][0]
    assert creada["motivo_empleado"].startswith("Visito clientes")

    # al dueño le llega con el porqué EN EL CUERPO (la campanita, no un badge mudo)
    avisos = notificaciones.listar(dueno)
    assert any("Visito clientes" in (n.get("cuerpo") or "") for n in avisos), avisos


def test_aprobar_una_solicitud_tilda_la_celda_en_la_matriz(cliente_tokens):
    c, t, empleado, dueno = cliente_tokens
    falta = next(m for m in auth.MODULOS
                 if m not in perfiles.features_efectivas(empleado)
                 and m not in main._MODULOS_NO_PEDIBLES)
    fila_antes = next(f for f in perfiles.matriz() if f["username"] == empleado)
    assert fila_antes["modulos"][falta] is False

    sid = c.post("/api/solicitudes", json={
        "token": t[empleado], "modulos": [falta], "motivo": "Lo necesito para trabajar.",
    }).json()["creadas"][0]["id"]
    r = c.post(f"/api/solicitudes/{sid}/resolver",
               json={"token": t[dueno], "aprobar": True, "motivo": ""})
    assert r.status_code == 200, r.text

    # LA celda quedó tildada: es el mismo estado que lee «Quién ve qué»
    fila = next(f for f in perfiles.matriz() if f["username"] == empleado)
    assert fila["modulos"][falta] is True
    assert falta in perfiles.features_efectivas(empleado)


def test_rechazar_no_toca_la_matriz(cliente_tokens):
    c, t, empleado, dueno = cliente_tokens
    falta = next(m for m in auth.MODULOS
                 if m not in perfiles.features_efectivas(empleado)
                 and m not in main._MODULOS_NO_PEDIBLES)
    sid = c.post("/api/solicitudes", json={
        "token": t[empleado], "modulos": [falta], "motivo": "porque sí",
    }).json()["creadas"][0]["id"]
    c.post(f"/api/solicitudes/{sid}/resolver",
           json={"token": t[dueno], "aprobar": False, "motivo": "todavía no"})
    fila = next(f for f in perfiles.matriz() if f["username"] == empleado)
    assert fila["modulos"][falta] is False


def test_pedibles_son_lo_que_le_falta_y_nunca_los_de_fabrica(cliente_tokens):
    c, t, empleado, _dueno = cliente_tokens
    p = c.get(f"/api/perfil/{empleado}?token={t[empleado]}").json()
    pedibles = {m["modulo"] for m in p["pedibles"]}
    assert pedibles, "un empleado siempre tiene algo que puede pedir"
    assert not (pedibles & set(p["features"])), "no se pide lo que ya se tiene"
    assert not (pedibles & main._MODULOS_NO_PEDIBLES), "los de fábrica no se piden"
    assert all(m["label"] for m in p["pedibles"]), "cada pedible viaja con su label"


def test_no_se_puede_pedir_un_modulo_de_fabrica(cliente_tokens):
    c, t, empleado, _dueno = cliente_tokens
    r = c.post("/api/solicitudes", json={
        "token": t[empleado], "modulos": ["gestion_equipo"], "motivo": "quiero"})
    assert r.status_code == 200
    d = r.json()
    assert d["creadas"] == [] and d["errores"], d
    assert "gestion_equipo" not in perfiles.features_efectivas(empleado)


def test_el_duenio_es_el_unico_que_resuelve(cliente_tokens):
    c, t, empleado, _dueno = cliente_tokens
    falta = next(m for m in auth.MODULOS
                 if m not in perfiles.features_efectivas(empleado)
                 and m not in main._MODULOS_NO_PEDIBLES)
    sid = c.post("/api/solicitudes", json={
        "token": t[empleado], "modulos": [falta], "motivo": "dale",
    }).json()["creadas"][0]["id"]
    # el propio solicitante NO se autoaprueba
    r = c.post(f"/api/solicitudes/{sid}/resolver",
               json={"token": t[empleado], "aprobar": True, "motivo": ""})
    assert r.status_code in (401, 403), r.text
    assert falta not in perfiles.features_efectivas(empleado)


def test_los_modulos_de_la_ficha_van_en_el_idioma_del_que_mira(cliente_tokens):
    """El panel del dueño se lee ENTERO en su idioma: los labels de módulo de un
    empleado que tiene el suyo en otro idioma no pueden salir en ese otro."""
    c, t, empleado, dueno = cliente_tokens
    perfiles.set_idioma(empleado, "en")
    perfiles.set_idioma(dueno, "es")
    listado = c.get(f"/api/perfiles?token={t[dueno]}").json()["perfiles"]
    fila = next(p for p in listado if p["username"] == empleado)
    # su preferencia sigue siendo la suya (Ángela le habla en inglés)…
    assert fila["idioma"] == "en"
    # …pero el dueño lee los módulos en español
    assert fila["modulos_labels"].get("perfil") == "Mi perfil", fila["modulos_labels"]

    # y al revés: con el dueño en inglés, la misma ficha se lee en inglés
    perfiles.set_idioma(dueno, "en")
    listado = c.get(f"/api/perfiles?token={t[dueno]}").json()["perfiles"]
    fila = next(p for p in listado if p["username"] == empleado)
    assert fila["modulos_labels"].get("perfil") == "My profile", fila["modulos_labels"]


def test_el_propio_perfil_se_lee_en_el_idioma_propio(cliente_tokens):
    c, t, empleado, _dueno = cliente_tokens
    perfiles.set_idioma(empleado, "en")
    p = c.get(f"/api/perfil/{empleado}?token={t[empleado]}").json()
    assert p["modulos_labels"].get("perfil") == "My profile"
    assert all(m["label"] for m in p["pedibles"])


# --- 3 · el demo real: nómina única y "qué resolvió esta semana" -----------------

def test_demo_nomina_unica_y_resueltos():
    backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_demo = os.path.join(os.path.dirname(backend), "data-demo")
    env = {**os.environ, "POLPILOT_TENANT": "demo", "POLPILOT_DATA_DIR": data_demo,
           "POLPILOT_DEMO_TODAY": "2026-07-07", "POLPILOT_DEMO_AUTOLOGIN": "1",
           "POLPILOT_DEMO_ROLE_SWITCH": "1", "PYTHONIOENCODING": "utf-8"}
    env.pop("ANTHROPIC_API_KEY", None)
    code = r"""
from fastapi.testclient import TestClient
import main
c = TestClient(main.app)
tok = c.post("/api/demo/autologin").json()["token"]
H = {"Authorization": "Bearer " + tok}

actividad = c.get("/api/equipo/actividad", headers=H).json()["actividad"]
nombres = c.get("/api/equipo/nombres", headers=H).json()["equipo"]
matriz = c.get("/api/admin/matriz?token=" + tok).json()["matriz"]

# 1 · LA MISMA GENTE en las tres vistas (el bug: 7 / 12 / 13)
a = {f["username"] for f in actividad}
n = {f["username"] for f in nombres}
m = {f["username"] for f in matriz}
assert a == n == m, ("nominas distintas", sorted(a), sorted(n), sorted(m))
assert len(a) >= 13, ("el demo tiene 13 personas", len(a))

# el dueño está en las tres (antes faltaba en "Lo que pasó con tu equipo")
assert "aldo" in a and "aldo" in n and "aldo" in m

# "Ver como" ya no filtra por superficie: los de piso viajan con la suya, para
# que la UI lo DIGA en vez de esconderlos
solo_mobile = [p for p in nombres if "desktop" not in (p.get("superficies") or [])]
assert solo_mobile, "el demo tiene roles de piso (mobile)"

# 2 · "qué resolvió esta semana": estructura sana y anclada al audit real
por_nombre = {f["nombre"]: f for f in actividad}
for f in actividad:
    assert isinstance(f["resueltos"], list)
    for par in f["resueltos"]:
        assert len(par) == 2 and isinstance(par[1], int) and par[1] > 0, par

# Nahuel cargó 2 remitos en la semana sembrada; Marta integró staging y cargó
marta = dict(por_nombre["Marta"]["resueltos"])
nahuel = dict(por_nombre["Nahuel"]["resueltos"])
assert nahuel.get("cargar_remito", 0) >= 2, por_nombre["Nahuel"]["resueltos"]
assert marta.get("integrar_staging", 0) >= 2, por_nombre["Marta"]["resueltos"]

# el que no trabajó esta semana queda VACÍO (no relleno)
vacios = [f for f in actividad if not f["resueltos"]]
assert vacios, "tiene que haber gente sin trabajo registrado esta semana"
print("OK")
"""
    r = subprocess.run([sys.executable, "-c", code], cwd=backend, env=env,
                       capture_output=True, text=True, timeout=180)
    assert r.returncode == 0 and "OK" in r.stdout, (r.stdout[-1500:], r.stderr[-1500:])


# --- Parte 2 y 3 · la vista-herramienta y el cruce de lo que reporta el piso ----

@pytest.fixture(autouse=True)
def piso_limpio():
    """piso.json es estado vivo: backup y restore, como con perfiles."""
    from core import piso as _piso
    path = _piso.PISO_JSON
    backup = open(path, encoding="utf-8").read() if os.path.exists(path) else None
    if backup is not None:
        os.remove(path)
    yield
    if os.path.exists(path):
        os.remove(path)
    if backup is not None:
        open(path, "w", encoding="utf-8").write(backup)


def test_reportar_no_toca_el_stock():
    """La regla inviolable: reportar es contar un hecho, no ajustar el sistema."""
    from core import piso, store
    antes = [(a["codigo"], a.get("stock")) for a in store.raw_actual()]
    a = next(x for x in store.raw_actual() if x.get("costo_iva"))
    piso.reportar("faltante", "deposito",
                  {"codigo": a["codigo"], "producto": a["descripcion"],
                   "cantidad": 5, "motivo": "roto"})
    assert [(x["codigo"], x.get("stock")) for x in store.raw_actual()] == antes


def test_un_faltante_se_vuelve_propuesta_de_reclamo_valorizada():
    from core import piso, store
    a = next(x for x in store.raw_actual()
             if x.get("costo_iva") and x.get("proveedor"))
    piso.reportar("faltante", "deposito",
                  {"codigo": a["codigo"], "producto": a["descripcion"],
                   "cantidad": 4, "motivo": "roto", "nota": "las separé"})
    props = piso.propuestas("es")
    assert len(props) == 1
    p = props[0]
    # valorizado a costo de catálogo, no a ojo
    assert p["monto"] == pytest.approx(4 * a["costo_iva"], rel=1e-6)
    assert p["tipo"] == "reclamar" and p["origen"] == "piso"
    assert a["proveedor"] in p["titulo"]
    # declara de dónde salió y que no se ejecutó nada
    assert p["fuentes"] and p["drill"]["supuestos"]
    assert any("No toqué" in x for x in p["drill"]["porque"])


def test_sin_reportes_no_hay_propuesta_inventada():
    from core import piso
    assert piso.propuestas("es") == []


def test_resolver_saca_la_propuesta_de_la_mesa():
    from core import piso, store
    a = next(x for x in store.raw_actual() if x.get("costo_iva") and x.get("proveedor"))
    r = piso.reportar("faltante", "deposito", {"codigo": a["codigo"], "cantidad": 2,
                                               "producto": a["descripcion"], "motivo": "roto"})
    assert piso.propuestas("es")
    piso.resolver(r["id"], "emilio")
    assert piso.propuestas("es") == [], "resuelto no vuelve a proponerse"


def test_los_reportes_validan_lo_minimo():
    from core import piso
    with pytest.raises(ValueError):
        piso.reportar("faltante", "x", {"cantidad": 1})          # sin producto
    with pytest.raises(ValueError):
        piso.reportar("conteo", "x", {"producto": "algo"})       # sin contado
    with pytest.raises(ValueError):
        piso.reportar("entrega", "x", {})                        # sin cliente
    with pytest.raises(ValueError):
        piso.reportar("inventado", "x", {})                      # tipo que no existe
    with pytest.raises(ValueError):
        piso.reportar("faltante", "x", {"producto": "a", "motivo": "raro"})


def test_cada_reporte_queda_atribuido_en_la_auditoria():
    """Lo que hace el de a pie tiene que llegar al panel del dueño: se audita
    con el slug que 'qué resolvió esta semana' sabe contar."""
    from core import piso, store
    n0 = len(store.audit.list())
    piso.reportar("conteo", "tomas", {"producto": "QUESO", "contado": 12})
    ev = store.audit.list()[len(store.audit.list()) - 1]
    assert len(store.audit.list()) == n0 + 1
    assert ev["actor"] == "tomas" and ev["accion"] == "marcar_conteo"
    assert main._es_trabajo(ev["accion"])


def test_solo_el_duenio_ve_todos_los_reportes(cliente_tokens):
    c, t, empleado, dueno = cliente_tokens
    from core import piso
    piso.reportar("conteo", empleado, {"producto": "A", "contado": 1})
    piso.reportar("conteo", "otro_usuario", {"producto": "B", "contado": 2})
    mios = c.get("/api/piso/reportes",
                 headers={"Authorization": f"Bearer {t[empleado]}"}).json()["reportes"]
    todos = c.get("/api/piso/reportes",
                  headers={"Authorization": f"Bearer {t[dueno]}"}).json()["reportes"]
    assert {r["actor"] for r in mios} == {empleado}
    assert len(todos) == 2


def test_reportar_pide_el_modulo_del_trabajo_que_reporta(cliente_tokens):
    """Coherencia con «Quién ve qué»: sin el módulo, la acción no existe."""
    c, t, empleado, _dueno = cliente_tokens
    from core import perfiles
    tiene_deposito = "deposito" in perfiles.features_efectivas(empleado)
    # la identidad viaja SIEMPRE en el header (nunca en el body): el reporte
    # queda atribuido a quien tiene la sesión, no a quien lo dice
    r = c.post("/api/piso/reporte",
               headers={"Authorization": f"Bearer {t[empleado]}"},
               json={"tipo": "faltante",
                     "datos": {"producto": "X", "cantidad": 1, "motivo": "roto"}})
    assert r.status_code == (200 if tiene_deposito else 403), r.text
    if tiene_deposito:
        assert r.json()["actor"] == empleado


# --- P41 · goals nuevos, tareas asignadas y prueba de entrega -------------------

def test_los_dos_objetivos_nuevos_existen_y_no_mueven_canonicos():
    from core import objetivos_medidos as om
    for oid in ("cobrar_morosos", "reponer_quiebres"):
        assert oid in om.DEFS and oid in om.ORDEN, oid
        d = om.DEFS[oid]
        # baseline/meta sintéticos, pero coherentes: se mejora hacia la meta
        assert d["direccion"] == "menor" and d["baseline"] > d["meta"]
        assert len(d["hist"]) == 3
        # el historial va SIEMPRE hacia la meta (no hay saltos raros)
        vals = [v for _, v in d["hist"]]
        assert vals == sorted(vals, reverse=True), vals
    # el umbral del objetivo es el MISMO que el del hallazgo de quiebre
    from core import oportunidades_neg as opn
    assert om.COBERTURA_QUIEBRE_DIAS == opn.COBERTURA_QUIEBRE_DIAS


def test_el_progreso_de_los_nuevos_se_calcula_no_se_hardcodea():
    from core import objetivos_medidos as om
    objs = om.construir({"cobrar_morosos": 85_700_000, "reponer_quiebres": 35},
                        "2026-07-07")
    por_id = {o["id"]: o for o in objs}
    mora = por_id["cobrar_morosos"]
    # (132M - 85,7M) / (132M - 20M)
    assert mora["progreso"] == round((132_000_000 - 85_700_000) / (132_000_000 - 20_000_000), 3)
    assert mora["historial"][-1] == {"fecha": "2026-07-07", "valor": 85_700_000}
    # sin dato real, el objetivo NO se inventa: simplemente no está
    assert "cobrar_morosos" not in {o["id"] for o in om.construir({"cobrar_morosos": None}, "2026-07-07")}


def test_una_tarea_asignada_la_cierra_su_duenio_no_cualquiera(cliente_tokens):
    """P41·4 — el scope de LECTURA ya existía; el de escritura faltaba."""
    c, t, empleado, dueno = cliente_tokens
    from core import recordatorios
    r = recordatorios.crear("Contá los 2 productos en negativo", empleado, dueno)
    otro = next(u for u, v in auth.USUARIOS.items()
                if u not in (empleado, dueno) and not v.get("interno"))
    creds = auth.cargar_o_generar_credenciales()
    tok_otro = c.post("/api/login", json={"username": otro, "password": creds[otro]}).json()["token"]

    # un tercero NO puede cerrarla
    resp = c.post(f"/api/recordatorios/{r['id']}/completar",
                  headers={"Authorization": f"Bearer {tok_otro}"})
    assert resp.status_code == 403, resp.text
    assert recordatorios.listar(empleado)[0]["estado"] != "hecho"

    # su destinatario sí
    resp = c.post(f"/api/recordatorios/{r['id']}/completar",
                  headers={"Authorization": f"Bearer {t[empleado]}"})
    assert resp.status_code == 200, resp.text
    # listar() esconde las hechas por default: la tarea sale de su lista de hoy
    assert not any(x["id"] == r["id"] for x in recordatorios.listar(empleado))
    hecha = next(x for x in recordatorios.listar(empleado, incluir_hechos=True)
                 if x["id"] == r["id"])
    assert hecha["estado"] == "hecho"


def test_el_duenio_asigna_y_la_persona_la_ve(cliente_tokens):
    c, t, empleado, dueno = cliente_tokens
    r = c.post("/api/recordatorios",
               headers={"Authorization": f"Bearer {t[dueno]}"},
               json={"texto": "Cargá el remito de La Ribera", "para": empleado})
    assert r.status_code == 200, r.text
    mias = c.get("/api/recordatorios",
                 headers={"Authorization": f"Bearer {t[empleado]}"}).json()["recordatorios"]
    assert any("La Ribera" in x["texto"] for x in mias), mias


def test_la_prueba_de_entrega_se_guarda_como_archivo_y_no_en_el_json():
    """La foto no puede quedar embebida en piso.json (lo haría impagable de leer):
    va a disco y en el reporte queda sólo el nombre."""
    from core import piso
    import base64 as _b64
    png = ("data:image/png;base64,"
           + _b64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 64).decode())
    r = piso.reportar("entrega", "walter", {"cliente": "Almacén San Martín", "prueba": png})
    assert "prueba" not in r["datos"], "el base64 no queda en el reporte"
    assert r["adjunto"] == f"{r['id']}.png"
    path = piso.adjunto_path(r["id"])
    assert path and os.path.exists(path) and os.path.getsize(path) > 0
    os.remove(path)


def test_una_entrega_sin_prueba_sigue_siendo_valida():
    from core import piso
    r = piso.reportar("entrega", "walter", {"cliente": "Kiosco Plaza"})
    assert "adjunto" not in r
    assert piso.adjunto_path(r["id"]) is None


def test_la_prueba_rechaza_lo_que_no_es_imagen_y_lo_muy_pesado():
    from core import piso
    import base64 as _b64
    with pytest.raises(ValueError):
        piso.reportar("entrega", "walter", {"cliente": "X", "prueba": "no-es-data-url"})
    pesada = "data:image/jpg;base64," + _b64.b64encode(b"0" * 2_100_000).decode()
    with pytest.raises(ValueError):
        piso.reportar("entrega", "walter", {"cliente": "X", "prueba": pesada})

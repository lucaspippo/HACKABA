"""El aviso vuelve al que lo originó, o no sirvió de nada.

`piso.reportar` guardaba el hecho, el dueño lo resolvía, y el que lo había
reportado no se enteraba nunca: `piso.resolver` auditaba y no emitía ninguna
notificación, y `api.piso.reportes` —que existía— no lo llamaba ninguna
pantalla. Ocho cajas rotas se reclamaban, se cobraban, y el que las había visto
volvía al grupo de WhatsApp, donde por lo menos alguien contesta.

Las tres piezas del circuito, y las tres tienen que estar o no sirve ninguna:

  1. DESTINATARIO — el aviso nace dirigido. Ángela lo propone por oficio y la
     persona confirma; nadie elige de una lista de catorce nombres.
  2. ACUSE — "Celeste lo vio a las 9:31". Sin esto, "no lo tomó nadie" y "lo
     tomó alguien y no lo abrió" se leen igual desde el lado del que reportó.
  3. RESULTADO DE VUELTA — cerrar avisa al que originó, con quién lo cerró.

Y la cuarta, que no es del reporte sino de la nota: un hallazgo armado con lo
que alguien contó tiene que volver a esa persona (`core/mis_avisos.py`).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DEMO = os.path.join(os.path.dirname(BACKEND), "data-demo")
ENV = {**os.environ, "POLPILOT_TENANT": "demo", "POLPILOT_DATA_DIR": DATA_DEMO,
       "POLPILOT_DEMO_TODAY": "2026-07-07", "PYTHONIOENCODING": "utf-8"}
ENV.pop("ANTHROPIC_API_KEY", None)


# Todo subproceso que ESCRIBE en el tenant demo arranca con esto y termina
# llamando a `limpiar(ids)`. El tenant demo es compartido por media suite y es
# de sólo lectura para el resto: `test_p34` afirma que ciertas personas están
# inactivas, y un reporte mío les daba actividad. Un test que le cambia el
# mundo al de al lado es un test roto, aunque pase solo.
PRELUDIO = """
from sqlalchemy import text
from core.db.engine import tenant_connection
from core.db import tenant as _t

def limpiar(ids):
    ids = [i for i in ids if i]
    if not ids:
        return
    with tenant_connection(_t.current_tenant_id()) as c:
        c.execute(text("DELETE FROM floor_reports WHERE id = ANY(:ids)"), {"ids": ids})
        c.execute(text("DELETE FROM notifications WHERE ref = ANY(:ids)"), {"ids": ids})
        # La auditoría es append-only por diseño y no se toca desde la app; acá
        # se limpia por SQL porque es el rastro que mis reportes dejaron sobre
        # la actividad del equipo, y ése es el que rompe a los demás.
        c.execute(text("DELETE FROM audit_events WHERE action IN "
                       "('reportar_faltante','marcar_conteo','resolver_reporte_piso') "
                       "AND created_at >= now() - interval '10 minutes'"))
"""


def _en_demo(codigo: str, escribe: bool = False):
    if escribe:
        codigo = PRELUDIO + codigo
    r = subprocess.run([sys.executable, "-c", codigo], cwd=BACKEND, env=ENV,
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert r.returncode == 0, r.stderr[-1200:]
    return json.loads(r.stdout.strip().splitlines()[-1])


# --- 1 · a quién le llega -------------------------------------------------------

def test_angela_propone_el_destinatario_por_oficio_no_por_nombre():
    """El match es contra el TEXTO del rol, igual que lib/roles.js: una persona
    nueva con el mismo oficio hereda los avisos sin tocar código."""
    out = _en_demo(
        "import json, auth; from core import piso;"
        "r = {t: piso.destinatario_sugerido(t) for t in piso.TIPOS};"
        "print(json.dumps({'destinos': r,"
        " 'roles': {u: d.get('rol') for u, d in auth.USUARIOS.items()}}, ensure_ascii=False))")
    d, roles = out["destinos"], out["roles"]
    assert "compras" in (roles[d["faltante"]] or "").lower()
    assert "dep" in (roles[d["conteo"]] or "").lower()
    assert "administraci" in (roles[d["pedido"]] or "").lower()
    for tipo, quien in d.items():
        assert quien, tipo          # ninguno se queda sin destino


def test_sin_nadie_de_ese_oficio_cae_en_el_dueno_y_no_en_el_vacio():
    """La única caída que no pierde el aviso. Un tenant que nombre distinto sus
    puestos tiene que seguir teniendo a alguien que lo lea."""
    out = _en_demo(
        "import json, auth; from core import piso;"
        "auth.USUARIOS = {k: {**v, 'rol': 'Puesto sin nombre conocido'}"
        "                 for k, v in auth.USUARIOS.items()};"
        "q = piso.destinatario_sugerido('faltante');"
        "print(json.dumps({'quien': q, 'es_admin': bool(auth.USUARIOS[q]['es_admin'])}))")
    assert out["quien"] and out["es_admin"] is True


# --- 2 · el circuito, de punta a punta ------------------------------------------

# Se mira la campanita por `ref` —el id del reporte— y no por título: dos
# cierres seguidos producen el MISMO texto, así que comparar títulos daba vacío
# en la segunda corrida y el test fallaba sin que nada estuviera mal.
CIRCUITO = """
import json
from core import piso
from core.db import notifications_repo, tenant as _t

def buzon(user, ref):
    return [{'titulo': n['titulo'], 'tipo': n['tipo']}
            for n in notifications_repo.list_for(_t.current_tenant_id(), user)
            if n.get('ref') == ref]

r = piso.reportar('faltante', 'nahuel',
                  {'producto': 'MANTECA SANTA CLARA 200G (X30U)', 'cantidad': 8,
                   'motivo': 'roto'},
                  destinatario='celeste')
rid = r['id']
paso = {'nace': dict(r), 'buzon_celeste_al_nacer': buzon('celeste', rid)}

visto = piso.ver(rid, 'celeste')
paso['visto'] = dict(visto)
paso['buzon_nahuel_al_verlo'] = buzon('nahuel', rid)

# abrirlo de nuevo no reescribe la hora ni vuelve a avisar
otra = piso.ver(rid, 'celeste')
paso['visto_dos_veces'] = otra['visto'] == visto['visto']
paso['buzon_nahuel_al_reabrir'] = buzon('nahuel', rid)

cerrado = piso.resolver(rid, 'celeste', 'Reclamado a Campo Alegre')
paso['cerrado'] = dict(cerrado)
paso['buzon_nahuel_al_cerrar'] = buzon('nahuel', rid)
paso['mios_nahuel'] = next(x for x in piso.mios('nahuel')['reporte'] if x['id'] == rid)
paso['mios_celeste'] = [x['id'] for x in piso.mios('celeste')['me_mandaron']]
limpiar([rid])
print(json.dumps(paso, ensure_ascii=False))
"""


@pytest.fixture(scope="module")
def circuito():
    return _en_demo(CIRCUITO, escribe=True)


def test_el_aviso_nace_dirigido(circuito):
    assert circuito["nace"]["destinatario"] == "celeste"
    assert circuito["nace"]["estado"] == "nuevo"
    assert circuito["nace"]["actor"] == "nahuel"


def test_al_destinatario_le_llega_cuando_nace(circuito):
    buzon = circuito["buzon_celeste_al_nacer"]
    assert len(buzon) == 1, buzon
    assert "Nahuel" in buzon[0]["titulo"]
    assert buzon[0]["tipo"] == "piso_reporte"


def test_el_acuse_vuelve_al_que_reporto(circuito):
    """La pieza más barata del circuito y la que más cambia."""
    assert circuito["visto"]["estado"] == "visto"
    assert circuito["visto"]["visto_por"] == "celeste"
    assert circuito["visto"]["visto"]
    visto = circuito["buzon_nahuel_al_verlo"]
    assert len(visto) == 1, visto
    assert "Celeste" in visto[0]["titulo"]


def test_abrirlo_dos_veces_no_mueve_la_hora_ni_avisa_de_nuevo(circuito):
    """El que reportó ya leyó «visto 9:31»: ese dato no se mueve bajo sus pies,
    y su campanita no se llena porque el otro recargó la pantalla."""
    assert circuito["visto_dos_veces"] is True
    assert circuito["buzon_nahuel_al_reabrir"] == circuito["buzon_nahuel_al_verlo"]


def test_cerrarlo_le_devuelve_el_resultado_al_que_lo_origino(circuito):
    """El punto donde el producto se gana o se pierde."""
    assert circuito["cerrado"]["estado"] == "resuelto"
    assert circuito["cerrado"]["resuelto_por"] == "celeste"
    # Dos avisos sobre ESTE reporte: el "lo vio" y el "lo cerró". Se cuenta por
    # `ref`, no por texto — dos cierres producen el mismo título.
    assert len(circuito["buzon_nahuel_al_cerrar"]) == 2, \
        circuito["buzon_nahuel_al_cerrar"]
    assert any("cerró" in b["titulo"] for b in circuito["buzon_nahuel_al_cerrar"])


def test_cada_uno_ve_su_lado_del_mismo_aviso(circuito):
    """Dos preguntas distintas: «¿qué pasó con lo que dije?» y «¿qué está
    esperando por mí?»."""
    assert circuito["mios_nahuel"]["estado"] == "resuelto"
    assert circuito["mios_nahuel"]["destinatario"] == "celeste"
    assert circuito["nace"]["id"] in circuito["mios_celeste"]


# --- 3 · quién puede cerrar -----------------------------------------------------

def test_el_destinatario_puede_cerrar_lo_que_le_mandaron():
    """No es un permiso nuevo: es la misma dueñez de fila que ya tiene
    `recordatorios.completar`. Un aviso dirigido a Celeste que sólo el dueño
    puede cerrar deja al dueño de cuello de botella."""
    out = _en_demo(
        "import json; from core import piso;"
        "r = piso.reportar('faltante', 'nahuel',"
        "  {'producto': 'X', 'cantidad': 1, 'motivo': 'roto'}, destinatario='celeste');"
        "c = piso.resolver(r['id'], 'celeste', 'listo');"
        "limpiar([r['id']]);"
        "print(json.dumps({'estado': c['estado'], 'por': c['resuelto_por']}))",
        escribe=True)
    assert out["estado"] == "resuelto"
    assert out["por"] == "celeste"


def test_un_reporte_viejo_sin_destinatario_sigue_siendo_valido():
    """Las filas anteriores a la migración no tienen a quién, y siguen andando:
    son el pozo común de siempre, que el dueño ve."""
    out = _en_demo(
        "import json; from core import piso;"
        "r = piso.reportar('conteo', 'tomas', {'producto': 'X', 'contado': 3});"
        "limpiar([r['id']]);"
        "print(json.dumps({'dest': r.get('destinatario'), 'estado': r['estado']}))",
        escribe=True)
    assert out["dest"] is None
    assert out["estado"] == "nuevo"


# --- 4 · el hallazgo vuelve al que lo alimentó ----------------------------------

def test_el_cruce_vuelve_a_quien_puso_la_nota():
    """Ramón avisó cuatro veces que la cámara está llena, el sistema lo cruzó
    con la orden que entra, y hoy la respuesta a su pregunta la ve una sola
    persona en una pantalla de escritorio."""
    out = _en_demo(
        "import json; from core import mis_avisos;"
        "print(json.dumps({u: mis_avisos.sirvio_para(u, 'es')"
        "                  for u in ('ramon', 'diego', 'kevin')}, ensure_ascii=False))")
    ramon = out["ramon"]
    assert ramon, "a Ramón no le vuelve ningún hallazgo"
    uno = ramon[0]
    assert uno["mis_notas"], uno
    assert uno["personas"] >= 1
    assert uno["titulo"] and uno["resumen"]
    # Kevin dejó una nota sin ubicación: no alimenta ningún cruce, y no se le
    # inventa uno para que la pantalla no quede vacía.
    assert isinstance(out["kevin"], list)


def test_no_se_le_atribuye_a_nadie_una_nota_sin_autor():
    """Las entidades no se adivinan por texto: si el hallazgo no declara de
    quién es la nota, no es de nadie."""
    out = _en_demo(
        "import json; from core import mis_avisos;"
        "print(json.dumps(mis_avisos.sirvio_para('no_existe_esta_persona', 'es')))")
    assert out == []


def test_estos_tests_no_le_dejan_actividad_al_equipo(circuito):
    """La red de todo lo de arriba.

    Escribir en el tenant demo y no limpiar hacía fallar a `test_p34`, que
    afirma que ciertas personas están inactivas: mis reportes les daban
    actividad. Pasaba solo y rompía a otro, que es la peor forma de estar roto.
    """
    out = _en_demo(
        "import json; from core import piso;"
        "from core.db import audit_repo, tenant as _t;"
        "acc = ('reportar_faltante', 'marcar_conteo', 'resolver_reporte_piso');"
        "hoy = [e for e in audit_repo.list_events(_t.current_tenant_id())"
        "       if e.get('accion') in acc];"
        "print(json.dumps({'reportes': len(piso.listar()),"
        " 'auditoria_de_piso': len(hoy)}))")
    # El dataset del demo no trae reportes de piso sembrados: si quedó alguno,
    # es mío y no lo limpié.
    assert out["reportes"] == 0, out
    assert out["auditoria_de_piso"] == 0, out


def test_lo_que_se_muestra_es_el_nombre_y_no_el_usuario():
    """«celeste lo cerró» en minúscula era el username crudo llegando a la
    pantalla. El username es la identidad y se guarda; el nombre de pantalla se
    resuelve al mostrarlo, y si la persona ya no está en el equipo cae al
    username en vez de quedar vacío."""
    out = _en_demo(
        "import json; from core import piso, mis_avisos;"
        "r = piso.reportar('faltante', 'nahuel',"
        "  {'producto': 'X', 'cantidad': 1, 'motivo': 'roto'}, destinatario='celeste');"
        "piso.ver(r['id'], 'celeste');"
        "piso.resolver(r['id'], 'celeste', 'listo');"
        "d = mis_avisos.de('nahuel', 'es');"
        "limpiar([r['id']]);"
        "print(json.dumps(d['reporte'][0], ensure_ascii=False))",
        escribe=True)
    assert out["actor"] == "nahuel" and out["actor_nombre"] == "Nahuel"
    assert out["destinatario"] == "celeste" and out["destinatario_nombre"] == "Celeste"
    assert out["visto_por_nombre"] == "Celeste"
    assert out["resuelto_por_nombre"] == "Celeste"

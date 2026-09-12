"""Los dos avisos que no salen del oficio.

Todo el resto de `piso.reportar` se rutea por OFICIO: un faltante va a compras,
un conteo al encargado. Estos dos no:

  · `pregunta` — el que recién entró le pregunta a SU referente, que es un dato
    de su ficha (`puesto.mentor`) y no del tipo de aviso. `usuarios_demo.py` se
    lo declaraba a Kevin y ninguna pantalla lo usaba: saber a quién preguntarle
    no sirve si preguntar sigue siendo pararse a buscarlo por el galpón.
  · `costo` — el precio de venta salió de un costo viejo. Lo levanta quien
    atiende el mostrador y lo arregla quien compra.

Los dos entran por el MISMO riel que el resto (destinatario, acuse, resultado
de vuelta): la respuesta de Ramón vuelve como la nota del cierre, y ahí está
todo el punto — una duda de martes deja de ser algo que el que entró tiene que
acordarse de volver a preguntar.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DEMO = os.path.join(os.path.dirname(BACKEND), "data-demo")
ENV = {**os.environ, "POLPILOT_TENANT": "demo", "POLPILOT_DATA_DIR": DATA_DEMO,
       "POLPILOT_DEMO_TODAY": "2026-07-07", "PYTHONIOENCODING": "utf-8"}
ENV.pop("ANTHROPIC_API_KEY", None)

# El tenant demo lo comparte media suite y para el resto es de sólo lectura:
# `test_p34` afirma que ciertas personas están inactivas y un reporte mío les
# daría actividad. Todo lo que escribe, limpia.
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
        c.execute(text("DELETE FROM audit_events WHERE action IN "
                       "('preguntar_referente','avisar_costo_viejo','resolver_reporte_piso') "
                       "AND created_at >= now() - interval '10 minutes'"))
"""


def _en_demo(codigo: str, escribe: bool = False):
    if escribe:
        codigo = PRELUDIO + codigo
    r = subprocess.run([sys.executable, "-c", codigo], cwd=BACKEND, env=ENV,
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert r.returncode == 0, r.stderr[-1200:]
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_kevin_tiene_referente_cargado_y_es_alguien_del_equipo():
    """El dato que estaba y no se usaba. Si esto se cae, el botón no tiene a
    quién mandarle nada."""
    out = _en_demo(
        "import json, auth;"
        "k = auth.USUARIOS['kevin'];"
        "m = (k.get('puesto') or {}).get('mentor');"
        "print(json.dumps({'mentor': m, 'existe': m in auth.USUARIOS,"
        " 'rol': (auth.USUARIOS.get(m) or {}).get('rol')}, ensure_ascii=False))")
    assert out["mentor"] == "ramon"
    assert out["existe"], "el referente tiene que ser un username REAL del equipo"
    assert "dep" in (out["rol"] or "").lower()


def test_la_pregunta_llega_al_referente_y_la_respuesta_vuelve():
    """El circuito entero en un solo test, porque media pieza no sirve: si la
    respuesta no vuelve, preguntar por acá es peor que preguntar en voz alta."""
    out = _en_demo(
        "import json; from core import piso;"
        "r = piso.reportar('pregunta', 'kevin',"
        "                  {'nota': '¿La leche va al pasillo 4 o a la cámara?'},"
        "                  destinatario='ramon');"
        "piso.ver(r['id'], 'ramon');"
        "c = piso.resolver(r['id'], 'ramon', 'A la cámara. El pasillo 4 es seco.');"
        "mios = piso.mios('kevin');"
        "de_ramon = piso.mios('ramon');"
        "print(json.dumps({'id': r['id'], 'destinatario': r['destinatario'],"
        " 'estado': c['estado'], 'nota': c.get('nota_dueno') or c.get('nota'),"
        " 'kevin_ve': [x['id'] for x in mios['reporte']],"
        " 'ramon_ve': [x['id'] for x in de_ramon['me_mandaron']]}, ensure_ascii=False));"
        "limpiar([r['id']])", escribe=True)
    assert out["destinatario"] == "ramon"
    assert out["id"] in out["ramon_ve"], "a Ramón le tiene que aparecer como suyo"
    assert out["id"] in out["kevin_ve"], "y a Kevin como algo que él dijo"
    assert out["estado"] == "resuelto"
    assert "cámara" in (out["nota"] or ""), "la RESPUESTA vuelve, no sólo el cierre"


def test_una_pregunta_vacia_no_entra():
    """Un aviso sin contenido le hace perder el tiempo al que lo recibe y le
    enseña al que lo mandó que esto no sirve."""
    out = _en_demo(
        "import json; from core import piso;"
        "err = None\n"
        "try:\n"
        "    piso.reportar('pregunta', 'kevin', {'nota': '   '}, destinatario='ramon')\n"
        "except ValueError as e:\n"
        "    err = str(e)\n"
        "print(json.dumps({'err': err}, ensure_ascii=False))")
    assert out["err"], "tiene que fallar, no guardar una pregunta en blanco"


def test_el_costo_viejo_va_a_quien_compra():
    """No lo arregla el que vende: lo arregla el que negocia con el proveedor.
    Mismo oficio que ya recibe los faltantes, por el mismo motivo."""
    out = _en_demo(
        "import json, auth; from core import piso;"
        "d = piso.destinatario_sugerido('costo');"
        "print(json.dumps({'quien': d, 'rol': auth.USUARIOS[d]['rol']}, ensure_ascii=False))")
    assert "compras" in out["rol"].lower(), out


def test_el_aviso_de_costo_necesita_el_producto():
    """«Hay un precio mal» no es accionable. El producto viene puesto desde la
    fila que la persona tocó, así que exigirlo no le cuesta nada a ella."""
    out = _en_demo(
        "import json; from core import piso;"
        "err = None\n"
        "try:\n"
        "    piso.reportar('costo', 'vanesa', {'nota': 'está viejo'})\n"
        "except ValueError as e:\n"
        "    err = str(e)\n"
        "print(json.dumps({'err': err}, ensure_ascii=False))")
    assert out["err"]


def test_los_dos_tipos_nuevos_tienen_su_slug_de_auditoria():
    """Sin slug, el trabajo no se cuenta en «qué resolvió esta semana» del panel
    del dueño — y `reportar` reventaría con KeyError al auditar."""
    out = _en_demo(
        "import json; from core import piso;"
        "print(json.dumps({'tipos': list(piso.TIPOS), 'acc': piso.ACCION}))")
    assert "pregunta" in out["tipos"] and "costo" in out["tipos"]
    assert out["acc"]["pregunta"] and out["acc"]["costo"]
    assert len(set(out["acc"].values())) == len(out["acc"]), "slugs duplicados"

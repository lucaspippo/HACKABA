"""Los avisos que cada oficio deja, como botones.

«Nota — agregar información» es un campo de texto libre que nace sin
destinatario y se muere: es exactamente el objeto que el modelo de flujo marcó
como roto. Un chofer parado en la puerta de un cliente que no está no escribe un
párrafo — toca «El cliente no estaba» y sigue.

Lo que se protege:

  1. EL OFICIO SALE DEL TEXTO DEL ROL. Una persona nueva con el mismo puesto
     hereda sus avisos sin tocar código, y un tenant que nombre distinto sus
     puestos se queda sin botones en vez de romperse.
  2. LOS CINCO DEL DEPÓSITO SE DISTINGUEN. Es la misma partición de la regex que
     `lib/roles.js`: si acá se pierde, Brian vuelve a ver los avisos de Nahuel.
  3. EL DESTINATARIO ES UN USERNAME REAL O ESTÁ VACÍO. Nunca inventado. El
     dataset no une un cliente con su preventista, así que
     `preventista_del_cliente` no se resuelve — y eso se dice.
  4. TODO LO QUE LA SEMILLA NOMBRA EXISTE. Tipos que `piso.py` acepta, motivos
     que valida, campos que el formulario sabe pedir.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAIZ = os.path.dirname(BACKEND)
DATA_DEMO = os.path.join(RAIZ, "data-demo")
ENV = {**os.environ, "POLPILOT_TENANT": "demo", "POLPILOT_DATA_DIR": DATA_DEMO,
       "POLPILOT_DEMO_TODAY": "2026-07-07", "PYTHONIOENCODING": "utf-8"}
ENV.pop("ANTHROPIC_API_KEY", None)

# Los campos que el formulario sabe pedir (frontend/src/lib/roles.js, CAMPO).
CAMPOS_CONOCIDOS = {"producto", "cantidad", "contado", "cliente", "pedido",
                    "ubicacion", "lote", "proveedor", "monto"}


def _semilla() -> dict:
    with open(os.path.join(DATA_DEMO, "avisos_por_oficio.json"), encoding="utf-8") as f:
        return json.load(f)


def _en_demo(codigo: str):
    r = subprocess.run([sys.executable, "-c", codigo], cwd=BACKEND, env=ENV,
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert r.returncode == 0, r.stderr[-900:]
    return json.loads(r.stdout.strip().splitlines()[-1])


TODOS = ("import json, auth; from core import avisos_oficio as ao;"
         "print(json.dumps({u: ao.de(d['rol'], 'es')"
         " for u, d in auth.USUARIOS.items() if not d.get('interno')},"
         " ensure_ascii=False))")


def test_cada_persona_del_demo_cae_en_el_oficio_que_declara_la_semilla():
    """La semilla dice `persona_demo` para cada oficio. Si el regex y la semilla
    se separan, alguien recibe los avisos de otro puesto — que es peor que no
    recibir ninguno."""
    out = _en_demo(TODOS)
    for oficio, bloque in _semilla()["oficios"].items():
        quien = bloque["persona_demo"]
        assert out[quien]["oficio"] == oficio, (quien, out[quien]["oficio"], oficio)


def test_los_cinco_del_deposito_no_se_pisan():
    """La misma partición que hizo falta en lib/roles.js. Si esto se cae, Brian
    vuelve a ver «vino roto» y Nahuel «no hay stock de este renglón»."""
    out = _en_demo(TODOS)
    ids = {u: {a["id"] for a in out[u]["avisos"]}
           for u in ("ramon", "nahuel", "tomas", "brian", "kevin")}
    for u, propios in ids.items():
        assert propios, u
        for otro, ajenos in ids.items():
            if otro != u:
                assert not (propios & ajenos), (u, otro, propios & ajenos)


def test_las_oficinas_no_tienen_lista_y_eso_no_es_un_error():
    """Administración, compras y el dueño escriben en vez de avisar desde el
    piso. Se devuelve la misma forma vacía, no un 500."""
    out = _en_demo(TODOS)
    for u in ("marta", "celeste", "aldo"):
        assert out[u]["oficio"] is None
        assert out[u]["avisos"] == []


def test_el_destinatario_es_alguien_real_o_esta_vacio():
    out = _en_demo(
        "import json, auth; from core import avisos_oficio as ao;"
        "r = [(u, a['id'], a['destinatario'], a['destino_sin_regla'])"
        "     for u, d in auth.USUARIOS.items() if not d.get('interno')"
        "     for a in ao.de(d['rol'], 'es')['avisos']];"
        "print(json.dumps({'filas': r, 'gente': sorted(auth.USUARIOS)}, ensure_ascii=False))")
    gente = set(out["gente"])
    for _u, aid, destino, sin_regla in out["filas"]:
        if destino is None:
            assert sin_regla, aid
        else:
            assert destino in gente, (aid, destino)
            assert not sin_regla, aid


def test_el_unico_destino_que_no_se_puede_resolver_se_dice():
    """`preventista_del_cliente` no existe como persona: el dataset no une un
    cliente con su preventista y elegir uno de los dos sería inventarlo. Cae
    vacío, y el formulario usa la propuesta por tipo."""
    sin = [a["id"] for b in _semilla()["oficios"].values() for a in b["avisos"]
           if a["destino_probable"] == "preventista_del_cliente"]
    assert sin == ["rep_no_estaba"], sin
    out = _en_demo(
        "import json, auth; from core import avisos_oficio as ao;"
        "a = [x for x in ao.de(auth.USUARIOS['walter']['rol'], 'es')['avisos']"
        "     if x['id'] == 'rep_no_estaba'][0];"
        "print(json.dumps(a, ensure_ascii=False))")
    assert out["destinatario"] is None and out["destino_sin_regla"] is True


def test_todo_lo_que_la_semilla_nombra_existe_en_el_codigo():
    """Tipos, motivos y campos. Una semilla que nombra un tipo que `piso.py` no
    acepta produce un botón que revienta al tocarlo."""
    out = _en_demo("import json; from core import piso;"
                   "print(json.dumps({'tipos': list(piso.TIPOS), 'motivos': list(piso.MOTIVOS)}))")
    for oficio, bloque in _semilla()["oficios"].items():
        for a in bloque["avisos"]:
            assert a["tipo"] in out["tipos"], (oficio, a["id"], a["tipo"])
            if a.get("motivo"):
                assert a["motivo"] in out["motivos"], (a["id"], a["motivo"])
            assert set(a["necesita"]) <= CAMPOS_CONOCIDOS, (a["id"], a["necesita"])
            assert a["texto"] and a["texto_en"], a["id"]


def test_el_texto_viaja_en_el_idioma_de_quien_mira():
    out = _en_demo(
        "import json, auth; from core import avisos_oficio as ao;"
        "rol = auth.USUARIOS['tomas']['rol'];"
        "print(json.dumps({'es': [a['texto'] for a in ao.de(rol, 'es')['avisos']],"
        " 'en': [a['texto'] for a in ao.de(rol, 'en')['avisos']]}, ensure_ascii=False))")
    assert out["es"] != out["en"]
    assert all(t for t in out["en"]), "ninguno se queda sin inglés"


AVISO_IDA_Y_VUELTA = """
from sqlalchemy import text
from core.db.engine import tenant_connection
from core.db import tenant as _t
import json
from core import piso
r = piso.reportar('aviso', 'tomas',
                  {'producto': 'JAMON COCIDO GUARANI (HORMA)', 'ubicacion': 'CAMARA 1',
                   'aviso_id': 'cnt_otra_ubicacion'}, destinatario='ramon')
mios = piso.mios('ramon')
print(json.dumps({'id': r['id'], 'estado': r['estado'],
                  'destinatario': r.get('destinatario'),
                  'llego': r['id'] in [x['id'] for x in mios['me_mandaron']]}))
with tenant_connection(_t.current_tenant_id()) as c:
    c.execute(text("DELETE FROM floor_reports WHERE id = :i"), {"i": r['id']})
    c.execute(text("DELETE FROM notifications WHERE ref = :i"), {"i": r['id']})
    c.execute(text("DELETE FROM audit_events WHERE action = 'avisar_desde_el_piso' "
                   "AND created_at >= now() - interval '10 minutes'"))
"""


def test_un_aviso_entra_por_el_riel_de_siempre():
    """Mismo `piso.reportar`, mismo destinatario, misma auditoría. Lo que cambia
    es que nace dirigido en vez de ser un texto libre sin dueño.

    Limpia lo que escribió: el tenant demo lo comparte media suite y para el
    resto es de sólo lectura."""
    out = _en_demo(AVISO_IDA_Y_VUELTA)
    assert out["destinatario"] == "ramon" and out["llego"] and out["estado"] == "nuevo"


def test_un_aviso_que_no_dice_de_que_es_no_entra():
    out = _en_demo(
        "import json; from core import piso;\n"
        "err = None\n"
        "try:\n"
        "    piso.reportar('aviso', 'tomas', {})\n"
        "except ValueError as e:\n"
        "    err = str(e)\n"
        "print(json.dumps({'err': err}, ensure_ascii=False))")
    assert out["err"]

"""
P·perfil bilingüe — la descripción de cada persona, también en inglés.

El demo se graba en inglés y las etiquetas del perfil ya estaban traducidas
("My role", "I take care of"), pero el CONTENIDO seguía en castellano: un
párrafo entero en español adentro de una pantalla en inglés.

Lo que se protege acá:
  1. Los 15 usuarios del demo tienen su `descripcion_en`, con los marcadores de
     bloque en inglés (si no, la vista no puede partirla en bloques).
  2. El castellano NO se movió: `descripcion` es la fuente y sobre ella matchea
     `perfiles.sugerir_modulos` — traducir no puede cambiar qué módulos sugiere.
  3. Lo que una persona REESCRIBE de su perfil se muestra tal cual en los dos
     idiomas: son sus palabras, no se traducen a sus espaldas.
  4. El `puesto` (sector/turno/contrato) viaja bilingüe; el nombre del mentor no
     se traduce.
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

# los mismos marcadores que lee el frontend (MiPerfil.BLOQUES)
MARCADORES_ES = ("Mi función:", "Me encargo de:", "Todos los días miro:", "Decido sobre:")
MARCADORES_EN = ("My role:", "I take care of:", "Every day I look at:", "I decide on:")


def _en_demo(codigo: str) -> dict:
    r = subprocess.run([sys.executable, "-c", codigo], cwd=BACKEND, env=ENV,
                       capture_output=True, text=True, encoding="utf-8", timeout=180)
    assert r.returncode == 0, r.stderr[-800:]
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_todos_tienen_descripcion_en_con_sus_marcadores():
    out = _en_demo(
        "import json, auth;"
        "print(json.dumps({u: {'es': v.get('descripcion',''), 'en': v.get('descripcion_en','')}"
        "                  for u, v in auth.USUARIOS.items()}, ensure_ascii=False))")
    assert len(out) == 15, sorted(out)
    for u, d in out.items():
        assert d["en"], f"{u} sin descripcion_en"
        assert d["en"] != d["es"], f"{u}: la traducción es idéntica al castellano"
        # el equipo PolPilot es la única descripción libre (no usa bloques)
        if u == "polpilot":
            continue
        for marca in MARCADORES_ES:
            assert marca in d["es"], f"{u}: falta «{marca}» en el castellano"
        for marca in MARCADORES_EN:
            assert marca in d["en"], f"{u}: falta «{marca}» en el inglés"


def test_el_castellano_es_la_fuente_y_no_se_movio():
    """Traducir no puede cambiar qué módulos sugiere Ángela: el matcher corre
    sobre `descripcion`, que quedó intacta."""
    out = _en_demo(
        "import json, auth;"
        "from core import perfiles;"
        "print(json.dumps({u: [s['modulo'] for s in perfiles.sugerir_modulos(u)]"
        "                  for u, v in auth.USUARIOS.items() if not v.get('interno')},"
        " ensure_ascii=False))")
    # la foto congelada de test_sugerencias: nadie nuevo pide nada por la traducción
    assert out["walter"] == ["cuentas", "cobranzas"]
    assert out["diego"] == ["logistica", "inventario"]
    assert out["kevin"] == [] and out["aldo"] == [] and out["ramon"] == []


def test_lo_que_la_persona_reescribe_no_se_traduce():
    """Con override, `descripcion_en` viaja en None: la vista cae al castellano
    y muestra EXACTAMENTE lo que esa persona escribió, en los dos idiomas."""
    out = _en_demo(
        "import json, auth;"
        "from core import perfiles;"
        "antes = auth.perfil_publico('tomas');"
        "perfiles.set_descripcion('tomas', 'Mi función: lo que yo escribí.');"
        "despues = auth.perfil_publico('tomas');"
        "perfiles.set_descripcion('tomas', None);"
        "vuelta = auth.perfil_publico('tomas');"
        "print(json.dumps({'antes_en': bool(antes['descripcion_en']),"
        " 'despues_desc': despues['descripcion'], 'despues_en': despues['descripcion_en'],"
        " 'restaurado_en': bool(vuelta['descripcion_en'])}, ensure_ascii=False))")
    assert out["antes_en"] is True
    assert out["despues_desc"] == "Mi función: lo que yo escribí."
    assert out["despues_en"] is None          # sus palabras, sin traducir
    assert out["restaurado_en"] is True       # al limpiar el override, vuelve la del seed


def test_el_puesto_viaja_bilingue_y_el_mentor_no_se_traduce():
    out = _en_demo(
        "import json, auth;"
        "print(json.dumps(auth.perfil_publico('kevin')['puesto'], ensure_ascii=False))")
    assert out["sector"] and out["sector_en"] and out["sector"] != out["sector_en"]
    assert out["turno"] and out["turno_en"] and out["turno"] != out["turno_en"]
    assert out["contrato"] and out["contrato_en"]
    assert out["mentor"]["nombre"] == "Ramón"   # el nombre propio no se traduce

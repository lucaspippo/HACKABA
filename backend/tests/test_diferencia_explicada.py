"""C7 · el ERP dice «faltan 6,5»; nosotros podemos decir por qué.

En el dataset del demo hay una diferencia de −6,5 unidades de leche en
Pasillo 4 · Rack B, y ese mismo día dos personas dejaron su aviso sobre ese
pasillo: Kevin («me mandaron a buscar leche al pasillo 4 y estaba en otro
rack») y Nahuel («corrí las cajas para hacer lugar»). La diferencia ya estaba
explicada y nadie los había juntado — el que la mira iba a mandar a recontar,
o peor, a ajustar el stock por un faltante que no existe.

Dos mitades, y las dos importan:

  · La explicación viaja CON la diferencia, para el que decide.
  · Y le vuelve al que dejó la nota: Kevin no necesita ver los pesos —eso es
    del que decide— sino que lo que dijo explicó una diferencia.

La nota es CONTEXTO, no decisión: no saca la diferencia de la lista.
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


def _en_demo(codigo: str):
    r = subprocess.run([sys.executable, "-c", codigo], cwd=BACKEND, env=ENV,
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert r.returncode == 0, r.stderr[-900:]
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_la_diferencia_del_pasillo_4_llega_con_las_dos_notas():
    out = _en_demo(
        "import json; from core import deposito;"
        "ex = [d for d in deposito.explicaciones() if d['notas']];"
        "print(json.dumps(ex, ensure_ascii=False))")
    assert len(out) == 1, [d["descripcion"] for d in out]
    d = out[0]
    assert "LECHE ENTERA EL PARANA" in d["descripcion"]
    assert d["diferencia"] == -6.5
    assert d["ubicaciones"] == ["Pasillo 4 - Rack B"]
    assert sorted(n["autor"] for n in d["notas"]) == ["kevin", "nahuel"]
    # ordenadas por fecha: la explicación se lee como pasó
    assert [n["fecha"] for n in d["notas"]] == sorted(n["fecha"] for n in d["notas"])


def test_la_nota_no_saca_la_diferencia_de_la_lista():
    """Es contexto para el que decide, no una decisión tomada por él."""
    out = _en_demo(
        "import json; from core import deposito;"
        "print(json.dumps({'sin': len(deposito.discrepancias()),"
        " 'con': len(deposito.explicaciones())}))")
    assert out["con"] == out["sin"]


def test_una_nota_vieja_no_explica_el_conteo_de_hoy():
    """La ventana es explícita: un aviso de hace un mes ya no explica nada, y
    dejarlo entrar sería inventar una causalidad.

    El borde, con el dataset del demo: las notas del pasillo 4 son del 06/07 y
    hoy es el 07/07. Con `dias=1` la ventana arranca el 06/07 y las incluye —
    un día de memoria alcanza para el turno anterior, que es justo el caso.
    Con `dias=0` sólo entra lo de hoy, y ya no explican nada."""
    out = _en_demo(
        "import json; from core import deposito;"
        "n = lambda d: len([x for x in deposito.explicaciones(dias=d) if x['notas']]);"
        "print(json.dumps({'hoy': n(0), 'ayer': n(1), 'quince': n(15)}))")
    assert out["quince"] >= 1
    assert out["ayer"] == out["quince"]   # el turno anterior sigue explicando
    assert out["hoy"] == 0                # sólo lo de hoy no explica el conteo


def test_las_diferencias_sin_nota_no_inventan_una():
    out = _en_demo(
        "import json; from core import deposito;"
        "print(json.dumps([{'d': x['descripcion'], 'n': len(x['notas'])}"
        "                  for x in deposito.explicaciones()], ensure_ascii=False))")
    assert len(out) >= 2
    assert sum(1 for x in out if x["n"] == 0) >= 1, "todas tienen nota: sospechoso"


def test_al_que_dejo_la_nota_le_vuelve_que_explico_algo():
    """La mitad barata que convierte «te miramos» en «servís». Kevin entró hace
    una semana y es su primer aporte al sistema."""
    out = _en_demo(
        "import json; from core import mis_avisos;"
        "print(json.dumps({u: mis_avisos.explico_una_diferencia(u, 'es')"
        "                  for u in ('kevin', 'nahuel', 'tomas')}, ensure_ascii=False))")
    for quien in ("kevin", "nahuel"):
        assert len(out[quien]) == 1, quien
        x = out[quien][0]
        assert "LECHE ENTERA EL PARANA" in x["titulo"]
        assert "-6.5" in x["resumen"] and "Pasillo 4" in x["resumen"]
        assert x["personas"] == 2          # "otras 1 personas dijeron lo mismo"
        assert len(x["mis_notas"]) == 1
        assert x["mis_notas"][0]["texto"]
    assert out["tomas"] == []              # no habló de esa ubicación


def test_nace_bilingue_y_sin_placeholders_sueltos():
    """`i18n.t` devuelve el texto SIN formatear cuando falta un parámetro — el
    bug se ve en vez de esconderse. Este test es el que lo ve."""
    out = _en_demo(
        "import json; from core import mis_avisos;"
        "print(json.dumps({l: mis_avisos.explico_una_diferencia('kevin', l)[0]"
        "                  for l in ('es', 'en')}, ensure_ascii=False))")
    assert out["es"]["titulo"] != out["en"]["titulo"]
    for lang in ("es", "en"):
        for campo in ("titulo", "resumen"):
            assert "{" not in out[lang][campo], (lang, campo, out[lang][campo])


def test_el_endpoint_del_deposito_manda_la_explicacion():
    out = _en_demo(
        "import json; from core import deposito;"
        "d = deposito.discrepancias_conocimiento();"
        "ex = deposito.explicaciones(d['visibles']);"
        "print(json.dumps({'campos': sorted(ex[0].keys())}, ensure_ascii=False))")
    for campo in ("codigo", "descripcion", "diferencia", "notas", "ubicaciones",
                  "stock_contable", "stock_fisico"):
        assert campo in out["campos"], campo

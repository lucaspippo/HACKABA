"""La ficha de un producto: la pantalla de datos del teléfono.

El desktop tiene 34 secciones. El criterio para mobile no es cuáles caben: es
que **la entrada correcta a un dato en el celular casi nunca es una lista.** Una
lista de 430 productos no la scrollea nadie con guantes. Se llega por una
búsqueda, un escaneo o una tarea, y se abre la ficha de ESE producto.

Lo que se protege:

  1. NINGÚN NÚMERO NUEVO. Todos salen de su motor y se citan — la plata en
     riesgo es la de `vencimientos`, los problemas los de `quality`.
  2. NINGÚN TOTAL. Una ficha es UN producto; sumar sus lotes con su
     inmovilizado y con lo que le compran no responde ninguna pregunta.
  3. UN CÓDIGO QUE NO EXISTE SE DICE. Escanear algo que no está en el catálogo
     es un caso real del depósito, no una rareza.
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

# El salame de Monte Chico: el producto del dataset que junta las tres cosas
# —un lote que se vence, notas del equipo y compradores— en una sola pantalla.
SALAME = 1286


def _en_demo(codigo: str):
    r = subprocess.run([sys.executable, "-c", codigo], cwd=BACKEND, env=ENV,
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert r.returncode == 0, r.stderr[-900:]
    return json.loads(r.stdout.strip().splitlines()[-1])


def _ficha(cod: int):
    return _en_demo("import json; from core import ficha;"
                    f"print(json.dumps(ficha.producto({cod}, 'es'), ensure_ascii=False))")


def test_el_salame_contesta_las_seis_preguntas_de_una():
    f = _ficha(SALAME)
    assert "MONTE CHICO" in f["producto"]
    assert f["ubicaciones"], "dónde está es la primera pregunta del depósito"
    assert f["stock"] and f["pvp"]
    assert len(f["lotes"]) == 1, f["lotes"]
    assert f["lotes"][0]["dias_restantes"] == 11
    assert f["compradores"], "a quién se lo ofrezco"
    assert f["dijeron"], "y qué dijo el equipo de esto"


def test_los_compradores_vienen_con_nombre_y_son_pocos():
    """Tres contestan «¿a quién se lo ofrezco?». Treinta son una lista que nadie
    lee en un teléfono."""
    f = _ficha(SALAME)
    assert len(f["compradores"]) <= 3
    for c in f["compradores"]:
        assert c["cliente"], c
        assert c["monto"] > 0
    # ordenados por plata, que es el orden con el que se decide a quién llamar
    assert [c["monto"] for c in f["compradores"]] == sorted(
        (c["monto"] for c in f["compradores"]), reverse=True)


def test_las_notas_traen_el_nombre_de_quien_las_dijo():
    """Un aviso sin autor no se puede ni preguntar ni desmentir."""
    f = _ficha(SALAME)
    for n in f["dijeron"]:
        assert n["autor_nombre"] and n["autor_nombre"][0].isupper(), n
    assert [n["fecha"] for n in f["dijeron"]] == sorted(
        (n["fecha"] for n in f["dijeron"]), reverse=True)


def test_la_plata_en_riesgo_es_la_de_vencimientos_y_no_una_cuenta_nueva():
    """The Counting Rule: el número canónico se cita, no se recalcula."""
    out = _en_demo(
        "import json; from core import ficha, vencimientos;"
        f"v = [i for i in vencimientos.en_riesgo(30)['items'] if i['codigo'] == {SALAME}];"
        f"f = ficha.producto({SALAME}, 'es')['lotes'];"
        "print(json.dumps({'motor': [x['plata_en_riesgo'] for x in v],"
        " 'ficha': [x['plata_en_riesgo'] for x in f]}))")
    assert out["ficha"] == out["motor"] and out["motor"]


def test_los_problemas_son_los_del_libro_del_dueno():
    """La misma clasificación que ve el dueño, no una segunda opinión."""
    out = _en_demo(
        "import json; from core import ficha, quality, store;"
        "from core.models import Articulo;"
        f"a = [x for x in store.raw_actual() if x['codigo'] == 1269][0];"
        "print(json.dumps({'motor': [i.categoria.value for i in quality.clasificar(Articulo.from_dict(a))],"
        " 'ficha': [p['categoria'] for p in ficha.producto(1269, 'es')['problemas']]}))")
    assert out["ficha"] == out["motor"]
    assert "costo_viejo" in out["ficha"], "el jamón de 535 días"


def test_la_ficha_no_inventa_un_total():
    f = _ficha(SALAME)
    for clave in ("total", "valor", "inmovilizado", "suma", "plata"):
        assert clave not in f, clave


def test_un_codigo_que_no_existe_devuelve_nada_y_no_una_ficha_vacia():
    """Escanear algo de otro sistema es un caso REAL del depósito. La única
    respuesta honesta es decirlo — una ficha con ceros se lee como un producto
    que existe y está en cero, que es lo contrario."""
    out = _en_demo("import json; from core import ficha;"
                   "print(json.dumps({'f': ficha.producto(999999, 'es')}))")
    assert out["f"] is None


def test_el_texto_viaja_en_el_idioma_de_quien_mira():
    out = _en_demo(
        "import json; from core import ficha;"
        "print(json.dumps({'es': [p['label'] for p in ficha.producto(1269, 'es')['problemas']],"
        " 'en': [p['label'] for p in ficha.producto(1269, 'en')['problemas']]}, ensure_ascii=False))")
    assert out["es"] and out["en"] and out["es"] != out["en"]

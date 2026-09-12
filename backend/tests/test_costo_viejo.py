"""El costo viejo, en la pantalla del que puede hacer algo.

`quality.py` ya marcaba los costos de más de un año: es una de las categorías
del libro triado del dueño. Lo que no existía era el lugar donde sirve — el
jamón cocido de balanza tiene el costo cargado hace 535 días y su precio de
venta salió de ahí, y quien mira ese precio todos los días es la que atiende el
mostrador.

Lo que se protege:

  1. UN SOLO UMBRAL. El de `quality.UMBRAL_COSTO_VIEJO_DIAS`. Dos pantallas que
     cuenten "costo viejo" con umbrales distintos son dos verdades.
  2. SÓLO LO QUE ELLA VENDE. El cruce con `mostrador.grupos` es lo que hace que
     esto sea suyo: 430 SKUs en la pantalla es la forma más rápida de que no
     mire ninguno.
  3. NINGÚN TOTAL (PRODUCT.md, The Counting Rule). El costo viejo no dice
     cuánto se pierde, dice que no se sabe cuánto se gana.
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


VIEJOS = ("import json; from core import mostrador;"
          "print(json.dumps(mostrador.costos_viejos('es'), ensure_ascii=False))")


def test_el_jamon_de_535_dias_esta_y_va_primero():
    """El hallazgo del relevamiento, tal cual está en el dataset."""
    r = _en_demo(VIEJOS)
    assert r["disponible"]
    jamon = next(x for x in r["items"] if "JAMON COCIDO GUARANI" in x["producto"])
    assert jamon["dias"] == 535
    assert jamon["venta_x_peso"] is True
    # ordenado por antigüedad: el que más tiempo lleva sin tocarse va arriba
    assert [x["dias"] for x in r["items"]] == sorted(
        (x["dias"] for x in r["items"]), reverse=True)


def test_solo_lo_que_se_vende_en_el_mostrador():
    """De los cinco costos viejos del catálogo, los que llegan a esta pantalla
    son los que alimentan un grupo de mostrador. La galletita y el jabón
    también están viejos y también entran — se venden en el mostrador. Lo que
    NO puede pasar es que entre algo de una categoría que el mostrador no
    vende."""
    out = _en_demo(
        "import json; from core import mostrador;"
        "cats = {c for g in mostrador.grupos() for c in (g.get('categorias') or [])};"
        "v = mostrador.costos_viejos('es');"
        "print(json.dumps({'cats': sorted(cats),"
        " 'mias': sorted({x['categoria'] for x in v['items']})}, ensure_ascii=False))")
    assert set(out["mias"]) <= set(out["cats"]), out


def test_el_umbral_es_el_del_libro_del_dueno():
    """Un solo número para «costo viejo» en todo el producto."""
    out = _en_demo(
        "import json; from core import mostrador, quality;"
        "print(json.dumps([mostrador.costos_viejos('es')['umbral_dias'],"
        " quality.UMBRAL_COSTO_VIEJO_DIAS]))")
    assert out[0] == out[1]


def test_el_recargo_actual_sale_de_los_dos_numeros_reales():
    """No es una estimación: es pvp contra el costo con el que se calculó."""
    r = _en_demo(VIEJOS)
    for x in r["items"]:
        if x["costo_neto"] and x["pvp"]:
            esperado = round((x["pvp"] / x["costo_neto"] - 1) * 100, 1)
            assert x["recargo_actual_pct"] == esperado, x


def test_la_fiambreria_trae_sus_dos_presentaciones():
    """La misma horma feteada deja ~80% y entera ~30%. Elegir una sería decidir
    por ella cuál de las dos es — y ahí está la diferencia de margen más grande
    del mostrador."""
    r = _en_demo(VIEJOS)
    jamon = next(x for x in r["items"] if "JAMON COCIDO GUARANI" in x["producto"])
    pres = {g["presentacion"] for g in jamon["grupos"]}
    assert pres == {"feteado", "pieza entera"}, jamon["grupos"]


def test_no_hay_ningun_total():
    """The Counting Rule. Sumar el inmovilizado de estas filas daría un número
    que parece plata en juego y no lo es."""
    r = _en_demo(VIEJOS)
    assert set(r) == {"disponible", "umbral_dias", "items"}
    for clave in ("total", "impacto", "inmovilizado", "plata"):
        assert clave not in r

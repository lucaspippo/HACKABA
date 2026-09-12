"""Dos lotes del mismo producto no pueden vender las mismas unidades.

`ritmo` (unidades de 12 meses / 365) es del PRODUCTO. `en_riesgo` lo aplicaba
lote por lote, así que dos lotes del mismo producto venciendo en la misma
ventana se repartían la misma venta dos veces: cada uno creía que él solo se
llevaba toda la demanda. El segundo salía con sobrante cero y desaparecía del
listado, y la plata en riesgo se informaba a la mitad.

POR QUÉ NADIE LO VIO: en el dataset del demo eso no pasa — los 8 lotes que
vencen dentro de 30 días son de 8 productos distintos. Un número mal que el
dataset no puede mostrar es peor que uno latente, porque ninguna corrida lo
delata. Por eso el escenario se siembra acá, en el test, y no en `data-demo/`:
tocar el dataset movería los canónicos que media suite fija, y el defecto es de
aritmética, no del demo. El último test de este archivo vigila el supuesto —
el día que el demo tenga dos lotes de un producto, avisa.

La unidad de esta cuenta es el producto, no la fila del depósito
(PRODUCT.md · The Counting Rule).
"""
from __future__ import annotations

import datetime
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

COSTO = 1_000.0        # $ por unidad
RITMO = 10.0           # unidades por día → 3650 en 12 meses


def _en_demo(codigo: str):
    r = subprocess.run([sys.executable, "-c", codigo], cwd=BACKEND, env=ENV,
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert r.returncode == 0, r.stderr[-900:]
    return json.loads(r.stdout.strip().splitlines()[-1])


@pytest.fixture
def deposito_con(monkeypatch):
    """Siembra lotes y el ritmo de venta, sin tocar el dataset ni la base."""
    from core import analisis, deposito, store, vencimientos

    def montar(lotes, ritmo=RITMO, decididos=None):
        filas = [{"codigo": 1, "producto": "PRODUCTO DE PRUEBA",
                  "ubicacion": "Pasillo 1 - Rack A", "lote": nombre,
                  "vencimiento": (datetime.date(2026, 7, 7)
                                  + datetime.timedelta(days=dias)).isoformat(),
                  "cantidad": cant, "dias_restantes": dias}
                 for nombre, cant, dias in lotes]
        monkeypatch.setattr(deposito, "hay_datos", lambda: True)
        monkeypatch.setattr(deposito, "vencimientos", lambda dias=30: list(filas))
        monkeypatch.setattr(deposito, "vencidos", lambda: [])
        monkeypatch.setattr(store, "raw_actual", lambda: [
            {"codigo": 1, "descripcion": "PRODUCTO DE PRUEBA", "costo_iva": COSTO,
             "estado": "activo", "venta_x_peso": False}])
        monkeypatch.setattr(analisis, "_unidades_por_codigo",
                            lambda dias=365: {1: ritmo * 365})
        monkeypatch.setattr(vencimientos, "_load", lambda: dict(decididos or {}))
        return vencimientos.en_riesgo(30)

    return montar


def test_dos_lotes_del_mismo_producto_no_pueden_vender_las_mismas_unidades(deposito_con):
    """EL TEST QUE EXPONE EL DEFECTO.

    100 unidades venciendo en 5 días y otras 100 en 10, vendiendo 10 por día.
    Hasta el día 10 se venden 100 en total, no 100 + 100: el lote que vence
    primero se lleva 50 y al segundo le quedan 50 de demanda, no 100.

    Antes del arreglo el segundo lote salía con sobrante 0 y no aparecía, y el
    total era $50.000 — la mitad del riesgo real, sin que nada lo dijera.
    """
    r = deposito_con([("L-A", 100, 5), ("L-B", 100, 10)])
    assert r["lotes_en_riesgo"] == 2, "el segundo lote se está vendiendo dos veces"
    assert r["total_en_riesgo"] == 100_000.0
    por_lote = {i["lote"]: i for i in r["items"]}
    assert por_lote["L-A"]["sobrante"] == 50.0
    assert por_lote["L-B"]["sobrante"] == 50.0


def test_el_que_vence_primero_se_lleva_la_venta_primero(deposito_con):
    """FEFO, y en el orden del depósito: el que se va a tirar antes vende antes.
    Al revés (el más lejano primero) el urgente quedaría sin demanda y el
    listado ordenaría mal la única decisión que importa."""
    r = deposito_con([("L-LEJOS", 40, 10), ("L-URGENTE", 40, 2)])
    por_lote = {i["lote"]: i for i in r["items"]}
    # el urgente vende sus 20 (10/día × 2 días) y le sobran 20
    assert por_lote["L-URGENTE"]["vendible_antes"] == 20.0
    assert por_lote["L-URGENTE"]["sobrante"] == 20.0
    # al lejano le quedan 100 − 20 = 80 de demanda: se vende entero y no aparece
    assert "L-LEJOS" not in por_lote


def test_la_demanda_repartida_nunca_supera_la_del_producto(deposito_con):
    """La propiedad, no el caso: la suma de lo vendible entre los lotes no
    puede pasar lo que el producto vende en la ventana más larga."""
    r = deposito_con([("L-1", 60, 3), ("L-2", 60, 6), ("L-3", 60, 9)])
    vendible = sum(i["vendible_antes"] for i in r["items"])
    assert vendible <= RITMO * 9 + 0.05, vendible


def test_un_solo_lote_por_producto_da_exactamente_lo_de_antes(deposito_con):
    """La red del arreglo: con un lote por producto —que es TODO el dataset del
    demo— la cuenta es la de siempre. Sin esto, los canónicos se moverían y el
    arreglo dejaría de ser un arreglo."""
    r = deposito_con([("L-UNICO", 100, 4)])
    i = r["items"][0]
    assert i["vendible_antes"] == 40.0          # 10/día × 4 días
    assert i["sobrante"] == 60.0
    assert i["plata_en_riesgo"] == 60_000.0
    assert r["total_en_riesgo"] == 60_000.0


def test_un_producto_sin_ritmo_no_se_salva_por_el_reparto(deposito_con):
    """Sin ventas en 12 meses no hay demanda que repartir: los dos lotes están
    enteros en riesgo, y el contador de «sin ritmo» los ve a los dos."""
    r = deposito_con([("L-A", 30, 5), ("L-B", 30, 9)], ritmo=0.0)
    assert r["lotes_en_riesgo"] == 2
    assert r["sin_ritmo"] == 2
    assert r["total_en_riesgo"] == 60_000.0


def test_un_lote_ya_decidido_igual_consume_demanda(deposito_con):
    """Si el dueño mandó el primer lote a los locales, esa mercadería se sigue
    vendiendo. Sacarlo del reparto le regalaría esas ventas al siguiente y
    volvería a bajar el riesgo por la puerta de atrás."""
    r = deposito_con([("L-A", 100, 5), ("L-B", 100, 10)],
                     decididos={"1|L-A": {"codigo": 1, "lote": "L-A",
                                          "tipo": "locales", "actor": "aldo"}})
    assert [g["lote"] for g in r["gestionados"]] == ["L-A"]
    por_lote = {i["lote"]: i for i in r["items"]}
    assert "L-A" not in por_lote                  # decidido: fuera del listado
    assert por_lote["L-B"]["sobrante"] == 50.0    # pero su demanda ya no está


# --- el supuesto que hace invisible al defecto ---------------------------------

def test_el_demo_no_tiene_dos_lotes_del_mismo_producto_en_la_ventana():
    """Vigila POR QUÉ esto no se veía. El día que el dataset tenga dos lotes de
    un producto venciendo juntos, este test falla y avisa que el escenario ya
    no es hipotético — y que los canónicos de vencimientos se movieron por una
    razón buena."""
    out = _en_demo(
        "import json, collections; from core import deposito;"
        "c = collections.Counter(f['codigo'] for f in deposito.vencimientos(30));"
        "print(json.dumps({'lotes': sum(c.values()), 'productos': len(c),"
        " 'repetidos': [k for k, v in c.items() if v > 1]}))")
    assert out["repetidos"] == [], out
    assert out["lotes"] == out["productos"]

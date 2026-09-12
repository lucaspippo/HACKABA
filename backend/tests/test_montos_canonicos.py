"""Los montos salen del backend; la pantalla los renderiza.

La segunda mitad de The Counting Rule (PRODUCT.md). El «$900M» no salió de una
fórmula mal escrita: salió de que la misma suma existía en dos lugares y sólo
uno era el canónico. `oportunidades_neg.recuperable()` se creó justamente para
eso, y su docstring dice «la suma vive acá y las dos pantallas leen de la misma
función» — pero `/api/oportunidades` nunca la mandó, así que el mapa se la
seguía haciendo con un `reduce`. Daba igual por casualidad: mismo filtro, mismos
ítems. Dos sumas del mismo número terminan divergiendo.

Lo que se protege acá:

  1. El endpoint MANDA el total, y es exactamente el canónico.
  2. El total se calcula DESPUÉS del recorte por rol: cada uno ve el total de
     lo que le corresponde ver, no el de la empresa.
  3. La exposición NO tiene total, a propósito. Mientras el campo no exista,
     nadie lo suma sin darse cuenta.
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


def test_el_total_recuperable_es_el_canonico_y_no_una_suma_de_la_pantalla():
    """Si el endpoint no lo manda, la pantalla lo suma sola. Ésa es la puerta."""
    out = _en_demo(
        "import json; from core import oportunidades_neg as opn;"
        "cards = opn.cards('es');"
        "rec = opn.recuperable(cards_=cards, lang='es');"
        "propio = round(sum(c['monto'] or 0 for c in cards"
        "                   if c.get('naturaleza') == 'recuperable'), 2);"
        "print(json.dumps({'canonico': rec['total'], 'a_mano': propio,"
        " 'componentes': len(rec['componentes'])}))")
    assert out["canonico"] == out["a_mano"]
    assert out["componentes"] > 0
    assert out["canonico"] > 0


def test_cada_rol_ve_el_total_de_lo_que_le_toca():
    """El recorte va ANTES de la suma. Al de depósito no le corresponde saber
    cuánto hay para cobrar, así que tampoco puede aparecer en su total."""
    out = _en_demo(
        "import json; from core import oportunidades_neg as opn;"
        "todas = opn.cards('es');"
        "dueno = opn.visibles_para(todas, ['inventario','cuentas','deposito',"
        "   'oportunidades','finanzas','caja','evolucion','alertas','logistica']);"
        "deposito = opn.visibles_para(todas, ['deposito','alertas']);"
        "print(json.dumps({'dueno': opn.recuperable(cards_=dueno)['total'],"
        " 'deposito': opn.recuperable(cards_=deposito)['total']}))")
    assert out["dueno"] > out["deposito"], out


def test_la_exposicion_se_lista_y_no_se_suma():
    """La concentración de clientes y la deuda que sale en un camión comparten
    clientes: un total sería el mismo peso dos veces. Que no exista el campo es
    lo que impide que alguien lo sume distraído."""
    out = _en_demo(
        "import json; from core import oportunidades_neg as opn;"
        "e = opn.exposicion(cards_=opn.cards('es'), lang='es');"
        "print(json.dumps(e, ensure_ascii=False))")
    assert "total" not in out, "la exposición no puede tener un total"
    assert out["disponible"] is True
    assert out["componentes"], out
    for c in out["componentes"]:
        assert c["monto"] and c["monto_fmt"] and c["titulo"]
    montos = [c["monto"] for c in out["componentes"]]
    assert montos == sorted(montos, reverse=True)


def test_lo_recuperable_y_la_exposicion_no_se_pisan():
    """Una tarjeta está de un lado o del otro, nunca en los dos: si se pisaran,
    el titular sumaría plata que además se muestra como riesgo."""
    out = _en_demo(
        "import json; from core import oportunidades_neg as opn;"
        "cards = opn.cards('es');"
        "rec = {c['id'] for c in opn.recuperable(cards_=cards)['componentes']};"
        "exp = {c['id'] for c in opn.exposicion(cards_=cards)['componentes']};"
        "print(json.dumps({'cruce': sorted(rec & exp)}))")
    assert out["cruce"] == []


def test_las_cuentas_mandan_su_total_calculado():
    """`cuentas.totales()` existe desde P11·B12 y su docstring dice por qué.
    Faltaba mandarlo, y la pantalla se sumaba los saldos sola."""
    out = _en_demo(
        "import json; from core import cuentas;"
        "t = cuentas.totales();"
        "propio = round(sum(c['saldo'] for c in cuentas.listar()), 2);"
        "print(json.dumps({'canonico': t['total_adeudado'], 'a_mano': propio}))")
    assert out["canonico"] == out["a_mano"]
    assert out["canonico"] > 0

"""C2 · quién está parado frente a quién.

El ERP sabe cuánto debe cada cliente, qué se vence y —si alguien lo cargó— lo
que el equipo contó. Lo que no sabe nadie es que Walter va a estar en la puerta
de Doña Elsa mañana, y ésa es la pregunta que junta tres consultas sueltas en
una decisión.

Lo que se protege:

  1. Los DOS plazos. La regla de la casa ("a Doña Elsa tolerale 45 días") tiene
     que viajar con la deuda: sin ella el número miente dos veces — marca en
     falso a quien tiene permiso, y no marca a quien lo pasó.
  2. Las notas son de CUALQUIER autor. El punto entero es que lo que escuchó
     Walter le llegue a quien va mañana.
  3. Los montos se CITAN, no se suman: `plata_en_riesgo` sale de
     `vencimientos` tal cual, y acá no hay ningún total (PRODUCT.md, The
     Counting Rule — la suma por camión ya existe y es canónica).
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


DONA_ELSA = ("import json; from core import parada;"
             "print(json.dumps(parada.de('Despensa Doña Elsa', 'es'), ensure_ascii=False))")


def test_la_deuda_llega_con_los_dos_plazos():
    """El del sistema y el de la casa. Doña Elsa está 66 días con 30 de plazo,
    pero el dueño le tolera 45: el exceso que importa es 21, no 36."""
    d = _en_demo(DONA_ELSA)["deuda"]
    assert d["saldo"] == 19_200_000
    assert d["dias_sin_pagar"] == 66
    assert d["plazo_dias"] == 30            # el del sistema
    assert d["tolerancia_dias"] == 45       # el de la casa
    assert d["exceso_tolerancia"] == 21     # 66 − 45, y no 66 − 30
    assert d["conocimiento"], "la regla que lo explica tiene que venir con el número"


def test_lo_que_dijo_uno_le_llega_al_que_va():
    """Walter escuchó que Doña Elsa se pone al día y hoy eso se muere ahí.
    Lucía anotó que pidió una entrega chica. Las dos le sirven al que toca el
    timbre, y las dos son de OTRA persona."""
    dijeron = _en_demo(DONA_ELSA)["dijeron"]
    autores = {n["autor"] for n in dijeron}
    assert {"walter", "lucia"} <= autores, autores
    # se muestra con nombre: un aviso sin autor no se puede preguntar ni desmentir
    assert all(n["autor_nombre"] and n["autor_nombre"][0].isupper() for n in dijeron)
    # de la más nueva a la más vieja: la última noticia manda
    assert [n["fecha"] for n in dijeron] == sorted(
        (n["fecha"] for n in dijeron), reverse=True)


def test_lo_que_se_vence_y_este_cliente_compra():
    v = _en_demo(DONA_ELSA)["vence_y_compra"]
    assert len(v) == 2, [x["producto"] for x in v]
    assert {"SALAME MILAN MONTE CHICO (PLANCHA)",
            "JAMON COCIDO EL PARANA (HORMA)"} == {x["producto"] for x in v}
    # ordenado por urgencia: lo que se vence antes va primero
    assert [x["dias_restantes"] for x in v] == sorted(x["dias_restantes"] for x in v)
    for x in v:
        assert x["le_compro"]["cantidad"] > 0, x
        assert x["plata_en_riesgo"] > 0


def test_la_plata_en_riesgo_es_la_de_vencimientos_y_no_una_cuenta_nueva():
    """The Counting Rule: el número canónico se cita, no se recalcula."""
    out = _en_demo(
        "import json; from core import parada, vencimientos;"
        "v = {i['codigo']: i['plata_en_riesgo'] for i in vencimientos.en_riesgo(30)['items']};"
        "p = parada.de('Despensa Doña Elsa', 'es')['vence_y_compra'];"
        "print(json.dumps([[x['plata_en_riesgo'], v.get(x['codigo'])] for x in p]))")
    for mio, canonico in out:
        assert mio == canonico


def test_la_parada_no_inventa_un_total():
    """La suma de deuda por camión ya existe y es canónica
    (`cobranza.exposicion_en_ruta`, deduplicada por cliente). Un segundo total
    calculado en otro lado sobre las mismas filas es exactamente cómo nacieron
    los dos dobles conteos que este repo ya pagó."""
    p = _en_demo(DONA_ELSA)
    assert set(p) == {"cliente", "deuda", "dijeron", "vence_y_compra"}
    for clave in ("total", "expuesto", "suma"):
        assert clave not in p


def test_un_cliente_sin_nada_no_inventa_nada():
    """Proveeduría La Rural no debe un peso. La parada tiene que decirlo así,
    no rellenar con un cero disfrazado de dato."""
    out = _en_demo(
        "import json; from core import parada;"
        "print(json.dumps(parada.de('Proveeduría La Rural', 'es'), ensure_ascii=False))")
    assert out["deuda"]["saldo"] == 0
    assert out["deuda"]["en_mora"] is False
    assert out["deuda"]["exceso_tolerancia"] is None


def test_un_cliente_que_no_existe_no_rompe_la_pantalla():
    out = _en_demo(
        "import json; from core import parada;"
        "print(json.dumps(parada.de('Kiosco Que No Existe', 'es'), ensure_ascii=False))")
    assert out["deuda"] is None
    assert out["dijeron"] == [] and out["vence_y_compra"] == []


def test_las_paradas_de_cada_uno_salen_por_su_nombre():
    """El chofer pide 'Walter' y no tiene que saber cómo se escribe su camión
    en el export del TMS."""
    out = _en_demo(
        "import json; from core import parada;"
        "print(json.dumps({'walter': parada.proximas('Walter'),"
        " 'todas': len(parada.proximas())}, ensure_ascii=False))")
    assert out["walter"], "Walter tiene paradas en el dataset"
    assert all("Walter" in p["transporte"] for p in out["walter"])
    assert out["todas"] > len(out["walter"])
    # ninguna entregada: una parada ya hecha no se puede reasignar ni instruir
    assert all(p["estado"] != "entregado" for p in out["walter"])

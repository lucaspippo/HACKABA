"""
P45 · El mismo concepto muestra el mismo número en todas las pantallas.

Dos incoherencias que el modelo real hizo visibles (ninguna la causó un cambio;
Sonnet 4.6 elegía siempre la misma herramienta y las tapaba):

  T1 · "plata parada" tenía DOS valores. El Home y el mapa sumaban todo el
       catálogo ($444.681.833); la rotación sumaba sólo lo clasificable
       ($444.411.436). La diferencia eran, exactos, los 3 productos fantasma.
  T2 · el mapa mostraba "$156,3M de capital recuperable" y Ángela no tenía
       ninguna herramienta para llegar a ese número.

Igual que P27/P38, todo lo que necesita datos corre en el DEMO por subproceso:
el piloto arranca sin ventas validadas, así que ahí `rotacion` no está
disponible y una prueba de coherencia se saltearía siempre — y una prueba que
nunca corre no protege nada. Lo que sí vale en cualquier tenant (que la tool
exista y esté gateada) se prueba en el proceso de la suite.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from core import oportunidades_neg as opn


def _en_demo(expr: str):
    """Evalúa una expresión en el tenant DEMO y devuelve su JSON."""
    backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_demo = os.path.join(os.path.dirname(backend), "data-demo")
    env = {**os.environ, "POLPILOT_TENANT": "demo", "POLPILOT_DATA_DIR": data_demo,
           "POLPILOT_DEMO_TODAY": "2026-07-07", "PYTHONIOENCODING": "utf-8"}
    env.pop("ANTHROPIC_API_KEY", None)
    r = subprocess.run([sys.executable, "-c", f"import json; print(json.dumps({expr}))"],
                       cwd=backend, env=env, capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr[-800:]
    return json.loads(r.stdout.strip().splitlines()[-1])


# --- T1 · una sola plata parada (propiedad: se prueba donde hay datos) ---------

def _rot_demo():
    """El paquete que necesitan las pruebas de propiedad, del tenant con datos.
    En el piloto `rotacion` no está disponible (sin ventas validadas), así que
    probar la propiedad ahí sería saltearla siempre — y una prueba que nunca
    corre no protege nada."""
    return _en_demo(
        "(lambda s, a: {"
        " 'store': round(sum(x.get('inmovilizado') or 0 for x in s.raw_actual()), 2),"
        " 'rot': a.rotacion('es'),"
        " 'anulados': [x['inmovilizado'] for x in s.raw_actual()"
        "              if x.get('estado') != 'activo' and (x.get('inmovilizado') or 0) > 0],"
        "})(__import__('core.store', fromlist=['x']),"
        "   __import__('core.analisis', fromlist=['x']))")


def test_la_plata_parada_es_un_solo_numero():
    """El del Home/mapa y el de rotación son el MISMO, al centavo. Si alguien
    vuelve a cambiar el universo de uno de los dos, esto lo caza."""
    d = _rot_demo()
    assert d["rot"]["inmovilizado_total"] == d["store"]


def test_los_estados_de_rotacion_cierran_el_total():
    """sano + atención + dormido + sin_clasificar = la plata parada. Sin resta
    invisible: lo que no se puede clasificar se ve, no desaparece."""
    d = _rot_demo()
    assert round(sum(d["rot"]["por_estado"].values()), 2) == d["rot"]["inmovilizado_total"]


def test_lo_no_clasificable_son_los_anulados_con_stock():
    """El monto que la rotación no puede medir tiene nombre y motivo — es el
    hallazgo de productos fantasma, no un residuo sin explicar."""
    d = _rot_demo()
    sc = d["rot"]["sin_clasificar"]
    assert sc["productos"] == len(d["anulados"])
    assert sc["monto"] == round(sum(d["anulados"]), 2)
    assert sc["motivo"] and not sc["motivo"].startswith("core.")


# --- T1 · los canónicos del demo -----------------------------------------------

def test_demo_los_dos_totales_coinciden_y_el_dormido_no_se_movio():
    """La unificación cambió el denominador de pct_dormido. Los canónicos que
    dependen de él (el 15,5% de objetivos medidos, el $68.927.214 del mapa)
    tienen que quedar exactamente igual."""
    d = _en_demo(
        "(lambda s, a, i: {"
        " 'store': round(sum(x.get('inmovilizado') or 0 for x in s.raw_actual()), 2),"
        " 'rot': a.rotacion('es')['inmovilizado_total'],"
        " 'dormido_fmt': i.pesos(a.rotacion('es')['por_estado']['dormido'], 'es'),"
        " 'pct': a.rotacion('es')['pct_dormido'],"
        " 'kpi_pct': a.completo('es')['kpis']['dormido']['pct'],"
        " 'fantasmas': a.rotacion('es')['sin_clasificar']['productos'],"
        "})(__import__('core.store', fromlist=['x']),"
        "   __import__('core.analisis', fromlist=['x']),"
        "   __import__('i18n'))")
    assert d["store"] == d["rot"] == 444681833.42
    assert d["dormido_fmt"] == "$68.927.214"
    assert d["pct"] == 15.5 and d["kpi_pct"] == 15.5
    assert d["fantasmas"] == 3


# --- T2 · el capital recuperable ------------------------------------------------

def test_demo_el_capital_recuperable_es_el_del_guion():
    r = _en_demo("__import__('core.oportunidades_neg', fromlist=['x']).recuperable(lang='es')")
    assert round(r["total"]) == 156_324_231
    assert r["total_fmt"] == "$156.324.231"
    assert {c["id"] for c in r["componentes"]} == {
        "cobrar_morosos", "despertar_dormido", "ventana_compra"}
    assert round(sum(c["monto"] for c in r["componentes"]), 2) == r["total"]


def test_demo_la_exposicion_jamas_entra_en_la_suma():
    """Los $470,8M son riesgo, no plata a cobrar: quedan afuera con su motivo.
    Es la regla que evitó el «$900M» de doble conteo."""
    r = _en_demo("__import__('core.oportunidades_neg', fromlist=['x']).recuperable(lang='es')")
    fuera = {c["id"] for c in r["excluidos"]}
    assert "concentracion" in fuera and "sobrecompra" in fuera
    assert "concentracion" not in {c["id"] for c in r["componentes"]}


def test_demo_angela_tiene_como_llegar_al_recuperable():
    """El agujero de T2: el número existía en el mapa y Ángela no podía citarlo.
    Además lo recibe YA FORMATEADO — no le queda nada que redondear."""
    r = _en_demo("__import__('angela')._run_tool('capital_recuperable', {})[0]")
    assert round(r["total"]) == 156_324_231
    assert r["total_fmt"] == "$156.324.231"


def test_la_tool_del_recuperable_existe_y_esta_gateada():
    import angela
    assert any(t["name"] == "capital_recuperable" for t in angela.TOOLS)
    # es lectura de negocio: sólo la ve quien tiene el módulo (misma matriz)
    assert angela.TOOL_FEATURE["capital_recuperable"] == "oportunidades"


def test_el_recuperable_no_depende_de_quien_pregunte():
    """El filtro por rol recorta lo que se MUESTRA, no lo que se suma: el total
    del negocio es uno solo (y sólo lo ve quien tiene el módulo)."""
    todas = opn.cards("es")
    if not todas:
        pytest.skip("sin datos en este tenant")
    import auth
    del_dueno = opn.visibles_para(todas, auth.USUARIOS["emilio"]["features"])
    assert opn.recuperable(del_dueno, "es")["total"] == opn.recuperable(todas, "es")["total"]

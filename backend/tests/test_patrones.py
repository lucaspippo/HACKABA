"""core/patrones.py — aprendizaje continuo: combos no percibidos y faltantes
de caja con patrón por día de semana.

Synthetic tests (this file) exercise the thresholds precisely with
constructed fixtures — no demo dataset needed, same pattern as
test_priorities.py. The canonical numbers on the DEMO dataset (the injected
yerba/azúcar combo, the Saturday shortfall) run in a subprocess, same
pattern as test_p38 / test_cruces.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from core import patrones


def _pedido(cliente_id, fecha, items):
    return {"cliente_id": cliente_id, "cliente": cliente_id, "fecha": fecha,
            "monto": sum(it["monto"] for it in items), "items": items}


def _item(codigo, producto, monto=1000.0):
    return {"codigo": codigo, "producto": producto, "categoria": "test",
            "cantidad": 1, "precio": monto, "monto": monto}


# --- sin dato, no hay card --------------------------------------------------

def test_piloto_sin_pedidos_ni_caja_no_ve_nada():
    """El piloto no tiene ventas_por_cliente.json ni historial de caja largo:
    ninguna de las dos cards se fuerza sin el soporte mínimo."""
    assert patrones.cards("es") == []


# --- 1 · combos no percibidos ------------------------------------------------

def _pedidos_combo(n_con_ambos, n_solo_ancla, n_solo_pareja=0, n_clientes=4):
    """`n_con_ambos` pedidos con A(yerba)+B(azúcar), `n_solo_ancla` con A pero
    sin B (el hueco), `n_solo_pareja` con B pero sin A (para que B siga siendo
    MÁS frecuente que A — el algoritmo ancla en el menos frecuente, igual que
    en el demo real: yerba es la rara, azúcar la de siempre). Más ruido de
    relleno (productos sin relación) para que el lift tenga contra qué
    compararse: a más población total, más raro es que A y B se crucen por
    azar, así que el relleno deja el lift cómodo sobre MIN_LIFT."""
    pedidos = []
    for i in range(n_con_ambos):
        cliente = f"cliente_{i % n_clientes}"
        items = [_item(1, "YERBA X", 2000.0), _item(2, "AZUCAR X", 1500.0)]
        pedidos.append(_pedido(cliente, f"2026-0{1 + i % 6}-01", items))
    for i in range(n_solo_ancla):
        cliente = f"cliente_falta_{i}"
        pedidos.append(_pedido(cliente, f"2026-0{1 + i % 6}-15",
                               [_item(1, "YERBA X", 2000.0)]))
    for i in range(n_solo_pareja):
        pedidos.append(_pedido(f"cliente_solo_azucar_{i}", "2026-01-20",
                               [_item(2, "AZUCAR X", 1500.0)]))
    total = n_con_ambos + n_solo_ancla + n_solo_pareja
    relleno = max(patrones.MIN_PEDIDOS_TOTAL, int(patrones.MIN_LIFT * total * 3))
    for i in range(relleno):
        pedidos.append(_pedido(f"ruido_{i}", "2026-01-01",
                               [_item(100 + i, f"RELLENO {i}", 500.0)]))
    return pedidos


def test_combo_no_percibido_mide_el_hueco_cuando_existe(monkeypatch):
    from core import ventas_cliente
    pedidos = _pedidos_combo(n_con_ambos=8, n_solo_ancla=2, n_solo_pareja=3)
    monkeypatch.setattr(ventas_cliente, "todos_los_pedidos", lambda: pedidos)
    c = next(x for x in patrones.cards("es") if x["id"] == "combo_no_percibido")
    assert c["datos"]["producto_ancla"] == "YERBA X"   # la menos frecuente: 10 < 11
    assert c["datos"]["producto_pareja"] == "AZUCAR X"
    assert c["datos"]["attach_pct"] == 80          # 8 de 10
    assert c["datos"]["pedidos_sin_pareja"] == 2
    # el hueco es plata dejada arriba del mostrador: 2 pedidos * $1500 el par
    assert c["monto"] == 3000.0
    assert c["monto_label"] == "venta cruzada sin aprovechar"
    assert c["naturaleza"] == "accionable"
    assert "YERBA X" in c["titulo"] and "AZUCAR X" in c["titulo"]


def test_combo_no_percibido_sin_hueco_mide_lo_ya_facturado(monkeypatch):
    from core import ventas_cliente
    pedidos = _pedidos_combo(n_con_ambos=6, n_solo_ancla=0)
    monkeypatch.setattr(ventas_cliente, "todos_los_pedidos", lambda: pedidos)
    c = next(x for x in patrones.cards("es") if x["id"] == "combo_no_percibido")
    assert c["datos"]["attach_pct"] == 100
    assert c["datos"]["pedidos_sin_pareja"] == 0
    # sin hueco: el monto es la facturación conjunta YA detectada, no una pérdida
    assert c["monto"] == round(6 * (2000.0 + 1500.0), 2)
    assert c["monto_label"] == "facturación conjunta ya detectada"


def test_combo_no_percibido_no_se_fuerza_con_poco_soporte(monkeypatch):
    """Dos clientes nomás, o muy pocas coincidencias: no alcanza para
    afirmar un patrón — la card no existe."""
    from core import ventas_cliente
    pedidos = _pedidos_combo(n_con_ambos=2, n_solo_ancla=0, n_clientes=1)
    monkeypatch.setattr(ventas_cliente, "todos_los_pedidos", lambda: pedidos)
    ids = [c["id"] for c in patrones.cards("es")]
    assert "combo_no_percibido" not in ids


def test_combo_no_percibido_ignora_pares_sin_lift(monkeypatch):
    """Dos productos populares que aparecen juntos seguido sólo porque ambos
    son populares (lift bajo) no cuentan como combo."""
    from core import ventas_cliente
    pedidos = []
    # A y B aparecen cada uno en la MITAD de los pedidos, independientes entre
    # sí (alternados) — se cruzan poco más de lo que el azar ya explicaría.
    for i in range(60):
        items = [_item(1, "POPULAR A", 1000.0)] if i % 2 == 0 else []
        items += [_item(2, "POPULAR B", 1000.0)] if i % 2 == 1 else []
        items += [_item(3 + i, f"RELLENO {i}", 200.0)]
        pedidos.append(_pedido(f"cliente_{i % 5}", "2026-01-01", items))
    monkeypatch.setattr(ventas_cliente, "todos_los_pedidos", lambda: pedidos)
    ids = [c["id"] for c in patrones.cards("es")]
    assert "combo_no_percibido" not in ids


# --- 2 · faltantes de caja con patrón por día de semana -----------------------

def _historial_caja(dias_normales=30, sabados_con_faltante=6, sabados_ok=2):
    """Lunes a viernes: sin faltante. Sábados: la mayoría con faltante grande.
    Fechas ancladas a semanas reales (2026 empieza en jueves)."""
    import datetime
    hist = []
    base = datetime.date(2026, 1, 5)  # un lunes
    semana = 0
    while len([d for d in hist if datetime.date.fromisoformat(d["fecha"]).weekday() < 5]) < dias_normales:
        lunes = base + datetime.timedelta(weeks=semana)
        for wd in range(5):  # lunes a viernes: sanos
            hist.append({"fecha": (lunes + datetime.timedelta(days=wd)).isoformat(),
                        "total": 100000, "diferencia": 0})
        semana += 1
    sabado = base + datetime.timedelta(days=5)
    for i in range(sabados_con_faltante):
        hist.append({"fecha": (sabado + datetime.timedelta(weeks=i)).isoformat(),
                    "total": 100000, "diferencia": -4000})
    for i in range(sabados_ok):
        hist.append({"fecha": (sabado + datetime.timedelta(weeks=sabados_con_faltante + i)).isoformat(),
                    "total": 100000, "diferencia": 0})
    return hist


def test_faltante_caja_encuentra_el_dia_senalado(monkeypatch):
    from core import caja
    hist = _historial_caja()
    monkeypatch.setattr(caja, "historial", lambda: hist)
    c = next(x for x in patrones.cards("es") if x["id"] == "faltante_caja_patron")
    assert c["datos"]["dia_semana"] == 5           # sábado
    assert c["datos"]["dia_nombre"] == "sábado"
    assert c["datos"]["pct_faltante_resto"] == 0   # lunes a viernes, sanos
    assert c["monto"] == 6 * 4000.0
    assert c["naturaleza"] == "riesgo"


def test_faltante_caja_no_se_fuerza_si_es_parejo(monkeypatch):
    """Faltantes repartidos por igual entre todos los días: no hay UN día que
    se destaque — no hay patrón que señalar."""
    from core import caja
    import datetime
    hist = []
    base = datetime.date(2026, 1, 5)
    for i in range(35):
        dif = -1000 if i % 3 == 0 else 0
        hist.append({"fecha": (base + datetime.timedelta(days=i)).isoformat(),
                    "total": 100000, "diferencia": dif})
    monkeypatch.setattr(caja, "historial", lambda: hist)
    ids = [c["id"] for c in patrones.cards("es")]
    assert "faltante_caja_patron" not in ids


def test_faltante_caja_no_se_fuerza_con_poco_historial(monkeypatch):
    from core import caja
    hist = _historial_caja(dias_normales=5, sabados_con_faltante=2, sabados_ok=0)
    monkeypatch.setattr(caja, "historial", lambda: hist)
    ids = [c["id"] for c in patrones.cards("es")]
    assert "faltante_caja_patron" not in ids


# --- bilingüe, como todo lo que llega a un humano -----------------------------

def test_todo_lo_nuevo_es_bilingue(monkeypatch):
    from core import ventas_cliente, caja
    monkeypatch.setattr(ventas_cliente, "todos_los_pedidos",
                        lambda: _pedidos_combo(n_con_ambos=8, n_solo_ancla=2))
    monkeypatch.setattr(caja, "historial", lambda: _historial_caja())
    es = {c["id"]: c for c in patrones.cards("es")}
    en = {c["id"]: c for c in patrones.cards("en")}
    assert set(es) == set(en) == {"combo_no_percibido", "faltante_caja_patron"}
    for cid in es:
        assert es[cid]["titulo"] != en[cid]["titulo"], cid
        assert es[cid]["resumen"] != en[cid]["resumen"], cid
        assert es[cid]["monto"] == en[cid]["monto"], cid   # el idioma no mueve un número


# --- entran al inbox de Prioridades como una fuente más -----------------------

def test_entran_al_inbox_de_prioridades(monkeypatch):
    from core import ventas_cliente, caja, priorities
    monkeypatch.setattr(ventas_cliente, "todos_los_pedidos",
                        lambda: _pedidos_combo(n_con_ambos=8, n_solo_ancla=2))
    monkeypatch.setattr(caja, "historial", lambda: _historial_caja())
    inbox = priorities.inbox("es", features=("caja", "cuentas", "oportunidades"))
    ids_act = [i["id"] for i in inbox["act"]]
    ids_watch = [i["id"] for i in inbox["watch"]]
    assert "combo_no_percibido" in ids_act        # accionable: compite por "hacer"
    assert "faltante_caja_patron" in ids_watch    # riesgo/proceso: para mirar, no cobrar
    # y respeta el filtro por módulo: sin "caja" habilitado, esa card no se ve
    sin_caja = priorities.inbox("es", features=("cuentas", "oportunidades"))
    assert "faltante_caja_patron" not in [i["id"] for i in sin_caja["watch"]]


# --- los números del DEMO, en subproceso (mismo patrón que test_p38) ----------

def _demo(expr: str):
    backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_demo = os.path.join(os.path.dirname(backend), "data-demo")
    env = {**os.environ, "POLPILOT_TENANT": "demo", "POLPILOT_DATA_DIR": data_demo,
           "POLPILOT_DEMO_TODAY": "2026-07-07", "PYTHONIOENCODING": "utf-8"}
    env.pop("ANTHROPIC_API_KEY", None)
    r = subprocess.run(
        [sys.executable, "-c", f"import json; print(json.dumps({expr}))"],
        cwd=backend, env=env, capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_demo_encuentra_el_combo_de_yerba_y_azucar():
    cs = _demo("__import__('core.patrones', fromlist=['x']).cards('es')")
    combo = next(c for c in cs if c["id"] == "combo_no_percibido")
    assert "YERBA" in combo["datos"]["producto_ancla"]
    assert "AZUCAR" in combo["datos"]["producto_pareja"]
    assert combo["datos"]["clientes"] >= 3
    assert combo["datos"]["lift"] >= patrones.MIN_LIFT


def test_demo_encuentra_el_faltante_de_los_sabados():
    cs = _demo("__import__('core.patrones', fromlist=['x']).cards('es')")
    caja_c = next(c for c in cs if c["id"] == "faltante_caja_patron")
    assert caja_c["datos"]["dia_semana"] == 5
    assert caja_c["datos"]["pct_faltante"] > caja_c["datos"]["pct_faltante_resto"]
    assert caja_c["monto"] > 0


def test_demo_no_mueve_los_canonicos_de_oportunidades():
    """Lo nuevo suma una fuente al inbox; NO reescribe los 10 hallazgos
    cerrados de oportunidades_neg ni su recuperable (test_p27/p38)."""
    out = _demo(
        "{'n': len(__import__('core.oportunidades_neg', fromlist=['x']).cards('es')),"
        " 'recuperable': __import__('core.oportunidades_neg', fromlist=['x']).recuperable("
        "__import__('core.oportunidades_neg', fromlist=['x']).cards('es'), 'es')['total']}")
    assert out["n"] == 10
    assert round(out["recuperable"]) == 156324231

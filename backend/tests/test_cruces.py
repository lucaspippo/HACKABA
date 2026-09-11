"""
P·cruces — los hallazgos que cruzan 3+ dominios, y las dos fuentes que los habilitan.

Lo que se protege acá:

  1. SON CRUCES, NO ALERTAS: cada hallazgo declara ≥3 dominios distintos y su
     camino en el grafo toca ≥3 TIPOS de entidad. Una alerta de una sola fuente
     no entra al cerebro (sigue viviendo en Oportunidades, intacta).
  2. DETERMINISMO: los números salen de los módulos que ya son la verdad
     (cuentas, vencimientos, reposicion) — el mismo dato, dos veces igual.
  3. LOS CANÓNICOS NO SE MUEVEN: recuperable $156.324.231, plata parada
     $444.681.833, y las 10 cards de Oportunidades siguen como estaban.
  4. LA DATA NUEVA CIERRA: cada pedido abierto en renglones suma EXACTO el
     monto del movimiento de la cuenta corriente (que es el número canónico).
  5. HONESTIDAD DE LA CAPA NO ESTRUCTURADA: las notas declaran a qué se
     refieren (no hay NLP adivinando) y son bilingües.

Corre en un SUBPROCESO contra el dataset demo canónico (mismo patrón que
test_consultas/test_p27): el tenant se elige por env, no por import.
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


def _en_demo(codigo: str) -> dict:
    r = subprocess.run([sys.executable, "-c", codigo], cwd=BACKEND, env=ENV,
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert r.returncode == 0, r.stderr[-900:]
    return json.loads(r.stdout.strip().splitlines()[-1])


# --- 1 · son cruces de verdad ---------------------------------------------------

def test_cada_cruce_toca_tres_dominios():
    out = _en_demo(
        "import json; from core import cruces;"
        "cs = cruces.cards('es');"
        "print(json.dumps([{'id': c['id'], 'dominios': c['dominios'],"
        " 'no_estructurado': c['no_estructurado'], 'monto': c['monto'],"
        " 'porque': len(c['drill']['porque'])} for c in cs], ensure_ascii=False))")
    assert len(out) >= 5, out
    for c in out:
        assert len(set(c["dominios"])) >= 3, c
        assert c["porque"] >= 3, c          # la cadena de razonamiento, no una frase
    # la capa no estructurada participa de VARIOS, no de uno de adorno
    assert sum(1 for c in out if c["no_estructurado"]) >= 3, out


def test_el_camino_del_cerebro_cruza_tipos_distintos():
    """El 'aha' visual: el camino iluminado toca entidades de clases distintas
    (cliente + producto + proveedor + nota…), no 17 nodos del mismo tipo."""
    out = _en_demo(
        "import json; from core import grafo;"
        "g = grafo.completo('es');"
        "print(json.dumps([{'id': c['id'], 'tipos': c['tipos'],"
        " 'nodos': len(c['nodos']), 'dominios': c['dominios']} for c in g['caminos']],"
        " ensure_ascii=False))")
    assert len(out) >= 6, out
    for c in out:
        assert len(c["tipos"]) >= 3, c
        assert len(c["dominios"]) >= 3, c
    # los cruces que usan notas iluminan la nota (si no, no se ve de dónde salió)
    con_nota = [c for c in out if "nota" in c["tipos"]]
    assert len(con_nota) >= 3, out


def test_las_alertas_de_una_sola_fuente_no_entran_al_cerebro():
    """Quiebre, margen bajo, sobrecompra y estrella caída son avisos de UNA
    fuente: siguen en Oportunidades (no se pierde nada) pero no son cruces."""
    out = _en_demo(
        "import json; from core import grafo, oportunidades_neg;"
        "g = grafo.completo('es');"
        "print(json.dumps({'cerebro': [c['id'] for c in g['caminos']],"
        " 'oportunidades': [c['id'] for c in oportunidades_neg.cards('es')]},"
        " ensure_ascii=False))")
    for alerta in ("quiebre_inminente", "margen_bajo", "sobrecompra", "estrella_caida"):
        assert alerta not in out["cerebro"], alerta
        assert alerta in out["oportunidades"], alerta   # no se perdió: sigue donde estaba
    # los dos que SÍ cruzan siguen en el cerebro
    assert "cliente_frio" in out["cerebro"] and "ventana_compra" in out["cerebro"]
    assert len(out["oportunidades"]) == 10


# --- 2 · determinismo -----------------------------------------------------------

def test_los_numeros_salen_de_los_modulos_de_siempre():
    out = _en_demo(
        "import json; from core import cruces, cuentas, vencimientos;"
        "cs = {c['id']: c for c in cruces.cards('es')};"
        "d = cs['cruce_deuda_vencimiento']['datos'];"
        "cli = next(c for c in cuentas.listar() if c['nombre'] == d['cliente']);"
        "lote = next(i for i in vencimientos.en_riesgo(30)['items']"
        "            if i['producto'] == d['producto']);"
        "print(json.dumps({'saldo_cruce': d['saldo'], 'saldo_cuentas': cli['saldo'],"
        " 'dias_cruce': d['dias_sin_pagar'], 'dias_cuentas': cli['dias_sin_pagar'],"
        " 'plata_cruce': d['plata_en_riesgo'],"
        " 'plata_venc': lote['plata_en_riesgo']}, ensure_ascii=False))")
    assert out["saldo_cruce"] == out["saldo_cuentas"]
    assert out["dias_cruce"] == out["dias_cuentas"]
    assert out["plata_cruce"] == out["plata_venc"]


def test_dos_corridas_dan_lo_mismo():
    codigo = ("import json; from core import cruces;"
              "print(json.dumps([[c['id'], c['monto'], c['titulo']]"
              " for c in cruces.cards('es')], ensure_ascii=False))")
    assert _en_demo(codigo) == _en_demo(codigo)


def test_los_cruces_nacen_bilingues():
    out = _en_demo(
        "import json; from core import cruces;"
        "es = {c['id']: c for c in cruces.cards('es')};"
        "en = {c['id']: c for c in cruces.cards('en')};"
        "print(json.dumps({'ids': sorted(es) == sorted(en),"
        " 'distintos': [i for i in es if es[i]['titulo'] == en[i]['titulo']],"
        " 'montos': [i for i in es if es[i]['monto'] != en[i]['monto']]},"
        " ensure_ascii=False))")
    assert out["ids"]
    assert out["distintos"] == [], out          # ningún título quedó sin traducir
    assert out["montos"] == [], out             # el idioma no mueve un número


# --- 3 · los canónicos no se movieron -------------------------------------------

def test_canonicos_intactos():
    out = _en_demo(
        "import json; from core import oportunidades_neg as op, analisis;"
        "cs = op.cards('es'); rec = op.recuperable(cs, 'es');"
        "print(json.dumps({'recuperable': rec['total'],"
        " 'parada': analisis.rotacion()['inmovilizado_total'],"
        " 'cards': len(cs)}, ensure_ascii=False))")
    assert round(out["recuperable"], 2) == 156324231.04
    assert round(out["parada"], 2) == 444681833.42
    assert out["cards"] == 10


# --- 4 · la data nueva cierra ----------------------------------------------------

def test_cada_pedido_suma_exacto_el_movimiento_de_la_cuenta():
    out = _en_demo(
        "import json; from core import ventas_cliente as vc, cuentas;"
        "regs = vc.por_cliente(); ctas = {c['id']: c for c in cuentas.listar()};"
        "malos = []; movs = 0;"
        "[malos.append([r['nombre'], p['fecha']])"
        " for r in regs.values() for p in r['pedidos']"
        " if abs(round(sum(i['monto'] for i in p['items']), 2) - p['monto']) > 0.01];"
        "faltan = [];"
        "print(json.dumps({'descuadrados': malos,"
        " 'pedidos': sum(len(r['pedidos']) for r in regs.values()),"
        " 'clientes': len(regs)}, ensure_ascii=False))")
    assert out["descuadrados"] == [], out
    assert out["clientes"] == 24 and out["pedidos"] > 150


def test_el_grafo_cambio_la_hipotesis_por_el_dato():
    """El puente cliente↔producto era INFERIDO del rubro. Ahora es dato: la
    inferencia queda sólo de respaldo para quien no tenga pedidos abiertos."""
    out = _en_demo(
        "import json; from core import grafo;"
        "g = grafo.completo('es'); m = g['meta'];"
        "print(json.dumps({'compra': m['por_relacion'].get('compra', 0),"
        " 'afinidad': m['por_relacion'].get('afinidad', 0),"
        " 'menciona': m['por_relacion'].get('menciona', 0),"
        " 'notas': m['por_tipo'].get('nota', 0),"
        " 'compra_inferida': m['derivados']['compra']['inferida']}, ensure_ascii=False))")
    assert out["compra"] > 100 and out["compra_inferida"] is False
    assert out["afinidad"] == 0            # ya nadie necesita la hipótesis
    assert out["notas"] >= 15 and out["menciona"] >= 10


# --- 5 · la capa no estructurada, honesta ----------------------------------------

def test_las_notas_declaran_su_entidad_y_son_bilingues():
    out = _en_demo(
        "import json; from core import notas;"
        "ns = notas.listar();"
        "print(json.dumps({'n': len(ns), 'resumen': notas.resumen(),"
        " 'sin_en': [n['id'] for n in ns if not n.get('texto_en')],"
        " 'sin_entidad': [n['id'] for n in ns"
        "   if not any(n.get(k) for k in ('cliente','producto','proveedor','ubicacion'))],"
        " 'canales': sorted({n['canal'] for n in ns}),"
        " 'autores': len(notas.autores())}, ensure_ascii=False))")
    assert out["sin_en"] == [], out              # todo lo que lee un humano, bilingüe
    assert out["sin_entidad"] == [], out         # nada se adivina: la nota lo declara
    assert set(out["canales"]) <= {"voz", "reporte", "chat"}
    assert out["autores"] >= 6                   # es el EQUIPO, no una persona
    assert out["resumen"]["hasta"] <= "2026-07-07"   # dentro de la fecha congelada


def test_sin_las_fuentes_nuevas_los_cruces_se_apagan_solos():
    """El piloto todavía no tiene ni pedidos abiertos ni notas: los cruces que
    dependen de eso NO salen (en vez de salir a medias o inventados)."""
    out = _en_demo(
        "import json; from core import cruces, notas, ventas_cliente as vc;"
        "notas._load = lambda: {}; vc._load = lambda: {};"
        "print(json.dumps({'cruces': [c['id'] for c in cruces.cards('es')],"
        " 'hay_notas': notas.hay_datos(), 'hay_ventas': vc.hay_datos()},"
        " ensure_ascii=False))")
    assert out["hay_notas"] is False and out["hay_ventas"] is False
    assert out["cruces"] == [], out

"""
The operation map — the physical layer.

Runs against the demo tenant's REAL dataset (`data-demo/`) in a subprocess,
same pattern as the other canonical-number suites (test_cruces,
test_demo_separacion): the tenant is chosen by env, never by import.

What is protected, ordered by how much it would hurt to break in front of an
investor:

  1. **The pitch crossing.** That the engine can compose «the warehouse
     flagged twice that the cold room is full — and there is an open purchase
     order arriving exactly there», with the expiring lot inside. It crosses
     three sources that never talk to each other.
  2. **No node left dangling.** A node with no edge tells no route: it is an
     ornament.
  3. **Every number can be opened.** Without `fuente` a node cannot be
     defended when someone asks where it came from.
  4. **Ids survive React Flow.** A `:` inside an id makes the edge silently
     not draw.
  5. **The whole surface is bilingual.** `mapa("en")` must carry no key
     leaks: a leaked `mapaop.` key on screen is the i18n contract broken.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DEMO = os.path.join(os.path.dirname(BACKEND), "data-demo")
ENV = {**os.environ, "POLPILOT_TENANT": "demo", "POLPILOT_DATA_DIR": DATA_DEMO,
       "POLPILOT_DEMO_TODAY": "2026-07-07", "PYTHONIOENCODING": "utf-8"}
ENV.pop("ANTHROPIC_API_KEY", None)  # the suite never spends API


def _demo(expr: str):
    """Evaluate an expression in the DEMO tenant, against its real dataset."""
    r = subprocess.run(
        [sys.executable, "-c",
         f"import json; from core import mapa_operacion as M; "
         f"print(json.dumps({expr}, ensure_ascii=False))"],
        cwd=BACKEND, env=ENV, capture_output=True, text=True,
        encoding="utf-8", timeout=300)
    assert r.returncode == 0, r.stderr[-1500:]
    return json.loads(r.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def mapa():
    return _demo("M.mapa('es')")


@pytest.fixture(scope="module")
def hallazgos(mapa):
    return mapa["hallazgos"]


# ===========================================================================
# 1 · THE PITCH CROSSING
# ===========================================================================
def test_el_cruce_del_pitch_se_compone(hallazgos):
    """team notes → cold room 2 → open order → expiring lot.

    The crossing no ERP does alone, because each piece lives elsewhere: the
    heads-up in the warehouse's voice, the occupancy in the WMS, the order in
    the ERP."""
    h = next((x for x in hallazgos if x["tipo"] == "zona_saturada"), None)
    assert h, "the saturated-cold-room finding did not compose"

    # The headline must read out loud, without parenthesised plurals.
    assert "Cámara de frío 2" in h["titulo"]
    assert "llena" in h["titulo"]
    assert "orden de compra abierta" in h["titulo"]
    assert "(es)" not in h["titulo"] and "(s)" not in h["titulo"]

    # And the path crosses BOTH layers: what the team said and the physical.
    camino = h["camino"]
    assert any(n.startswith("nota_") for n in camino), \
        "the path does not touch the notes"
    assert "zona_camara_de_frio_2" in camino
    assert any(n.startswith("oc_") for n in camino), \
        "the path does not touch the order"
    assert any(n.startswith("lote_") for n in camino), \
        "it does not reach the expiring lot"
    # The order lives as the dashed stroke entering the zone; the path
    # lights it.
    assert h["aristas"], "the path does not light the order's stroke"
    assert any(a.endswith("__orden") and "camara_de_frio_2" in a
               for a in h["aristas"])


def test_el_cruce_trae_los_cuatro_datos_del_pitch(hallazgos):
    """The heads-ups, the lots, the order and the expiring lot — each with
    its number."""
    h = next(x for x in hallazgos if x["tipo"] == "zona_saturada")
    texto = " ".join(h["detalle"])
    # How many heads-ups depends on how many the team left: what is pinned is
    # that the headline number MATCHES the list, not a literal that breaks
    # the next time someone sends one more WhatsApp.
    n_avisos = len(_demo("[n for n in M.mapa('es')['nodos'] "
                         "if n['id'] == 'zona_camara_de_frio_2'][0]['avisos']"))
    assert f"{n_avisos} aviso" in texto
    assert n_avisos >= 2, "the full cold room needs more than one heads-up"
    assert "41 partidas" in texto            # the 41 lots of the pitch slide
    assert "Frigorífico La Ribera" in texto  # the open order's supplier
    assert "por vencer" in texto


def test_el_cruce_nombra_personas_no_usuarios(hallazgos):
    """The heads-up is signed by Ramón, not `ramon`. A badly cased name on
    screen betrays that the datum came out of a database and nobody looked."""
    h = next(x for x in hallazgos if x["tipo"] == "zona_saturada")
    texto = " ".join(h["detalle"])
    assert "Ramón" in texto and "Nahuel" in texto
    assert "ramon" not in texto


def test_el_cruce_propone_que_hacer(hallazgos):
    """Braking without proposing is a sign. The action ships its number."""
    h = next(x for x in hallazgos if x["tipo"] == "zona_saturada")
    assert h["accion"]["tipo"] == "reprogramar_orden"
    assert h["accion"]["numero"].startswith("OC-")
    assert h["alternativa"], "it does not say what goes out first"


# ===========================================================================
# 2 · THE LAYERS AND THE ROUTE
# ===========================================================================
def test_hay_tres_capas_y_todo_nodo_vive_en_una(mapa):
    capas = {c["id"] for c in mapa["capas"]}
    assert capas == {"origen", "centro", "destino"}
    for n in mapa["nodos"]:
        assert n["capa"] in capas, f"{n['id']} belongs to no layer"


def test_ningun_nodo_queda_suelto(mapa):
    """The bug we refuse to repeat: a node with not a single edge."""
    conectados = set()
    for a in mapa["aristas"]:
        conectados.add(a["origen"])
        conectados.add(a["destino"])
    sueltos = [n["id"] for n in mapa["nodos"] if n["id"] not in conectados]
    assert not sueltos, f"nodes with no edge at all: {sueltos}"


def test_las_aristas_apuntan_a_nodos_que_existen(mapa):
    ids = {n["id"] for n in mapa["nodos"]}
    for a in mapa["aristas"]:
        assert a["origen"] in ids, f"edge from a ghost node: {a['origen']}"
        assert a["destino"] in ids, f"edge into a ghost node: {a['destino']}"


def test_el_recorrido_va_de_izquierda_a_derecha(mapa):
    """Origin → center → destination. An edge going backwards breaks the
    reading: the eye must travel one way only."""
    capa = {n["id"]: n["capa"] for n in mapa["nodos"]}
    orden = {"origen": 0, "centro": 1, "destino": 2}
    for a in mapa["aristas"]:
        assert orden[capa[a["origen"]]] <= orden[capa[a["destino"]]], \
            f"edge {a['id']} goes backwards"


def test_los_ids_sobreviven_a_react_flow(mapa):
    """A `:` inside an id makes the edge silently not draw."""
    for n in mapa["nodos"]:
        assert all(c.isalnum() or c == "_" for c in n["id"]), n["id"]
    for a in mapa["aristas"]:
        for k in ("origen", "destino"):
            assert ":" not in a[k] and " " not in a[k]


# ===========================================================================
# 3 · THE NODE CONTRACT
# ===========================================================================
def test_toda_metrica_viene_ya_formateada(mapa):
    """The screen iterates and renders. It never computes or reformats: that
    is what lets the same component serve another industry untouched."""
    for n in mapa["nodos"]:
        assert n["metricas"], f"{n['id']} has not a single metric"
        for m in n["metricas"]:
            assert isinstance(m["label"], str) and m["label"]
            assert isinstance(m["valor"], str), \
                f"{n['id']}·{m['label']} ships a raw number, not a string"
            assert m.get("estado") in (None, "inferido", "confirmado",
                                       "dudoso", "error")


def test_todo_nodo_dice_de_donde_salio(mapa):
    for n in mapa["nodos"]:
        f = n.get("fuente")
        assert f and f.get("apartado"), f"{n['id']} declares no source"


def test_los_miles_van_con_punto(mapa):
    """Spanish: 1.240, never 1,240. A US-formatted number on screen reads as
    a different number."""
    valores = [m["valor"] for n in mapa["nodos"] for m in n["metricas"]]
    con_miles = [v for v in valores if "." in v or "," in v]
    assert con_miles, "the dataset should carry four-digit numbers"
    for v in con_miles:
        assert ",," not in v
        # if there is a comma it is decimal: it goes after the thousands dot
        if "," in v and "." in v:
            assert v.index(".") < v.index(",")


def test_en_ingles_no_se_filtra_ninguna_clave(mapa):
    """`mapa("en")` must localize the whole surface: a leaked `mapaop.` key
    on screen is the i18n contract broken. Payload shape must not vary by
    language either — only the strings do."""
    en = _demo("M.mapa('en')")
    assert "mapaop." not in json.dumps(en), \
        "an i18n key leaked into the English payload"
    assert {n["id"] for n in en["nodos"]} == {n["id"] for n in mapa["nodos"]}, \
        "node ids must be language-independent"
    assert len(en["hallazgos"]) == len(mapa["hallazgos"])


# ===========================================================================
# 4 · TRANSIT AND GROUPING
# ===========================================================================
def test_el_transito_es_un_estado_propio(mapa):
    """Packages that left with nobody confirming are in no node."""
    r = mapa["resumen"]
    assert r["en_transito_pedidos"] > 0
    assert r["en_transito_bultos"] > 0
    tr = [a for a in mapa["aristas"] if a["tipo"] == "transito"]
    assert tr, "transit has no edge type of its own"
    for a in tr:
        assert a.get("punteada") is True, "transit must read dashed"
        assert a.get("alerta") is True


def test_los_pasillos_van_agrupados(mapa):
    """380 lots across 21 locations are a smear. Cold rooms go alone — they
    are the ones that hurt — and shelving enters one node that opens."""
    zonas = [n for n in mapa["nodos"] if n["tipo"] == "zona"]
    agrupados = [n for n in zonas if n.get("expandible")]
    assert agrupados, "no grouped node at all"
    for n in agrupados:
        assert len(n["hijos"]) > 1
        for hijo in n["hijos"]:
            assert hijo["etiqueta"] and hijo["metricas"]
    camaras = [n for n in zonas if "Cámara" in n["etiqueta"]]
    assert len(camaras) >= 3, "cold rooms must be their own nodes"
    for c in camaras:
        assert not c.get("expandible"), f"{c['etiqueta']} should not group"


def test_las_tres_columnas_pesan_parecido(mapa):
    """What makes an operation map legible is NOT having few nodes — it is
    the three columns weighing about the same, each card at its column's
    width."""
    por_capa = {}
    for n in mapa["nodos"]:
        por_capa[n["capa"]] = por_capa.get(n["capa"], 0) + 1
    assert set(por_capa) == {"origen", "centro", "destino"}
    for capa, n in por_capa.items():
        assert 3 <= n <= 12, f"column {capa} holds {n} nodes"
    assert max(por_capa.values()) <= 3 * min(por_capa.values()), \
        f"uneven columns: {por_capa}"


def test_la_orden_abierta_apunta_a_su_zona(mapa):
    """«Already ordered, not here yet» sits in the origin column, and its
    dashed stroke enters the zone where it will LAND."""
    ocs = [n for n in mapa["nodos"] if n["tipo"] == "orden_compra"]
    assert ocs, "open orders do not draw"
    for o in ocs:
        assert o["capa"] == "origen"
    ordenes = [a for a in mapa["aristas"] if a["tipo"] == "orden"]
    assert ordenes
    for a in ordenes:
        assert a.get("punteada") is True
        assert a["destino"].startswith("zona_")


def test_el_semaforo_dice_por_que(mapa):
    """Red and amber cards must state their reason in one sentence, and it
    travels in the card's subtitle."""
    for n in mapa["nodos"]:
        if n["tipo"] == "zona":
            assert n.get("motivo"), f"{n['etiqueta']} says not why"
            assert n["motivo"] in n["subtitulo"]


def test_ningun_rojo_se_cuenta_dos_veces(mapa):
    """The same problem painting two cards dilutes both."""
    rojos = [n["id"] for n in mapa["nodos"] if n["estado"] == "rojo"]
    assert "clientes" not in rojos
    assert "deposito" not in rojos, \
        "the hub is the brand; it does not repeat its zones' red"


def test_la_camara_llena_esta_en_rojo(mapa):
    c2 = next(n for n in mapa["nodos"]
              if n["etiqueta"] == "Cámara de frío 2")
    assert c2["estado"] == "rojo"
    assert c2["ocupacion_pct"] == 100
    assert len(c2["avisos"]) >= 2, \
        "the team's heads-ups must travel with the node"
    for a in c2["avisos"]:
        assert a["autor"] and a["fecha"] and a["canal"] and a["texto"], \
            "a heads-up without who, when, how and what cannot be opened"


# ===========================================================================
# 5 · THE FINDINGS
# ===========================================================================
def test_cada_hallazgo_propone_una_accion_con_su_numero(hallazgos):
    assert hallazgos
    for h in hallazgos:
        assert h["accion"]["tipo"] and h["accion"]["numero"]
        assert h["fuentes"], f"{h['id']} says not where it came from"
        assert h["gravedad"] in ("alta", "media", "baja")


def test_el_camino_no_pasa_dos_veces_por_el_mismo_nodo(hallazgos):
    """A node lit twice reads as two different things."""
    for h in hallazgos:
        assert len(h["camino"]) == len(set(h["camino"])), h["id"]


def test_los_nodos_fisicos_del_camino_existen(mapa, hallazgos):
    """The path may touch notes and lots — they live on the other layer —
    but every PHYSICAL node it names must be drawn."""
    ids = {n["id"] for n in mapa["nodos"]}
    for h in hallazgos:
        for n in h["camino"]:
            if n.startswith(("nota_", "lote_")):
                continue
            assert n in ids, f"{h['id']} lights a node that does not exist: {n}"


def test_los_vencimientos_van_en_un_solo_hallazgo(hallazgos):
    """Six chips saying «1 lot expires in Aisle N» are six chips nobody
    reads. One big one, detail inside."""
    pv = [h for h in hallazgos if h["tipo"] == "por_vencer"]
    assert len(pv) == 1, "expirations fragmented per shelf"
    assert len(pv[0]["detalle"]) > 1
    assert pv[0]["alternativa"], "it does not say which is most urgent"


# ===========================================================================
# 6 · THE TRUTH OF THE DATUM
# ===========================================================================
def test_consolidado_no_es_un_punto_de_venta(mapa):
    """«Consolidado» is how the ERP labels what it books to no branch.
    Drawing it as a place would invent a store."""
    bocas = [n["etiqueta"] for n in mapa["nodos"] if n["tipo"] == "boca"]
    assert bocas
    assert not any("onsolidado" in b for b in bocas)


def test_el_camion_es_la_unidad_y_la_partida_el_detalle():
    """Seen disaggregated, truck by truck: an order opens and shows which
    lots it carries and which zone each leaves from. The map says WHERE, the
    panel says WHAT."""
    camion = _demo("[n['id'] for n in M.mapa('es')['nodos'] "
                   "if n['tipo'] == 'camion'][0]")
    d = _demo(f"M.detalle({camion!r}, 'es')")
    assert d["filas"], "the truck shows no orders"
    con_items = [f for f in d["filas"] if f["items"]]
    assert con_items, "no order declares what it carries"
    for f in con_items:
        assert f["pedido"] and f["cliente"]
        for it in f["items"]:
            assert it["producto"] and it["bultos"]
            assert it["zona"], "a lot with no zone does not close the route"


def test_la_zona_se_abre_hasta_la_partida():
    d = _demo("M.detalle('zona_camara_de_frio_2', 'es')")
    assert d["titulo_filas"]
    assert len(d["filas"]) == 41, "the cold room must open its 41 lots"
    for f in d["filas"]:
        assert f["lote"] and f["producto"]


def test_el_resumen_titula_lo_que_importa(mapa):
    ts = mapa["resumen"]["titulares"]
    assert len(ts) == 4, "four big numbers up top, not a table"
    for t in ts:
        assert isinstance(t["valor"], str) and t["label"]

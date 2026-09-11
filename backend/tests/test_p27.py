"""
P27 — El set CERRADO de oportunidades serias.

Dos frentes:
  (a) en el PILOTO (env de la suite): las cards que dependen de datos que no
      están se caen con gracia — nunca se fuerzan;
  (b) en el DEMO (subproceso con el tenant demo, como test_kpis): el set entero
      vive, cada card con su $, sus fuentes cruzadas y su gráfico P21, y los
      NÚMEROS CANÓNICOS del guion quedan clavados acá — si se mueven, el guion
      se entera por este archivo.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from core import oportunidades_neg


def _demo_cards(lang: str = "es") -> list[dict]:
    backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_demo = os.path.join(os.path.dirname(backend), "data-demo")
    env = {**os.environ, "POLPILOT_TENANT": "demo", "POLPILOT_DATA_DIR": data_demo,
           "POLPILOT_DEMO_TODAY": "2026-07-07", "PYTHONIOENCODING": "utf-8"}
    env.pop("ANTHROPIC_API_KEY", None)
    r = subprocess.run(
        [sys.executable, "-c",
         "import json; from core import oportunidades_neg as o; "
         f"print(json.dumps(o.cards({lang!r})))"],
        cwd=backend, env=env, capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr[-500:]
    return json.loads(r.stdout.strip().splitlines()[-1])


# --- (a) piloto: honestidad ante datos ausentes ---------------------------------

def test_piloto_solo_cards_sostenibles():
    ids = {c["id"] for c in oportunidades_neg.cards("es")}
    # Sin ventas validadas ni cartera con historial, el set de ventas cae entero.
    for imposible in ("ventana_compra", "cliente_frio", "estrella_caida",
                      "quiebre_inminente", "pre_pico", "concentracion",
                      "sobrecompra", "cargar_precios"):
        assert imposible not in ids, imposible


# --- (b) demo: el set entero, con los números canónicos del guion ----------------

def test_demo_set_cerrado_completo():
    cards = _demo_cards("es")
    ids = {c["id"] for c in cards}
    assert ids == {"cobrar_morosos", "despertar_dormido", "ventana_compra",
                   "cliente_frio", "estrella_caida", "quiebre_inminente",
                   "pre_pico", "concentracion", "margen_bajo",
                   # P38·D — la oferta del proveedor medida contra la rotación
                   "sobrecompra"}


def test_demo_cards_anatomia_completa():
    """Toda card: $ > 0, tipo válido, fuentes cruzadas, porqué, y el gráfico
    en el contrato P21 (series/puntos/meta) — el frontend lo renderiza con el
    renderer de siempre, cero charts inventados."""
    for c in _demo_cards("es"):
        assert c["monto"] > 0, c["id"]
        assert c["tipo"] in oportunidades_neg.TIPOS_VALIDOS, c["id"]
        assert c["fuentes"], c["id"]
        assert c["drill"]["porque"], c["id"]
        g = c["drill"].get("grafico")
        assert g and g["ok"] and g["series"][0]["puntos"], c["id"]
        assert g["meta"]["unidad"], c["id"]
        # P30·A1 — toda card declara su NATURALEZA (la fuente única anti-doble-conteo)
        assert c["naturaleza"] in ("recuperable", "accionable", "riesgo"), c["id"]


def test_demo_naturaleza_anti_doble_conteo():
    """P30·A1 — solo lo RECUPERABLE es homogéneo y sumable (cobranza vencida +
    capital dormido + ahorro). La concentración es RIESGO: jamás en la suma.
    El total recuperable canónico es $156.324.231 — el número del guion."""
    por_id = {c["id"]: c for c in _demo_cards("es")}
    recuperables = {i: c for i, c in por_id.items() if c["naturaleza"] == "recuperable"}
    assert set(recuperables) == {"cobrar_morosos", "despertar_dormido", "ventana_compra"}
    assert round(sum(c["monto"] for c in recuperables.values())) == 156324231
    assert por_id["concentracion"]["naturaleza"] == "riesgo"
    # la concentración declara que su $ es facturación 12m, no deuda
    assert por_id["concentracion"]["monto_label"]
    assert por_id["concentracion"]["datos"]["facturacion_total_12m"] > por_id["concentracion"]["monto"]


def test_demo_numeros_canonicos_del_guion():
    por_id = {c["id"]: c for c in _demo_cards("es")}
    # 3 · la ventana de compra RECALCULADA con razonamiento de dueño:
    #     adelantar solo la compra que ibas a hacer igual (~$1.7M de ahorro
    #     sobre ~$29.8M de compra segura). Antes (P25): $2.023.614.
    v = por_id["ventana_compra"]
    assert round(v["monto"]) == 1697017
    assert v["datos"]["dias_hasta_lista"] == 0  # la lista nueva llega HOY
    # 4 · el cliente que se enfría: La Rural, -65% vs SU histórico (ventana 180d)
    f = por_id["cliente_frio"]
    assert f["datos"]["cliente"] == "Proveeduría La Rural"
    assert f["datos"]["caida_pct"] == 65
    assert f["datos"]["ventana_dias"] == 180
    # 5 · quiebre inminente: la gaseosa #3 por facturación, 7 días de cobertura
    q = por_id["quiebre_inminente"]
    assert q["datos"]["producto"] == "GASEOSA COLA LA RIBERA 2.25L (X6U)"
    assert q["datos"]["dias_cobertura"] == 7
    assert q["datos"]["rank_facturacion"] == 3
    # 6 · pre-pico: diciembre ×1.91 en fiambres; cubrís 18 días a ritmo de pico;
    #     la compra grande se planifica en octubre (mes 10)
    p = por_id["pre_pico"]
    assert p["datos"]["indice"] == 1.91 and p["datos"]["mes_pico"] == 12
    assert p["datos"]["cobertura_pico_dias"] == 18
    assert p["datos"]["mes_plan"] == 10
    # 7 · concentración: el top 3 concentra 41% (>40 → la card vive)
    c = por_id["concentracion"]
    assert c["datos"]["pct_top3"] == 41.5
    assert round(c["monto"]) == 470800000
    # 8 · estrella en caída: el vino #2, 4 meses seguidos — dos productos
    #     DISTINTOS entre estrella y quiebre (la exclusión funciona)
    e = por_id["estrella_caida"]
    assert e["datos"]["producto"] == "VINO TINTO LA RIBERA 750CC (X6U)"
    assert e["datos"]["racha_meses"] >= 3
    assert e["datos"]["rank_facturacion"] == 2
    assert e["datos"]["producto"] != q["datos"]["producto"]


def test_demo_bilingue():
    es = {c["id"]: c["titulo"] for c in _demo_cards("es")}
    en = {c["id"]: c["titulo"] for c in _demo_cards("en")}
    assert set(es) == set(en)
    for k in es:
        if k in ("ventana_compra",):  # el título lleva solo el nombre propio
            continue
        assert es[k] != en[k], k  # traducidas de verdad

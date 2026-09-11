"""
P38 — los casos de uso REALES de una distribuidora de alimentos.

  B · quiebre con anticipación (ventas × stock × tiempo de reposición)
  C · margen por grupo en los DOS canales (mayorista y mostrador)
  D · sobrecompra (oferta × rotación real × vencimiento del lote)
  E · el reporte de cierres por local que hoy alguien hace a mano
  F · venta a local propio vs venta real
  G · pesables con unidades + peso + precio
  H · vencimientos gestionados (vencimiento × ritmo real de venta)

Igual que P27: el PILOTO comprueba que nada se fuerza sin datos, y el DEMO
(subproceso con su tenant) comprueba los números. La regla de oro de este
prompt está clavada en `test_demo_numeros_canonicos_intactos`: lo nuevo suma
pantallas, no reescribe montos que ya se mostraban.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from core import margenes, mostrador, pricing, reposicion, traslados, vencimientos


def _demo(expr: str):
    """Evalúa una expresión en el tenant DEMO y devuelve su JSON."""
    backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_demo = os.path.join(os.path.dirname(backend), "data-demo")
    env = {**os.environ, "POLPILOT_TENANT": "demo", "POLPILOT_DATA_DIR": data_demo,
           "POLPILOT_DEMO_TODAY": "2026-07-07", "PYTHONIOENCODING": "utf-8"}
    env.pop("ANTHROPIC_API_KEY", None)
    r = subprocess.run(
        [sys.executable, "-c", f"import json; print(json.dumps({expr}))"],
        cwd=backend, env=env, capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr[-800:]
    return json.loads(r.stdout.strip().splitlines()[-1])


def _cards(lang="es"):
    return {c["id"]: c for c in _demo(
        f"__import__('core.oportunidades_neg', fromlist=['x']).cards({lang!r})")}


# --- el piloto no inventa nada de esto ------------------------------------------

def test_piloto_sin_canal_minorista_ni_traslados():
    """El piloto (un supermercado, sin bocas propias ni traslados cargados) no
    ve ninguna de estas pantallas: devuelven `disponible=False`, no ceros."""
    assert not mostrador.hay_datos()
    assert not traslados.hay_datos()
    assert mostrador.comparativo(7)["disponible"] is False
    assert traslados.resumen("es")["disponible"] is False
    assert margenes.minorista("es")["disponible"] is False


def test_lead_time_default_cuando_el_proveedor_no_lo_declara():
    dias, propio = reposicion.dias_reposicion("Proveedor Que No Existe")
    assert dias > 0 and propio is False   # se usa un supuesto, y se DICE que lo es


# --- B · quiebre con anticipación -------------------------------------------------

def test_quiebre_cruza_el_tiempo_del_proveedor():
    q = _cards()["quiebre_inminente"]
    d = q["datos"]
    # las tres claves históricas siguen intactas (las lee la notificación sembrada)
    assert d["producto"] == "GASEOSA COLA LA RIBERA 2.25L (X6U)"
    assert d["dias_cobertura"] == 7 and d["rank_facturacion"] == 3
    # y el tercer factor, que es lo nuevo: la ventana ES la resta
    assert d["dias_reposicion"] == 3
    assert d["dias_para_negociar"] == d["dias_cobertura"] - d["dias_reposicion"] == 4
    assert d["unidades_mes"] > 0 and d["cantidad_sugerida"] > 0
    assert any("reposici" in f or "lead time" in f for f in q["fuentes"])
    # llega con la orden armada, esperando aprobación
    p = q["propuesta"]
    assert p["tipo"] == "orden_compra" and p["cantidad"] > 0 and p["proveedor"]


def test_quiebre_cantidad_sugerida_entera_por_unidad():
    """Nadie pide 1.006,9 botellas: lo que se pide por unidad es entero."""
    q = _cards()["quiebre_inminente"]
    assert q["datos"]["cantidad_sugerida"] == float(int(q["datos"]["cantidad_sugerida"]))


# --- C · margen por grupo, en los dos canales -------------------------------------

def test_margen_por_grupo_dos_canales():
    m = _demo("__import__('core.margenes', fromlist=['x']).completo('es')")
    may, mino = m["mayorista"], m["minorista"]
    assert may["disponible"] and mino["disponible"]
    # mayorista: márgenes de distribución, todos los grupos con su $ y su %
    assert len(may["grupos"]) == 8
    for g in may["grupos"]:
        assert g["ventas_12m"] > 0 and 0 < g["margen_pct"] < 40
        assert g["recargo_pct"] > g["margen_pct"]   # sobre costo siempre da más
    # mostrador: el otro planeta — feteado arriba, pieza entera abajo
    por_id = {g["id"]: g for g in mino["grupos"]}
    assert por_id["feteado"]["recargo_pct_rubro"] == 80.0
    assert por_id["pieza_entera"]["recargo_pct_rubro"] == 30.0
    assert por_id["congelados"]["recargo_pct_rubro"] == 60.0
    assert por_id["feteado"]["margen_pct"] > por_id["pieza_entera"]["margen_pct"]
    # y el canal minorista deja MUCHO más margen que el mayorista
    assert mino["total"]["margen_pct"] > may["total"]["margen_pct"] * 1.5


def test_margen_detalle_marca_al_que_esta_abajo_de_su_grupo():
    d = _demo("__import__('core.margenes', fromlist=['x'])"
              ".detalle('limpieza y perfumería', 'es')")
    assert d["promedio_defendible"] and d["items"]
    # ordenado del que menos deja al que más
    margenes_ = [i["margen_unitario_pct"] for i in d["items"]]
    assert margenes_ == sorted(margenes_)
    bajos = [i for i in d["items"] if i["bajo_su_grupo"]]
    assert bajos and all(i["margen_unitario_pct"] < d["promedio_pct"] for i in bajos)


def test_hallazgo_de_margen_nombra_al_producto():
    c = _cards()["margen_bajo"]
    d = c["datos"]
    assert d["producto"] in c["titulo"]
    assert d["margen_pct"] < d["promedio_grupo_pct"]


# --- D · sobrecompra ---------------------------------------------------------------

def test_sobrecompra_mide_la_oferta_contra_la_rotacion():
    c = _cards()["sobrecompra"]
    d = c["datos"]
    assert d["cantidad_sugerida"] < d["oferta"]          # comprar MENOS, ese es el punto
    assert d["meses_para_venderlo"] > 6                  # la oferta es un disparate
    assert c["monto"] > 0 and c["monto_label"]           # $ etiquetado: no es plata a cobrar
    assert c["naturaleza"] == "accionable"               # jamás en la suma de recuperable
    assert c["propuesta"]["cantidad"] == d["cantidad_sugerida"]


# --- E · el reporte de cierres por local ------------------------------------------

def test_cierres_por_local_suman_exactamente_la_caja():
    """La caja del negocio no cambia: se abre por boca. Peso a peso."""
    caja = _demo("__import__('json').load(open("
                 "__import__('os').path.join("
                 "__import__('core.paths', fromlist=['x']).DATA_DIR, 'caja.json'),"
                 " encoding='utf-8'))['historial']")
    cierres = _demo("__import__('core.mostrador', fromlist=['x']).cierres()")
    por_dia = {}
    for c in cierres:
        por_dia[c["fecha"]] = por_dia.get(c["fecha"], 0) + c["total"]
    assert len(por_dia) == len(caja)
    for d in caja:
        assert por_dia[d["fecha"]] == d["total"], d["fecha"]


def test_comparativo_semanal_tiene_una_historia():
    r = _demo("__import__('core.mostrador', fromlist=['x']).comparativo(7)")
    assert r["disponible"] and len(r["locales"]) == 3
    assert r["mejor"]["variacion_pct"] > r["peor"]["variacion_pct"]
    # el reporte dice algo: un local crece y otro cae de verdad
    assert r["mejor"]["variacion_pct"] > 0 > r["peor"]["variacion_pct"]
    assert round(sum(f["total"] for f in r["locales"])) == round(r["total"])


# --- F · local propio vs venta real ------------------------------------------------

def test_traslados_separan_el_local_propio_de_la_venta_real():
    r = _demo("__import__('core.traslados', fromlist=['x']).resumen('es')")
    assert r["disponible"] and r["total_12m"] > 0
    # el local propio se colaría entre los mejores clientes
    assert r["top_local"]["puesto_como_cliente"] <= 3
    assert r["top_local"]["local"] not in {c["cliente"] for c in r["clientes_reales"]}
    # y desplaza a UN cliente real que factura MENOS que él (si dijera el #1,
    # el copy mentiría: "arriba de X" cuando X está arriba)
    desplazado = next(c for c in r["clientes_reales"]
                      if c["cliente"] == r["top_local"]["desplaza"])
    assert desplazado["monto"] < r["top_local"]["monto"]
    # y hay un producto que sube de puesto sólo por la reposición interna
    d = r["distorsionado"]
    assert d["pos_crudo"] < d["pos_real"]
    assert round(d["unidades_crudo"]) == round(d["unidades_real"] + d["unidades_traslado"])


def test_los_traslados_no_contaminan_las_ventas_del_sistema():
    """La lectura real es la que TODO el resto del sistema ya usaba: los
    traslados viven en su propio archivo y jamás entraron a las ventas."""
    ventas = _demo("[f.get('producto') for f in "
                   "__import__('core.esquema', fromlist=['x']).filas('venta')]")
    destinos = _demo("sorted({f['destino'] for f in "
                     "__import__('core.traslados', fromlist=['x']).filas()})")
    assert destinos and all(d not in ventas for d in destinos)


# --- G · pesables: unidades + peso + precio ------------------------------------------

def test_pesable_expone_unidades_ademas_del_peso():
    """El chofer y el local piden UNIDADES ('bajá 100 jamones'), no kilos."""
    arts = _demo("[a for a in __import__('core.store', fromlist=['x']).raw_actual() "
                 "if a.get('venta_x_peso') and a.get('valor_peso') and (a.get('stock') or 0) > 0][:5]")
    assert arts
    for a in arts:
        u = pricing.unidades_de(a)
        assert u is not None and u >= 0
        assert abs(u - round(a["stock"] / a["valor_peso"])) < 0.51
    # y un producto por unidad NO inventa un peso por pieza
    assert pricing.unidades_de({"venta_x_peso": False, "stock": 10}) is None


def test_pesable_enriquecido_trae_las_tres_cosas():
    a = _demo("[a for a in __import__('core.store', fromlist=['x']).raw_actual() "
              "if a.get('venta_x_peso') and a.get('valor_peso') and a.get('pvp')][0]")
    e = pricing.enriquecer(a)
    assert e["unidad_pricing"] == "kg" and e["label_precio"] == "$/kg"
    assert e["unidades"] is not None and e["peso_por_unidad"] == a["valor_peso"]
    assert e["precio_por_unidad"] is not None     # peso × precio: lo que se cobra


# --- H · vencimientos gestionados ----------------------------------------------------

def test_vencimientos_cruzan_ritmo_de_venta():
    r = _demo("__import__('core.vencimientos', fromlist=['x']).en_riesgo(30, 'es')")
    assert r["disponible"] and r["lotes_en_riesgo"] > 0
    for i in r["items"]:
        # sólo aparece lo que NO llegás a vender: el sobrante es real
        assert i["sobrante"] > 0
        assert abs(i["sobrante"] - (i["cantidad"] - i["vendible_antes"])) < 0.15
        assert i["plata_en_riesgo"] > 0
        assert 0 <= i["dias_restantes"] <= 30
    # ordenado por urgencia
    assert [i["dias_restantes"] for i in r["items"]] == sorted(
        i["dias_restantes"] for i in r["items"])


def test_vencimientos_proponen_accion_sin_ejecutarla():
    p = _demo("__import__('core.vencimientos', fromlist=['x']).propuesta('es')")
    assert p and p["tipo"] == "promocion_vencimiento" and p["cantidad"] > 0


# --- A · "Datos a corregir" cuenta lo mismo en todas las pantallas ---------------------

def test_a_corregir_es_un_solo_numero():
    """El badge del sidebar, el filtro de la tabla de stock y el contador del
    Inicio salen todos de resumen.a_corregir, que cuenta REGISTROS (un producto
    con dos problemas es uno, no dos) e incluye el costo viejo — que la propia
    app ya trata como un dato a corregir."""
    from core import store
    n = store.panorama()["resumen"]["a_corregir"]
    con_estado = [a for a in store.articulos_con_estado() if a["estado_calidad"] != "ok"]
    assert n == len(con_estado)
    # y no es la suma cruda de los grupos si algún producto acumula problemas
    al = store.panorama()["alertas"]
    suma = sum(al[g]["cantidad"] for g in
               ("fantasmas", "negativos", "sin_pvp", "balanza", "costo_viejo"))
    assert n <= suma


# --- la regla de oro: nada de lo viejo se movió --------------------------------------

def test_demo_numeros_canonicos_intactos():
    """Lo nuevo suma tarjetas y vistas; NO reescribe un solo monto existente.
    (El total recuperable y el resto viven clavados en test_p27; acá se
    verifica que las cards nuevas no entren en esa suma.)"""
    cards = _cards()
    recuperables = [c for c in cards.values() if c["naturaleza"] == "recuperable"]
    assert {c["id"] for c in recuperables} == {"cobrar_morosos", "despertar_dormido",
                                               "ventana_compra"}
    assert round(sum(c["monto"] for c in recuperables)) == 156324231
    assert round(cards["ventana_compra"]["monto"]) == 1697017
    assert cards["concentracion"]["datos"]["pct_top3"] == 41.5


def test_todo_lo_nuevo_es_bilingue():
    es, en = _cards("es"), _cards("en")
    assert set(es) == set(en)
    for cid in ("sobrecompra", "quiebre_inminente", "margen_bajo"):
        assert es[cid]["titulo"] != en[cid]["titulo"], cid
        assert es[cid]["resumen"] != en[cid]["resumen"], cid
    m_es = _demo("__import__('core.margenes', fromlist=['x']).minorista('es')")
    m_en = _demo("__import__('core.margenes', fromlist=['x']).minorista('en')")
    assert [g["label"] for g in m_es["grupos"]] != [g["label"] for g in m_en["grupos"]]

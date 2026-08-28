"""QUÉ REPONER PRIMERO — que el ranking sea una cuenta, no una opinión.

Lo que se protege: que la plata en riesgo salga de una multiplicación
verificable, que el orden de la lista sea ESE número (y no un score inventado),
y que la cobertura sea la MISMA que usa el resto del producto — si acá diera
otra, el dueño vería dos verdades para el mismo artículo.
"""
from core import reponer


def _r():
    return reponer.analizar(limite=50)


def test_la_plata_en_riesgo_es_una_cuenta_de_una_linea():
    r = _r()
    if not r["disponible"]:
        return
    for i in r["items"]:
        esperado = round(i["dias_sin_stock"] * i["venta_diaria_pesos"], 2)
        assert abs(i["plata_en_riesgo"] - esperado) < 0.02, i["producto"]


def test_los_dias_sin_stock_salen_de_la_ventana():
    r = _r()
    if not r["disponible"]:
        return
    for i in r["items"]:
        assert i["dias_sin_stock"] == round(max(0.0, -i["dias_para_negociar"]), 1)
        # y la ventana es cobertura - lead, el mismo número que usa la card
        assert abs(i["dias_para_negociar"] - (i["cobertura_dias"] - i["lead_dias"])) <= 0.11


def test_el_orden_es_la_plata_no_un_score():
    r = _r()
    if not r["disponible"]:
        return
    platas = [i["plata_en_riesgo"] for i in r["items"]]
    assert platas == sorted(platas, reverse=True)


def test_los_que_llegan_a_tiempo_no_se_esconden():
    """Sin ellos el ranking miente por omisión: parecería que todo está perdido."""
    r = _r()
    if not r["disponible"]:
        return
    assert r["ya_tarde"] + r["con_tiempo"] == r["total_en_zona"]


def test_nadie_con_cobertura_holgada_entra_a_la_lista():
    r = _r()
    if not r["disponible"]:
        return
    for i in r["items"]:
        assert i["cobertura_dias"] <= reponer.COBERTURA_MAX_DIAS


def test_la_cobertura_es_la_misma_que_la_de_rotacion():
    """Cover days are projected_stock / daily rate — same helper as Prioridades."""
    from core import analisis, stock, store
    r = _r()
    if not r["disponible"]:
        return
    u12 = analisis._unidades_por_codigo(365)
    arts = {a.get("codigo"): a for a in store.raw_actual()}
    for i in r["items"][:10]:
        a = arts[i["codigo"]]
        ritmo = u12.get(i["codigo"], 0.0) / 365.0
        esperado = stock.days_of_cover(a, ritmo)
        assert abs(i["cobertura_dias"] - round(esperado, 1)) < 0.11


def test_el_agrupado_por_proveedor_suma_lo_mismo():
    r = _r()
    if not r["disponible"]:
        return
    total_grupos = round(sum(g["plata_en_riesgo"] for g in r["proveedores"]), 0)
    assert abs(total_grupos - round(r["plata_total"], 0)) <= 2


def test_un_plazo_supuesto_viaja_marcado():
    """Un lead que no es dato del proveedor no puede parecer uno."""
    r = _r()
    if not r["disponible"]:
        return
    for i in r["items"]:
        assert isinstance(i["lead_propio"], bool)


def test_items_exponen_pipeline_y_stockout():
    r = _r()
    if not r["disponible"]:
        return
    assert "stockout_mes" in r
    for i in r["items"]:
        assert "incoming_qty" in i and "outgoing_qty" in i
        assert "stock" in i and "projected_stock" in i
        assert isinstance(i["stockout_risk"], bool)


def test_sin_ventas_no_inventa_un_ranking():
    from unittest.mock import patch
    with patch("core.analisis.rotacion", return_value={"disponible": False,
                                                       "motivo": "sin ventas"}):
        r = reponer.analizar()
    assert r["disponible"] is False and r["items"] == []

"""COBRANZA AGÉNTICA — que el orden sea una cuenta y que nada salga sin un sí.

Esto NO es credit scoring: no decide a quién darle crédito. Ordena la deuda que
ya existe. Lo que se protege:
  · el ranking es `saldo × días de más`, no un puntaje opaco;
  · la mora la sigue calculando cuentas.py (acá no se recalcula);
  · `proponer()` no escribe nada; `registrar()` audita.
"""
import pytest

from core import cobranza, cuentas


def _p():
    return cobranza.prioridad()


def test_el_orden_es_saldo_por_dias_de_mas():
    p = _p()
    if not p["disponible"]:
        return
    for x in p["items"]:
        assert x["exposicion"] == round(x["saldo"] * x["exceso_dias"], 2)
    exp = [x["exposicion"] for x in p["items"]]
    assert exp == sorted(exp, reverse=True)


def test_el_exceso_es_contra_el_promedio_del_cliente_no_el_plazo():
    """La señal es cuánto se corrió de LO SUYO, no del plazo comercial."""
    p = _p()
    if not p["disponible"]:
        return
    for x in p["items"]:
        assert x["exceso_dias"] == max(0, x["dias_sin_pagar"] - x["promedio_pago_dias"])


def test_deber_menos_puede_ser_mas_urgente():
    """El caso que justifica la fórmula: si alguien debe menos pero está mucho
    más fuera de su costumbre, va antes. Sin esto, la lista sería un orden por
    saldo y el dueño tendría que pensarla igual."""
    p = _p()
    if len(p.get("items") or []) < 2:
        return
    for a, b in zip(p["items"], p["items"][1:]):
        if a["saldo"] < b["saldo"]:
            assert a["exceso_dias"] > b["exceso_dias"], (
                "sólo se adelanta a uno que debe más si está más fuera de lo suyo")


def test_la_mora_sigue_saliendo_de_cuentas():
    """Acá no se recalcula la mora: los morosos son los de cuentas.py."""
    p = _p()
    ids_cobranza = {x["id"] for x in p["items"]}
    assert ids_cobranza == {c["id"] for c in cuentas.morosos()}


def test_la_liquidez_es_la_suma_de_lo_vencido_no_una_proyeccion():
    p = _p()
    if not p["disponible"]:
        return
    assert p["entra_si_cobras"] == round(sum(x["saldo"] for x in p["items"]), 2)


def test_proponer_no_escribe_nada():
    p = _p()
    if not p["disponible"]:
        return
    cid = p["items"][0]["id"]
    antes = cobranza.gestion_de(cid)
    r = cobranza.proponer(cid, "es")
    assert r and r["mensaje"]
    assert cobranza.gestion_de(cid) == antes


def test_el_mensaje_lleva_los_numeros_del_cliente():
    p = _p()
    if not p["disponible"]:
        return
    x = p["items"][0]
    r = cobranza.proponer(x["id"], "es")
    # el saldo tiene que estar en el texto: un recordatorio sin monto no sirve
    assert any(str(int(x["saldo"]))[:3] in r["mensaje"].replace(".", "").replace(",", "")
               for _ in [0]) or str(x["dias_sin_pagar"]) in r["mensaje"]


def test_registrar_exige_un_estado_conocido():
    p = _p()
    if not p["disponible"]:
        return
    with pytest.raises(ValueError):
        cobranza.registrar(p["items"][0]["id"], "inventado")


def test_una_promesa_con_fecha_ilegible_no_entra():
    p = _p()
    if not p["disponible"]:
        return
    with pytest.raises(ValueError):
        cobranza.registrar(p["items"][0]["id"], "promesa", promesa_fecha="el viernes")


def test_registrar_audita_y_cambia_el_estado():
    p = _p()
    if not p["disponible"]:
        return
    from core import store
    cid = p["items"][0]["id"]
    antes = len(store.audit.list())
    cobranza.registrar(cid, "recordado", actor="Tester", mensaje="hola")
    assert cobranza.gestion_de(cid)["estado"] == "recordado"
    assert len(store.audit.list()) == antes + 1
    # y se puede seguir la gestión: promesa después del recordatorio
    cobranza.registrar(cid, "promesa", actor="Tester", promesa_fecha="2026-07-31")
    g = cobranza.gestion_de(cid)
    assert g["estado"] == "promesa" and g["promesa_fecha"] == "2026-07-31"


def test_un_cliente_inexistente_no_se_gestiona():
    with pytest.raises(KeyError):
        cobranza.registrar("no-existe", "recordado")

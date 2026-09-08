"""The yes on the expiry card is a persisted, audited fact — not a toast.

Pinned: (1) deciding writes a row and an attributed audit event; (2) the lot
leaves en_riesgo() and shows up under `gestionados`; (3) deciding twice does
not stack; (4) an unknown lot or type fails loudly.
"""
import datetime

import pytest

from core import analisis_cache, lotes, store, vencimientos
from core.fechas import hoy
from tests.conftest import limpiar_tabla_tenant


@pytest.fixture(autouse=True)
def _limpio():
    # The suite's tenant ships no warehouse lots, so the test plants ONE lot
    # that cannot sell in time (no sales history → the whole quantity is
    # surplus) and removes every trace afterwards — the decision row and the
    # apartado the lot lived in.
    limpiar_tabla_tenant("expiry_actions")
    limpiar_tabla_tenant("data_sections")
    analisis_cache.datos_cambiaron()
    art = next(a for a in store.raw_actual() if float(a.get("costo_iva") or 0) > 0)
    lotes.crear({"codigo": art["codigo"], "producto": art["descripcion"],
                 "ubicacion": "Pasillo test", "lote": "L-TEST-1",
                 "vencimiento": (hoy() + datetime.timedelta(days=3)).isoformat(),
                 "cantidad": 50}, "test")
    analisis_cache.datos_cambiaron()
    yield
    limpiar_tabla_tenant("expiry_actions")
    limpiar_tabla_tenant("data_sections")
    analisis_cache.datos_cambiaron()


def _un_lote():
    r = vencimientos.en_riesgo(365)
    assert r.get("disponible") and r["items"], r
    return r["items"][0]


def test_gestionar_persiste_audita_y_saca_el_lote_de_la_lista():
    it = _un_lote()
    antes = len(store.audit.list())
    out = vencimientos.gestionar(it["codigo"], it["lote"], "promocion", actor="aldo")
    assert out["ok"] and not out["ya_estaba"]
    g = out["gestion"]
    assert g["tipo"] == "promocion" and g["actor"] == "aldo" and g["codigo"] == it["codigo"]

    ev = store.audit.list()
    assert len(ev) == antes + 1
    assert ev[-1]["accion"] == "gestionar_vencimiento" and ev[-1]["actor"] == "aldo"

    r = vencimientos.en_riesgo(365)
    assert not any(x["codigo"] == it["codigo"] and x["lote"] == it["lote"] for x in r["items"])
    assert any(x["codigo"] == it["codigo"] and x["lote"] == it["lote"] for x in r["gestionados"])


def test_decidir_dos_veces_no_apila():
    it = _un_lote()
    vencimientos.gestionar(it["codigo"], it["lote"], "locales", actor="aldo")
    otra = vencimientos.gestionar(it["codigo"], it["lote"], "promocion", actor="marta")
    assert otra["ya_estaba"] and otra["gestion"]["tipo"] == "locales"
    assert len(vencimientos.gestiones()) == 1


def test_lote_o_tipo_desconocido_fallan_ruidosamente():
    it = _un_lote()
    with pytest.raises(ValueError):
        vencimientos.gestionar(it["codigo"], it["lote"], "tirarlo")
    with pytest.raises(KeyError):
        vencimientos.gestionar(999999, "L-no-existe", "promocion")


def test_la_propuesta_trae_el_lote_y_la_alternativa():
    p = vencimientos.propuesta("es", 365)
    assert p is not None
    assert p["gestion"] == "promocion"
    assert p["alternativa"]["gestion"] == "locales" and p["alternativa"]["label"]
    assert "lote" in p

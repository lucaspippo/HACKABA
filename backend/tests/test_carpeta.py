"""The delivery folder (core/carpeta.py).

What is protected, in order of how expensive it would be to get wrong:

  1. EVERY FIELD SAYS WHERE IT CAME FROM, and never "the system". A document
     somebody signs cannot have boxes of unknown origin — that source line is
     the difference between a copilot and a PDF generator.
  2. AN INCOMPLETE DOCUMENT IS STILL RETURNED, with its gaps marked and
     counted. "Generate it when everything is there" is not the question
     anybody has; "what is missing" is.
  3. THE CROSS-CHECK compares numbers that come from the same source, so it
     holds — and it is the check no single form does on its own.
  4. The completeness percentage counts REQUIRED fields against required
     fields. Reporting 100% on a document still missing one is worse than
     reporting nothing.
"""
from __future__ import annotations

import pytest

from core import carpeta, cuentas, esquema
from tests.conftest import limpiar_tabla_tenant

# The suite's tenant ships accounts but no logistics rows, so the folder would
# have no subject at all. One delivery is planted here, for an account that
# really exists, and removed afterwards.
_PEDIDO = {"pedido": "P-9100", "direccion": "Ruta 11 km 30",
           "estado": "pendiente", "fecha_prevista": "2026-07-09",
           "transporte": "Camión 1"}


@pytest.fixture(autouse=True)
def _con_entrega():
    ctas = cuentas.listar()
    if not ctas:
        pytest.skip("este tenant no tiene cuentas corrientes")
    fila = {**_PEDIDO, "cliente": ctas[0]["nombre"]}
    limpiar_tabla_tenant("data_sections")
    esquema.reemplazar_filas("logistica", [fila])
    yield fila
    limpiar_tabla_tenant("data_sections")


def _docs(numero):
    return [carpeta.documento(numero, d, "es") for d in carpeta.DOCUMENTOS]


def test_todo_campo_dice_de_donde_salio():
    for d in _docs(_PEDIDO["pedido"]):
        campos = [c for s in d["secciones"] for c in s["campos"]]
        assert campos, d["id"]
        for c in campos:
            # A field with a value must say where the value came from.
            if c["estado"] == "completo":
                assert c["fuente"], (d["id"], c["etiqueta"])
                assert "sistema" not in c["fuente"].lower(), c["fuente"]
                assert "system" not in c["fuente"].lower(), c["fuente"]


def test_el_documento_incompleto_se_muestra_igual_con_los_huecos_contados():
    """The account in this dataset has no tax id: the delivery note is
    therefore incomplete, and it still comes back — with the gap named."""
    d = carpeta.documento(_PEDIDO["pedido"], "remito_entrega", "es")
    c = d["completitud"]
    assert d["secciones"], "un documento incompleto igual se arma"
    if c["faltan"]:
        assert c["que_falta"], "si falta algo, tiene que decir QUÉ falta"
        assert len(c["que_falta"]) == c["faltan"]
        # And the missing ones are marked field by field, not only counted.
        vacios = [x for s in d["secciones"] for x in s["campos"] if x["estado"] == "falta"]
        assert len(vacios) == c["faltan"]


def test_el_porcentaje_cuenta_obligatorios_contra_obligatorios():
    """100% with a required field missing is worse than no number at all."""
    for d in _docs(_PEDIDO["pedido"]):
        c = d["completitud"]
        if c["faltan"] > 0:
            assert c["pct"] < 100, (d["id"], c)


def test_el_control_cruzado_compara_la_misma_fuente():
    cc = carpeta.control_cruzado(_PEDIDO["pedido"], "es")
    assert cc["checks"], cc
    for chk in cc["checks"]:
        assert chk["que"], chk
        assert "ok" in chk
    # The customer is the same on both documents by construction.
    cliente = next(c for c in cc["checks"] if "liente" in c["que"] or "ustomer" in c["que"])
    assert cliente["ok"], cliente


def test_la_carpeta_lista_los_dos_documentos_con_lo_que_le_falta_a_cada_uno():
    c = carpeta.carpeta(_PEDIDO["pedido"], "es")
    assert c["total_documentos"] == len(carpeta.DOCUMENTOS) == 2
    assert {d["id"] for d in c["documentos"]} == set(carpeta.DOCUMENTOS)
    for d in c["documentos"]:
        assert d["numero"], d
        assert "faltan" in d["completitud"]
    assert c["listos"] == sum(1 for d in c["documentos"] if d["completitud"]["faltan"] == 0)


def test_el_numero_del_documento_es_estable():
    """Reopening the folder shows the same number, not a fresh one."""
    a = carpeta.documento(_PEDIDO["pedido"], "remito_entrega", "es")["numero"]
    b = carpeta.documento(_PEDIDO["pedido"], "remito_entrega", "es")["numero"]
    assert a == b and a


def test_un_pedido_que_no_existe_no_inventa_una_carpeta():
    assert carpeta.carpeta("P-0000") is None
    assert carpeta.documento("P-0000", "remito_entrega") is None
    assert carpeta.documento(_PEDIDO["pedido"], "no_existe") is None


def test_es_bilingue():
    es = carpeta.documento(_PEDIDO["pedido"], "estado_cuenta", "es")
    en = carpeta.documento(_PEDIDO["pedido"], "estado_cuenta", "en")
    assert es["titulo"] != en["titulo"], (es["titulo"], en["titulo"])
    assert [s["titulo"] for s in es["secciones"]] != [s["titulo"] for s in en["secciones"]]

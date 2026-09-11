"""EL BORDE — que ningún número dicho por una máquina entre sin pasar el peaje.

Dos cosas se protegen acá, y las dos son plata:
  · ESCALA: un ×1000 no se ve. Entra al stock y nadie lo nota hasta que no cierra.
  · FECHA: 07/09 leído como 9 de julio tira un lote sano o vende uno vencido.

Y una tercera, igual de importante: que el validador NO grite de más. Un
validador con falsos positivos se apaga a la semana y deja de proteger.
"""
import datetime

import pytest

from core import validacion

UNIDAD = {"codigo": 1, "descripcion": "LECHE 1L (X12U)", "um": "UN",
          "venta_x_peso": False, "costo_iva": 1000.0}
PESABLE = {"codigo": 2, "descripcion": "JAMON COCIDO (HORMA)", "um": "KG",
           "venta_x_peso": True, "costo_iva": 20000.0}


# --- Fechas: locale argentino, sin heurística -------------------------------

@pytest.mark.parametrize("texto,esperado", [
    ("07/09/2026", (2026, 9, 7)),      # 7 de SEPTIEMBRE, no 9 de julio
    ("01/02/2026", (2026, 2, 1)),      # el caso ambiguo por excelencia
    ("20/11/2026", (2026, 11, 20)),
    ("2026-09-07", (2026, 9, 7)),      # ISO: no es ambiguo, se acepta
    ("07-09-2026", (2026, 9, 7)),
    ("07.09.2026", (2026, 9, 7)),
])
def test_parse_ar_siempre_dia_primero(texto, esperado):
    assert validacion.parse_ar(texto) == datetime.date(*esperado)


def test_parse_ar_no_explota_con_basura():
    for basura in ("", None, "ayer", "13/13/2026", "32/01/2026"):
        assert validacion.parse_ar(basura) is None


def test_manda_el_papel_cuando_el_modelo_convirtio_mal():
    # el papel dice 07/09/2026 (7 sep) y el modelo devolvió 9 de julio
    r = validacion.conciliar_fecha("07/09/2026", "2026-07-09", "fecha", "es")
    assert r["fecha"] == "2026-09-07"
    assert r["fuente"] == "papel"
    assert r["alerta"] and r["alerta"]["tipo"] == "fecha_locale"


def test_sin_discrepancia_no_hay_ruido():
    r = validacion.conciliar_fecha("07/09/2026", "2026-09-07", "fecha", "es")
    assert r["fecha"] == "2026-09-07" and r["alerta"] is None


def test_sin_texto_crudo_se_usa_lo_del_modelo_y_se_dice():
    r = validacion.conciliar_fecha(None, "2026-09-07", "fecha", "es")
    assert r["fecha"] == "2026-09-07" and r["fuente"] == "modelo"


# --- Escala: el error que no se ve ------------------------------------------

@pytest.mark.parametrize("recibido,pedido", [(600, 60), (6000, 60), (60000, 60),
                                             (6, 60), (0.6, 60)])
def test_potencia_de_diez_contra_la_orden_es_escala(recibido, pedido):
    s = validacion.validar_cantidad(UNIDAD, recibido, pedido=pedido, lang="es")
    assert s and s["tipo"] == "cantidad_escala"
    assert s["sugerido"] == pedido        # puede proponer, no aplicar


def test_un_faltante_normal_no_es_un_error_de_escala():
    # 8 de 10 es mercadería que faltó, no un separador mal leído
    assert validacion.validar_cantidad(UNIDAD, 8, pedido=10, lang="es") is None


def test_una_diferencia_grande_pero_no_redonda_no_es_escala():
    s = validacion.validar_cantidad(UNIDAD, 137, pedido=60, lang="es")
    assert s is None or s["tipo"] != "cantidad_escala"


def test_decimal_imposible_en_producto_por_unidad():
    s = validacion.validar_cantidad(UNIDAD, 1.234, lang="es")
    assert s and s["tipo"] == "cantidad_decimal"


def test_un_pesable_si_puede_venir_fraccionado():
    # 6,7 kg de jamón es una cantidad legítima: no puede saltar la alarma
    assert validacion.validar_cantidad(PESABLE, 6.7, lang="es") is None


def test_cantidad_cero_o_negativa_no_entra():
    for mala in (0, -5):
        s = validacion.validar_cantidad(UNIDAD, mala, lang="es")
        assert s and s["tipo"] == "cantidad_invalida"


def test_cantidad_ilegible_pide_que_la_escriba_un_humano():
    s = validacion.validar_cantidad(UNIDAD, "no se lee", lang="es")
    assert s and s["tipo"] == "cantidad_ilegible"


def test_magnitud_contra_el_historial():
    historial = [80, 75, 90, 82]
    assert validacion.validar_cantidad(UNIDAD, 78, historial=historial, lang="es") is None
    s = validacion.validar_cantidad(UNIDAD, 8000, historial=historial, lang="es")
    assert s and s["tipo"] == "cantidad_magnitud"


def test_historial_corto_no_opina():
    # con dos entradas no se puede decir qué es "lo normal"
    assert validacion.validar_cantidad(UNIDAD, 8000, historial=[80, 75], lang="es") is None


# --- Qué frena y qué no ------------------------------------------------------

def test_solo_las_cantidades_frenan_la_persistencia():
    avisos = [{"tipo": "cantidad_escala"}, {"tipo": "precio_escala"},
              {"tipo": "fecha_locale"}, {"tipo": "cantidad_decimal"}]
    frenan = {a["tipo"] for a in validacion.bloqueantes(avisos)}
    # un precio raro puede ser real; una cantidad rara mueve el stock
    assert frenan == {"cantidad_escala", "cantidad_decimal"}


def test_corregir_el_numero_limpia_la_sospecha():
    items = [{"codigo": 1, "cantidad": 6000}]
    resolver = lambda it: UNIDAD  # noqa: E731
    validacion.validar_items(items, pedidos={1: 60}, resolver=resolver, lang="es")
    assert "sospecha" in items[0]
    items[0]["cantidad"] = 60
    avisos = validacion.validar_items(items, pedidos={1: 60}, resolver=resolver, lang="es")
    assert "sospecha" not in items[0] and avisos == []

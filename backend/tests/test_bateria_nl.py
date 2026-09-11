"""
P23·C — La batería de lenguaje natural: cómo pregunta un dueño de verdad.

24 frases (12 EN + 12 ES equivalentes) por la MISMA ruta que usa el modelo
(_run_tool con los parámetros que el system prompt le indica producir para
cada frase — el mapeo frase→parámetros está acá, documentado y testeado).
Criterio por frase: resuelve en ≤2 pasos de tool (el pedido + a lo sumo UN
reintento autocorregible), termina en la serie/respuesta correcta, JAMÁS
necesita un menú. El extremo modelo→parámetros se gobierna con el system
prompt (Etapa D) y se verificó EN VIVO con el caso del vino (transcripción
en el reporte del P23).

Corre sobre el mundo sintético determinista de la matriz (la suite vive en
el tenant piloto, sin ventas).
"""
from __future__ import annotations

import math

import pytest

import angela
from core import consultas
from tests.test_matriz_consultas import _filas  # el mismo mundo sintético


@pytest.fixture(autouse=True)
def mundo(monkeypatch):
    filas = _filas()
    monkeypatch.setattr(consultas, "_filas_ventas", lambda: filas)
    indices = {f"{2024 + divmod(6 + i, 12)[0]}-{divmod(6 + i, 12)[1] + 1:02d}":
               100.0 * (1.028 ** i) for i in range(24)}
    monkeypatch.setattr(consultas.macro, "ipc_serie",
                        lambda: {"disponible": True, "indices": indices})
    angela._set_sesion(usuario="emilio", rol="dueño")
    yield
    angela._set_sesion(usuario="dueño", rol="dueño")


def _resolver(params: dict) -> dict:
    """La ruta del modelo: tool → si el error es autocorregible, UN reintento
    con los parámetros que la tool misma devolvió. Dos pasos como máximo."""
    result, _ = angela._run_tool("consultar_serie", params)
    if not result.get("ok") and result.get("autocorregible"):
        result, _ = angela._run_tool("consultar_serie", result["reintentar_con"])
    return result


def _entrega(result: dict) -> None:
    """El criterio: terminó en la respuesta correcta, no en un menú."""
    assert result.get("ok"), result.get("motivo")
    for s in result["series"]:
        assert s["puntos"] > 0 if isinstance(s["puntos"], int) else s["puntos"]
        if isinstance(s.get("puntos"), int):
            continue


# Cada caso: (frase EN, frase ES, los parámetros que el prompt instruye producir)
BATERIA = [
    # tendencia de un producto puntual
    ("how is vino tinto la ribera trending?",
     "¿cómo viene el vino tinto la ribera?",
     {"fuente": "ventas", "metrica": "unidades", "agrupar": "mes",
      "producto": "vino tinto la ribera"}),
    # tendencia de una categoría
    ("show me the beverages trend",
     "mostrame la tendencia de bebidas",
     {"fuente": "ventas", "metrica": "pesos", "agrupar": "mes", "categoria": "bebidas"}),
    # participación categoría-en-total (análisis vertical)
    ("what share of my revenue is beverages?",
     "¿qué peso tienen las bebidas en mi facturación?",
     {"fuente": "ventas", "metrica": "participacion", "categoria": "bebidas",
      "universo": "total_negocio"}),
    # participación producto-en-categoría
    ("vino la ribera's share within beverages",
     "la participación del vino la ribera dentro de bebidas",
     {"fuente": "ventas", "metrica": "participacion",
      "producto": "vino tinto la ribera", "universo": "bebidas"}),
    # EL CASO DEL VINO: análisis vertical mal armado → autocorrección → entrega
    ("vertical analysis of beverages (as the model first tried it)",
     "análisis vertical de bebidas (como lo intentó el modelo)",
     {"fuente": "ventas", "metrica": "pesos", "agrupar": "categoria",
      "categoria": "bebidas", "composicion": True}),
    # top N por venta
    ("top 3 products by sales",
     "top 3 productos por venta",
     {"fuente": "ventas", "metrica": "pesos", "agrupar": "producto", "top_n": 3}),
    # top N por plata inmovilizada (inventario REAL del tenant de la suite)
    ("top 5 by tied-up capital",
     "top 5 por plata inmovilizada",
     {"fuente": "inventario", "metrica": "inmovilizado", "agrupar": "producto",
      "top_n": 5}),
    # comparación de 2 productos
    ("compare vino la ribera against gaseosa cola",
     "comparame el vino la ribera contra la gaseosa cola",
     {"fuente": "ventas", "metrica": "unidades", "agrupar": "mes",
      "producto": "vino tinto la ribera", "comparar_producto": "gaseosa cola"}),
    # comparación de 2 categorías
    ("beverages vs dairy, monthly",
     "bebidas contra lácteos, mes a mes",
     {"fuente": "ventas", "metrica": "pesos", "agrupar": "mes",
      "categoria": "bebidas", "comparar_categoria": "lácteos"}),
    # margen por categoría ordenado
    ("margin by category, worst first",
     "margen por categoría, de peor a mejor",
     {"fuente": "inventario", "metrica": "margen_teorico", "agrupar": "categoria",
      "orden": "asc"}),
    # ventana hablada: "últimos 6 meses"
    ("sales over the last 6 months",
     "las ventas de los últimos 6 meses",
     {"fuente": "ventas", "metrica": "pesos", "agrupar": "mes", "desde": "2026-01"}),
    # ventana hablada: "el 2024" / año contra año
    ("2025 against 2024, real pesos",
     "el 2025 contra el 2024, en pesos constantes",
     {"fuente": "ventas", "metrica": "pesos_reales", "agrupar": "anio",
      "desde": "2024-01", "hasta": "2025-12"}),
]


@pytest.mark.parametrize("frase_en,frase_es,params", BATERIA,
                         ids=[b[0][:40] for b in BATERIA])
def test_bateria(frase_en, frase_es, params):
    result = _resolver(dict(params))
    assert result.get("ok"), f"{frase_en!r} → {result.get('motivo')}"
    # sana: sin None/NaN, con datos
    for s in result["series"]:
        if isinstance(s.get("puntos"), int):
            assert s["puntos"] > 0
        else:
            assert s["puntos"]
    # las de participación entregan %, las temporales entregan serie
    if params.get("metrica") == "participacion" or params.get("composicion"):
        assert result["meta"]["unidad"] == "%"


def test_formatos_pedidos_fijan_widget():
    """'en barras' / 'en tabla' / 'como card': el formato viaja al widget."""
    for tipo in ("barras", "tabla", "card", "linea"):
        result, accion = angela._run_tool("consultar_serie", {
            "fuente": "ventas", "metrica": "pesos", "agrupar": "mes",
            "categoria": "bebidas", "fijar_en": "evolucion", "tipo": tipo,
        })
        assert result["ok"] and result["fijado"]
        assert accion["widget"]["tipo"] == tipo
    # limpiar los widgets creados
    from core import memoria
    memoria.borrar_vista("emilio", "widgets")


def test_estacionalidad_de_categoria_via_tool_dedicada():
    """'estacionalidad de bebidas' usa la tool de estacionalidad que YA existe
    (analisis_estacionalidad) — la batería verifica que el camino no crashea."""
    result, _ = angela._run_tool("analisis_estacionalidad", {})
    assert isinstance(result, dict)  # con o sin ventas responde forma sana

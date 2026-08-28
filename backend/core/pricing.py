"""
Pricing consciente de la UNIDAD — la distribuidora vende dos cosas distintas.

Un producto de balanza (fiambre, queso feteado) se pricea POR PESO: el stock
está en kg, el precio en $/kg, el costo en $/kg. Un producto normal se pricea
POR UNIDAD. Tratarlos igual rompe el margen, la venta a pérdida y — sobre todo
— el delta export de vuelta a Faro.

La señal canónica es `venta_x_peso` (viene de Faro). Este módulo es el ÚNICO
lugar donde se decide la unidad y se calcula el margen/pérdida con conciencia de
ella. El número puede ser el mismo (costo vs pvp, ambos en la misma unidad),
pero la SEMÁNTICA y las etiquetas cambian, y el export tiene que decir cuál es.

Funciones puras: reciben un dict de artículo, no tocan disco ni UI.
"""
from __future__ import annotations


def es_por_peso(art: dict) -> bool:
    return bool(art.get("venta_x_peso"))


def unidad(art: dict) -> str:
    """La unidad de pricing: 'kg' para balanza, 'unidad' para el resto."""
    return "kg" if es_por_peso(art) else "unidad"


def label_precio(art: dict) -> str:
    """Etiqueta para mostrar el precio sin ambigüedad."""
    return "$/kg" if es_por_peso(art) else "$/u"


def margen_pct(art: dict) -> float | None:
    """Margen sobre el costo, en la MISMA unidad (para balanza: $/kg vs $/kg;
    para unidad: $/u vs $/u). None si falta precio o costo. El cálculo es el
    mismo, pero acá queda explícito que se compara peras con peras."""
    costo, pvp = art.get("costo_iva"), art.get("pvp")
    if not costo or not pvp:
        return None
    return round((pvp - costo) / costo * 100, 2)


def margen_sobre_venta_pct(art: dict) -> float | None:
    """Margin on the sale: (pvp − cost) / pvp. Same definition as Márgenes
    (`margen_unitario_pct`). None if PVP or cost is missing. Distinct from
    `margen_pct`, which is markup on cost."""
    costo, pvp = art.get("costo_iva"), art.get("pvp")
    if not costo or not pvp:
        return None
    return round((pvp - costo) / pvp * 100, 2)


def margen_pesos(art: dict) -> float | None:
    """Peso gap per unit: pvp − cost. None if either side is missing."""
    costo, pvp = art.get("costo_iva"), art.get("pvp")
    if costo is None or pvp is None:
        return None
    return round(float(pvp) - float(costo), 2)


def es_a_perdida(art: dict) -> bool:
    """Vende por debajo del costo, comparando en su unidad. Un producto por peso
    NUNCA se evalúa contra un precio por unidad: ambos lados son $/kg."""
    costo, pvp = art.get("costo_iva"), art.get("pvp")
    return bool(costo and pvp and costo > pvp and art.get("estado") != "anulado")


# ---------------------------------------------------------------------------
# P38·G — un pesable son TRES cosas a la vez, no una.
#
# El sistema lo guarda en kg porque así se pricea. Pero el chofer no carga
# kilos: carga jamones. El encargado del local no pide "522 kg de jamón", pide
# "bajame 100 jamones". Y el cliente no paga ni una cosa ni la otra: paga el
# peso de SU pieza por el precio del kilo. Las tres conviven y el producto
# tiene que poder decir las tres — es donde los ERP del rubro se quedan cortos.
#
# El puente es `valor_peso`: el peso teórico de una pieza (la horma, la
# plancha, la pieza), que Faro ya trae y que el saneamiento de balanza usa
# para detectar calibraciones fuera de rango. Sin él no se inventa un peso
# promedio: se devuelve None y la UI muestra sólo kg, que es la verdad.
# ---------------------------------------------------------------------------

def peso_por_unidad(art: dict) -> float | None:
    """Cuánto pesa UNA pieza (horma / plancha / pieza). None si no es pesable
    o si el peso teórico no está cargado."""
    if not es_por_peso(art):
        return None
    v = art.get("valor_peso")
    return float(v) if v and float(v) > 0 else None


def unidades_de(art: dict) -> float | None:
    """Cuántas PIEZAS son los kilos que hay. Redondeado: media horma no es una
    unidad que alguien pueda bajar del camión."""
    p = peso_por_unidad(art)
    if p is None:
        return None
    return float(round((art.get("stock") or 0) / p))


def precio_por_unidad(art: dict) -> float | None:
    """Lo que sale UNA pieza: peso de la pieza × precio del kilo. Para un
    producto por unidad es, sencillamente, su precio."""
    pvp = art.get("pvp")
    if not pvp:
        return None
    p = peso_por_unidad(art)
    return round(pvp * p, 2) if p is not None else float(pvp)


def enriquecer(art: dict) -> dict:
    """Agrega los campos de pricing conscientes de unidad (para API/UI/Ángela).
    No pisa nada existente; sólo suma unidad_pricing, label_precio, margen_pct
    y —para los pesables— las tres lecturas: unidades, peso y precio por pieza."""
    return {
        **art,
        "unidad_pricing": unidad(art),
        "label_precio": label_precio(art),
        "margen_pct": margen_pct(art),
        "margen_venta_pct": margen_sobre_venta_pct(art),
        "margen_pesos": margen_pesos(art),
        "peso_por_unidad": peso_por_unidad(art),
        "unidades": unidades_de(art),
        "precio_por_unidad": precio_por_unidad(art),
    }

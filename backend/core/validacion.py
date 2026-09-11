"""
validacion.py · EL BORDE — donde un número dicho por una máquina se vuelve dato.

El principio de la casa: Ángela decide QUÉ MIRAR y CÓMO DECIRLO; el código
decide CUÁNTO ES. Este módulo es el peaje. Todo número o identificador que sale
de un modelo (la visión leyendo un remito, la voz del depósito dictando una
cantidad) pasa por acá ANTES de tocar el stock, la deuda o un vencimiento.

Por qué importa tanto: un error de ESCALA no se ve. "1.234" en Argentina son mil
doscientos treinta y cuatro; un modelo que lo lee como 1,234 mete un número mil
veces más chico y nadie lo nota hasta que el stock no cierra. Y una fecha mal
convertida (07/09 leído como 9 de julio en vez de 7 de septiembre) tira un lote
sano a la basura o vende uno vencido. Las dos cosas son plata.

Lo que hace este módulo NO es adivinar el número correcto: es DETECTAR que el
número es implausible y frenarlo para que lo mire un humano. Nunca corrige solo.

Tres familias de regla, todas explicables en una línea:

  · ESCALA vs la orden — si lo recibido es exactamente 10, 100 o 1000 veces lo
    pedido, no faltó ni sobró mercadería: se leyó mal el separador de miles.
  · DECIMAL IMPOSIBLE — un producto que se vende por unidad no puede venir en
    cantidad 12,5. Es el "1.234" leído como 1,234.
  · MAGNITUD vs el historial — si de este producto siempre entran ~80 y ahora
    entran 8.000, algo pasó. Se avisa; no se decide.

Las fechas van aparte y con una regla dura: se parsean del TEXTO tal como está
impreso, con locale argentino fijo (DD/MM/AAAA). No se confía en el ISO que
devolvió el modelo, porque si convirtió mal ya no hay forma de darse cuenta.
"""
from __future__ import annotations

import datetime
import statistics
import unicodedata

import i18n

from . import esquema, store

# --- parámetros, explícitos ---------------------------------------------------
POTENCIAS = (1000.0, 100.0, 10.0, 0.1, 0.01, 0.001)
TOL_POTENCIA = 0.02      # 2%: reconocer una potencia de 10 "exacta" con ruido
RATIO_HISTORIAL = 20     # cuántas veces por encima/debajo del histórico ya es raro
MIN_HISTORIAL = 3        # con menos entradas, el histórico no dice nada
RAZON_PRECIO = 5         # el umbral que ya usaba chequeos() para el precio


def _t(key: str, lang: str | None = None, **p) -> str:
    return i18n.t(key, lang, **p)


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


# =============================================================================
# 1 · Fechas — locale argentino fijo, sobre el texto impreso
# =============================================================================

_FORMATOS_AR = ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y")


def parse_ar(texto) -> datetime.date | None:
    """La fecha como la escribe un argentino: DD/MM/AAAA, siempre.

    07/09/2026 es 7 de SEPTIEMBRE. No hay heurística de "si el primero es mayor
    que 12 entonces...": esa heurística es justamente la que falla en los días
    1 al 12, que son el 40% del mes. El formato ISO (aaaa-mm-dd) se acepta
    porque no es ambiguo.
    """
    if isinstance(texto, datetime.datetime):
        return texto.date()
    if isinstance(texto, datetime.date):
        return texto
    s = str(texto or "").strip()
    if not s:
        return None
    # ISO primero: aaaa-mm-dd no se puede confundir con nada
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        pass
    for fmt in _FORMATOS_AR:
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def conciliar_fecha(texto, iso, campo: str, lang: str | None = None) -> dict:
    """Compara lo que dice el PAPEL contra lo que convirtió el modelo.

    Manda el papel. Si el modelo se equivocó, la fecha buena es la del parser
    determinista y queda registrada la discrepancia (el humano la ve).
    """
    del_papel = parse_ar(texto) if texto else None
    del_modelo = parse_ar(iso) if iso else None

    if del_papel is None:
        # sin texto crudo no hay nada que conciliar: queda lo del modelo, dicho
        return {"fecha": del_modelo.isoformat() if del_modelo else None,
                "fuente": "modelo" if del_modelo else None, "alerta": None}
    if del_modelo is not None and del_papel != del_modelo:
        return {
            "fecha": del_papel.isoformat(), "fuente": "papel",
            "alerta": {
                "tipo": "fecha_locale", "campo": campo,
                "detalle": _t("core.val.fecha_locale", lang, texto=str(texto),
                              modelo=del_modelo.isoformat(),
                              correcta=del_papel.isoformat()),
            },
        }
    return {"fecha": del_papel.isoformat(), "fuente": "papel", "alerta": None}


# =============================================================================
# 2 · Cantidades — plausibilidad contra el catálogo
# =============================================================================

def _potencia_de_diez(razon: float) -> float | None:
    """¿La razón es 10, 100, 1000 (o sus inversos) con poco ruido?"""
    for p in POTENCIAS:
        if abs(razon - p) <= p * TOL_POTENCIA:
            return p
    return None


def _historial_cantidades() -> dict[int, list[float]]:
    por_codigo: dict[int, list[float]] = {}
    for f in esquema.filas("recepciones"):
        cod, cant = f.get("codigo"), f.get("cantidad")
        if cod is None or not cant:
            continue
        por_codigo.setdefault(int(cod), []).append(float(cant))
    return por_codigo


def validar_cantidad(articulo: dict, cantidad, *, pedido: float | None = None,
                     historial: list[float] | None = None,
                     lang: str | None = None) -> dict | None:
    """¿Esta cantidad es plausible para ESTE producto? None = sin objeción.

    Devuelve {tipo, detalle, sugerido} — `sugerido` sólo cuando la regla puede
    decir con confianza cuál era el número (potencia de 10 exacta contra lo
    pedido). Nunca se aplica solo: es una propuesta para el humano.
    """
    try:
        cant = float(cantidad)
    except (TypeError, ValueError):
        return {"tipo": "cantidad_ilegible", "sugerido": None,
                "detalle": _t("core.val.cant_ilegible", lang,
                              producto=articulo.get("descripcion", "?"))}
    nombre = articulo.get("descripcion", "?")
    if cant <= 0:
        return {"tipo": "cantidad_invalida", "sugerido": None,
                "detalle": _t("core.val.cant_invalida", lang, producto=nombre,
                              cantidad=cant)}

    # R1 · contra lo PEDIDO: una potencia de 10 exacta no es un faltante, es
    # un separador de miles mal leído. Es la regla de más confianza.
    if pedido:
        razon = cant / float(pedido)
        p = _potencia_de_diez(razon)
        if p is not None:
            return {"tipo": "cantidad_escala", "sugerido": float(pedido),
                    "detalle": _t("core.val.cant_escala_oc", lang, producto=nombre,
                                  recibido=cant, pedido=pedido,
                                  factor=("%g" % p))}

    # R2 · decimal imposible: un producto por UNIDAD no viene fraccionado.
    # (Los pesables sí: 6,7 kg de jamón es una cantidad legítima.)
    es_pesable = bool(articulo.get("venta_x_peso")) or _norm(articulo.get("um")) == "kg"
    if not es_pesable and abs(cant - round(cant)) > 1e-6:
        return {"tipo": "cantidad_decimal", "sugerido": None,
                "detalle": _t("core.val.cant_decimal", lang, producto=nombre,
                              cantidad=cant)}

    # R3 · magnitud contra lo que SIEMPRE entra de este producto
    if historial and len(historial) >= MIN_HISTORIAL:
        tipico = statistics.median(historial)
        if tipico > 0:
            razon = cant / tipico
            if razon >= RATIO_HISTORIAL or razon <= 1 / RATIO_HISTORIAL:
                return {"tipo": "cantidad_magnitud", "sugerido": None,
                        "detalle": _t("core.val.cant_magnitud", lang, producto=nombre,
                                      cantidad=("%g" % cant), tipico=("%g" % tipico))}
    return None


def validar_precio(articulo: dict, precio, lang: str | None = None) -> dict | None:
    """Precio del comprobante contra el costo del catálogo (regla histórica de
    chequeos(), acá para que la use también la voz)."""
    try:
        p = float(precio)
    except (TypeError, ValueError):
        return None
    costo = articulo.get("costo_iva")
    if not p or not costo:
        return None
    razon = (p * 1.21) / float(costo)      # el precio de factura viene neto
    if razon > RAZON_PRECIO or razon < 1 / RAZON_PRECIO:
        return {"tipo": "precio_escala", "sugerido": None,
                "detalle": _t("core.comp.chk_precio", lang,
                              producto=articulo.get("descripcion", "?"),
                              precio=p, costo=costo)}
    return None


# =============================================================================
# 3 · La pasada completa sobre una extracción (visión o voz)
# =============================================================================

def validar_items(items: list[dict], *, pedidos: dict | None = None,
                  resolver=None, lang: str | None = None) -> list[dict]:
    """Marca cada ítem sospechoso con `sospecha` y devuelve la lista de avisos.

    `pedidos` = {codigo: cantidad} de la orden de compra, si hay.
    `resolver` = función item → artículo del catálogo (la de comprobantes).
    """
    if resolver is None:
        catalogo = {int(a["codigo"]): a for a in store.raw_actual()}

        def resolver(it):                                   # noqa: F811
            cod = it.get("codigo")
            return catalogo.get(int(cod)) if cod is not None else None

    historial = _historial_cantidades()
    avisos = []
    for it in items or []:
        art = resolver(it)
        if not art:
            continue
        pedido = (pedidos or {}).get(int(art["codigo"]))
        s = validar_cantidad(art, it.get("cantidad"), pedido=pedido,
                             historial=historial.get(int(art["codigo"])), lang=lang)
        if s is None:
            s = validar_precio(art, it.get("precio_unitario"), lang=lang)
        if s:
            it["sospecha"] = s          # viaja al frontend: el ítem se pinta
            avisos.append({**s, "codigo": art["codigo"]})
        else:
            it.pop("sospecha", None)    # el humano corrigió: la sospecha se va
    return avisos


def bloqueantes(avisos: list[dict]) -> list[dict]:
    """Cuáles de estos avisos NO pueden persistirse sin que un humano los toque.

    Un precio raro se muestra y se sigue (la factura puede tener un precio raro
    de verdad). Una CANTIDAD implausible no: es la que mueve el stock.
    """
    return [a for a in avisos if str(a.get("tipo", "")).startswith("cantidad_")]

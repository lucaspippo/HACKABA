"""
escena.py · LA ESCENA DEL RECLAMO — ocho nodos, colocados, y nada más.

POR QUÉ ESTO NO ES EL GRAFO.

El cerebro (`core/grafo.py`) tiene 605 entidades y corre un layout de fuerzas.
Con seiscientos nodos eso está bien: el núcleo denso emerge solo y esa
emergencia ES parte de lo que se muestra. Con ocho nodos es lo peor posible —
la simulación los empuja, los junta, tiembla, y las etiquetas se pisan entre
ellas. Medido en vivo: nodos de 2 px, imposibles de tocar, y etiquetas
ilegibles.

Así que para el caso del reclamo la posición **se decide**, no se gana. Y se
decide con un sentido: se lee de izquierda a derecha como una frase.

    QUIÉN LO DIJO  →  QUÉ PASÓ  →  A QUIÉN  →  QUÉ EXIGE

Abajo, separado por una línea, el otro proveedor con su propia regla. No es
parte del reclamo: está para que se vea que **pide otra cosa**. Esa comparación
es el caso entero — «cada proveedor tiene su procedimiento y no está escrito en
ningún lado».

NADA ACÁ SE INVENTA. Las ocho piezas salen de donde ya estaban: la nota de
`notas`, las dos reglas de `conocimiento`, la orden de `esquema`, el producto
de `store`, la entrega de `recepciones`. Este módulo las ACOMODA; el que las
cruza sigue siendo `core/cruces.py::_cruce_reclamo_devolucion`.

Las coordenadas van en un lienzo de 1000×560 y el frente las escala. Se
eligieron a mano para que ningún nodo toque a otro y ninguna etiqueta caiga
sobre una línea.
"""
from __future__ import annotations

import datetime

import i18n

from . import conocimiento, deposito, esquema, notas, store
from .fechas import hoy, parse_fecha

# El lienzo lógico. El frente hace viewBox="0 0 1000 560" y escala a lo que
# haya — así la escena se ve igual en un monitor y en un proyector.
ANCHO, ALTO = 1000, 560

# La línea que separa el caso del contraste.
Y_SEPARADOR = 400

PROVEEDOR_CASO = "Lácteos Campo Alegre"
PROVEEDOR_CONTRASTE = "Frigorífico La Ribera"


def _t(key: str, lang: str | None = None, **params) -> str:
    return i18n.t(key, lang, **params)


def _regla_de(proveedor: str) -> dict | None:
    """La pieza de conocimiento con el procedimiento de ese proveedor."""
    for p in conocimiento.listar():
        if p.get("efecto") != "exige_evidencia":
            continue
        ent = (p.get("entidad") or "").lower()
        if ent and ent in proveedor.lower():
            return p
    return None


def _requisitos_leibles(regla: dict, lang: str) -> str:
    reclamo = (regla.get("params") or {}).get("reclamo") or {}
    nombres = [_t(f"escena.req_{r}", lang) for r in (reclamo.get("requisitos") or [])]
    if not nombres:
        return "—"
    if len(nombres) == 1:
        return nombres[0]
    return ", ".join(nombres[:-1]) + _t("escena.y", lang) + nombres[-1]


def _ultima_entrega(proveedor: str, codigo) -> str | None:
    """Cuándo llegó físicamente. NO es la fecha de la orden: se ordena un día y
    se recibe otro, y el plazo del reclamo corre desde que llegó."""
    mejor = None
    for f in esquema.filas("recepciones"):
        if (f.get("proveedor") or "") != proveedor:
            continue
        if codigo is not None and f.get("codigo") != codigo:
            continue
        fecha = f.get("fecha")
        if fecha and (mejor is None or fecha > mejor):
            mejor = fecha
    return mejor


def plazo(regla: dict, entrega: str | None, lang: str = "es") -> dict:
    """La ventana para reclamar: desde que la mercadería llegó.

    Es la línea que se dice en voz alta, así que sale de una resta entre dos
    fechas reales y no de un texto escrito a mano. Si falta la entrega, se dice
    que falta en vez de inventar un número.
    """
    dias = ((regla.get("params") or {}).get("reclamo") or {}).get("plazo_dias")
    f_ent = parse_fecha(entrega)
    if not f_ent or dias is None:
        return {"hay": False, "texto": _t("escena.plazo_sin_fecha", lang)}
    vence = f_ent + datetime.timedelta(days=int(dias))
    quedan = (vence - hoy()).days
    return {
        "hay": True,
        "entrega": f_ent.isoformat(),
        "vence": vence.isoformat(),
        "dias_plazo": int(dias),
        "quedan": quedan,
        "vencido": quedan < 0,
        # «La entrega fue el 05/07. Quedan 3 días para reclamar.»
        "texto": _t("escena.plazo", lang, entrega=f"{f_ent:%d/%m}", quedan=quedan)
        if quedan > 0 else
        _t("escena.plazo_hoy", lang, entrega=f"{f_ent:%d/%m}") if quedan == 0 else
        _t("escena.plazo_vencido", lang, entrega=f"{f_ent:%d/%m}", dias=abs(quedan)),
    }


def _nodo(nid, tipo, x, y, **extra) -> dict:
    return {"id": nid, "tipo": tipo, "x": x, "y": y, **extra}


def reclamo(lang: str = "es") -> dict:
    """La escena completa: ocho nodos colocados, sus aristas y el plazo."""
    # --- las piezas, de donde ya estaban --------------------------------
    nota = next((n for n in notas.listar(tipo="incidencia_entrega")
                 if (n.get("proveedor") or "") == PROVEEDOR_CASO), None)
    regla_caso = _regla_de(PROVEEDOR_CASO)
    regla_otro = _regla_de(PROVEEDOR_CONTRASTE)
    if not (nota and regla_caso and regla_otro):
        return {"disponible": False}

    producto_nombre = nota.get("producto")
    art = next((a for a in store.raw_actual()
                if (a.get("descripcion") or "") == producto_nombre), None)
    codigo = art.get("codigo") if art else None

    orden = next((oc for oc in esquema.filas("ordenes_compra")
                  if (oc.get("estado") or "") == "abierta"
                  and (oc.get("proveedor") or "") == PROVEEDOR_CASO), None)

    lote = next((f for f in deposito._filas()
                 if (f.get("producto") or "") == producto_nombre), None)

    entrega = _ultima_entrega(PROVEEDOR_CASO, codigo)
    el_plazo = plazo(regla_caso, entrega, lang)

    r_caso = (regla_caso.get("params") or {}).get("reclamo") or {}
    r_otro = (regla_otro.get("params") or {}).get("reclamo") or {}
    o_caso = regla_caso.get("origen") or {}
    o_otro = regla_otro.get("origen") or {}

    # --- las posiciones, decididas --------------------------------------
    # La fila de arriba se lee como una frase. Las x están separadas 230-250 px
    # para que ni el post-it (150 de ancho) ni la tarjeta de regla (170) se
    # toquen con el vecino.
    nodos = [
        _nodo("persona", "persona", 96, 176,
              nombre=_nombre_de(nota.get("autor")),
              rol=_rol_de(nota.get("autor"))),
        _nodo("nota", "nota", 392, 158,
              texto=notas.texto_en(nota, lang),
              canal=nota.get("canal"), autor=nota.get("autor"),
              fecha=nota.get("fecha")),
        _nodo("producto", "producto", 706, 142,
              nombre=producto_nombre, lote=(lote or {}).get("lote")),
        _nodo("proveedor", "proveedor", 404, 400, nombre=PROVEEDOR_CASO),
        _nodo("regla", "regla", 880, 250,
              texto=regla_caso.get("texto"),
              requisitos=_requisitos_leibles(regla_caso, lang),
              canal=r_caso.get("canal"), plazo_dias=r_caso.get("plazo_dias"),
              quien=_nombre_de(o_caso.get("quien")), cuando=o_caso.get("cuando")),
        _nodo("orden", "orden", 150, 396,
              numero=(orden or {}).get("numero"),
              fecha=(orden or {}).get("fecha")),
        # EL ÚLTIMO ESLABÓN: el reclamo SALE. Sin esto la cadena terminaba
        # en la regla y parecía que el sistema entrega un informe. El producto
        # se vende justamente por lo contrario — PRODUCT.md, The Action
        # Principle: un proceso que termina en un informe está incompleto.
        _nodo("envio", "envio", 726, 452,
              canal=r_caso.get("canal"),
              destinatario=PROVEEDOR_CASO,
              adjuntos=_requisitos_leibles(regla_caso, lang)),
    ]

    # --- las aristas, en el ORDEN en que se trazan -----------------------
    # El orden importa: es la secuencia del show. Cada una se dibuja creciendo
    # de origen a destino, no aparece entera.
    aristas = [
        {"de": "persona", "a": "nota", "rel": "dijo",
         "etiqueta": _t("escena.rel_dijo", lang, canal=_canal_leible(nota.get("canal"), lang)),
         "curva": -0.16, "dx": -16},
        {"de": "nota", "a": "producto", "rel": "menciona",
         "etiqueta": _t("escena.rel_que_llego", lang), "curva": -0.26},
        {"de": "nota", "a": "proveedor", "rel": "menciona",
         "etiqueta": _t("escena.rel_de_quien", lang), "curva": 0.24,
         "dx": -34},
        {"de": "proveedor", "a": "producto", "rel": "provee",
         "etiqueta": _t("escena.rel_provee", lang), "curva": 0.3},
        {"de": "proveedor", "a": "orden", "rel": "ordena",
         "etiqueta": _t("escena.rel_ordena", lang), "curva": 0.18},
        # LOS DESPLAZAMIENTOS DE ETIQUETA (dx/dy) no son decoracion: tres
        # aristas llegan al proveedor desde abajo y sus puntos medios caen casi
        # encima. Sin correrlas, «exige» se lee pisada con «se envia por mail»
        # y con la tarjeta verde. Se corrigen aca, junto a las posiciones, que
        # es donde vive el resto de lo decidido a mano.
        {"de": "regla", "a": "proveedor", "rel": "exige",
         "etiqueta": _t("escena.rel_exige", lang),
         "curva": -0.2, "fuerte": True, "dy": -30},
        # y el cierre: el reclamo armado sale al proveedor, por donde ese
        # proveedor pide y con lo que ese proveedor pide
        {"de": "regla", "a": "envio", "rel": "arma",
         "etiqueta": _t("escena.rel_arma", lang), "curva": 0.2, "dx": 46},
        {"de": "envio", "a": "proveedor", "rel": "envia",
         "etiqueta": _t("escena.rel_envia", lang,
                        canal=_canal_leible(r_caso.get("canal"), lang)),
         # La caja del envio tiene ancho AUTO (crece con el texto de la regla),
         # asi que esta etiqueta se corre bien a la izquierda para no quedar
         # debajo de ella. Lo verifica scripts/revisar_escena.py.
         "curva": 0.26, "fuerte": True, "dx": -54, "dy": 30},
    ]

    # qué tiene y qué falta, para el encabezado
    tiene, falta = [], []
    for r in (r_caso.get("requisitos") or []):
        etiqueta = _t(f"escena.req_{r}", lang)
        if r == "numero_remito" and orden:
            tiene.append({"que": etiqueta, "valor": orden.get("numero")})
        elif r == "numero_lote" and lote:
            tiene.append({"que": etiqueta, "valor": lote.get("lote")})
        else:
            falta.append(etiqueta)

    return {
        "disponible": True,
        "id": "reclamo",
        "titulo": _t("escena.titulo", lang, proveedor=PROVEEDOR_CASO),
        "lienzo": {"ancho": ANCHO, "alto": ALTO},
        "nodos": nodos,
        "aristas": aristas,
        "plazo": el_plazo,
        "tiene": tiene,
        "falta": falta,
        # La procedencia, para mostrarla dentro de la respuesta de Ángela.
        # El id de la pieza de conocimiento, para que el guion pueda CITARLA
        # en el texto ([·](memoria:k23)) y el chat pinte el cerebrito.
        "regla_id": regla_caso.get("id"),
        # lo que aparece al TOCAR el producto (precargado: ver expansion())
        "expansion": expansion(lang),
        "producto": producto_nombre,
        "cruce_id": "cruce_reclamo_devolucion",
        "procedencia": {
            "consulto": [_t("escena.fuente_notas", lang),
                         _t("escena.fuente_ordenes", lang),
                         _t("escena.fuente_deposito", lang)],
            "recordo": {
                "texto": regla_caso.get("texto"),
                "quien": _nombre_de(o_caso.get("quien")),
                "cuando": o_caso.get("cuando"),
                "veces": regla_caso.get("veces_aplicada"),
            },
        },
    }


# =============================================================================
# LO QUE HAY DETRAS DEL CAMINO — el nodo que se toca y se abre.
#
# EL PROBLEMA QUE RESUELVE. Mirando la escena, ocho nodos prolijos, es razonable
# pensar que eso es TODO lo que el sistema tiene. No lo es: es un recorte de 605
# entidades. Tocando un nodo y viendo aparecer el resto de sus relaciones, el
# grafo pasa de «ocho cosas dibujadas» a «una porcion de un cerebro».
#
# POR QUE EL PRODUCTO Y NO EL PROVEEDOR. Medido sobre el grafo real:
#
#   Lacteos Campo Alegre   grado 83  — pero 73 son `provee` a productos.
#                                      Expandirlo son 73 puntos iguales: una
#                                      nube monotona que no dice nada nuevo.
#   LECHE ENTERA CAMPO     grado 14  — repartido en OCHO tipos distintos:
#   ALEGRE 1L (X12U)                   rubro, proveedor, 3 locales, 4 coventas,
#                                      2 clientes, remito, ubicacion, nota.
#
# El segundo es el que cuenta algo: el mismo producto vive en la venta, en la
# co-compra, en la logistica, en el deposito y en las notas del equipo. Ocho
# cajas rotas dejan de ser ocho cajas.
#
# Tres de esas catorce ya estan en la escena (proveedor, nota, remito), asi que
# al tocar aparecen ONCE nodos nuevos. Alcanza para que se note y no tanto como
# para tapar lo que ya estaba.
NODO_EXPANDIBLE = "producto"
TOPE_EXPANSION = 14          # si algun dia hubiera mas, se corta acá

# Como se leen las relaciones del grafo, en palabras.
_REL_LEIBLE = {
    "compra": "lo compra", "coventa": "se vende junto con", "guarda": "guardado en",
    "menciona": "lo menciona", "pertenece": "es de", "pide": "lo pide",
    "provee": "lo provee", "vende": "se vende en",
}

# El orden en que se reparten alrededor: agrupados por tipo, para que el ojo
# lea familias y no una lista.
_ORDEN_TIPOS = ("rubro", "local", "cliente", "producto", "ubicacion")


def expansion(lang: str = "es") -> dict:
    """Las otras relaciones del producto del caso, ya colocadas.

    Va DENTRO de la respuesta de `reclamo()` y no en un endpoint aparte: se
    toca en vivo delante de un jurado, y una llamada de red en ese momento es
    un riesgo que no compra nada. Vienen precargadas y el click solo las
    muestra.
    """
    from . import grafo as _grafo

    nota = next((n for n in notas.listar(tipo="incidencia_entrega")
                 if (n.get("proveedor") or "") == PROVEEDOR_CASO), None)
    if not nota:
        return {}
    producto_nombre = nota.get("producto")
    art = next((a for a in store.raw_actual()
                if (a.get("descripcion") or "") == producto_nombre), None)
    if not art:
        return {}
    pid = f"prod:{art.get('codigo')}"

    g = _grafo.completo(lang)
    nodos_g = {n["id"]: n for n in g["nodos"]}
    if pid not in nodos_g:
        return {}

    # lo que YA se ve en la escena no se repite
    ya = {"proveedor", "nota", "remito"}
    vecinos = []
    for a in g["aristas"]:
        otro = (a["target"] if a["source"] == pid
                else a["source"] if a["target"] == pid else None)
        if otro is None or otro not in nodos_g:
            continue
        n = nodos_g[otro]
        if n["tipo"] in ya:
            continue
        vecinos.append({"id": otro, "tipo": n["tipo"],
                        "nombre": n.get("nombre") or otro,
                        "rel": _REL_LEIBLE.get(a["rel"], a["rel"])})

    vecinos.sort(key=lambda v: (_ORDEN_TIPOS.index(v["tipo"])
                                if v["tipo"] in _ORDEN_TIPOS else 99, v["nombre"]))
    vecinos = vecinos[:TOPE_EXPANSION]
    if not vecinos:
        return {}

    # --- las posiciones, decididas (igual que el resto de este modulo) -------
    # Un abanico arriba y a la derecha del producto: hacia abajo-izquierda esta
    # el resto de la escena y no se toca. Dos radios para que no queden todas
    # sobre la misma circunferencia, que se lee como un reloj.
    import math
    cx, cy = 706, 142
    n = len(vecinos)
    colocados = []
    for i, v in enumerate(vecinos):
        # SOLO hacia arriba y a la derecha, de -150° a 0°. Abajo esta la
        # tarjeta de la regla (880,250) y el envio (726,452): bajar de la
        # horizontal ponia nodos encima de las dos. Lo verifica
        # scripts/revisar_escena.py, que tambien mira la expansion.
        ang = math.radians(-150 + (150 * i / max(1, n - 1)))
        r = 200 if i % 2 == 0 else 300
        colocados.append({**v,
                          "x": round(cx + r * math.cos(ang)),
                          "y": round(cy + r * math.sin(ang))})

    xs = [c["x"] for c in colocados] + [0, ANCHO]
    ys = [c["y"] for c in colocados] + [0, ALTO]
    margen = 90
    vb = [min(xs) - margen, min(ys) - margen,
          max(xs) - min(xs) + margen * 2, max(ys) - min(ys) + margen * 2]

    return {
        "desde": "producto",
        "titulo": _t("escena.expansion_titulo", lang, producto=producto_nombre),
        "nodos": colocados,
        # El lienzo se agranda al abrir: ese alejarse ES el mensaje —lo que
        # estabas mirando era un recorte.
        "lienzo_abierto": vb,
    }


def _nombre_de(usuario: str | None) -> str:
    if not usuario:
        return "—"
    try:
        import auth
        u = auth.USUARIOS.get(str(usuario).strip().lower())
        if u and u.get("nombre"):
            return u["nombre"]
    except Exception:  # noqa: BLE001
        pass
    return str(usuario).title()


def _rol_de(usuario: str | None) -> str:
    try:
        import auth
        return (auth.USUARIOS.get(str(usuario or "").strip().lower()) or {}).get("rol") or ""
    except Exception:  # noqa: BLE001
        return ""


def _canal_leible(canal: str | None, lang: str) -> str:
    return _t(f"escena.canal_{canal or 'reporte'}", lang)

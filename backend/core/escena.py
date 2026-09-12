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
import re

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
        # la pieza que explica POR QUE existe esa regla (el reclamo rechazado)
        "regla_origen_id": _origen_de(regla_caso),
        # QUE APARECE AL TOCAR CADA NODO, precargado (ver expansion()).
        # Indexado por id de nodo de la escena: hoy el producto y el proveedor.
        "expansiones": {k: v for k, v in
                        (("producto", expansion(lang)),
                         ("proveedor", expansion_proveedor(lang))) if v},
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
TOPE_POR_GRUPO = 4           # un racimo mas alto que esto ya no se lee de un vistazo

# Como se leen las relaciones del grafo, en palabras.
_REL_LEIBLE = {
    "compra": "lo compra", "coventa": "se vende junto con", "guarda": "guardado en",
    "menciona": "lo menciona", "pertenece": "es de", "pide": "lo pide",
    "provee": "lo provee", "vende": "se vende en",
}

# Los GRUPOS: una relacion, un racimo.
#
# EN DOS COLUMNAS A LA DERECHA, no en abanico alrededor del producto. El
# producto esta en (706,142), o sea pegado al borde superior derecho del
# lienzo: cualquier racimo puesto "alrededor" cae encima del post-it de la nota
# o de la tarjeta de la regla, y correrlo mas lejos lo empuja mas adentro del
# caso. Probado con cuatro configuraciones de angulo y radio: ninguna daba cero.
#
# A la derecha hay lugar vacio de sobra —el caso termina en x≈965— y el lienzo
# se agranda al abrir igual. Ademas se lee mejor: cinco bloques en columna se
# recorren de arriba abajo, un abanico obliga a girar la cabeza.
_COLUMNAS = (
    # (x, [relaciones de esa columna, de arriba a abajo])
    (1090, ("se vende junto con", "se vende en")),
    (1420, ("lo compra", "es de", "guardado en")),
)
_Y_INICIAL = -60          # arranca arriba del producto
_SEPARACION_GRUPO = 54    # aire entre un racimo y el siguiente
# Cuanto ocupa cada nodo de la expansion, de arriba a abajo.
# Ya no es una pildora de 30: son FORMAS —disco, rombo, tarjeta— con el nombre
# DEBAJO, igual que los nodos del caso. Eso pide mas aire vertical.
_ALTO_CHIP = 82


def _nombre_corto(nombre: str) -> str:
    """El nombre sin el gramaje ni el pack.

    «MANTECA SANTA CLARA 200G (X30U)» -> «MANTECA SANTA CLARA». Un nombre
    cortado con puntos suspensivos se lee como un error, no como una
    abreviatura, asi que en vez de truncar se saca lo que no identifica al
    producto: el envase. Si aun asi no entra, entra igual — la chip crece.
    """
    n = re.sub(r"\s*\([^)]*\)\s*$", "", nombre or "").strip()
    n = re.sub(r"\s+X\d+\s*$", "", n, flags=re.I)
    n = re.sub(r"\s+\d+([.,]\d+)?\s*(KG|G|GR|ML|L|CC|U)\s*$", "", n, flags=re.I)
    return n.strip() or (nombre or "")


def expansion(lang: str = "es") -> dict:
    """Las otras relaciones del producto del caso, ya colocadas.

    Va DENTRO de la respuesta de `reclamo()` y no en un endpoint aparte: se
    toca en vivo delante de un jurado, y una llamada de red en ese momento es
    un riesgo que no compra nada. Vienen precargadas y el click solo las
    muestra.

    AGRUPADAS POR RELACION, no repartidas en abanico. Once nodos sueltos
    alrededor de uno son once cosas para leer y ninguna se lee; agrupadas son
    CINCO: «se vende junto con estos cuatro», «se vende en estas tres». La
    etiqueta va una vez por racimo en vez de una por nodo, que ademas era de
    donde salian la mitad de los solapamientos.
    """
    import math

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

    ya = {"proveedor", "nota", "remito"}     # lo que ya se ve en la escena
    por_rel = {}
    for a in g["aristas"]:
        otro = (a["target"] if a["source"] == pid
                else a["source"] if a["target"] == pid else None)
        if otro is None or otro not in nodos_g:
            continue
        n = nodos_g[otro]
        if n["tipo"] in ya:
            continue
        rel = _REL_LEIBLE.get(a["rel"], a["rel"])
        por_rel.setdefault(rel, []).append(
            {"id": otro, "tipo": n["tipo"], "nombre": _nombre_corto(n.get("nombre") or otro)})

    grupos, total = [], 0
    for x, rels in _COLUMNAS:
        y = _Y_INICIAL
        for rel in rels:
            miembros = por_rel.get(rel) or []
            if not miembros:
                continue
            miembros.sort(key=lambda m: m["nombre"])
            miembros = miembros[:TOPE_POR_GRUPO]
            total += len(miembros)
            for i, m in enumerate(miembros):
                m["x"], m["y"] = x, y + 62 + i * _ALTO_CHIP
            grupos.append({"rel": rel, "x": x, "y": y, "nodos": miembros})
            y += 62 + len(miembros) * _ALTO_CHIP + _SEPARACION_GRUPO

    if not grupos:
        return {}

    # El encuadre, ajustado a los extremos REALES. Con un margen generoso a
    # ambos lados el lienzo se iba a 1940 de ancho y la escena quedaba al 51%:
    # el caso —que es lo que hay que seguir leyendo— se volvia ilegible. Se mide
    # el ancho de cada chip y se deja poco aire.
    planos = [m for gr in grupos for m in gr["nodos"]]
    medio_chip = lambda n: max(112.0, len(n) * 5.75 + 46) / 2
    x0 = min([0] + [m["x"] - medio_chip(m["nombre"]) for m in planos])
    x1 = max([ANCHO] + [m["x"] + medio_chip(m["nombre"]) for m in planos])
    y0 = min([0] + [gr["y"] - 14 for gr in grupos])
    y1 = max([ALTO] + [m["y"] + 46 for m in planos])
    m_ = 46
    vb = [x0 - m_, y0 - m_, (x1 - x0) + m_ * 2, (y1 - y0) + m_ * 2]

    return {
        "desde": "producto",
        "titulo": _t("escena.expansion_titulo", lang, producto=producto_nombre),
        "grupos": grupos,
        "lienzo_abierto": vb,
    }


def expansion_proveedor(lang: str = "es") -> dict:
    """LAS REGLAS DE ESTE PROVEEDOR, colgando del rombo.

    La respuesta cita UNA regla. Pero el negocio le enseño CUATRO cosas sobre
    Lacteos Campo Alegre, y que se vean juntas cambia lo que se entiende: no es
    que alguien cargo un dato suelto para que el demo funcione — hay un cuerpo
    de conocimiento sobre cada proveedor, y la respuesta uso la que
    correspondia. Son cuatro, asi que entran de una y no hace falta agrupar.
    """
    from . import grafo as _grafo

    g = _grafo.completo(lang)
    nodos_g = {n["id"]: n for n in g["nodos"]}
    pid = next((nid for nid, n in nodos_g.items()
                if n["tipo"] == "proveedor"
                and (n.get("nombre") or "") == PROVEEDOR_CASO), None)
    if not pid:
        return {}

    reglas = []
    for a in g["aristas"]:
        otro = (a["target"] if a["source"] == pid
                else a["source"] if a["target"] == pid else None)
        if otro and nodos_g.get(otro, {}).get("tipo") == "conocimiento":
            reglas.append({"id": otro, "tipo": "conocimiento",
                           "nombre": nodos_g[otro].get("nombre") or otro})
    if not reglas:
        return {}
    reglas.sort(key=lambda r: r["id"])
    reglas = reglas[:5]

    # DEBAJO del rombo, fuera del lienzo base. Pegado al proveedor caia sobre
    # el propio rombo y sobre la orden de compra (verificado: 3 choques). El
    # lienzo se agranda al abrir igual, asi que hay lugar abajo y ahi no hay
    # nada que pisar.
    x, y0 = 540, 600
    for i, r in enumerate(reglas):
        r["x"], r["y"] = x, y0 + i * _ALTO_CHIP
    grupos = [{"rel": _t("escena.rel_le_enseñaron", lang), "x": x, "y": y0 - 62,
               "nodos": reglas}]

    ancho_chip = lambda n: max(112.0, len(n) * 5.75 + 46)
    x0 = min([0] + [r["x"] - ancho_chip(r["nombre"]) / 2 for r in reglas])
    x1 = max([ANCHO] + [r["x"] + ancho_chip(r["nombre"]) / 2 for r in reglas])
    y1 = max([ALTO] + [r["y"] + 46 for r in reglas])
    m_ = 46
    return {
        "desde": "proveedor",
        "titulo": _t("escena.expansion_prov", lang, proveedor=PROVEEDOR_CASO),
        "grupos": grupos,
        "lienzo_abierto": [x0 - m_, -m_, (x1 - x0) + m_ * 2, y1 + m_ * 2],
    }


def _origen_de(regla: dict) -> str | None:
    """La pieza que cuenta de donde salio esta regla, si la hay.

    Se busca por entidad: otra pieza del mismo proveedor que NO sea la regla
    misma y que no exija evidencia — o sea, el relato del hecho que la origino.
    """
    ent = (regla.get("entidad") or "").strip().lower()
    if not ent:
        return None
    for p in conocimiento.listar():
        if p.get("id") == regla.get("id"):
            continue
        if (p.get("entidad") or "").strip().lower() != ent:
            continue
        if p.get("efecto") == "exige_evidencia":
            continue
        if "rechaz" in (p.get("texto") or "").lower():
            return p.get("id")
    return None


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

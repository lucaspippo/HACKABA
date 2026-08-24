"""
onboarding.py — lo que el que recién entra tiene que aprender, con datos REALES.

El dolor: cuando entra alguien nuevo al depósito tarda semanas en ser
productivo, porque el conocimiento de cómo se trabaja acá (dónde va cada cosa,
cada cuánto repone cada proveedor, qué se hace con una factura, qué reglas puso
el dueño) no está escrito en ningún lado: vive en la cabeza de los que llevan
años. Y como la rotación en trabajo físico es alta, ese costo se paga seguido.

PolPilot ya tiene ese conocimiento repartido en sus módulos. Este archivo no
inventa uno nuevo: lo JUNTA y lo deja consultable por el que recién entró.

    · ubicaciones  → core/deposito.py (el export del WMS: pasillo, rack, cámara)
    · reposición   → core/reposicion.py (los días que tarda cada proveedor) y
                     core/analisis.py (el ritmo real de venta de un producto)
    · reglas       → core/conocimiento.py ("lo que Aldo le enseñó a Ángela"),
                     ya filtrado a lo que ESTA persona puede ver
    · contactos    → el equipo real del tenant (auth.USUARIOS), por rol
    · procesos     → los pasos de los flujos que el producto REALMENTE tiene
                     (carga por foto, reporte de faltante, conteo, voz). Es el
                     único texto autoral del módulo, y está acá —en el código—
                     y no en el modelo, para que Ángela lo REDACTE pero no lo
                     invente. Cada proceso declara qué features necesita.

DETERMINISMO: todo lo que devuelve sale de un archivo de datos o del catálogo de
procesos de acá. Si un dato no está (no hay export de depósito, no hay ventas
validadas), se devuelve el hueco declarado (`hay_datos: False`) para que Ángela
lo diga en vez de rellenar.

SCOPE: la guía se arma PARA un usuario y se recorta con SUS features (las
efectivas, no las del seed). El de depósito ve el depósito; nadie ve por acá un
módulo que la matriz «Quién ve qué» no le dio.
"""
from __future__ import annotations

import unicodedata

from . import analisis, conocimiento, deposito, esquema, perfiles, reposicion, store

# Los procesos del oficio. Describen lo que el sistema hace HOY (cada paso tiene
# su contraparte en una pantalla real), en el orden en que se hacen. `need` son
# las features sin las cuales ese proceso no le sirve a la persona.
PROCESOS = [
    {
        "id": "recepcion",
        "need": ["cargar"],
        "pasos": [
            "Pedile el remito al que trae la mercadería antes de bajar nada.",
            "Sacale la foto desde «Cargar remito con foto»: Ángela lo lee y lo cruza "
            "solo contra la orden de compra que ya estaba en el sistema.",
            "Contá los bultos contra lo que dice el remito ANTES de firmar.",
            "Si falta algo o vino roto, no lo dejes pasar: reportalo en el momento; "
            "queda a tu nombre y el dueño lo ve en su panel.",
            "Guardá cada lote en su ubicación y cargá la fecha de vencimiento.",
        ],
        "pasos_en": [
            "Ask for the delivery note before anything comes off the truck.",
            "Photograph it from \"Load delivery note with a photo\": Ángela reads it and "
            "matches it against the purchase order already in the system.",
            "Count the pallets against the note BEFORE you sign.",
            "If something is missing or arrived damaged, don't let it through: report it "
            "right there; it is filed under your name and the owner sees it.",
            "Put every lot in its location and load the expiry date.",
        ],
    },
    {
        "id": "factura",
        "need": ["cargar"],
        "pasos": [
            "La factura la termina cargando administración, pero la foto la puede sacar "
            "cualquiera: no la dejes arriba de un escritorio.",
            "Sacale la foto en «Cargar datos»: Ángela la lee y la cruza contra el remito "
            "y contra la orden de compra.",
            "Revisá lo que leyó (proveedor, número, total) y recién ahí dale el OK: "
            "nada entra al sistema sin que un humano confirme.",
            "Si el proveedor o el total no coinciden con lo que entró al depósito, "
            "avisá antes de confirmar.",
        ],
        "pasos_en": [
            "Admin ends up filing the invoice, but anyone can take the photo: don't leave "
            "it sitting on a desk.",
            "Photograph it in \"Load data\": Ángela reads it and matches it against the "
            "delivery note and the purchase order.",
            "Check what she read (supplier, number, total) and only then approve: nothing "
            "enters the system without a human confirming.",
            "If the supplier or the total don't match what actually came in, flag it before "
            "confirming.",
        ],
    },
    {
        "id": "faltante",
        "need": ["deposito"],
        "pasos": [
            "Reportalo el mismo día desde «Reportar diferencia o faltante», en «Mi día».",
            "Poné producto, cantidad y motivo: roto, faltante, vencido o no pedido.",
            "Si tenés las manos ocupadas, decilo por voz: Ángela te muestra qué entendió "
            "y lo manda recién cuando vos confirmás.",
            "Queda registrado con tu nombre y le llega al encargado y al dueño. No hace "
            "falta que se lo cuentes a nadie por WhatsApp.",
        ],
        "pasos_en": [
            "Report it the same day from \"Report a shortage or difference\", in \"My day\".",
            "Enter product, quantity and reason: damaged, missing, expired or not ordered.",
            "If your hands are full, say it out loud: Ángela shows you what she understood "
            "and only sends it once you confirm.",
            "It is filed under your name and reaches the manager and the owner. No need to "
            "tell anyone over WhatsApp.",
        ],
    },
    {
        "id": "conteo",
        "need": ["deposito"],
        "pasos": [
            "Los conteos son cíclicos: cada semana se cuenta una parte del depósito, "
            "no todo de una vez.",
            "Si el estante dice una cosa y el sistema otra, marcá el conteo con lo que "
            "contaste de verdad.",
            "No corrijas el stock por tu cuenta: las correcciones en lote las aprueba "
            "el dueño.",
            "Las diferencias quedan a la vista en «Datos a corregir» hasta que alguien "
            "las resuelve.",
        ],
        "pasos_en": [
            "Counts are cyclical: each week covers a part of the warehouse, not all of it.",
            "If the shelf says one thing and the system another, log the count with what you "
            "actually counted.",
            "Don't fix stock on your own: bulk corrections are approved by the owner.",
            "Differences stay visible under \"Data to fix\" until someone resolves them.",
        ],
    },
    {
        "id": "ubicar",
        "need": ["deposito"],
        "pasos": [
            "Para saber dónde está algo, preguntale a Ángela «¿dónde está …?»: te da "
            "pasillo, rack, lote y vencimiento del último export del depósito.",
            "Lo que va a frío va a cámara; lo seco a pasillo y rack.",
            "Primero sale lo que vence antes: si hay dos lotes del mismo producto, "
            "agarrá el de fecha más corta.",
            "Si movés algo de lugar, avisale al encargado: si no, el sistema queda "
            "diciendo una ubicación que ya no es.",
        ],
        "pasos_en": [
            "To find something, ask Ángela \"where is …?\": she gives you aisle, rack, lot "
            "and expiry from the latest warehouse export.",
            "Chilled goods go to the cold rooms; dry goods to aisle and rack.",
            "Shortest expiry goes out first: with two lots of the same product, take the one "
            "that expires sooner.",
            "If you move something, tell the manager: otherwise the system keeps pointing at "
            "a location that isn't true anymore.",
        ],
    },
    {
        "id": "preguntar",
        "need": [],
        "pasos": [
            "Todo lo que no sepas, preguntáselo a Ángela desde «Mi día»: sabe el "
            "catálogo, el depósito, los proveedores y las reglas de la casa.",
            "Si el dato no existe, te lo dice — no te inventa una respuesta.",
            "Lo que es decisión (precios, crédito, correcciones de stock) no lo resuelve "
            "ella ni vos: lo aprueba el dueño.",
            "Lo que sí es tuyo: reportar lo que ves en el piso, y hacerlo el mismo día.",
        ],
        "pasos_en": [
            "Anything you don't know, ask Ángela from \"My day\": she knows the catalogue, "
            "the warehouse, the suppliers and the house rules.",
            "If the data doesn't exist she says so — she won't make an answer up.",
            "Decisions (prices, credit, stock corrections) are neither hers nor yours: the "
            "owner approves them.",
            "What IS yours: reporting what you see on the floor, and doing it the same day.",
        ],
    },
]

# A quién se le avisa qué. El rol se busca por TEXTO (igual que lib/roles.js):
# una persona nueva con el mismo rol hereda el contacto sin tocar código.
CONTACTOS = [
    {"id": "deposito", "match": ("encargado de dep", "encargada de dep")},
    {"id": "compras", "match": ("compras",)},
    {"id": "administracion", "match": ("administraci",)},
    {"id": "dueno", "match": ("dueño", "dueno")},
]


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


# --- las piezas ---------------------------------------------------------------

def ubicaciones() -> dict:
    """El mapa del depósito tal como lo dice el export: cada ubicación con
    cuántos lotes tiene y un par de ejemplos de lo que se guarda ahí."""
    filas = esquema.filas("deposito")
    if not filas:
        return {"hay_datos": False, "ubicaciones": []}
    por_ubi: dict[str, dict] = {}
    for f in filas:
        u = f.get("ubicacion") or ""
        if not u:
            continue
        g = por_ubi.setdefault(u, {"ubicacion": u, "lotes": 0, "productos": set(), "ejemplos": []})
        g["lotes"] += 1
        g["productos"].add(f.get("codigo"))
        if len(g["ejemplos"]) < 3 and f.get("producto"):
            g["ejemplos"].append(f["producto"])
    out = []
    for g in por_ubi.values():
        out.append({"ubicacion": g["ubicacion"], "lotes": g["lotes"],
                    "productos": len(g["productos"]), "ejemplos": g["ejemplos"]})
    out.sort(key=lambda x: x["ubicacion"])
    frio = [x["ubicacion"] for x in out if "camara" in _norm(x["ubicacion"])]
    return {"hay_datos": True, "ubicaciones": out, "total": len(out),
            "lotes": len(filas), "frio": frio}


def donde_esta(texto: str) -> dict:
    """Dónde está guardado un producto — el dato real del depósito, no un
    recuerdo. Delega en el mismo lector que usa Ángela para el dueño."""
    if not deposito.hay_datos():
        return {"hay_datos": False, "resultados": []}
    res = deposito.ubicacion_de(texto or "")
    return {"hay_datos": True, "buscado": texto, "resultados": res[:12],
            "encontrados": len(res)}


def proveedores() -> dict:
    """Cada cuánto llega el pedido de cada proveedor: los días que tarda desde
    que se emite la orden hasta que la mercadería entra al depósito."""
    conds = reposicion.condiciones()
    out = []
    for c in conds:
        lead, propio = reposicion.dias_reposicion(c.get("proveedor"))
        out.append({
            "proveedor": c.get("proveedor"),
            "dias_reposicion": lead,
            "dato_propio": propio,
            "nota": c.get("nota"),
            "frecuencia_lista_dias": c.get("frecuencia_lista_dias"),
        })
    out.sort(key=lambda x: x["dias_reposicion"])
    default, _ = reposicion.dias_reposicion(None)
    return {"hay_datos": bool(out), "proveedores": out, "dias_default": default}


def cada_cuanto(texto: str, limite: int = 4) -> dict:
    """Cada cuánto se repone un producto: su ritmo REAL de venta (unidades de
    los últimos 12 meses), los días de stock que quedan a ese ritmo y lo que
    tarda su proveedor. Las tres cosas juntas son la respuesta honesta; ninguna
    sola alcanza. Sin ventas validadas se dice, no se estima."""
    t = _norm(texto)
    if not t:
        return {"encontrados": 0, "items": []}
    arts = [a for a in store.raw_actual()
            if str(a.get("codigo")) == t or t in _norm(a.get("descripcion"))]
    if not arts:
        return {"encontrados": 0, "items": []}
    u12 = analisis._unidades_por_codigo(365)
    hay_ventas = bool(u12)
    items = []
    for a in arts[:limite]:
        u = float(u12.get(a.get("codigo"), 0.0))
        ritmo = u / 365.0
        stock = float(a.get("stock") or 0)
        lead, propio = reposicion.dias_reposicion(a.get("proveedor"))
        items.append({
            "codigo": a.get("codigo"),
            "producto": a.get("descripcion"),
            "proveedor": a.get("proveedor") or None,
            "stock": stock,
            "unidades_12m": round(u, 2),
            "por_dia": round(ritmo, 3) if ritmo else 0,
            "dias_de_stock": round(stock / ritmo, 1) if ritmo > 0 else None,
            "dias_reposicion_proveedor": lead,
            "lead_es_dato_propio": propio,
        })
    return {"encontrados": len(arts), "items": items, "hay_ventas": hay_ventas}


def reglas(usuario: dict) -> list[dict]:
    """Las reglas del dueño que le APLICAN a esta persona: activas y dentro de
    su ámbito (core/conocimiento.visibles_para hace el recorte server-side)."""
    piezas = [p for p in conocimiento.visibles_para(usuario)
              if p.get("estado", "activo") == "activo"]
    return [conocimiento.resumen_pieza(p) for p in piezas]


def contactos() -> list[dict]:
    """A quién avisarle qué. Sale del equipo real del tenant, por rol."""
    import auth
    out = []
    for c in CONTACTOS:
        for u in auth.USUARIOS.values():
            if u.get("interno"):
                continue
            if any(m in _norm(u.get("rol")) for m in c["match"]):
                out.append({"para": c["id"], "username": u["username"],
                            "nombre": u["nombre"], "rol": u["rol"]})
                break
    return out


def procesos(feats: set[str]) -> list[dict]:
    """Los procesos que ESTA persona puede ejecutar de verdad (los que necesitan
    un módulo que no tiene, no se le enseñan: sería enseñarle un botón que no ve)."""
    return [{"id": p["id"], "pasos": p["pasos"], "pasos_en": p["pasos_en"]}
            for p in PROCESOS if all(f in feats for f in p["need"])]


# --- la guía completa ---------------------------------------------------------

def guia(usuario: dict) -> dict:
    """Todo lo que el que recién entró necesita, recortado a sus permisos.
    Es la fuente de la pantalla de onboarding Y de la tool de Ángela: un solo
    lugar, para que la pantalla y el chat nunca digan cosas distintas."""
    import auth
    username = usuario.get("username") or ""
    feats = set(usuario.get("features") or perfiles.features_efectivas(username))
    g = {
        "persona": {
            "username": username,
            "nombre": usuario.get("nombre"),
            "rol": usuario.get("rol"),
            "antiguedad": auth.antiguedad(username),
            "puesto": auth.puesto(username),
        },
        "procesos": procesos(feats),
        "reglas": reglas(usuario),
        "contactos": contactos(),
    }
    # Depósito e inventario van detrás de su módulo: la guía respeta la misma
    # matriz que el resto del producto, no una puerta lateral.
    g["ubicaciones"] = ubicaciones() if "deposito" in feats else {"hay_datos": False,
                                                                  "sin_modulo": True,
                                                                  "ubicaciones": []}
    g["reposicion"] = proveedores() if "inventario" in feats else {"hay_datos": False,
                                                                   "sin_modulo": True,
                                                                   "proveedores": []}
    return g

"""
mapa_operacion.py · The physical chain: where goods come from, where they
are, and where they go.

THE EXISTING MAP SHOWS THE SOURCES. THIS ONE SHOWS THE MERCHANDISE.

`MapaNegocio.jsx` draws the eight data domains and their crossings: it answers
*what crosses with what*. That is the product's differentiator and it is not
touched. But it lacks one bone: **where the stuff physically is**. A supplier
delivers, goods land in a warehouse zone, a truck loads them and leaves for a
customer. That route lived on no screen, and it is the one that carries the
flagship example:

    "The warehouse crew flagged twice that the cold room is full — and there
     is an open purchase order arriving exactly there."

That finding crosses three things that live in different places: **what the
team said** (a voice note), **the physical layer** (41 lots in that room) and
**the ERP** (the open order). Without the physical layer the crossing cannot
even be written down.

---

HOW IT IS BUILT

Three named layers, read left to right because that is how the business runs.
Position MEANS something: a node sits where it sits because of the moment of
the route it occupies, not because an algorithm placed it there.

    WHERE IT COMES FROM     WHERE IT IS             WHERE IT GOES
    ──────────────────    ────────────────────    ──────────────────────
    suppliers             ┌────────┬────────┐     trucks
    open orders           │ zone   │ zone   │     own branches
                          ├────[ LOGO ]─────┤     customers
                          │ zone   │ zone   │
                          └────────┴────────┘

**GROUP BEFORE DRAWING.** The warehouse holds 380 lots across 18 locations.
Drawn loose they are a smear. The cold rooms go as their own nodes — they are
the ones that hurt — and the fifteen aisles collapse into one node that opens
on click.

**TRANSIT IS A STATE, NOT A LABEL.** An order "on the road" is bultos that
left the warehouse and nobody confirmed at destination: they are in no node.
That is the map's only dashed red stroke, deliberately visible from across
the room.

**NOTHING IS INVENTED.** Every node carries `fuente` with the data section
and row count it came from, and every finding carries the `camino` of nodes
that produced it. When someone asks where a number came from, it opens.

**NUMBERS SHIP FORMATTED, PER LANGUAGE.** A node exposes `metricas: [{label,
valor, estado}]` with the value already written the way it reads. The screen
iterates and renders; it never computes or reformats. That contract is what
lets the same component serve another industry — or another language —
without touching it. Every user-facing string goes through i18n (house rule:
bilingual from day one), so `mapa(lang)` is computed and cached per language
via core/analisis_cache, same as /api/grafo and /api/analisis.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from collections import defaultdict
from functools import lru_cache

import i18n

from . import esquema, store
from .fechas import hoy, parse_fecha
from .paths import DATA_DIR, EMPRESA, LOGO, SISTEMA_GESTION

# How many days ahead the map looks to say "this expires soon". Thirty is the
# horizon something can still be done about: promote it, push it to the branch
# that rotates it, or call the customer who takes it.
DIAS_POR_VENCER = 30

# Zones that get a node of their own. The rest is grouped: they are shelving
# aisles, and fifteen aisle nodes tell nobody anything.
ZONAS_PROPIAS = ("cámara", "camara")

# Canonical (language-independent) name for the grouped aisles. It feeds node
# IDS, so it must never vary by language — only the label shown does.
GRUPO_PASILLOS = "Pasillos y racks"

# ERP labels that are NOT a physical point of sale.
NO_SON_BOCAS = ("consolidado",)

EN_TRANSITO = "en camino"

DIAS_RECIENTE = 7          # "this week": what is still fresh

# Customer channels. A distributor has hundreds of customers: drawn loose that
# is not a map, it is a phone book. They group by CHANNEL, which is how the
# sales side thinks of them, and the detail opens on click. Ids are stable;
# display names are localized at build time.
CANALES = [
    ("autoservicios", ("supermercado", "super", "autoservicio", "mercadito",
                       "minimercado")),
    ("gastronomia", ("bar", "comidas", "comedor", "hosteria", "hoteleria",
                     "bufete", "panaderia", "rotiseria")),
    ("despensas", ("despensa", "kiosco", "granja", "almacen")),
]
CANAL_OTROS = "otros"

# Channel chips: the three that come in FROM OUTSIDE go first — they are the
# ones no ERP captures, and the reading order of the chips tells the thesis
# without writing it.
ORDEN_CANAL = {"whatsapp": 0, "email": 1, "foto": 2, "voz": 3, "chat": 4,
               "reporte": 5}
# Los canales que el sistema de gestión NO ve. `voz` entró acá después de
# mirarlo en la demo: estaba marcado como interno, y un audio que manda alguien
# del depósito con las manos ocupadas es exactamente lo que ningún ERP captura
# — es el canal más nuestro de todos. Con la voz adentro son 21 de 31 avisos,
# no 14. `chat` y `reporte` sí quedan afuera de la lista: ésos ocurren DENTRO
# de PolPilot, así que el sistema los ve por definición.
DE_AFUERA = ("whatsapp", "email", "foto", "voz")

# How each audit action reads for a person (i18n key suffix per action). What
# is not in the dict shows raw: better than hiding it. Only actions that WRITE
# a datum back into the system count for the "returns to the ERP" band — an
# Ángela query is valuable but closes no loop.
ACCION_LEIBLE = {
    "integrar_staging": "acc_integrar_staging",
    "confirmar_remito": "acc_confirmar_remito",
    "confirmar_factura": "acc_confirmar_factura",
    "confirmar_orden_compra": "acc_confirmar_orden_compra",
    "aplicar_correccion": "acc_aplicar_correccion",
    "movimiento": "acc_movimiento",
    "validacion_montos_ventas": "acc_validacion_montos_ventas",
    "reportar_faltante": "acc_reportar_faltante",
    "cargar_remito": "acc_cargar_remito",
    "confirmar_movimiento": "acc_confirmar_movimiento",
    "aplicar_propuesta": "acc_aplicar_propuesta",
}
ESCRIBEN_EN_EL_SISTEMA = set(ACCION_LEIBLE)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def T(key: str, lang: str, **params) -> str:
    """Every user-facing string in this module goes through here."""
    return i18n.t("mapaop." + key, lang, **params)


def _sn(s) -> str:
    t = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in t if not unicodedata.combining(c)).strip().lower()


def _sid(x: str) -> str:
    """An id React Flow can use in a CSS selector.

    Inherited from a lost afternoon: React Flow locates nodes and edges with
    `[data-id="..."]`, and a `:` inside the id makes the selector not match.
    The edge simply DOES NOT DRAW, with no console error. Ids are sanitized
    here, once, for everyone. They contain data values (zone names), never
    translated text, so they are identical in both languages.
    """
    out = _sn(x).replace(":", "_").replace(">", "_").replace(" ", "_")
    return "".join(c if (c.isalnum() or c == "_") else "_" for c in out)


def _num(v, lang: str = "es") -> str:
    n = f"{round(v or 0):,}"
    return n.replace(",", ".") if lang != "en" else n


def _dec(v, lang: str = "es") -> str:
    """One decimal for scale-weighed kilos; integer for what moves in bultos."""
    v = float(v or 0)
    if abs(v - round(v)) < 0.05:
        return _num(v, lang)
    if lang == "en":
        return f"{v:,.1f}"
    return f"{v:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _dia(iso: str | None, lang: str = "es") -> str:
    if not iso:
        return T("sin_fecha", lang)
    p = str(iso).split("-")
    return f"{p[2]}/{p[1]}" if len(p) == 3 else str(iso)


def _sin_repetir(ids: list[str]) -> list[str]:
    """A path that passes twice through the same node lights it twice and
    reads as two different things. First-appearance order is kept."""
    visto, out = set(), []
    for x in ids:
        if x not in visto:
            visto.add(x)
            out.append(x)
    return out


def _metrica(label: str, valor: str, estado: str | None = None) -> dict:
    """The node contract: the screen iterates this and interprets nothing."""
    m = {"label": label, "valor": valor}
    if estado:
        m["estado"] = estado
    return m


def _nodo(nid, tipo, capa, etiqueta, **extra) -> dict:
    return {"id": _sid(nid), "tipo": tipo, "capa": capa, "etiqueta": etiqueta,
            "metricas": [], "estado": "neutro", **extra}


def _arista(origen, destino, tipo, **extra) -> dict:
    o, d = _sid(origen), _sid(destino)
    return {"id": f"{o}__{d}__{tipo}", "origen": o, "destino": d, "tipo": tipo,
            **extra}


def _fuente(apartado: str, filas: int, detalle_key: str | None = None,
            lang: str = "es") -> dict:
    """Where this number came from. Without it a node cannot be defended."""
    f = {"apartado": apartado, "filas": filas}
    if detalle_key:
        f["detalle"] = T("fte_" + detalle_key, lang)
    return f


def _y(nombres: list[str], lang: str) -> str:
    """«Nahuel, Ramón y Tomás», never «Nahuel y Ramón y Tomás». The headline
    gets read out loud in a meeting; a badly built enumeration is heard."""
    if not nombres:
        return T("el_equipo", lang)
    if len(nombres) == 1:
        return nombres[0]
    return ", ".join(nombres[:-1]) + T("conj_y", lang) + nombres[-1]


def _nombre_de(usuario: str | None, lang: str = "es") -> str:
    """A note is signed by a person, not a `username`. «Ramón», not «ramon»."""
    if not usuario:
        return T("alguien_del_equipo", lang)
    try:
        import auth
        u = auth.USUARIOS.get(str(usuario).strip().lower())
        if u and u.get("nombre"):
            return u["nombre"]
    except Exception:
        pass
    return str(usuario).title()


# ---------------------------------------------------------------------------
# What the versioned seed lacks, merged at read time
# ---------------------------------------------------------------------------
# `apartados.json` is a versioned seed the suite regenerates. What the map
# additionally needs — what each delivery order carries, and the open purchase
# order the warehouse note anticipates — lives in its own file and is merged
# here. The main seed stays byte-identical and this does not vanish on the
# next `generar.py` run (which does not know this file exists, on purpose).
SEED_MAPA = os.path.join(DATA_DIR, "mapa_operacion_seed.json")


@lru_cache(maxsize=1)
def _extra() -> dict:
    try:
        with open(SEED_MAPA, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def refrescar() -> None:
    """Drop the merged-seed cache (tests point DATA_DIR elsewhere). The main
    payload cache lives in core/analisis_cache and is invalidated by the
    persistence choke points via datos_cambiaron(), same as every analysis."""
    _extra.cache_clear()


# ---------------------------------------------------------------------------
# Reading the data sections
# ---------------------------------------------------------------------------
def hay_datos() -> bool:
    return bool(esquema.filas("deposito"))


def _zona_de_codigo() -> dict[int, str]:
    """Which location each product code lives in. If it is in several, the one
    holding the most wins: that is where they will pick it from."""
    mejor: dict[int, float] = {}
    zona: dict[int, str] = {}
    for f in esquema.filas("deposito"):
        c, q = f.get("codigo"), float(f.get("cantidad") or 0)
        if c is None:
            continue
        if q >= mejor.get(c, -1):
            zona[c], mejor[c] = f.get("ubicacion"), q
    return zona


def _es_zona_propia(nombre: str) -> bool:
    return any(k in _sn(nombre) for k in ZONAS_PROPIAS)


def _grupo_de(ubicacion: str) -> str:
    return ubicacion if _es_zona_propia(ubicacion) else GRUPO_PASILLOS


def _etiqueta_grupo(grupo: str, lang: str) -> str:
    """The label a group shows. Location names are tenant data and stay as-is;
    only the synthetic aisle group has a translated display name."""
    return T("grupo_pasillos", lang) if grupo == GRUPO_PASILLOS else grupo


def zonas() -> list[dict]:
    """Each warehouse zone with what it holds today.

    Occupancy does not come from a declared capacity — nobody ever loads one —
    but from comparing zones: the fullest marks 100%. It is honest, and it is
    what the warehouse manager already knows when he says «nothing else fits
    in here».
    """
    h = hoy()
    porzona: dict[str, dict] = {}
    for f in esquema.filas("deposito"):
        u = f.get("ubicacion")
        if not u:
            continue
        z = porzona.setdefault(u, {
            "id": u, "nombre": u, "grupo": _grupo_de(u), "partidas": 0,
            "cantidad": 0.0, "por_vencer": [], "vencidos": [], "productos": set(),
        })
        z["partidas"] += 1
        z["cantidad"] += float(f.get("cantidad") or 0)
        z["productos"].add(f.get("codigo"))
        v = parse_fecha(f.get("vencimiento"))
        if v:
            d = (v - h).days
            if d < 0:
                z["vencidos"].append(f)
            elif d <= DIAS_POR_VENCER:
                z["por_vencer"].append({**f, "dias": d})

    tope = max((z["partidas"] for z in porzona.values()), default=1) or 1
    for z in porzona.values():
        z["productos"] = len(z["productos"])
        z["ocupacion_pct"] = round(z["partidas"] / tope * 100)
        z["por_vencer"].sort(key=lambda x: x["dias"])
    return sorted(porzona.values(), key=lambda z: -z["partidas"])


def _notas_por_zona() -> dict[str, list[dict]]:
    """Team notes that talk about a concrete location.

    Voice and chat heads-ups: «nothing else fits in cold room 2». They are in
    no ERP table and they are half the information of the business.
    """
    from . import notas as notas_equipo
    out: dict[str, list[dict]] = defaultdict(list)
    for n in notas_equipo.listar():
        u = n.get("ubicacion")
        if u:
            out[u].append(n)
    return out


def ordenes_abiertas() -> list[dict]:
    zona = _zona_de_codigo()
    out = []
    propias = esquema.filas("ordenes_compra")
    vistas = {o.get("numero") for o in propias}
    todas = propias + [o for o in _extra().get("ordenes_extra", [])
                       if o.get("numero") not in vistas]
    for o in todas:
        if _sn(o.get("estado")) not in ("abierta", "pendiente"):
            continue
        items = list(o.get("items") or [])
        destinos: dict[str, int] = defaultdict(int)
        for it in items:
            z = zona.get(it.get("codigo"))
            if z:
                destinos[z] += int(it.get("cantidad") or 0)
        out.append({
            **o,
            "bultos": sum(int(i.get("cantidad") or 0) for i in items),
            "destinos": dict(sorted(destinos.items(), key=lambda kv: -kv[1])),
            "zona_principal": next(iter(sorted(destinos.items(),
                                               key=lambda kv: -kv[1])),
                                   (None, 0))[0],
        })
    return sorted(out, key=lambda o: o.get("fecha") or "")


def pedidos() -> list[dict]:
    """Delivery orders with their line items. The truck is the unit; the lot
    is the detail."""
    extra = _extra().get("items_por_pedido", {})
    out = []
    for f in esquema.filas("logistica"):
        items = list(f.get("items") or extra.get(f.get("pedido")) or [])
        out.append({
            **f,
            "items": items,
            "bultos": f.get("bultos") or sum(int(i.get("bultos") or 0)
                                             for i in items),
            "zonas": sorted({i.get("zona") for i in items if i.get("zona")}),
            "partidas": len(items),
        })
    return out


def en_transito() -> list[dict]:
    """Bultos that left and nobody confirmed. They are in no node."""
    return [p for p in pedidos() if _sn(p.get("estado")) == EN_TRANSITO]


def canal_de(cliente: str) -> str:
    c = _sn(cliente)
    for cid, claves in CANALES:
        if any(k in c for k in claves):
            return cid
    return CANAL_OTROS


def _reciente(fecha, dias: int = DIAS_RECIENTE) -> bool:
    if not fecha:
        return False
    d = parse_fecha(fecha)
    return bool(d and 0 <= (hoy() - d).days <= dias)


def _nombre_canal(canal: str | None, lang: str) -> str:
    c = canal or "reporte"
    key = "canal_" + c
    nombre = i18n.t("mapaop." + key, lang)
    # i18n.t returns the key itself when missing: an unknown channel shows
    # titled raw rather than a broken key.
    return c.title() if nombre == "mapaop." + key else nombre


# ---------------------------------------------------------------------------
# THE CONTEXT — what is in no system at all
# ---------------------------------------------------------------------------
def canales_de_entrada(lang: str) -> dict:
    """Where the information the ERP never sees comes in through.

    Voice notes, chats and floor reports left by people who in many cases DO
    NOT HAVE A USER in any ERP. Each chip opens the detail: who, when, what
    they said, and which map node it hit.

    Channels are the ones that EXIST in the data. There is no WhatsApp chip if
    not a single note came in that way: a zero counter nobody can open is
    worse than not showing it.
    """
    from . import notas as notas_equipo
    todas = notas_equipo.listar()
    por_canal = defaultdict(list)
    for n in todas:
        por_canal[n.get("canal") or "reporte"].append(n)

    chips = []
    for canal, ns in sorted(por_canal.items(),
                            key=lambda kv: (ORDEN_CANAL.get(kv[0], 9),
                                            -len(kv[1]))):
        chips.append({
            "id": canal,
            "nombre": _nombre_canal(canal, lang),
            "de_afuera": canal in DE_AFUERA,
            "total": len(ns),
            "recientes": len([n for n in ns if _reciente(n.get("fecha"))]),
            # Which map node each note hit: that is what draws the dashed
            # amber stroke. A note with no destination lights nothing.
            "afecta": sorted({_sid(f"zona:{_grupo_de(n['ubicacion'])}")
                              for n in ns if n.get("ubicacion")}),
        })
    return {
        "total": len(todas),
        "de_afuera": sum(len(v) for k, v in por_canal.items()
                         if k in DE_AFUERA),
        "chips": chips,
        "afecta": sorted({a for c in chips for a in c["afecta"]}),
        "fuente": _fuente("notas_equipo", len(todas), "notas", lang),
    }


def bloque_equipo(lang: str) -> dict:
    """The team, in one block. Not a card per person.

    The number that matters is not headcount: it is how many people **load
    information the ERP does not have**.
    """
    from . import notas as notas_equipo, recordatorios
    try:
        import auth
        personas = [u for u in auth.USUARIOS.values()
                    if u.get("username") != "polpilot" and not u.get("interno")]
    except Exception:
        personas = []
    todas = notas_equipo.listar()
    autores = notas_equipo.autores()
    try:
        pend = [r for r in recordatorios.listar() if not r.get("hecho")]
    except Exception:
        pend = []

    # Front avatars are the people who flagged the MOST, not alphabetical:
    # the photo has to show the ones actually loading.
    orden = sorted(personas, key=lambda u: -autores.get(u["username"], 0))
    return {
        "personas": len(personas),
        "con_avisos": len(autores),
        "avisos_recientes": len([n for n in todas if _reciente(n.get("fecha"))]),
        "tareas_pendientes": len(pend),
        "avatares": [{"username": u["username"], "nombre": u["nombre"],
                      "inicial": (u["nombre"] or "?")[0].upper(),
                      "color": u.get("color") or "#6e6a63",
                      "rol": u.get("rol"),
                      "avisos": autores.get(u["username"], 0)}
                     for u in orden[:4]],
        "resto": max(0, len(personas) - 4),
        "afecta": sorted({_sid(f"zona:{_grupo_de(n['ubicacion'])}")
                          for n in todas if n.get("ubicacion")}),
        "fuente": _fuente("equipo", len(personas), "equipo", lang),
    }


def reglas_de_la_casa(lang: str) -> dict:
    """The criterion nobody wrote down and no ERP can capture.

    It is not configured: it accumulates, because someone corrected the
    system's proposals. An ERP that does not execute has nowhere to grow it.
    """
    from . import conocimiento
    try:
        piezas = [p for p in conocimiento.listar()
                  if p.get("estado") != "borrada"]
    except Exception:
        piezas = []
    # The pieces that touch the warehouse are the ones that light a map node.
    del_deposito = [p for p in piezas
                    if p.get("nodo") in ("deposito", "inventario")]
    ejemplos = [p["texto"] for p in (del_deposito or piezas)[:2]
                if p.get("texto")]
    afecta = []
    if del_deposito:
        afecta = sorted({_sid(f"zona:{_grupo_de(z['id'])}") for z in zonas()})
    return {
        "total": len(piezas),
        "aplicaciones": sum(p.get("veces_aplicada") or 0 for p in piezas),
        "ejemplos": ejemplos,
        "afecta": afecta,
        "fuente": _fuente("conocimiento", len(piezas), "reglas", lang),
    }


def vuelve_al_sistema(lang: str, dias: int = 30) -> dict:
    """Step 5: the corrected datum returns to the management system.

    If this is empty the loop does NOT close, and the map has to say so. A
    fixed green check would be decoration — and the first «did this really
    update?» question would have no answer.

    WHAT THIS ARC IS, SAID OUT LOUD. The AI-native systems of record being
    built right now close the same loop — ingest the unstructured, reason over
    it, and *write back* to the record — with the agent doing the writing. This
    product closes it too, and the difference is the whole argument: **a person
    signs**, and the signature is in the audit log with a name and an hour.
    That is not a limitation to apologise for in a business where the owner
    answers for it with their own assets; it is the requirement.

    So the band reports WHO, not just how many. `firmantes` was the missing
    half: the count already proved the loop closes, and nothing said that every
    one of those writes has a human behind it.
    """
    try:
        registros = store.audit.list()
    except Exception:
        registros = []
    recientes = [r for r in registros
                 if _reciente((r.get("cuando") or "")[:10], dias)]
    por_accion = defaultdict(int)
    firmantes: dict[str, int] = {}
    for r in recientes:
        a = r.get("accion") or ""
        if a in ESCRIBEN_EN_EL_SISTEMA:
            por_accion[a] += 1
            quien = (r.get("actor") or "").strip()
            if quien:
                firmantes[quien] = firmantes.get(quien, 0) + 1
    chips = [{"id": a, "texto": T(ACCION_LEIBLE[a], lang), "n": n}
             for a, n in sorted(por_accion.items(), key=lambda kv: -kv[1])[:4]]
    quienes = [k for k, _ in sorted(firmantes.items(), key=lambda kv: -kv[1])]
    return {
        "total": len(registros),
        "recientes": len(recientes),
        "dias": dias,
        "chips": chips,
        "vacio": not chips,
        # Quiénes firmaron esas escrituras. Vacío es vacío: si nadie firmó
        # nada, la frase no se muestra en vez de decir «0 personas».
        "firmantes": [{"quien": _nombre_de(k, lang), "n": firmantes[k]}
                      for k in quienes],
        "firma": (T("devuelve_firma", lang,
                    quienes=_y([_nombre_de(k, lang) for k in quienes[:3]], lang))
                  if quienes else None),
        "fuente": _fuente("auditoria", len(registros), "auditoria", lang),
    }


def cobranza() -> dict:
    """What is left to collect — and where the system's payment term is not
    the house's.

    An ERP flags a customer late at 30 days because that is the term it has
    loaded. If the owner gave that customer 45, the ERP is wrong twice: it
    flags when it should not, and it does not flag when it should. The amber
    border on that card says exactly this: **this term is house criterion,
    not system data**.
    """
    from . import conocimiento, cuentas
    try:
        cs = [c for c in cuentas.listar() if (c.get("saldo") or 0) > 0]
    except Exception:
        cs = []
    try:
        reglas = conocimiento.listar()
    except Exception:
        reglas = []

    # The customer with a house term is not inferred: the rule names them,
    # and the number comes from the rule's own text.
    especial = None
    for p in reglas:
        txt = _sn(p.get("texto"))
        m = re.search(r"(\d{2})\s*d[ií]as", txt)
        if not m:
            continue
        for c in cs:
            nombre = _sn(c["nombre"])
            if nombre in txt or (len(nombre.split()) > 1 and
                                 " ".join(nombre.split()[-2:]) in txt):
                especial = {
                    "cliente": c["nombre"], "saldo": c["saldo"],
                    "plazo_casa": int(m.group(1)),
                    "plazo_sistema": c.get("plazo_dias"),
                    "dias": c.get("dias_sin_pagar"),
                    "regla": p.get("texto"),
                    "excedido": (c.get("dias_sin_pagar") or 0) > int(m.group(1)),
                }
                break
        if especial:
            break

    return {
        "total": sum(c["saldo"] for c in cs),
        "clientes": len(cs),
        "especial": especial,
        "fuente": {"apartado": "cuentas", "filas": len(cs)},
    }


def contexto(lang: str) -> dict:
    """The five layers that are not merchandise, in one place."""
    cob = cobranza()
    cob["fuente"] = _fuente("cuentas", cob["fuente"]["filas"], "cuentas", lang)
    return {
        "canales": canales_de_entrada(lang),
        "equipo": bloque_equipo(lang),
        "reglas": reglas_de_la_casa(lang),
        "devuelve": vuelve_al_sistema(lang),
        "cobranza": cob,
    }


# ---------------------------------------------------------------------------
# THE MAP
# ---------------------------------------------------------------------------
def _mapa_calc(lang: str) -> dict:
    """The route, in three evenly weighted columns.

    THE LESSON THAT COST TWO ATTEMPTS: neither twenty-one cramped nodes where
    nothing reads, nor ten with an empty column. What makes an operation map
    legible is not having FEW nodes — it is that **the three columns weigh
    about the same** and every card has its column's width.

    Here it is 8 · 5 · 10, and each column is filled with what is genuinely
    disaggregated in the head of whoever looks at it:

      · **where it comes from** — the suppliers by name, plus what is already
        ordered and has not arrived. A single "Suppliers" node says nothing to
        someone who knows all six;
      · **where it is** — the four zones in a grid with the brand in the gap.
        The warehouse is not drawn separately: the grid IS the warehouse;
      · **where it goes** — in TWO groups: first what is leaving right now,
        then which channel it goes to. Hundreds of customers are not hundreds
        of nodes: they are four channels that open.
    """
    capas = [
        {"id": "origen", "titulo": T("capa_origen", lang),
         "detalle": T("capa_origen_det", lang)},
        {"id": "centro", "titulo": T("capa_centro", lang),
         "detalle": T("capa_centro_det", lang)},
        {"id": "destino", "titulo": T("capa_destino", lang),
         "detalle": T("capa_destino_det", lang)},
    ]
    if not hay_datos():
        return {"hay_datos": False, "capas": capas, "nodos": [], "aristas": [],
                "hallazgos": [], "resumen": {}}

    nodos: list[dict] = []
    aristas: list[dict] = []
    zs = zonas()
    notas_zona = _notas_por_zona()
    zona_cod = _zona_de_codigo()
    peds = pedidos()
    ords = ordenes_abiertas()

    total_partidas = sum(z["partidas"] for z in zs)
    total_cant = sum(z["cantidad"] for z in zs)
    por_vencer = [x for z in zs for x in z["por_vencer"]]

    # === CENTER · the grid IS the warehouse ================================
    nodos.append(_nodo(
        "deposito", "deposito", "centro", T("hub_nombre", lang),
        subtitulo=T("hub_sub", lang), es_hub=True,
        # The hub is the brand in the gap: it does not repeat its zones'
        # state. Two reds for the same cause dilute both.
        estado="neutro",
        metricas=[_metrica(T("m_partidas", lang), _num(total_partidas, lang)),
                  _metrica(T("m_zonas", lang), _num(len(zs), lang)),
                  _metrica(T("m_vencen_dias", lang, dias=DIAS_POR_VENCER),
                           _num(len(por_vencer), lang),
                           "dudoso" if por_vencer else None)],
        fuente=_fuente("deposito", total_partidas, "deposito", lang)))

    grupos: dict[str, list[dict]] = defaultdict(list)
    for z in zs:
        grupos[z["grupo"]].append(z)

    orden_zonas = sorted(grupos.items(),
                         key=lambda kv: -sum(z["partidas"] for z in kv[1]))
    for pos, (grupo, lista) in enumerate(orden_zonas):
        partidas = sum(z["partidas"] for z in lista)
        cant = sum(z["cantidad"] for z in lista)
        pv = [x for z in lista for x in z["por_vencer"]]
        venc = [x for z in lista for x in z["vencidos"]]
        avisos = [n for z in lista for n in notas_zona.get(z["id"], [])]
        ocup = max(z["ocupacion_pct"] for z in lista)
        agrupado = len(lista) > 1
        entrantes = [o for o in ords
                     if o["zona_principal"]
                     and _grupo_de(o["zona_principal"]) == grupo]

        # The traffic light, with a criterion that fits in one sentence:
        #   RED    — money being lost, or something that will not fit;
        #   AMBER  — needs attention, there is still time;
        #   NEUTRAL— nothing to do here today.
        if venc:
            estado, motivo = "rojo", T("motivo_vencidas", lang)
        elif avisos and ocup >= 100 and entrantes:
            estado, motivo = "rojo", T("motivo_llena_en_camino", lang)
        elif pv:
            estado, motivo = "amarillo", T("motivo_vence_pronto", lang)
        elif avisos or ocup >= 100:
            estado, motivo = "amarillo", T("motivo_al_tope", lang)
        else:
            estado, motivo = "neutro", T("motivo_sin_novedades", lang)

        metricas = [_metrica(T("m_partidas", lang), _num(partidas, lang)),
                    _metrica(T("m_unidades", lang), _dec(cant, lang))]
        # Bottom badges: the state of what is inside, in three words.
        badges = []
        sanas = partidas - len(pv) - len(venc)
        if sanas > 0:
            badges.append({"texto": T("b_en_orden", lang, n=_num(sanas, lang)),
                           "tono": "verde"})
        if pv:
            badges.append({"texto": T("b_por_vencer", lang,
                                      n=_num(len(pv), lang)),
                           "tono": "amarillo"})
        if venc:
            badges.append({"texto": T("b_vencidas", lang,
                                      n=_num(len(venc), lang)),
                           "tono": "rojo"})
        if avisos:
            badges.append({"texto": T("b_avisos_uno" if len(avisos) == 1
                                      else "b_avisos_varios", lang,
                                      n=_num(len(avisos), lang)),
                           "tono": "amarillo"})
        if entrantes:
            badges.append({"texto": T("b_bultos_en_camino", lang,
                                      n=_num(sum(o["bultos"]
                                                 for o in entrantes), lang)),
                           "tono": "amarillo"})

        sub = (T("z_sub_agrupada", lang, n=len(lista), motivo=motivo)
               if agrupado
               else T("z_sub_propia", lang, pct=ocup, motivo=motivo))
        nodos.append(_nodo(
            f"zona:{grupo}", "zona", "centro", _etiqueta_grupo(grupo, lang),
            celda=pos, subtitulo=sub,
            estado=estado, motivo=motivo, badges=badges,
            ocupacion_pct=None if agrupado else ocup, expandible=agrupado,
            metricas=metricas,
            hijos=[{"id": _sid(f"zona:{z['id']}"), "etiqueta": z["nombre"],
                    "metricas": [_metrica(T("m_partidas", lang),
                                          _num(z["partidas"], lang)),
                                 _metrica(T("m_unidades", lang),
                                          _dec(z["cantidad"], lang)),
                                 _metrica(T("m_ocupacion", lang),
                                          f"{z['ocupacion_pct']}%")]}
                   for z in lista] if agrupado else [],
            avisos=[{"id": n["id"], "autor": n.get("autor"),
                     "fecha": n.get("fecha"), "canal": n.get("canal"),
                     "texto": (n.get("texto_en") if lang == "en"
                               and n.get("texto_en") else n.get("texto"))}
                    for n in avisos],
            fuente=_fuente("deposito", partidas, "zona", lang)))
        aristas.append(_arista("deposito", f"zona:{grupo}", "contiene",
                               etiqueta=T("a_partidas", lang,
                                          n=_num(partidas, lang))))

    # The grid CORRIDORS: two zones loaded together in the same delivery have
    # traffic between them. It is what makes the four cards read as a route
    # instead of four loose things — and it comes from the data, not from
    # drawing a line because it looks nice.
    juntas: dict[tuple[str, str], int] = defaultdict(int)
    for p in peds:
        gs = sorted({_grupo_de(z) for z in p["zonas"]})
        for i, a in enumerate(gs):
            for b in gs[i + 1:]:
                juntas[(a, b)] += 1
    for (a, b), n in sorted(juntas.items(), key=lambda kv: -kv[1]):
        if n < 3:
            continue          # two deliveries do not make a corridor
        aristas.append(_arista(f"zona:{a}", f"zona:{b}", "corredor",
                               etiqueta=T("a_pedidos", lang,
                                          n=_num(n, lang)),
                               peso=n))

    # === ORIGIN · suppliers by name, and what is already ordered ===========
    recep = esquema.filas("recepciones")
    prov: dict[str, dict] = {}
    for f in recep:
        p = f.get("proveedor")
        if not p:
            continue
        d = prov.setdefault(p, {"nombre": p, "recepciones": 0, "cantidad": 0.0,
                                "ultima": None, "zonas": defaultdict(int)})
        d["recepciones"] += 1
        d["cantidad"] += float(f.get("cantidad") or 0)
        fe = f.get("fecha")
        if fe and (d["ultima"] is None or fe > d["ultima"]):
            d["ultima"] = fe
        z = zona_cod.get(f.get("codigo"))
        if z:
            d["zonas"][_grupo_de(z)] += 1

    ordenados = sorted(prov.values(), key=lambda d: -d["recepciones"])
    PROVEEDORES_CON_NOMBRE = 4
    for p in ordenados[:PROVEEDORES_CON_NOMBRE]:
        principal = max(p["zonas"], key=p["zonas"].get) if p["zonas"] else None
        nodos.append(_nodo(
            f"prov:{p['nombre']}", "proveedor", "origen", p["nombre"],
            subtitulo=T("prov_sub", lang, dia=_dia(p["ultima"], lang)),
            metricas=[_metrica(T("m_recepciones", lang),
                               _num(p["recepciones"], lang)),
                      _metrica(T("m_unidades", lang),
                               _dec(p["cantidad"], lang))],
            fuente=_fuente("recepciones", p["recepciones"], "proveedor", lang)))
        if principal:
            n = p["zonas"][principal]
            aristas.append(_arista(f"prov:{p['nombre']}", f"zona:{principal}",
                                   "recepcion", peso=n,
                                   etiqueta=T("a_recepciones", lang,
                                              n=_num(n, lang))))

    resto = ordenados[PROVEEDORES_CON_NOMBRE:]
    if resto:
        # They do not disappear: they group. Whoever wants all six sees them
        # on click.
        rec = sum(p["recepciones"] for p in resto)
        zonas_resto = defaultdict(int)
        for p in resto:
            for z, n in p["zonas"].items():
                zonas_resto[z] += n
        nodos.append(_nodo(
            "prov_otros", "proveedor", "origen", T("prov_otros", lang),
            subtitulo=T("prov_otros_sub", lang, n=len(resto)),
            expandible=True,
            metricas=[_metrica(T("m_recepciones", lang), _num(rec, lang)),
                      _metrica(T("m_unidades", lang),
                               _dec(sum(p["cantidad"] for p in resto), lang))],
            hijos=[{"id": _sid(f"prov:{p['nombre']}"), "etiqueta": p["nombre"],
                    "metricas": [_metrica(T("m_recepciones", lang),
                                          _num(p["recepciones"], lang))]}
                   for p in resto],
            fuente=_fuente("recepciones", rec, "prov_otros", lang)))
        if zonas_resto:
            principal = max(zonas_resto, key=zonas_resto.get)
            aristas.append(_arista("prov_otros", f"zona:{principal}",
                                   "recepcion",
                                   etiqueta=T("a_recepciones", lang,
                                              n=_num(zonas_resto[principal],
                                                     lang))))

    for o in ords:
        zg = _grupo_de(o["zona_principal"]) if o["zona_principal"] else None
        nodos.append(_nodo(
            f"oc:{o['numero']}", "orden_compra", "origen", o["numero"],
            subtitulo=o.get("proveedor"), estado="amarillo",
            metricas=[_metrica(T("m_bultos", lang), _num(o["bultos"], lang)),
                      _metrica(T("m_llega", lang),
                               _dia(o.get("entrega_prevista") or o.get("fecha"),
                                    lang),
                               None if o.get("entrega_prevista") else "dudoso")],
            orden=o,
            fuente=_fuente("ordenes_compra", len(o.get("items") or []),
                           "orden", lang)))
        if zg:
            aristas.append(_arista(f"oc:{o['numero']}", f"zona:{zg}", "orden",
                                   etiqueta=T("a_bultos", lang,
                                              n=_num(o["bultos"], lang)),
                                   punteada=True))

    # === DESTINATION · two groups: leaving now, and which channel ==========
    # Group 1 — what is going out. The ones that left with no confirmation go
    # by name and number: they are the ones that hurt. The rest enters one
    # summary card, which is all a manager needs to know about them today.
    tr = sorted(en_transito(), key=lambda p: p.get("fecha_prevista") or "")
    for p in tr:
        nodos.append(_nodo(
            f"ped:{p['pedido']}", "pedido", "destino", p["pedido"],
            subtitulo=p.get("cliente"), estado="rojo", pedido=p,
            metricas=[_metrica(T("m_bultos", lang), _num(p["bultos"], lang)),
                      _metrica(T("m_prevista", lang),
                               _dia(p.get("fecha_prevista"), lang), "error")],
            fuente=_fuente("logistica", 1, "pedido_transito", lang)))
        # Which zone it left from: the one that put the most lots in it.
        zg = _grupo_de(p["zonas"][0]) if p.get("zonas") else None
        aristas.append(_arista(zg and f"zona:{zg}" or "deposito",
                               f"ped:{p['pedido']}", "transito",
                               punteada=True, alerta=True,
                               etiqueta=T("a_sin_confirmar", lang,
                                          n=_num(p["bultos"], lang))))

    pend = [p for p in peds if _sn(p.get("estado")) == "pendiente"]
    if pend:
        camiones = sorted({p.get("transporte") for p in pend
                           if p.get("transporte")})
        nodos.append(_nodo(
            "por_salir", "camion", "destino", T("por_salir", lang),
            subtitulo=T("por_salir_sub", lang, n=len(camiones)),
            expandible=True,
            metricas=[_metrica(T("m_pedidos", lang), _num(len(pend), lang)),
                      _metrica(T("m_bultos_cap", lang),
                               _num(sum(p["bultos"] for p in pend), lang))],
            hijos=[{"id": _sid(f"camion:{c}"), "etiqueta": c,
                    "metricas": [_metrica(T("m_pedidos", lang),
                                          _num(len([p for p in pend
                                                    if p.get("transporte") == c]),
                                               lang))]}
                   for c in camiones],
            fuente=_fuente("logistica", len(pend), "pendientes", lang)))
        # The waiting deliveries load from EVERY zone: hanging them off one
        # was a simplification that also crossed the cold room with a label
        # on top. They come from the warehouse hub, which sits in the gap.
        aristas.append(_arista("deposito", "por_salir", "carga",
                               etiqueta=T("a_pedidos", lang,
                                          n=_num(len(pend), lang))))

    # Group 2 — where it goes. Own branches are split from third-party shops
    # because they OPERATE differently: the front counter needs no truck.
    desde = f"{hoy().year - 1}-{hoy().month:02d}-{hoy().day:02d}"
    repo: dict[str, int] = defaultdict(int)
    try:
        from . import traslados
        for f in traslados.filas():
            if (f.get("fecha") or "") >= desde and f.get("destino"):
                repo[f["destino"]] += 1
    except Exception:
        pass

    bocas: dict[str, int] = defaultdict(int)
    for v in esquema.filas("venta"):
        b = v.get("boca")
        if b and _sn(b) not in NO_SON_BOCAS and (v.get("fecha") or "") >= desde:
            bocas[b] += 1

    sucursales = sorted(b for b in bocas if repo.get(b))
    mostrador = sorted(b for b in bocas if not repo.get(b))

    if mostrador:
        # Revenue does NOT go here: it is money, not route, and it lives in
        # Evolución.
        movs = sum(bocas[b] for b in mostrador)
        nodos.append(_nodo(
            "mostrador", "boca", "destino",
            mostrador[0] if len(mostrador) == 1 else T("mostrador", lang),
            subtitulo=T("mostrador_sub", lang),
            metricas=[_metrica(T("m_movimientos", lang), _num(movs, lang))],
            expandible=len(mostrador) > 1,
            hijos=[{"id": _sid(f"boca:{b}"), "etiqueta": b,
                    "metricas": [_metrica(T("m_movimientos", lang),
                                          _num(bocas[b], lang))]}
                   for b in mostrador],
            fuente=_fuente("venta", movs, "mostrador", lang)))
        aristas.append(_arista("deposito", "mostrador", "mostrador",
                               etiqueta=T("a_mismo_predio", lang)))

    if sucursales:
        reps = sum(repo[b] for b in sucursales)
        nodos.append(_nodo(
            "sucursales", "boca", "destino", T("sucursales", lang),
            subtitulo=T("sucursales_sub", lang, n=len(sucursales)),
            expandible=True,
            metricas=[_metrica(T("m_reposiciones", lang), _num(reps, lang)),
                      _metrica(T("m_locales", lang),
                               _num(len(sucursales), lang))],
            hijos=[{"id": _sid(f"boca:{b}"), "etiqueta": b,
                    "metricas": [_metrica(T("m_reposiciones", lang),
                                          _num(repo[b], lang)),
                                 _metrica(T("m_movimientos_cap", lang),
                                          _num(bocas[b], lang))]}
                   for b in sucursales],
            fuente=_fuente("traslados", reps, "sucursales", lang)))
        aristas.append(_arista("deposito", "sucursales", "reposicion",
                               etiqueta=T("a_reposiciones", lang,
                                          n=_num(reps, lang))))

    # Shops, by channel. The detail — who each one is — opens on click.
    por_canal: dict[str, dict] = {}
    for p in peds:
        cli = p.get("cliente")
        if not cli:
            continue
        cid = canal_de(cli)
        c = por_canal.setdefault(cid, {"id": cid,
                                       "clientes": set(), "pedidos": 0,
                                       "bultos": 0, "en_camino": []})
        c["clientes"].add(cli)
        c["pedidos"] += 1
        c["bultos"] += p["bultos"]
        if _sn(p.get("estado")) == EN_TRANSITO:
            c["en_camino"].append(p)

    for c in sorted(por_canal.values(), key=lambda d: -len(d["clientes"])):
        nodos.append(_nodo(
            f"canal:{c['id']}", "cliente", "destino",
            T("canal_grupo_" + c["id"], lang),
            subtitulo=T("canal_sub", lang, n=len(c["clientes"])),
            expandible=True,
            metricas=[_metrica(T("m_pedidos", lang),
                               _num(c["pedidos"], lang)),
                      _metrica(T("m_bultos_cap", lang),
                               _num(c["bultos"], lang))],
            hijos=[{"id": _sid(f"cli:{x}"), "etiqueta": x,
                    "metricas": [_metrica(T("m_pedidos", lang),
                                          _num(len([p for p in peds
                                                    if p.get("cliente") == x]),
                                               lang))]}
                   for x in sorted(c["clientes"])],
            fuente=_fuente("logistica", c["pedidos"], "canal", lang)))
        # Every in-transit delivery points at ITS channel: the dashed red does
        # not die in a generic node, it reaches whoever is waiting.
        for p in c["en_camino"]:
            aristas.append(_arista(f"ped:{p['pedido']}", f"canal:{c['id']}",
                                   "transito", punteada=True, alerta=True))
        pend_canal = c["pedidos"] - len(c["en_camino"])
        if pend_canal > 0:
            aristas.append(_arista("por_salir", f"canal:{c['id']}", "reparto",
                                   etiqueta=T("a_pedidos", lang,
                                              n=_num(pend_canal, lang))))

    ctx = contexto(lang)
    nctx, actx = _nodos_de_contexto(ctx, lang)
    cob = ctx["cobranza"]
    if cob["clientes"]:
        nodos.append(_nodo(
            "cobranza", "cobranza", "destino", T("cobranza", lang),
            subtitulo=T("cobranza_sub", lang, n=cob["clientes"]),
            metricas=[_metrica(T("m_por_cobrar", lang),
                               "$" + _num(cob["total"] / 1_000_000, lang) + "M")],
            fuente=cob["fuente"]))
        for cid in [n["id"] for n in nodos if n.get("tipo") == "cliente"][:1]:
            aristas.append(_arista(cid, "cobranza", "cobranza"))
        esp = cob["especial"]
        if esp:
            excede = esp["dias"] - esp["plazo_casa"]
            nodos.append(_nodo(
                "cobranza_criterio", "cobranza", "destino", esp["cliente"],
                subtitulo=T("criterio_sub", lang, a=esp["plazo_sistema"],
                            b=esp["plazo_casa"]),
                estado="amarillo", criterio=True, regla=esp["regla"],
                metricas=[_metrica(T("m_de_saldo", lang),
                                   "$" + _num(esp["saldo"] / 1_000_000, lang)
                                   + "M")],
                badges=[{"texto": T("b_lleva_dias", lang, n=esp["dias"]),
                         "tono": "rojo"},
                        {"texto": T("b_excede", lang, n=excede),
                         "tono": "rojo"}] if esp["excedido"] else
                       [{"texto": T("b_lleva_dias", lang, n=esp["dias"]),
                         "tono": "amarillo"}],
                fuente=cob["fuente"]))
            aristas.append(_arista("cobranza", "cobranza_criterio", "cobranza",
                                   punteada=True))

    return {
        "hay_datos": True,
        "empresa": EMPRESA,
        # Per-tenant, decided by the BACKEND (P37: the frontend hardcodes no
        # client): the demo's bundled logo, or /api/marca/logo on the pilot.
        "logo": LOGO,
        "capas": capas,
        "nodos": nodos,
        "aristas": aristas,
        "contexto": ctx,
        "nodos_contexto": nctx,
        "aristas_contexto": actx,
        "hallazgos": _hallazgos_calc(lang),
        "resumen": _resumen(zs, peds, por_vencer, total_partidas, total_cant,
                            lang),
    }


def _nodos_de_contexto(ctx: dict, lang: str) -> tuple[list[dict], list[dict]]:
    """The four pieces that are not merchandise, ready to draw.

    They go with `peso: 3` — the lightest of the three. At a glance it must be
    clear what is route and what is the context explaining it. Their strokes
    are DASHED AMBER and leave toward the nodes that information actually
    touched: a note about cold room 2 lights cold room 2, not everything.
    """
    nodos, aristas = [], []

    can = ctx["canales"]
    nodos.append(_nodo(
        "canales", "canales", "contexto", T("canales_titulo", lang),
        subtitulo=T("canales_sub", lang, a=_num(can["de_afuera"], lang),
                    b=_num(can["total"], lang)),
        peso=3, banda="arriba",
        metricas=[_metrica(T("m_avisos", lang), _num(can["total"], lang))],
        # Two labelled groups instead of a per-chip tag: which side of the
        # system a channel sits on is the point of the band, so it is said
        # once per group and not repeated on every chip.
        rotulo_afuera=T("chips_afuera", lang),
        rotulo_adentro=T("chips_adentro", lang),
        chips=can["chips"], fuente=can["fuente"]))
    for destino in can["afecta"]:
        aristas.append(_arista("canales", destino, "informacion",
                               punteada=True))

    eq = ctx["equipo"]
    nodos.append(_nodo(
        "equipo", "equipo", "contexto", T("equipo_titulo", lang),
        subtitulo=T("equipo_sub", lang, p=eq["personas"], c=eq["con_avisos"]),
        peso=3,
        metricas=[_metrica(T("m_avisos_semana", lang),
                           _num(eq["avisos_recientes"], lang))],
        avatares=eq["avatares"], resto=eq["resto"],
        pie=T("equipo_pie", lang, a=_num(eq["avisos_recientes"], lang),
              t=_num(eq["tareas_pendientes"], lang)),
        fuente=eq["fuente"]))
    for destino in eq["afecta"]:
        aristas.append(_arista("equipo", destino, "informacion",
                               punteada=True))

    rg = ctx["reglas"]
    nodos.append(_nodo(
        "reglas", "reglas", "contexto", T("reglas_titulo", lang),
        subtitulo=T("reglas_sub", lang, t=rg["total"], a=rg["aplicaciones"]),
        peso=3, ejemplos=rg["ejemplos"],
        metricas=[_metrica(T("m_reglas", lang), _num(rg["total"], lang))],
        fuente=rg["fuente"]))
    for destino in rg["afecta"][:2]:
        aristas.append(_arista("reglas", destino, "criterio", punteada=True))

    dv = ctx["devuelve"]
    nodos.append(_nodo(
        "devuelve", "devuelve", "contexto", T("devuelve_titulo", lang),
        # WHICH system, not "a system". Tenant identity (core/paths.py): the
        # product mounts on whatever the business already uses. The write-back
        # rail today is the CSV delta export — the honest phase 1 of the
        # connector (core/conectores.py); Odoo stays read-only for now.
        sistema=SISTEMA_DESTINO, via=T("devuelve_via", lang),
        subtitulo=(T("devuelve_sub", lang, n=_num(dv["recientes"], lang),
                     d=dv["dias"])
                   if not dv["vacio"] else T("devuelve_vacio", lang)),
        peso=3, banda="abajo", chips=dv["chips"], vacio=dv["vacio"],
        # Quién firmó. Va en el nodo y no sólo en el detalle porque es la
        # línea que distingue este círculo del de un agente que escribe solo.
        firma=dv.get("firma"), firmantes=dv.get("firmantes") or [],
        metricas=[_metrica(T("m_devoluciones", lang),
                           _num(dv["recientes"], lang))],
        fuente=dv["fuente"]))
    return nodos, aristas


SISTEMA_DESTINO = SISTEMA_GESTION


def _cobrar_total() -> float:
    try:
        return cobranza()["total"]
    except Exception:
        return 0.0


def _cobrar_pie(lang: str) -> str:
    """The worst case, not the average: it is the one to call today."""
    try:
        e = cobranza()["especial"]
        return (T("titular_cobrar_pie", lang, cliente=e["cliente"],
                  dias=e["dias"])
                if e else T("titular_cobrar_pie_neutro", lang))
    except Exception:
        return T("titular_cobrar_pie_neutro", lang)


def _resumen(zs, peds, por_vencer, total_partidas, total_cant,
             lang: str) -> dict:
    tr = [p for p in peds if _sn(p.get("estado")) == EN_TRANSITO]
    pend = [p for p in peds if _sn(p.get("estado")) == "pendiente"]
    return {
        "partidas": total_partidas,
        "unidades": round(total_cant, 1),
        "zonas": len(zs),
        "por_vencer": len(por_vencer),
        "en_transito_bultos": sum(p["bultos"] for p in tr),
        "en_transito_pedidos": len(tr),
        "pedidos_pendientes": len(pend),
        # THE FOUR NUMBERS UP TOP IMPLY AN ACTION. «380 lots in the warehouse»
        # is inventory: it does not tell the owner good or bad, and it takes
        # the place of something that does. The lot total lives in the brand
        # at the center, where it belongs.
        "titulares": [
            {"label": T("titular_vencen", lang, dias=DIAS_POR_VENCER),
             "valor": _num(len(por_vencer), lang),
             "estado": "dudoso" if por_vencer else None,
             "pie": T("titular_vencen_pie", lang)},
            {"label": T("titular_sin_confirmar", lang),
             "valor": _num(sum(p["bultos"] for p in tr), lang),
             "estado": "error" if tr else None,
             "pie": T("titular_sin_confirmar_pie", lang,
                      n=_num(len(tr), lang))},
            {"label": T("titular_sin_salir", lang),
             "valor": _num(len(pend), lang),
             "pie": T("titular_sin_salir_pie", lang)},
            {"label": T("titular_cobrar", lang),
             "valor": "$" + _num(_cobrar_total() / 1_000_000, lang) + "M",
             "estado": "dudoso", "pie": _cobrar_pie(lang)},
        ],
    }


# ---------------------------------------------------------------------------
# THE FINDINGS — each with its path and what to do about it
# ---------------------------------------------------------------------------
def _hallazgos_calc(lang: str) -> list[dict]:
    """What the crossing produces, ordered by what hurts most.

    Each finding carries:
      · `camino`  — the node sequence that produced it, to light up on the
                    map. It crosses both layers: what the team said and the
                    physical one. That mix is the product.
      · `accion`  — what can be done, with the exact number. Without it this
                    is a sign; with it, a tool.
      · `fuentes` — where it came from, so it can be opened.
    """
    if not hay_datos():
        return []
    out: list[dict] = []
    zs = zonas()
    notas_zona = _notas_por_zona()
    ords = ordenes_abiertas()

    # 1 · THE SATURATED ZONE WITH GOODS ON THE WAY.
    #     The crossing no ERP does alone: the heads-up lives in the team's
    #     voice, the occupancy in the warehouse, the order in the ERP.
    for z in zs:
        avisos = notas_zona.get(z["id"], [])
        if not avisos or z["ocupacion_pct"] < 100:
            continue
        entrantes = [o for o in ords
                     if _grupo_de(o["zona_principal"] or "")
                     == _grupo_de(z["id"])]
        primero = z["por_vencer"][0] if z["por_vencer"] else None
        # The path starts at what the team said, passes through the order
        # that has not arrived, and ends at the zone with the expiring lot.
        # The three sources that never talk to each other, lit in order.
        zona_id = _sid(f"zona:{_grupo_de(z['id'])}")
        camino = [_sid(f"nota:{n['id']}") for n in avisos]
        camino += [_sid(f"oc:{o['numero']}") for o in entrantes]
        camino.append(zona_id)
        aristas_camino = [f"{_sid('oc:' + o['numero'])}__{zona_id}__orden"
                          for o in entrantes]
        quienes = _y(sorted({_nombre_de(n.get("autor"), lang)
                             for n in avisos}), lang)
        # The headline is read out loud in a meeting: no "order(s)" and no
        # parenthesised plurals. It costs four lines and it shows.
        veces = (T("veces_una", lang) if len(avisos) == 1
                 else T("veces_n", lang, n=len(avisos)))
        cola = (T("saturada_cola_ninguna", lang) if not entrantes else
                T("saturada_cola_una", lang) if len(entrantes) == 1 else
                T("saturada_cola_varias", lang, n=len(entrantes)))
        texto = T("saturada_titulo", lang, veces=veces, zona=z["nombre"],
                  cola=cola)
        detalle = [T("saturada_avisos_uno" if len(avisos) == 1
                     else "saturada_avisos_varios", lang, n=len(avisos),
                     quienes=quienes, zona=z["nombre"]),
                   T("saturada_partidas", lang,
                     n=_num(z["partidas"], lang))]
        for o in entrantes:
            detalle.append(T("saturada_orden", lang, numero=o["numero"],
                             proveedor=o["proveedor"],
                             bultos=_num(o["bultos"], lang)))
        if primero:
            detalle.append(T("saturada_lote", lang,
                             producto=primero["producto"],
                             lote=primero["lote"], dias=primero["dias"]))
        out.append({
            "id": f"zona_saturada:{_sid(z['id'])}",
            "tipo": "zona_saturada",
            "titulo": texto,
            "chip": (T("saturada_chip_orden", lang, zona=z["nombre"],
                       numero=entrantes[0]["numero"])
                     if entrantes else T("saturada_chip", lang,
                                         zona=z["nombre"])),
            "detalle": detalle,
            "gravedad": "alta",
            "camino": _sin_repetir(
                camino + ([_sid(f"lote:{primero['lote']}")]
                          if primero else [])),
            "aristas": aristas_camino,
            "accion": ({"tipo": "reprogramar_orden",
                        "numero": entrantes[0]["numero"]}
                       if entrantes else
                       {"tipo": "revisar_zona", "numero": z["nombre"]}),
            "alternativa": (T("saturada_alternativa", lang,
                              producto=primero["producto"],
                              lote=primero["lote"])
                            if primero and entrantes else None),
            "fuentes": [_fuente("notas_equipo", len(avisos)),
                        _fuente("deposito", z["partidas"]),
                        _fuente("ordenes_compra", len(entrantes))],
        })

    # 2 · WHAT LEFT AND NOBODY CONFIRMED.
    tr = en_transito()
    if tr:
        bultos = sum(p["bultos"] for p in tr)
        out.append({
            "id": "en_transito",
            "tipo": "en_transito",
            "titulo": T("transito_titulo", lang, n=_num(bultos, lang)),
            "chip": T("transito_chip", lang, n=_num(bultos, lang)),
            "detalle": [T("transito_det", lang, pedido=p["pedido"],
                          cliente=p["cliente"], camion=p["transporte"],
                          bultos=_num(p["bultos"], lang),
                          dia=_dia(p.get("fecha_prevista"), lang))
                        for p in tr],
            "gravedad": "alta",
            # Every in-transit delivery is its own node: the path lights them
            # all, from the warehouse to the channel waiting for them.
            "camino": _sin_repetir(
                ["deposito"] + [_sid(f"ped:{p['pedido']}") for p in tr]
                + [_sid(f"canal:{canal_de(p.get('cliente'))}") for p in tr]),
            "aristas": [f"deposito__{_sid('ped:' + p['pedido'])}__transito"
                        for p in tr],
            "accion": {"tipo": "confirmar_entrega", "numero": tr[0]["pedido"]},
            "fuentes": [_fuente("logistica", len(tr), "pedidos_transito",
                                lang)],
        })

    # 3 · WHAT IS ABOUT TO EXPIRE.
    #     ONE for the whole warehouse, not one per shelf. Six chips saying
    #     «1 lot expires in Aisle N» are six chips nobody reads.
    pv = sorted([{**x, "zona": z["nombre"]} for z in zs
                 for x in z["por_vencer"]],
                key=lambda x: x["dias"])
    if pv:
        urgente = pv[0]
        out.append({
            "id": "por_vencer",
            "tipo": "por_vencer",
            "titulo": (T("vencer_titulo_varias", lang, n=len(pv),
                         dias=DIAS_POR_VENCER)
                       if len(pv) > 1 else
                       T("vencer_titulo_una", lang, dias=urgente["dias"])),
            "chip": T("vencer_chip", lang,
                      producto=urgente["producto"].split("(")[0].strip()[:26],
                      dias=urgente["dias"]),
            "detalle": [T("vencer_det", lang, producto=x["producto"],
                          lote=x["lote"], cantidad=_dec(x["cantidad"], lang),
                          zona=x["zona"], dias=x["dias"]) for x in pv[:8]],
            "gravedad": "alta" if urgente["dias"] <= 10 else "media",
            "camino": _sin_repetir(
                [_sid(f"zona:{_grupo_de(urgente['zona'])}"),
                 _sid(f"lote:{urgente['lote']}")]),
            "accion": {"tipo": "liberar_lote", "numero": urgente["lote"]},
            "alternativa": T("vencer_alternativa", lang,
                             producto=urgente["producto"],
                             zona=urgente["zona"], dias=urgente["dias"]),
            "fuentes": [_fuente("deposito", len(pv), "por_vencer", lang)],
        })

    # 4 · WHAT ALREADY EXPIRED. Not an alert: money already lost, still
    #     taking up shelf space.
    vencidos = sorted([{**x, "zona": z["nombre"]} for z in zs
                       for x in z["vencidos"]],
                      key=lambda x: x.get("vencimiento") or "")
    if vencidos:
        out.append({
            "id": "vencidos",
            "tipo": "vencidos",
            "titulo": (T("vencidos_titulo_varias", lang, n=len(vencidos))
                       if len(vencidos) > 1 else
                       T("vencidos_titulo_una", lang)),
            "detalle": [T("vencidos_det", lang, producto=x["producto"],
                          lote=x["lote"], cantidad=_dec(x["cantidad"], lang),
                          zona=x["zona"],
                          dia=_dia(x.get("vencimiento"), lang))
                        for x in vencidos[:6]],
            "gravedad": "alta",
            "camino": _sin_repetir(
                [_sid(f"zona:{_grupo_de(vencidos[0]['zona'])}"),
                 _sid(f"lote:{vencidos[0]['lote']}")]),
            "accion": {"tipo": "dar_de_baja", "numero": vencidos[0]["lote"]},
            "alternativa": T("vencidos_alternativa", lang),
            "fuentes": [_fuente("deposito", len(vencidos))],
        })

    # 5 · AN ORDER WITH NO KNOWN LANDING ZONE.
    for o in ords:
        if o["zona_principal"]:
            continue
        out.append({
            "id": f"orden_sin_destino:{_sid(o['numero'])}",
            "tipo": "orden_sin_destino",
            "titulo": T("sin_destino_titulo", lang, numero=o["numero"]),
            "detalle": [T("sin_destino_det", lang, proveedor=o["proveedor"],
                          bultos=_num(o["bultos"], lang))],
            "gravedad": "baja",
            "camino": [_sid(f"oc:{o['numero']}"), "deposito"],
            "accion": {"tipo": "asignar_zona", "numero": o["numero"]},
            "fuentes": [_fuente("ordenes_compra", len(o.get("items") or []))],
        })

    # 6 · THE TERM THE SYSTEM DOES NOT KNOW.
    #     The ERP flagged her late at 30 because that is the loaded term. The
    #     owner had given her 45. And she is late even so: the house criterion
    #     does not save her — it convicts her with grounds.
    cob = cobranza()
    esp = cob.get("especial")
    if esp and esp.get("excedido"):
        out.append({
            "id": "cobranza_criterio",
            "tipo": "cobranza",
            "titulo": T("cobranza_titulo", lang, cliente=esp["cliente"],
                        dias=esp["dias"]),
            "chip": T("cobranza_titulo", lang, cliente=esp["cliente"],
                      dias=esp["dias"]),
            "detalle": [T("cobranza_det_debe", lang,
                          saldo=_num(esp["saldo"], lang)),
                        T("cobranza_det_plazos", lang,
                          a=esp["plazo_sistema"], b=esp["plazo_casa"]),
                        T("cobranza_det_excede", lang,
                          n=esp["dias"] - esp["plazo_casa"]),
                        T("cobranza_det_regla", lang, regla=esp["regla"])],
            "gravedad": "alta",
            "camino": ["cobranza_criterio"],
            "aristas": [],
            "accion": {"tipo": "llamar_cliente", "numero": esp["cliente"]},
            "alternativa": None,
            "fuentes": [cob["fuente"]],
        })

    # 7 · WHAT IS WAITING ON THE LOADING DOCK.
    pend = [p for p in pedidos() if _sn(p.get("estado")) == "pendiente"]
    if pend:
        out.append({
            "id": "sin_salir",
            "tipo": "sin_salir",
            "titulo": T("sin_salir_titulo", lang, n=_num(len(pend), lang)),
            "chip": T("sin_salir_titulo", lang, n=_num(len(pend), lang)),
            "detalle": [T("sin_salir_det", lang, pedido=p["pedido"],
                          cliente=p.get("cliente"),
                          bultos=_num(p["bultos"], lang),
                          camion=p.get("transporte"))
                        for p in pend[:6]],
            "gravedad": "media",
            "camino": ["por_salir"],
            "aristas": [],
            "accion": {"tipo": "despachar", "numero": pend[0]["pedido"]},
            "alternativa": None,
            "fuentes": [_fuente("logistica", len(pend))],
        })

    orden = {"alta": 0, "media": 1, "baja": 2}
    return sorted(out, key=lambda h: orden.get(h["gravedad"], 9))


# ---------------------------------------------------------------------------
# A NODE'S DETAIL — the panel that opens on click
# ---------------------------------------------------------------------------
def _listado(nid: str, lang: str) -> dict | None:
    """What is inside a node. The panel changes; the camera does not move.

    Resolved by id PREFIX, without rebuilding the map: a panel that takes
    four seconds is a panel that does not exist.
    """
    nid = (nid or "").strip()
    base, _, sufijo = nid.partition(":")

    # --- the context layer -------------------------------------------------
    if base == "canales":
        from . import notas as notas_equipo
        ns = notas_equipo.listar()
        if sufijo:
            ns = [n for n in ns if (n.get("canal") or "reporte") == sufijo]
        return {
            "titulo_filas": (T("lst_canal", lang,
                               canal=_nombre_canal(sufijo, lang))
                             if sufijo else T("lst_canales", lang)),
            "fuente": _fuente("notas_equipo", len(ns)),
            "filas": [{"quien": _nombre_de(n.get("autor"), lang),
                       "cuando": _dia(n.get("fecha"), lang),
                       "canal": _nombre_canal(n.get("canal"),
                                                           lang),
                       "dijo": (n.get("texto_en")
                                             if lang == "en"
                                             and n.get("texto_en")
                                             else n.get("texto")),
                       "afecta": n.get("ubicacion") or "—"}
                      for n in ns],
        }

    if base == "equipo":
        eq = bloque_equipo(lang)
        from . import notas as notas_equipo
        autores = notas_equipo.autores()
        try:
            import auth
            personas = [u for u in auth.USUARIOS.values()
                        if u.get("username") != "polpilot"
                        and not u.get("interno")]
        except Exception:
            personas = []
        personas.sort(key=lambda u: -autores.get(u["username"], 0))
        return {
            "titulo_filas": T("lst_equipo", lang),
            "fuente": eq["fuente"],
            "filas": [{"quien": u["nombre"],
                       "rol": u.get("rol"),
                       "avisos":
                           _num(autores.get(u["username"], 0), lang)}
                      for u in personas],
        }

    if base == "reglas":
        from . import conocimiento
        try:
            piezas = [p for p in conocimiento.listar()
                      if p.get("estado") != "borrada"]
        except Exception:
            piezas = []
        return {
            "titulo_filas": T("lst_reglas", lang),
            "fuente": _fuente("conocimiento", len(piezas)),
            "filas": [{"regla": (p.get("texto_en")
                                              if lang == "en"
                                              and p.get("texto_en")
                                              else p.get("texto")),
                       "sobre": p.get("nodo") or "—",
                       "aplicada":
                           _num(p.get("veces_aplicada") or 0, lang)}
                      for p in piezas],
        }

    if base == "devuelve":
        try:
            regs = store.audit.list()
        except Exception:
            regs = []
        regs = [r for r in regs
                if (r.get("accion") in ESCRIBEN_EN_EL_SISTEMA
                    and _reciente((r.get("cuando") or "")[:10], 30))]
        regs.sort(key=lambda r: r.get("cuando") or "", reverse=True)
        return {
            "titulo_filas": T("lst_devuelve", lang),
            "fuente": _fuente("auditoria", len(regs)),
            "filas": [{"quien": _nombre_de(r.get("actor"), lang),
                       "que": (T(ACCION_LEIBLE[r["accion"]], lang)
                                            if r.get("accion") in ACCION_LEIBLE
                                            else r.get("accion")),
                       "cuando":
                           _dia((r.get("cuando") or "")[:10], lang)}
                      for r in regs],
        }

    if base in ("cobranza", "cobranza_criterio"):
        from . import cuentas
        try:
            cs = sorted([c for c in cuentas.listar()
                         if (c.get("saldo") or 0) > 0],
                        key=lambda c: -c["saldo"])
        except Exception:
            cs = []
        cob = cobranza()
        return {
            "titulo_filas": T("lst_cobranza", lang),
            "fuente": _fuente("cuentas", len(cs), "cuentas", lang),
            "criterio": cob["especial"],
            "filas": [{"cliente": c["nombre"],
                       "saldo": "$" + _num(c["saldo"], lang),
                       "plazo": T("dias_n", lang,
                                               n=c.get("plazo_dias")),
                       "sin_pagar": T("dias_n", lang,
                                                   n=c.get("dias_sin_pagar"))}
                      for c in cs],
        }

    # --- the physical route ------------------------------------------------
    if base == "deposito":
        zs = zonas()
        return {
            "titulo_filas": T("lst_deposito", lang),
            "fuente": _fuente("deposito", sum(z["partidas"] for z in zs)),
            "filas": [{"zona": z["nombre"],
                       "partidas": _num(z["partidas"], lang),
                       "unidades": _dec(z["cantidad"], lang),
                       "ocupacion": f"{z['ocupacion_pct']}%"}
                      for z in zs],
        }

    if base.startswith("zona_"):
        nombre = base[len("zona_"):]
        zs = [z for z in zonas()
              if _sid(_grupo_de(z["id"])) == nombre or _sid(z["id"]) == nombre]
        ubis = {z["id"] for z in zs}
        filas = [f for f in esquema.filas("deposito")
                 if f.get("ubicacion") in ubis]
        filas.sort(key=lambda f: f.get("vencimiento") or "9999")
        return {
            "titulo_filas": T("lst_zona", lang),
            "fuente": _fuente("deposito", len(filas)),
            "filas": [{"lote": f.get("lote"), "producto": f.get("producto"),
                       "cantidad": _dec(f.get("cantidad"), lang),
                       "ubicacion": f.get("ubicacion"),
                       "vencimiento": f.get("vencimiento")}
                      for f in filas[:120]],
        }

    if base.startswith("prov_"):
        if base == "prov_otros":
            recep = esquema.filas("recepciones")
            por = defaultdict(lambda: {"n": 0, "cant": 0.0})
            for f in recep:
                d = por[f.get("proveedor")]
                d["n"] += 1
                d["cant"] += float(f.get("cantidad") or 0)
            filas = sorted(por.items(), key=lambda kv: -kv[1]["n"])[4:]
            return {
                "titulo_filas": T("lst_prov_otros", lang),
                "fuente": _fuente("recepciones",
                                  sum(d["n"] for _, d in filas)),
                "filas": [{"proveedor": p,
                           "recepciones": _num(d["n"], lang),
                           "unidades": _dec(d["cant"], lang)}
                          for p, d in filas],
            }
        recep = [f for f in esquema.filas("recepciones")
                 if _sid(f"prov:{f.get('proveedor')}") == base]
        recep.sort(key=lambda f: f.get("fecha") or "", reverse=True)
        return {
            "titulo_filas": T("lst_recepciones", lang),
            "fuente": _fuente("recepciones", len(recep)),
            "filas": [{"fecha": f.get("fecha"), "producto": f.get("producto"),
                       "cantidad": _dec(f.get("cantidad"), lang)}
                      for f in recep[:60]],
        }

    if base.startswith("oc_"):
        o = next((x for x in ordenes_abiertas()
                  if _sid(f"oc:{x['numero']}") == base), None)
        if not o:
            return None
        zc = _zona_de_codigo()
        return {
            "titulo_filas": T("lst_orden", lang),
            "fuente": _fuente("ordenes_compra", len(o.get("items") or [])),
            "filas": [{"producto": i.get("producto"),
                       "bultos": _num(i.get("cantidad"), lang),
                       "zona": zc.get(i.get("codigo"))
                       or T("sin_ubicacion", lang)}
                      for i in (o.get("items") or [])],
        }

    # A delivery, a truck or a channel: truck on top, lot underneath.
    peds = pedidos()
    if base.startswith("ped_"):
        p = next((x for x in peds if _sid(f"ped:{x['pedido']}") == base), None)
        if not p:
            return None
        return {
            "titulo_filas": f"{p['pedido']} · {p.get('cliente')}",
            "fuente": _fuente("logistica", 1),
            "filas": [{"pedido": p["pedido"], "cliente": p.get("cliente"),
                       "estado": p.get("estado"),
                       "bultos": _num(p["bultos"], lang),
                       "prevista": p.get("fecha_prevista"),
                       "items": p.get("items") or []}],
        }

    if base == "por_salir":
        pend = [p for p in peds if _sn(p.get("estado")) == "pendiente"]
        return {
            "titulo_filas": T("lst_pedidos", lang),
            "fuente": _fuente("logistica", len(pend)),
            "filas": [{"pedido": p["pedido"], "cliente": p.get("cliente"),
                       "camion": p.get("transporte"),
                       "bultos": _num(p["bultos"], lang),
                       "items": p.get("items") or []} for p in pend],
        }

    if base.startswith("canal_"):
        cid = base[len("canal_"):]
        filas = [p for p in peds if canal_de(p.get("cliente")) == cid]
        return {
            "titulo_filas": T("lst_pedidos", lang),
            "fuente": _fuente("logistica", len(filas)),
            "filas": [{"pedido": p["pedido"], "cliente": p.get("cliente"),
                       "estado": p.get("estado"),
                       "bultos": _num(p["bultos"], lang),
                       "items": p.get("items") or []} for p in filas],
        }

    if base in ("mostrador", "sucursales"):
        from . import traslados
        desde = f"{hoy().year - 1}-{hoy().month:02d}-{hoy().day:02d}"
        por = defaultdict(int)
        try:
            for f in traslados.filas():
                if (f.get("fecha") or "") >= desde and f.get("destino"):
                    por[f["destino"]] += 1
        except Exception:
            pass
        bocas = defaultdict(int)
        for v in esquema.filas("venta"):
            b = v.get("boca")
            if b and _sn(b) not in NO_SON_BOCAS \
                    and (v.get("fecha") or "") >= desde:
                bocas[b] += 1
        quiere = (lambda b: bool(por.get(b))) if base == "sucursales" \
            else (lambda b: not por.get(b))
        return {
            "titulo_filas": T("lst_locales", lang),
            "fuente": _fuente("venta", sum(bocas.values())),
            "filas": [{"local": b,
                       "movimientos": _num(n, lang),
                       "reposiciones": _num(por.get(b, 0), lang)}
                      for b, n in sorted(bocas.items(), key=lambda kv: -kv[1])
                      if quiere(b)],
        }

    return None


# ===========================================================================
# THE PANEL — the right question
# ---------------------------------------------------------------------------
# Whoever taps «Cold room 2» already knows there are 41 lots: it is written on
# the card. What they want to know is WHY it is red and WHAT TO DO. Hence the
# order: what is going on → where it came from → what can be done → and only
# at the bottom, folded, the listing. The listing is the last resort.
#
# NOTHING HERE WRITES. The proposal is asked of Ángela through the same rail
# as everything else — propose, approve, write back —: the button touches no
# stock and no order on its own.
# ===========================================================================
def _hallazgo_de(nid: str, lang: str) -> dict | None:
    """The finding whose path passes through this node, if any. It is the
    source of «what to do»: the proposal and action are already there."""
    for h in mapa(lang)["hallazgos"]:
        if nid in (h.get("camino") or []):
            return h
    return None


def _nodo_del_mapa(nid: str, lang: str) -> dict | None:
    m = mapa(lang)
    for n in m["nodos"] + m.get("nodos_contexto", []):
        if n["id"] == nid:
            return n
    return None


def _verbo(tipo: str, lang: str) -> str:
    key = "verbo_" + tipo
    v = i18n.t("mapaop." + key, lang)
    return tipo.replace("_", " ") if v == "mapaop." + key else v


# ---------------------------------------------------------------------------
# WHERE A NODE LIVES IN THE APP — so the panel always has an exit.
# ---------------------------------------------------------------------------
# The panel must never end in a negation. "Nothing is stuck here" is a report,
# and design rule #1 says a process that ends in a report is unfinished. So
# every node declares the section that OWNS it: with a finding, the panel
# offers the action; without one, it offers to go see the thing, with the item
# already focused. The question to Ángela stays as the third exit, always.
#
# Section ids are the app's own (DesktopApp's CATALOGO / ALIAS_SECCION), and
# `foco` is the value that section highlights on arrival. Nothing here is a
# new endpoint or a new table: it is a lookup over the node the map already
# built.
_SECCION_FIJA = {
    "deposito": ("deposito", None),
    "canales": ("equipo", None),        # the heads-ups are the team's
    "equipo": ("equipo", None),
    "reglas": ("aprendizaje", None),    # what the system learned
    "devuelve": ("auditoria", None),    # every write-back is a logged approval
    "cobranza": ("cobranzas", None),
    "por_salir": ("deposito", None),    # logistica → deposito (ALIAS_SECCION)
    "mostrador": ("caja", None),        # the counter IS the till
    "sucursales": ("movimientos", None),  # internal transfers
}
_SECCION_DE_TIPO = {
    "zona": "deposito",
    "proveedor": "proveedores",
    "orden_compra": "ordenes_compra",
    "pedido": "deposito",
    "camion": "deposito",
    "boca": "movimientos",
    "cliente": "cuentas",
    "cobranza": "cobranzas",
}


def _ver(n: dict | None, base: str, lang: str) -> dict | None:
    """Where to send whoever wants to see this node's data in full."""
    if base in _SECCION_FIJA:
        seccion, foco = _SECCION_FIJA[base]
    elif n and n.get("tipo") in _SECCION_DE_TIPO:
        seccion = _SECCION_DE_TIPO[n["tipo"]]
        # The focus is the node's own label: the section resolves it the same
        # way a Home card's highlight does.
        foco = n.get("etiqueta")
    else:
        return None
    return {"seccion": seccion, "foco": foco,
            "label": T("ver_en", lang, seccion=T("sec_" + seccion, lang))}


def _que_hacer(h: dict | None, pregunta: str, lang: str) -> dict:
    if not h:
        return {"propuesta": None, "accion": None,
                "boton": T("boton_preguntar", lang), "pregunta": pregunta}
    verbo = _verbo(h["accion"]["tipo"], lang)
    return {
        "propuesta": h.get("alternativa") or h["titulo"],
        "accion": h["accion"],
        "boton": T("boton_preparar", lang, verbo=verbo,
                   numero=h["accion"]["numero"]),
        "pregunta": T("pregunta_preparar", lang, verbo=verbo,
                      numero=h["accion"]["numero"]),
    }


def detalle(nid: str, lang: str = "es") -> dict | None:
    nid = (nid or "").strip()
    base = nid.split(":")[0]
    lst = _listado(nid, lang)
    n = _nodo_del_mapa(base, lang)
    if lst is None and n is None:
        return None

    etiqueta = ((n or {}).get("etiqueta")
                or (lst or {}).get("titulo_filas") or nid)
    pregunta = T("pregunta_nodo", lang, nombre=etiqueta)
    h = _hallazgo_de(base, lang)
    if h and n and n.get("tipo") == "pedido":
        # The transit finding names the first delivery on the list. Whoever
        # tapped THIS one wants to confirm this one: it gets its own number.
        h = {**h, "accion": {**h["accion"],
                             "numero": (n.get("pedido") or {})
                             .get("pedido", h["accion"]["numero"])}}
    que_pasa: list[str] = []
    de_donde: list[dict] = []

    if n and n.get("tipo") == "zona":
        ocup = n.get("ocupacion_pct")
        avisos = n.get("avisos") or []
        if ocup is not None:
            que_pasa.append(T("qp_ocupacion_tope" if ocup >= 100
                              else "qp_ocupacion", lang, pct=ocup))
        if avisos:
            que_pasa.append(T("qp_avisos_uno" if len(avisos) == 1
                              else "qp_avisos_varios", lang, n=len(avisos)))
        entrantes = [o for o in ordenes_abiertas()
                     if o["zona_principal"]
                     and _etiqueta_grupo(_grupo_de(o["zona_principal"]), lang)
                     == etiqueta]
        for o in entrantes:
            que_pasa.append(T("qp_orden_llega", lang, numero=o["numero"],
                              bultos=_num(o["bultos"], lang),
                              dia=_dia(o.get("entrega_prevista")
                                       or o.get("fecha"), lang)))
            de_donde.append({"tipo": "orden",
                             "titulo": f"{o['numero']} · {o['proveedor']}",
                             "texto": T("dd_orden", lang,
                                        bultos=_num(o["bultos"], lang),
                                        dia=_dia(o.get("entrega_prevista")
                                                 or o.get("fecha"), lang))})
        for b in (n.get("badges") or []):
            # Expiry badges promote to a sentence; the rest stay badges.
            if any(k in b["texto"] for k in ("vencer", "vencid", "expir")):
                que_pasa.append(b["texto"] + ".")
        for a in avisos:
            de_donde.append({"tipo": "aviso",
                             "titulo": f"{_nombre_de(a.get('autor'), lang)} · "
                                       f"{_dia(a.get('fecha'), lang)} · "
                                       f"{_nombre_canal(a.get('canal'), lang)}",
                             "texto": a.get("texto")})
        if not que_pasa:
            que_pasa.append(T("qp_sin_novedades", lang))

    elif n and n.get("tipo") == "pedido":
        p = n.get("pedido") or {}
        que_pasa.append(T("qp_pedido_salio", lang,
                          bultos=_num(p.get("bultos"), lang),
                          camion=p.get("transporte"),
                          cliente=p.get("cliente"),
                          dia=_dia(p.get("fecha_prevista"), lang)))
        que_pasa.append(T("qp_pedido_sin_confirmar", lang))
        de_donde.append({"tipo": "pedido", "titulo": p.get("pedido"),
                         "texto": T("dd_pedido", lang,
                                    n=len(p.get("items") or []),
                                    estado=p.get("estado"))})

    elif n and n.get("tipo") == "orden_compra":
        o = n.get("orden") or {}
        zg = _grupo_de(o["zona_principal"]) if o.get("zona_principal") else None
        que_pasa.append(T("qp_orden", lang, bultos=_num(o.get("bultos"), lang),
                          proveedor=o.get("proveedor"),
                          dia=_dia(o.get("entrega_prevista")
                                   or o.get("fecha"), lang)))
        if zg:
            que_pasa.append(T("qp_orden_zona", lang,
                              zona=_etiqueta_grupo(zg, lang)))
            zn = _nodo_del_mapa(_sid(f"zona:{zg}"), lang)
            if zn and (zn.get("ocupacion_pct") or 0) >= 100:
                que_pasa.append(T("qp_orden_zona_llena", lang))
        de_donde.append({"tipo": "orden", "titulo": o.get("numero"),
                         "texto": T("dd_orden_items", lang,
                                    n=len(o.get("items") or []),
                                    estado=o.get("estado"))})

    elif n and n.get("tipo") == "cobranza":
        cob = cobranza()
        esp = cob.get("especial")
        if n.get("criterio") and esp:
            que_pasa.append(T("qp_cob_debe", lang,
                              saldo=_num(esp["saldo"], lang),
                              dias=esp["dias"]))
            que_pasa.append(T("cobranza_det_plazos", lang,
                              a=esp["plazo_sistema"], b=esp["plazo_casa"]))
            if esp.get("excedido"):
                que_pasa.append(T("cobranza_det_excede", lang,
                                  n=esp["dias"] - esp["plazo_casa"]))
            de_donde.append({"tipo": "regla",
                             "titulo": T("dd_regla", lang),
                             "texto": esp.get("regla")})
        else:
            que_pasa.append(T("qp_cob_total", lang,
                              total=_num(cob["total"], lang),
                              n=cob["clientes"]))
            if esp:
                que_pasa.append(T("qp_cob_caso", lang, cliente=esp["cliente"],
                                  dias=esp["dias"]))

    elif n and n.get("tipo") == "proveedor":
        m0 = (n.get("metricas") or [{}])[0]
        que_pasa.append(f"{m0.get('valor', '')} {m0.get('label', '')}. "
                        f"{n.get('subtitulo', '')}.")
        from . import notas as notas_equipo
        for a in notas_equipo.listar(proveedor=etiqueta):
            de_donde.append({"tipo": "aviso",
                             "titulo": f"{_nombre_de(a.get('autor'), lang)} · "
                                       f"{_dia(a.get('fecha'), lang)} · "
                                       f"{_nombre_canal(a.get('canal'), lang)}",
                             "texto": a.get("texto")})
        if de_donde:
            que_pasa.append(T("qp_prov_avisos_uno" if len(de_donde) == 1
                              else "qp_prov_avisos_varios", lang,
                              n=len(de_donde)))

    elif base == "equipo":
        eq = bloque_equipo(lang)
        que_pasa.append(T("qp_equipo", lang, p=eq["personas"],
                          c=eq["con_avisos"]))
        que_pasa.append(T("qp_equipo_tareas_una" if eq["tareas_pendientes"] == 1
                          else "qp_equipo_tareas", lang,
                          a=eq["avisos_recientes"],
                          t=eq["tareas_pendientes"]))
    elif base == "reglas":
        rg = reglas_de_la_casa(lang)
        que_pasa.append(T("qp_reglas", lang, t=rg["total"],
                          a=rg["aplicaciones"]))
        que_pasa.append(T("qp_reglas_origen", lang))
    elif base == "canales":
        can = canales_de_entrada(lang)
        que_pasa.append(T("qp_canales", lang, a=can["de_afuera"],
                          b=can["total"]))
    elif base == "devuelve":
        dv = vuelve_al_sistema(lang)
        que_pasa.append(T("qp_devuelve", lang, n=dv["recientes"],
                          d=dv["dias"])
                        if not dv["vacio"] else T("qp_devuelve_vacio", lang))
    elif lst and lst.get("titulo_filas"):
        que_pasa.append(lst["titulo_filas"] + ".")

    if h and h.get("detalle") and not de_donde:
        for d in h["detalle"]:
            de_donde.append({"tipo": "hecho", "titulo": None, "texto": d})

    salida = {
        "titulo": etiqueta,
        "estado": (n or {}).get("estado", "neutro"),
        "que_pasa": que_pasa,
        "de_donde": de_donde,
        "que_hacer": _que_hacer(h, pregunta, lang),
        # The guaranteed exit: with or without a finding, the panel can always
        # take you to the section that owns this node (see _ver).
        "ver": _ver(n, base, lang),
        "listado": ({"titulo": lst.get("titulo_filas") or T("lst_detalle",
                                                            lang),
                     "filas": lst.get("filas") or []} if lst else None),
        "fuente": (lst or {}).get("fuente") or (n or {}).get("fuente"),
        "pregunta": pregunta,
        # compatibility with what the screen and the tests already read
        "titulo_filas": (lst or {}).get("titulo_filas"),
        "filas": (lst or {}).get("filas") or [],
    }
    if lst and lst.get("criterio"):
        salida["criterio"] = lst["criterio"]
    return salida


# ---------------------------------------------------------------------------
# Cached entry points — same discipline as /api/grafo and /api/analisis:
# computed per language, invalidated by the persistence choke points through
# analisis_cache.datos_cambiaron().
# ---------------------------------------------------------------------------
def mapa(lang: str = "es") -> dict:
    from . import analisis_cache
    return analisis_cache.get_o_computar("mapa_operacion", lang,
                                         lambda: _mapa_calc(lang))


def hallazgos(lang: str = "es") -> list[dict]:
    return mapa(lang).get("hallazgos", [])

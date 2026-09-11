"""
Comprobantes de compra (P10): orden de compra / remito / factura / recibo.

La foto entra por visión (vision_facturas.py) → extracción con confianza →
CONFIRMACIÓN HUMANA → acá, que persiste por los rieles que YA existen:
apartados (esquema), stock del inventario (store, con backup + audit),
cobros de clientes (cuentas.registrar_cobro) — y la cuenta corriente del
PROVEEDOR, que es nueva pero chiquita (un JSON por tenant, patrón de la casa).

El criterio de Ángela vive en los CRUCES:
  - remito ↔ orden de compra: qué coincide, qué falta, qué no se pidió —
    ANTES de tocar stock.
  - factura ↔ remito: los montos contra lo que de verdad llegó, y el impacto
    en la cuenta del proveedor.
  - recibo ↔ cliente moroso: el cobro baja la deuda y el scoring se recompone.

Nada entra sin el sí explícito del humano (la tesis del producto).
"""
from __future__ import annotations

import datetime
import json
import os
import re
import unicodedata

from . import esquema, paths, store, validacion
from .fechas import parse_fecha, hoy

DATA_DIR = paths.DATA_DIR
PROVEEDORES_JSON = os.path.join(DATA_DIR, "proveedores.json")

TIPOS_COMPROBANTE = ("factura", "remito", "orden_compra", "recibo")

# Umbral compartido con el validador de montos de ventas (misma paranoia ×1000).
UMBRAL_DIF_PCT = 20


def _t(key: str, lang: str | None = None, **params) -> str:
    import i18n
    return i18n.t(key, lang, **params)


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).lower().strip()


_FORMAS_LEGALES = re.compile(
    r"\b(s\.?\s?a\.?(c\.?i\.?f?\.?)?|s\.?\s?r\.?\s?l\.?|s\.?\s?h\.?|s\.?a\.?s\.?)\b\.?")


def _norm_proveedor(s) -> str:
    """El nombre del proveedor sin la forma societaria: la factura dice
    «LÁCTEOS CAMPO ALEGRE S.A.» y el catálogo «Lácteos Campo Alegre» — son
    el mismo y los cruces tienen que saberlo."""
    n = _FORMAS_LEGALES.sub("", _norm(s))
    return re.sub(r"[.,]+$", "", n).strip()


def _ahora() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


# --- Cuenta corriente del proveedor -------------------------------------------

def _prov_load() -> list[dict]:
    try:
        return json.load(open(PROVEEDORES_JSON, encoding="utf-8"))
    except Exception:
        return []


def _prov_save(items: list[dict]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    json.dump(items, open(PROVEEDORES_JSON, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


def proveedores_conocidos() -> set[str]:
    """Los proveedores REALES del tenant: los del catálogo + recepciones +
    los que ya tienen cuenta corriente (una factura confirmada por foto crea
    la cuenta: ese proveedor ES conocido aunque no tenga artículos propios)."""
    nombres = set()
    for a in store.raw_actual():
        if a.get("proveedor"):
            nombres.add(a["proveedor"])
    for f in esquema.filas("recepciones"):
        if f.get("proveedor"):
            nombres.add(f["proveedor"])
    for p in _prov_load():
        if p.get("proveedor"):
            nombres.add(p["proveedor"])
    return nombres


def resolver_proveedor(nombre: str) -> dict:
    """¿Este proveedor existe, es nuevo, o parece un duplicado de uno conocido?
    (filosofía de saneamiento: un parecido es conversación, no un alta a ciegas)"""
    n = _norm_proveedor(nombre)
    conocidos = proveedores_conocidos()
    for c in conocidos:
        if _norm_proveedor(c) == n:
            return {"estado": "conocido", "nombre": c}
    for c in conocidos:
        nc = _norm_proveedor(c)
        if n and (n in nc or nc in n):
            return {"estado": "parecido", "nombre": nombre, "parecido_a": c}
    return {"estado": "nuevo", "nombre": nombre}


def cuenta_proveedor(nombre: str) -> dict:
    items = _prov_load()
    n = _norm_proveedor(nombre)
    p = next((x for x in items if _norm_proveedor(x["proveedor"]) == n), None)
    return p or {"proveedor": nombre, "saldo": 0.0, "movimientos": []}


def _asentar_proveedor(nombre: str, tipo: str, monto: float,
                       numero: str | None, vencimiento: str | None) -> dict:
    items = _prov_load()
    n = _norm_proveedor(nombre)
    p = next((x for x in items if _norm_proveedor(x["proveedor"]) == n), None)
    if not p:
        p = {"proveedor": nombre, "saldo": 0.0, "movimientos": []}
        items.append(p)
    p["saldo"] = round(p["saldo"] + (monto if tipo == "factura" else -monto), 2)
    p["movimientos"].append({"fecha": _ahora(), "tipo": tipo, "monto": monto,
                             "numero": numero, "vencimiento": vencimiento})
    if vencimiento:
        p["vencimiento_proximo"] = vencimiento
    _prov_save(items)
    return p


# --- Matching de ítems contra el catálogo --------------------------------------

def _resolver_codigo(item: dict) -> dict | None:
    """El artículo del catálogo al que apunta este ítem del comprobante:
    por código si viene impreso, si no por nombre (normalizado). None = no está
    en el catálogo (se dice, nunca se inventa)."""
    raw = store.raw_actual()
    cod = item.get("codigo")
    if cod is not None:
        try:
            cod = int(cod)
            a = next((x for x in raw if x.get("codigo") == cod), None)
            if a:
                return a
        except (TypeError, ValueError):
            pass
    n = _norm(item.get("descripcion"))
    if not n:
        return None
    exacto = next((x for x in raw if _norm(x.get("descripcion")) == n), None)
    if exacto:
        return exacto
    return next((x for x in raw
                 if n in _norm(x.get("descripcion")) or _norm(x.get("descripcion")) in n),
                None)


# --- Chequeos automáticos post-extracción (la paranoia ×1000 aplica acá) -------

def chequeos(extraccion: dict, lang: str | None = None) -> dict:
    """Los controles que corren SOLOS apenas la visión lee el comprobante:
    suma de ítems vs total declarado (con detección de factor de escala, la
    misma cicatriz del validador de montos), proveedor contra los conocidos,
    y precio de cada ítem contra el costo del catálogo."""
    resultado = {"alertas": [], "proveedor": None, "items_catalogo": 0}
    items = extraccion.get("items") or []

    # 1) suma de ítems vs total declarado
    suma = 0.0
    for it in items:
        sub = it.get("subtotal")
        if sub is None and it.get("cantidad") is not None and it.get("precio_unitario") is not None:
            sub = float(it["cantidad"]) * float(it["precio_unitario"])
        suma += float(sub or 0)
    declarado = extraccion.get("subtotal") or extraccion.get("total")
    con_iva = declarado is extraccion.get("total") and extraccion.get("subtotal") is None
    if items and declarado:
        base = float(declarado) / (1.21 if con_iva else 1.0)
        dif_pct = abs(suma - base) / base * 100 if base else 0
        if dif_pct > UMBRAL_DIF_PCT:
            factor = (suma / base) if base else 0
            pista = ""
            if factor > 5:
                pista = _t("core.ventas.pista_inflados", lang)
            elif 0 < factor < 0.2:
                pista = _t("core.ventas.pista_miniatura", lang)
            resultado["alertas"].append({
                "tipo": "suma_no_cierra",
                "detalle": _t("core.comp.chk_suma", lang, pct=round(dif_pct),
                              pista=pista).strip(),
            })

    # 2) proveedor contra los conocidos del tenant
    prov = (extraccion.get("proveedor") or {}).get("razon_social") or ""
    if prov:
        r = resolver_proveedor(prov)
        resultado["proveedor"] = r
        if r["estado"] == "parecido":
            resultado["alertas"].append({
                "tipo": "proveedor_parecido",
                "detalle": _t("core.comp.chk_prov_parecido", lang,
                              nombre=prov, conocido=r["parecido_a"]),
            })
        elif r["estado"] == "nuevo":
            resultado["alertas"].append({
                "tipo": "proveedor_nuevo",
                "detalle": _t("core.comp.chk_prov_nuevo", lang, nombre=prov),
            })

    # 3) EL BORDE (core/validacion): cantidad y precio de cada ítem contra el
    #    catálogo, la orden y el historial. Acá se atrapa el error de escala,
    #    que es el que no se ve y el que mueve el stock.
    for it in items:
        a = _resolver_codigo(it)
        if a:
            resultado["items_catalogo"] += 1
            it["codigo_catalogo"] = a["codigo"]

    pedidos = _pedidos_de_orden_abierta(prov)
    avisos = validacion.validar_items(
        items, pedidos=pedidos, resolver=_resolver_codigo, lang=lang)
    resultado["alertas"].extend(avisos)
    # lo que NO se puede persistir sin que un humano lo toque
    resultado["bloqueantes"] = validacion.bloqueantes(avisos)

    # 4) fechas: manda el PAPEL, no la conversión del modelo
    resultado["alertas"].extend(_conciliar_fechas(extraccion, lang))
    return resultado


def _pedidos_de_orden_abierta(proveedor: str) -> dict:
    """{codigo: cantidad} de la OC abierta del proveedor — el contraste que
    convierte "llegaron 800" en "pediste 80, esto es un ×10"."""
    ordenes = _ordenes_abiertas(proveedor) if proveedor else []
    if not ordenes:
        return {}
    return {int(i["codigo"]): float(i["cantidad"])
            for i in ordenes[0].get("items", []) if i.get("codigo") is not None}


def _conciliar_fechas(extraccion: dict, lang: str | None = None) -> list[dict]:
    """La fecha del comprobante y la de cada lote, reparseadas del texto impreso
    con locale argentino. Si el modelo convirtió mal, se corrige acá y se dice."""
    alertas = []
    r = validacion.conciliar_fecha(extraccion.get("fecha_texto"),
                                   extraccion.get("fecha"), "fecha", lang)
    if r["fecha"]:
        extraccion["fecha"] = r["fecha"]
    if r["alerta"]:
        alertas.append(r["alerta"])
    for it in extraccion.get("items") or []:
        rv = validacion.conciliar_fecha(it.get("vencimiento_texto"),
                                        it.get("vencimiento"), "vencimiento", lang)
        if rv["fecha"]:
            it["vencimiento"] = rv["fecha"]
        if rv["alerta"]:
            alertas.append({**rv["alerta"],
                            "producto": it.get("descripcion")})
    return alertas


# --- Cruces del circuito de compra ---------------------------------------------

def _ordenes_abiertas(proveedor: str) -> list[dict]:
    n = _norm_proveedor(proveedor)
    return [o for o in esquema.filas("ordenes_compra")
            if o.get("estado") == "abierta" and _norm_proveedor(o.get("proveedor")) == n]


def cruzar_remito(extraccion: dict) -> dict:
    """Remito ↔ orden de compra: coincidencias, faltantes, sobrantes y lo que
    no se pidió — el control se hace ANTES de ingresar al stock."""
    prov = (extraccion.get("proveedor") or {}).get("razon_social") or ""
    ordenes = _ordenes_abiertas(prov)
    if not ordenes:
        return {"oc_encontrada": None, "coincidencias": 0, "diferencias": [],
                "total_items": len(extraccion.get("items") or [])}
    oc = ordenes[0]
    pedidos = {}
    for it in oc.get("items", []):
        pedidos[int(it["codigo"])] = {"producto": it["producto"],
                                      "cantidad": float(it["cantidad"])}
    coincidencias, diferencias, vistos = 0, [], set()
    for it in extraccion.get("items") or []:
        a = _resolver_codigo(it)
        cod = a["codigo"] if a else None
        recibido = float(it.get("cantidad") or 0)
        if cod in pedidos:
            vistos.add(cod)
            if abs(recibido - pedidos[cod]["cantidad"]) < 0.01:
                coincidencias += 1
            else:
                diferencias.append({"tipo": "cantidad",
                                    "producto": pedidos[cod]["producto"],
                                    "pedido": pedidos[cod]["cantidad"],
                                    "recibido": recibido})
        else:
            diferencias.append({"tipo": "no_pedido",
                                "producto": (a or {}).get("descripcion")
                                or it.get("descripcion"),
                                "recibido": recibido})
    for cod, p in pedidos.items():
        if cod not in vistos:
            diferencias.append({"tipo": "faltante", "producto": p["producto"],
                                "pedido": p["cantidad"]})
    return {"oc_encontrada": {"numero": oc.get("numero"), "fecha": oc.get("fecha")},
            "coincidencias": coincidencias, "diferencias": diferencias,
            "total_items": len(pedidos)}


def _recepciones_recientes(proveedor: str, dias: int = 7) -> list[dict]:
    """Contra qué reconciliar la factura: si hay remitos INGRESADOS POR FOTO
    de este proveedor en la ventana, la factura se cruza contra ESOS (son la
    entrega que vino a cobrar); si no, contra las recepciones del período."""
    n = _norm_proveedor(proveedor)
    desde = hoy() - datetime.timedelta(days=dias)
    out = []
    for f in esquema.filas("recepciones"):
        if _norm_proveedor(f.get("proveedor")) != n:
            continue
        fecha = parse_fecha(f.get("fecha"))
        if fecha and fecha >= desde:
            out.append(f)
    por_foto = [f for f in out if str(f.get("origen", "")).startswith("remito")]
    return por_foto or out


def cruzar_factura(extraccion: dict) -> dict:
    """Factura ↔ remito: ¿lo facturado coincide con lo que de verdad llegó?"""
    prov = (extraccion.get("proveedor") or {}).get("razon_social") or ""
    recibidos = {}
    for f in _recepciones_recientes(prov):
        try:
            recibidos[int(f["codigo"])] = recibidos.get(int(f["codigo"]), 0) + float(f["cantidad"])
        except (TypeError, ValueError, KeyError):
            continue
    if not recibidos:
        return {"remito_encontrado": False, "coincidencias": 0, "diferencias": []}
    coincidencias, diferencias = 0, []
    for it in extraccion.get("items") or []:
        a = _resolver_codigo(it)
        if not a:
            continue
        cod = a["codigo"]
        facturado = float(it.get("cantidad") or 0)
        if cod in recibidos:
            if abs(facturado - recibidos[cod]) < 0.01:
                coincidencias += 1
            else:
                diferencias.append({"tipo": "cantidad", "producto": a["descripcion"],
                                    "recibido": recibidos[cod], "facturado": facturado})
        else:
            diferencias.append({"tipo": "no_recibido", "producto": a["descripcion"],
                                "facturado": facturado})
    return {"remito_encontrado": True, "coincidencias": coincidencias,
            "diferencias": diferencias}


# --- Confirmación (nada entra sin el sí explícito) ------------------------------

def confirmar_remito(extraccion: dict, actor: str = "dueño",
                     lang: str | None = None) -> dict:
    """Con el sí: la mercadería ENTRA al stock (con backup + audit, como toda
    escritura de la casa), las filas van al apartado de recepciones, y si había
    una orden de compra abierta queda marcada como recibida."""
    prov = (extraccion.get("proveedor") or {}).get("razon_social") or ""

    # EL FRENO. La validación se recorre de nuevo ACÁ, sobre lo que el humano
    # va a confirmar de verdad — no sobre lo que se le mostró hace un rato. Si
    # quedó una cantidad implausible, no se persiste NADA: se devuelve el
    # motivo, el humano corrige el número arriba y vuelve a confirmar (ahí la
    # sospecha ya no está y pasa). Un precio raro no frena: una factura puede
    # tener un precio raro de verdad. Una cantidad rara mueve el stock.
    avisos = validacion.validar_items(
        extraccion.get("items") or [], pedidos=_pedidos_de_orden_abierta(prov),
        resolver=_resolver_codigo, lang=lang)
    frenos = validacion.bloqueantes(avisos)
    if frenos:
        raise ValueError(_t("core.val.bloqueado", lang, n=len(frenos)))

    _conciliar_fechas(extraccion, lang)   # manda el papel, no el modelo
    cruce = cruzar_remito(extraccion)
    fecha = extraccion.get("fecha") or hoy().isoformat()

    raw = store.raw_actual()
    backup = store.versiones.save(
        {"articulos": raw},
        motivo=f"Backup antes de ingresar remito {extraccion.get('numero') or ''}".strip(),
        autor=actor)
    ingresados, sin_catalogo, filas_recepcion = 0, [], []
    filas_deposito = []
    for it in extraccion.get("items") or []:
        a = _resolver_codigo(it)
        cantidad = float(it.get("cantidad") or 0)
        if not a:
            sin_catalogo.append(it.get("descripcion"))
            continue
        art = next(x for x in raw if x.get("codigo") == a["codigo"])
        art["stock"] = round((art.get("stock") or 0) + cantidad, 2)
        if (art.get("stock") or 0) > 0 and art.get("costo_iva"):
            art["inmovilizado"] = round(art["stock"] * art["costo_iva"], 2)
        ingresados += 1
        filas_recepcion.append({
            "fecha": fecha, "codigo": art["codigo"], "producto": art["descripcion"],
            "proveedor": prov, "cantidad": cantidad, "deposito": "Depósito Central",
            "origen": f"remito {extraccion.get('numero') or 's/n'} (foto)",
        })
        # El remito trae lote y vencimiento; el depósito los necesita para que la
        # alerta de vencimiento exista desde que la mercadería toca el piso y no
        # cuando ya es tarde. Sin vencimiento leído no se inventa una fila.
        vto = (it.get("vencimiento") or "").strip()
        if vto and parse_fecha(vto):
            filas_deposito.append({
                "codigo": art["codigo"], "producto": art["descripcion"],
                "ubicacion": "Depósito Central - a ubicar",
                "lote": (it.get("lote") or "").strip() or "s/l",
                "vencimiento": vto, "cantidad": cantidad,
                "origen": f"remito {extraccion.get('numero') or 's/n'} (foto)",
            })
    store.guardar(raw)
    if filas_recepcion:
        esquema.crear_apartado("recepciones", filas_recepcion)
    if filas_deposito:
        esquema.crear_apartado("deposito", filas_deposito)
    if cruce.get("oc_encontrada"):
        _cerrar_orden(cruce["oc_encontrada"]["numero"])
    store.audit.record(actor=actor, accion="cargar_remito",
                       antes={"numero": extraccion.get("numero"), "proveedor": prov},
                       despues={"items_al_stock": ingresados,
                                "version_backup": backup["id"],
                                "diferencias_oc": len(cruce.get("diferencias") or [])})
    return {"ok": True, "tipo": "remito", "items_al_stock": ingresados,
            "sin_catalogo": sin_catalogo, "version_backup": backup["id"],
            "lotes_al_deposito": len(filas_deposito),
            # Si faltó mercadería, Ángela PROPONE el reclamo — no lo dispara.
            # El dueño decide (POST /api/remito/reclamar).
            "reclamo_sugerido": reclamo_sugerido(cruce, prov, lang),
            "cruce_oc": cruce, "sync": _sync_simulado(lang)}


def reclamo_sugerido(cruce: dict, proveedor: str, lang: str | None = None) -> dict | None:
    """Lo que falta del remito contra la orden, listo para reclamarle al
    proveedor. Devuelve la PROPUESTA, no el reclamo: quien decide es el dueño.

    Es determinista: el monto sale de cantidad faltante × costo de catálogo, no
    de una estimación. Se engancha con el circuito que ya existe (core/piso):
    cada faltante entra como reporte y `piso.propuestas()` los agrupa por
    proveedor en el reclamo que el dueño aprueba."""
    faltantes = [d for d in (cruce.get("diferencias") or [])
                 if d.get("tipo") in ("faltante", "cantidad")]
    if not faltantes:
        return None
    catalogo = {_norm(a.get("descripcion")): a for a in store.raw_actual()}
    items, monto = [], 0.0
    for d in faltantes:
        pedido = float(d.get("pedido") or 0)
        recibido = float(d.get("recibido") or 0)
        falta = round(pedido - recibido, 2)
        if falta <= 0:                     # llegó de MÁS: no es un reclamo
            continue
        art = catalogo.get(_norm(d.get("producto")))
        costo = float((art or {}).get("costo_iva") or 0)
        monto += falta * costo
        items.append({"producto": d.get("producto"), "pedido": pedido,
                      "recibido": recibido, "falta": falta,
                      "monto": round(falta * costo, 2)})
    if not items:
        return None
    return {"proveedor": proveedor, "items": items, "monto": round(monto, 2),
            "oc": (cruce.get("oc_encontrada") or {}).get("numero"),
            "texto": _t("core.comp.reclamo_prop", lang, n=len(items),
                        proveedor=proveedor)}


def _cerrar_orden(numero: str) -> None:
    data = esquema._load()
    oc_ap = data.get("ordenes_compra")
    if not oc_ap:
        return
    for o in oc_ap.get("filas", []):
        if o.get("numero") == numero:
            o["estado"] = "recibida"
    esquema._save(data)


def confirmar_factura(extraccion: dict, actor: str = "dueño",
                      lang: str | None = None) -> dict:
    """Con el sí: la factura entra al apartado de compras y golpea la cuenta
    corriente del proveedor (ahora le debés $X, vence tal fecha)."""
    cruce = cruzar_factura(extraccion)
    prov = (extraccion.get("proveedor") or {}).get("razon_social") or ""
    total = float(extraccion.get("total") or 0)
    fecha = extraccion.get("fecha") or hoy().isoformat()
    vencimiento = extraccion.get("vencimiento")
    if not vencimiento:
        cond = _norm(extraccion.get("condicion"))
        m = re.search(r"(\d+)\s*d", cond)
        base = parse_fecha(fecha) or hoy()
        vencimiento = (base + datetime.timedelta(days=int(m.group(1)) if m else 30)).isoformat()

    fila = {
        "fecha": fecha, "numero": extraccion.get("numero"),
        "proveedor": prov, "cuit": (extraccion.get("proveedor") or {}).get("cuit"),
        "condicion": extraccion.get("condicion"),
        "subtotal": extraccion.get("subtotal"), "iva": extraccion.get("iva"),
        "total": total, "vencimiento": vencimiento,
        "items": extraccion.get("items") or [],
        "cargado_por": actor, "sync_erp": "simulado",
    }
    esquema.crear_apartado("compras", [fila])
    cuenta = _asentar_proveedor(prov, "factura", total, extraccion.get("numero"), vencimiento)
    store.audit.record(actor=actor, accion="cargar_factura",
                       antes={"numero": extraccion.get("numero"), "proveedor": prov},
                       despues={"total": total, "vencimiento": vencimiento})
    return {"ok": True, "tipo": "factura", "total": total,
            "vencimiento": vencimiento, "saldo_proveedor": cuenta["saldo"],
            "cruce_remito": cruce, "sync": _sync_simulado(lang)}


def confirmar_recibo(extraccion: dict, actor: str = "dueño",
                     lang: str | None = None) -> dict:
    """Con el sí: el cobro del cliente baja su deuda por el riel de siempre
    (cuentas.registrar_cobro): scoring y caja se recomponen solos."""
    from . import cuentas
    nombre = ((extraccion.get("cliente") or {}).get("razon_social")
              or (extraccion.get("proveedor") or {}).get("razon_social") or "")
    monto = float(extraccion.get("total") or 0)
    c = cuentas.buscar(nombre)
    if not c:
        return {"ok": False, "tipo": "recibo",
                "error": _t("core.comp.recibo_sin_cliente", lang, nombre=nombre)}
    antes = {"saldo": c["saldo"], "dias_sin_pagar": c.get("dias_sin_pagar", 0)}
    actualizado = cuentas.registrar_cobro(c["id"], monto)
    store.audit.record(actor=actor, accion="cargar_recibo",
                       antes={"cliente": c["nombre"], **antes},
                       despues={"cobro": monto, "saldo": actualizado["saldo"]})
    return {"ok": True, "tipo": "recibo", "cliente": c["nombre"], "cobro": monto,
            "saldo_antes": antes["saldo"], "saldo_despues": actualizado["saldo"],
            "scoring": actualizado.get("score"), "sync": _sync_simulado(lang)}


def confirmar_orden_compra(extraccion: dict, actor: str = "dueño",
                           lang: str | None = None) -> dict:
    """Una orden de compra cargada por foto queda ABIERTA, esperando su remito."""
    prov = (extraccion.get("proveedor") or {}).get("razon_social") or ""
    items = []
    for it in extraccion.get("items") or []:
        a = _resolver_codigo(it)
        items.append({"codigo": (a or {}).get("codigo") or it.get("codigo"),
                      "producto": (a or {}).get("descripcion") or it.get("descripcion"),
                      "cantidad": it.get("cantidad")})
    fila = {"numero": extraccion.get("numero"),
            "fecha": extraccion.get("fecha") or hoy().isoformat(),
            "proveedor": prov, "estado": "abierta", "items": items,
            "cargado_por": actor}
    esquema.crear_apartado("ordenes_compra", [fila])
    store.audit.record(actor=actor, accion="cargar_orden_compra",
                       antes={"numero": fila["numero"]}, despues={"items": len(items)})
    return {"ok": True, "tipo": "orden_compra", "numero": fila["numero"],
            "items": len(items), "sync": _sync_simulado(lang)}


def confirmar_lista_precios(extraccion: dict, actor: str = "dueño",
                            lang: str | None = None) -> dict:
    """P22·A — el OK a la lista de precios: actualización masiva de costos con
    backup. El preview ya decidió qué entra (los ítems que llegan acá son los
    aprobados/corregidos; los retenidos no viajan)."""
    from . import lista_precios
    d = lista_precios.diff(extraccion, lang)
    aplicables = [{"codigo": x["codigo"], "precio_nuevo": x["precio_nuevo"]}
                  for x in d["items"]
                  if x["estado"] == "ok" and x.get("precio_nuevo")]
    r = lista_precios.aplicar(aplicables, actor=actor, lang=lang)
    if not r.get("ok"):
        return r
    r["proveedor"] = d["proveedor"]
    r["retenidos"] = len(d["dudosos"])
    r["promedio_pct"] = d["promedio_pct"]
    r["sync"] = _sync_simulado(lang)
    return r


def confirmar(extraccion: dict, actor: str = "dueño", lang: str | None = None) -> dict:
    tipo = extraccion.get("tipo_comprobante")
    fns = {"remito": confirmar_remito, "factura": confirmar_factura,
           "recibo": confirmar_recibo, "orden_compra": confirmar_orden_compra,
           "lista_precios": confirmar_lista_precios}
    if tipo not in fns:
        raise ValueError(f"tipo de comprobante desconocido: {tipo}")
    r = fns[tipo](extraccion, actor, lang)
    if r.get("ok"):
        r["mensaje_angela"] = mensaje_proactivo(r, extraccion, lang)
    return r


def _fecha_legible(iso, lang: str | None = None) -> str:
    f = parse_fecha(iso)
    if not f:
        return str(iso or "")
    if (lang or "").startswith("en"):
        import i18n
        return f"{i18n.mes_nombre(f.month, lang)} {f.day}, {f.year}"
    return f.strftime("%d/%m/%Y")


def mensaje_proactivo_partes(resultado: dict, extraccion: dict) -> list[dict]:
    """Lo mismo que `mensaje_proactivo`, pero SIN renderizar: [{k, p}, ...].

    Por qué existe: el texto que se ve en pantalla se arma en el FRONTEND, en el
    idioma que el usuario está mirando. El backend resuelve su idioma del perfil
    y el chrome resuelve el suyo del navegador; cuando no coinciden —y no
    coinciden— salía un párrafo en español sobre una UI en inglés. Acá viajan la
    decisión y los NÚMEROS (que siguen siendo del core, deterministas); el idioma
    lo pone quien dibuja.

    Convención de params, para que el frontend formatee sin saber de cada clave:
      · `*_pesos`  → plata, se formatea con peso()
      · `*_fecha`  → fecha ISO, se formatea con fecha()
      · el resto viaja tal cual
    """
    numero = extraccion.get("numero") or "s/n"
    prov = (extraccion.get("proveedor") or {}).get("razon_social") or ""
    tipo = resultado.get("tipo")
    out: list[dict] = []

    if tipo == "remito":
        out.append({"k": "remito", "p": {"numero": numero, "proveedor": prov,
                                         "n": resultado.get("items_al_stock", 0)}})
        cruce = resultado.get("cruce_oc") or {}
        if cruce.get("oc_encontrada"):
            out.append({"k": "remito_oc", "p": {
                "oc": cruce["oc_encontrada"]["numero"],
                "n": cruce.get("coincidencias", 0),
                "m": cruce.get("total_items", 0),
                "d": len(cruce.get("diferencias") or [])}})
        else:
            out.append({"k": "remito_sin_oc", "p": {}})
        if resultado.get("lotes_al_deposito"):
            out.append({"k": "remito_lotes",
                        "p": {"n": resultado["lotes_al_deposito"]}})
        if resultado.get("sin_catalogo"):
            out.append({"k": "sin_catalogo", "p": {
                "lista": ", ".join(str(x) for x in resultado["sin_catalogo"])}})

    elif tipo == "factura":
        out.append({"k": "factura", "p": {"numero": numero, "proveedor": prov,
                                          "total_pesos": resultado.get("total") or 0}})
        cruce = resultado.get("cruce_remito") or {}
        if cruce.get("remito_encontrado"):
            difs = len(cruce.get("diferencias") or [])
            out.append({"k": "factura_cierra", "p": {}} if not difs
                       else {"k": "factura_dif", "p": {"n": difs}})
        else:
            out.append({"k": "factura_sin_remito", "p": {}})
        out.append({"k": "factura_cuenta", "p": {
            "proveedor": prov,
            "saldo_pesos": resultado.get("saldo_proveedor") or 0,
            "vence_fecha": resultado.get("vencimiento")}})

    elif tipo == "recibo":
        out.append({"k": "recibo", "p": {
            "cliente": resultado.get("cliente"),
            "monto_pesos": resultado.get("cobrado") or 0,
            "antes_pesos": resultado.get("saldo_antes") or 0,
            "despues_pesos": resultado.get("saldo_despues") or 0,
            "score": resultado.get("scoring") or ""}})

    elif tipo == "lista_precios":
        # el efecto en cascada, con los números REALES: margen antes → después
        pct = lambda v: f"{v:g}%" if v is not None else "—"   # noqa: E731
        out.append({"k": "lista", "p": {
            "n": resultado.get("items", 0), "proveedor": prov,
            "antes": pct(resultado.get("margen_antes")),
            "despues": pct(resultado.get("margen_despues")),
            "backup": resultado.get("version_backup")}})
        if resultado.get("retenidos"):
            out.append({"k": "lista_retenidos", "p": {"n": resultado["retenidos"]}})
    return out


def mensaje_proactivo(resultado: dict, extraccion: dict, lang: str | None = None) -> str:
    """El análisis que Ángela dice SOLA apenas se confirma una carga: qué entró,
    el cruce que corresponde y qué impactó. Determinista (lo compone el core con
    los números ya calculados, no el modelo): en cámara dice siempre lo mismo."""
    import i18n
    numero = extraccion.get("numero") or "s/n"
    prov = (extraccion.get("proveedor") or {}).get("razon_social") or ""
    tipo = resultado.get("tipo")
    partes: list[str] = []
    if tipo == "remito":
        partes.append(_t("core.comp.pro_remito", lang, numero=numero,
                         proveedor=prov, n=resultado.get("items_al_stock", 0)))
        cruce = resultado.get("cruce_oc") or {}
        if cruce.get("oc_encontrada"):
            difs = len(cruce.get("diferencias") or [])
            dif = _t("core.comp.pro_remito_dif", lang, d=difs) if difs else ""
            partes.append(_t("core.comp.pro_remito_oc", lang,
                             oc=cruce["oc_encontrada"]["numero"],
                             n=cruce.get("coincidencias", 0),
                             m=cruce.get("total_items", 0), dif=dif))
        else:
            partes.append(_t("core.comp.pro_remito_sin_oc", lang))
        if resultado.get("sin_catalogo"):
            partes.append(_t("core.comp.pro_sin_catalogo", lang,
                             lista=", ".join(str(x) for x in resultado["sin_catalogo"])))
    elif tipo == "factura":
        partes.append(_t("core.comp.pro_factura", lang, numero=numero, proveedor=prov,
                         total=i18n.pesos(resultado.get("total") or 0, lang)))
        cruce = resultado.get("cruce_remito") or {}
        if cruce.get("remito_encontrado"):
            difs = len(cruce.get("diferencias") or [])
            partes.append(_t("core.comp.pro_factura_cierra", lang) if not difs
                          else _t("core.comp.pro_factura_dif", lang, n=difs))
        else:
            partes.append(_t("core.comp.pro_factura_sin_remito", lang))
        partes.append(_t("core.comp.pro_factura_cuenta", lang, proveedor=prov,
                         saldo=i18n.pesos(resultado.get("saldo_proveedor") or 0, lang),
                         fecha=_fecha_legible(resultado.get("vencimiento"), lang)))
    elif tipo == "recibo":
        score = resultado.get("scoring")
        score_txt = _t(f"core.cuentas.score_id_{score}", lang) if score else "—"
        partes.append(_t("core.comp.pro_recibo", lang,
                         cliente=resultado.get("cliente"),
                         monto=i18n.pesos(resultado.get("cobro") or 0, lang),
                         antes=i18n.pesos(resultado.get("saldo_antes") or 0, lang),
                         despues=i18n.pesos(resultado.get("saldo_despues") or 0, lang),
                         score=score_txt))
    elif tipo == "orden_compra":
        partes.append(_t("core.comp.pro_oc", lang, numero=numero, proveedor=prov,
                         n=resultado.get("items", 0)))
    elif tipo == "lista_precios":
        # el efecto en cascada, con los números REALES: margen antes → después
        partes.append(_t("core.comp.pro_lista", lang, n=resultado.get("items", 0),
                         proveedor=prov,
                         antes=f"{resultado.get('margen_antes'):g}%"
                         if resultado.get("margen_antes") is not None else "—",
                         despues=f"{resultado.get('margen_despues'):g}%"
                         if resultado.get("margen_despues") is not None else "—",
                         backup=resultado.get("version_backup")))
        if resultado.get("retenidos"):
            partes.append(_t("core.comp.pro_lista_retenidos", lang,
                             n=resultado["retenidos"]))
    return " ".join(p for p in partes if p).strip()


def _sync_simulado(lang: str | None = None) -> dict:
    """El tramo hacia el ERP es SIMULADO Y SE DICE (honestidad de UI de la
    casa). El delta export real es UPDATE-only: forzarlo a INSERTs sería
    mentirle al ERP — por eso acá hay una cola declarada, no un export trucho."""
    # `k` es la clave para que el frontend lo diga en SU idioma; `mensaje` queda
    # renderizado para los consumidores que no dibujan (notificaciones, logs).
    return {"estado": "simulado", "k": "sync_simulado",
            "mensaje": _t("core.comp.sync_simulado", lang)}


# --- Lectura para Ángela (tool consultar_compras) -------------------------------

def compras_recientes(n: int = 5) -> list[dict]:
    filas = esquema.filas("compras")
    out = sorted(filas, key=lambda f: str(f.get("fecha") or ""), reverse=True)[:n]
    return [{k: v for k, v in f.items() if k != "items"} | {"items": len(f.get("items") or [])}
            for f in out]


def resumen_proveedor(nombre: str) -> dict:
    r = resolver_proveedor(nombre)
    cuenta = cuenta_proveedor(r.get("parecido_a") or r["nombre"])
    return {"proveedor": cuenta["proveedor"], "saldo": cuenta["saldo"],
            "vencimiento_proximo": cuenta.get("vencimiento_proximo"),
            "movimientos": cuenta["movimientos"][-5:]}


def recepciones_recientes_resumen(n: int = 5) -> list[dict]:
    """Los remitos INGRESADOS POR FOTO, agrupados por comprobante — la mitad
    de la respuesta a «¿qué acabo de cargar?» que antes faltaba: un remito
    confirmado vive en recepciones, no en compras."""
    grupos: dict = {}
    for f in esquema.filas("recepciones"):
        origen = str(f.get("origen") or "")
        if not origen.startswith("remito"):
            continue  # recepciones del WMS/seed: no son comprobantes cargados
        clave = (origen, f.get("proveedor"), f.get("fecha"))
        g = grupos.setdefault(clave, {"fecha": f.get("fecha"),
                                      "proveedor": f.get("proveedor"),
                                      "origen": origen, "items": 0, "unidades": 0.0})
        g["items"] += 1
        try:
            g["unidades"] = round(g["unidades"] + float(f.get("cantidad") or 0), 2)
        except (TypeError, ValueError):
            pass
    out = sorted(grupos.values(), key=lambda g: str(g.get("fecha") or ""), reverse=True)
    return out[:n]


def cobros_recientes(n: int = 5) -> list[dict]:
    """Los cobros registrados (recibos por foto y cobros por chat), leídos del
    riel de cuentas — la otra mitad que faltaba."""
    from . import cuentas
    out = []
    for c in cuentas.listar():
        for m in c.get("movimientos", []):
            if m.get("tipo") == "cobro":
                out.append({"fecha": m.get("fecha"), "cliente": c["nombre"],
                            "monto": m.get("monto"), "saldo_actual": c["saldo"]})
    out.sort(key=lambda x: str(x.get("fecha") or ""), reverse=True)
    return out[:n]


def comprobantes_recientes(n: int = 5) -> dict:
    """TODO lo cargado por comprobante, por sus tres rieles: facturas (compras),
    remitos (recepciones al stock) y recibos (cobros de clientes)."""
    return {"compras_recientes": compras_recientes(n),
            "recepciones_recientes": recepciones_recientes_resumen(n),
            "cobros_recientes": cobros_recientes(n)}

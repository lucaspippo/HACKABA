"""
cruces.py — LOS HALLAZGOS QUE NINGÚN ERP CON CHAT PUEDE DAR.

La diferencia entre una alerta y un cruce:

    ALERTA  mira UNA fuente y avisa un umbral. "Te quedan 7 días de gaseosa."
            Cualquier ERP con un chat encima lo hace, y por eso no prueba nada.
    CRUCE   junta fuentes que NO se hablan entre sí y encadena una consecuencia
            que nadie tenía a la vista. "El que más te debe se lleva justo lo
            que se te vence la semana que viene: ofrecele saldar con eso."

Este módulo hace lo segundo. Cada cruce toca TRES O MÁS dominios distintos
(cuentas · ventas · depósito · proveedores · logística · notas del equipo) y
declara cuáles en `dominios`, para que el que mire pueda auditarlo.

DOS FUENTES NUEVAS lo hacen posible:
  · `ventas_cliente` — qué se lleva cada cliente (antes la cuenta corriente
    decía "Pedido mayorista" y un monto, nunca el producto).
  · `notas` — la capa NO estructurada: lo que el equipo le cuenta a Ángela por
    voz, por reporte del piso o por chat. Lo que sabe el que maneja el camión y
    nunca llega a un sistema.

DETERMINISMO (la regla de la casa): acá se DETECTA y se CALCULA. Cada número
sale de los módulos que ya son la verdad del negocio (`cuentas`, `vencimientos`,
`reposicion`, `analisis`) — este archivo no recalcula ni redondea un canónico.
Ángela recibe el cruce armado y sólo pone las palabras. Si falta el dato, el
cruce no sale: no hay hallazgo a medias.

El shape de salida es el MISMO de `oportunidades_neg.cards()` (id, titulo,
monto, resumen, datos, fuentes, drill) para que el camino del cerebro
(`grafo.caminos`) los resuelva sin un caso especial.
"""
from __future__ import annotations

import datetime

import i18n

from . import (analisis, cuentas, deposito, notas, reposicion, store,
               ventas_cliente, vencimientos)
from .fechas import hoy

# --- parámetros del cruce, explícitos (nada mágico) ---------------------------
VENTANA_NOTAS_DIAS = 30      # una nota de hace tres meses ya no es una señal
REINCIDENCIA_MIN = 2         # "pasó dos veces" es patrón; una vez es anécdota
TOP_CLIENTE_PRODUCTOS = 6    # cuántos productos se miran de cada cliente
CLIENTE_CLAVE_TOP = 8        # "de los que más te compran" = top 8 de 24
DELAY_EMPEORA_DIAS = 3       # cuánto tiene que estirarse el pago para contar


def _t(key: str, lang: str | None = None, **params) -> str:
    return i18n.t(key, lang, **params)


def _pesos(n, lang) -> str:
    return i18n.pesos(n or 0, lang)


def _desde(dias: int) -> str:
    return (hoy() - datetime.timedelta(days=dias)).isoformat()


def _card(cid, tipo, titulo, monto, resumen, dominios, fuentes, porque,
          datos, involucrados, accion_chat, navegar=None, no_estructurado=False) -> dict:
    """El shape común. `dominios` es la prueba de que el cruce es un cruce."""
    return {
        "id": cid, "tipo": tipo, "titulo": titulo, "monto": monto,
        "resumen": resumen, "accion_chat": accion_chat, "navegar": navegar,
        "fuentes": fuentes,
        "dominios": dominios,
        "cruce": True,
        "no_estructurado": no_estructurado,
        "datos": datos,
        "drill": {"porque": porque, "grafico": None,
                  "involucrados": involucrados, "supuestos": []},
    }


def _nota_dict(n, lang) -> dict:
    return {"id": n["id"], "autor": n["autor"], "fecha": n["fecha"],
            "canal": n["canal"], "tipo": n["tipo"],
            "texto": notas.texto_en(n, lang)}


# =============================================================================
# 1 · CUENTAS × VENTAS × DEPÓSITO
#     El que más te debe se lleva justo lo que se te vence.
# =============================================================================

def _cruce_deuda_vencimiento(lang, ctx) -> dict | None:
    morosos = [c for c in ctx["clientes"] if c.get("en_mora")]
    riesgo = ctx["vencen"]
    if not morosos or not riesgo or not ventas_cliente.hay_datos():
        return None

    mejor = None
    for c in sorted(morosos, key=lambda x: -x["saldo"]):
        # TODO lo que compra, no sólo su top: el producto que se vence puede ser
        # el octavo de su lista y el cruce vale igual (lo que importa es que SÍ
        # se lo lleva). El `share` de cada uno se calcula sobre su total real.
        compras = ventas_cliente.compras_de(c["id"], top=None)
        por_cod = {x["codigo"]: x for x in compras}
        for lote in riesgo:
            comprado = por_cod.get(lote.get("codigo"))
            if not comprado:
                continue
            # el que más plata pone en juego manda (deuda + lote que se tira)
            valor = float(lote.get("plata_en_riesgo") or 0)
            if not mejor or valor > mejor["valor"]:
                mejor = {"cliente": c, "lote": lote, "comprado": comprado, "valor": valor}
    if not mejor:
        return None

    c, lote, comprado = mejor["cliente"], mejor["lote"], mejor["comprado"]
    dias = int(lote.get("dias_restantes") or 0)
    return _card(
        "cruce_deuda_vencimiento", "cobrar",
        _t("core.cru.deuda_venc_t", lang, cliente=c["nombre"]),
        float(lote.get("plata_en_riesgo") or 0),
        _t("core.cru.deuda_venc_r", lang, cliente=c["nombre"],
           dias_deuda=c["dias_sin_pagar"], producto=lote["producto"], dias=dias),
        ["cuentas", "ventas", "deposito"],
        [_t("core.opn.f_cuentas", lang), _t("core.cru.f_ventas_cliente", lang),
         _t("core.cru.f_vencimientos", lang)],
        [_t("core.cru.deuda_venc_p1", lang, cliente=c["nombre"],
            saldo=_pesos(c["saldo"], lang), dias=c["dias_sin_pagar"]),
         _t("core.cru.deuda_venc_p2", lang, producto=lote["producto"], dias=dias,
            plata=_pesos(lote.get("plata_en_riesgo"), lang),
            sobra=round(float(lote.get("sobrante") or 0))),
         _t("core.cru.deuda_venc_p3", lang, cliente=c["nombre"],
            monto=_pesos(comprado["monto"], lang),
            unidades=round(comprado["cantidad"]),
            pedidos=comprado["pedidos"])],
        {"cliente": c["nombre"], "producto": lote["producto"],
         "codigo": lote.get("codigo"), "saldo": c["saldo"],
         "dias_sin_pagar": c["dias_sin_pagar"], "dias_para_vencer": dias,
         "plata_en_riesgo": lote.get("plata_en_riesgo"),
         "comprado_12m": comprado["monto"]},
        [{"nombre": c["nombre"], "monto": c["saldo"],
          "detalle": _t("core.opn.morosos_i", lang, dias=c["dias_sin_pagar"])},
         {"nombre": lote["producto"], "monto": lote.get("plata_en_riesgo"),
          "detalle": _t("core.cru.deuda_venc_i", lang, dias=dias,
                        lote=lote.get("lote") or "—")}],
        _t("core.cru.deuda_venc_chat", lang, cliente=c["nombre"],
           producto=lote["producto"]),
        "cuentas")


# =============================================================================
# 2 · PROVEEDORES × VENTAS × INVENTARIO (+ notas del equipo)
#     El proveedor con señales de ruido es el único que te surte tu estrella.
# =============================================================================

def _cruce_proveedor_estrella(lang, ctx) -> dict | None:
    if not ctx["rank"]:
        return None
    # proveedores sobre los que el equipo dejó una nota (la señal blanda)
    con_nota: dict[str, list] = {}
    for n in notas.listar(tipo="nota_proveedor", desde=_desde(60),
                          excluir=ctx["sin_notas"]):
        if n.get("proveedor"):
            con_nota.setdefault(n["proveedor"], []).append(n)
    if not con_nota:
        return None

    por_prov: dict[str, list] = {}
    for a in ctx["arts"]:
        prov = (a.get("proveedor") or "").strip()
        if prov:
            por_prov.setdefault(prov, []).append(a)

    mejor = None
    for prov, notas_prov in con_nota.items():
        arts = por_prov.get(prov) or []
        if not arts:
            continue
        # la estrella de ESE proveedor: su producto mejor rankeado
        estrella, pos = None, None
        for a in arts:
            p = ctx["rank_pos"].get(a.get("descripcion"))
            if p and (pos is None or p < pos):
                estrella, pos = a, p
        if not estrella or pos > 15:
            continue
        fact = sum(ctx["fact_12m"].get(a.get("descripcion"), 0.0) for a in arts)
        lead, propio = reposicion.dias_reposicion(prov)
        if not mejor or fact > mejor["fact"]:
            mejor = {"prov": prov, "arts": arts, "estrella": estrella, "pos": pos,
                     "fact": fact, "lead": lead, "lead_propio": propio,
                     "notas": notas_prov}
    if not mejor:
        return None

    p, e = mejor["prov"], mejor["estrella"]
    # dependencia: cuántos de sus productos NO tienen otro proveedor en el rubro
    rubro = (e.get("tipo") or "").strip()
    alternativas = {(a.get("proveedor") or "").strip()
                    for a in ctx["arts"] if (a.get("tipo") or "").strip() == rubro}
    alternativas.discard(p)
    return _card(
        "cruce_proveedor_estrella", "riesgo",
        _t("core.cru.prov_estrella_t", lang, proveedor=p),
        mejor["fact"],
        _t("core.cru.prov_estrella_r", lang, proveedor=p,
           producto=e.get("descripcion"), pos=mejor["pos"], dias=mejor["lead"]),
        ["proveedores", "ventas", "inventario", "notas"],
        [_t("core.cru.f_notas", lang), _t("core.opn.f_ventas12", lang),
         _t("core.cru.f_condiciones", lang)],
        [_t("core.cru.prov_estrella_p1", lang, proveedor=p,
            n=len(mejor["arts"]), fact=_pesos(mejor["fact"], lang)),
         _t("core.cru.prov_estrella_p2", lang, producto=e.get("descripcion"),
            pos=mejor["pos"], dias=mejor["lead"]),
         _t("core.cru.prov_estrella_p3", lang, autor=mejor["notas"][0]["autor"],
            texto=notas.texto_en(mejor["notas"][0], lang)),
         _t("core.cru.prov_estrella_p4", lang, rubro=rubro,
            n=len(alternativas)) if alternativas
         else _t("core.cru.prov_estrella_p4_solo", lang, rubro=rubro)],
        {"proveedor": p, "producto": e.get("descripcion"),
         "codigo": e.get("codigo"), "posicion_ranking": mejor["pos"],
         "facturacion_12m": round(mejor["fact"], 2),
         "dias_reposicion": mejor["lead"], "alternativas_rubro": len(alternativas),
         "notas": [_nota_dict(n, lang) for n in mejor["notas"]]},
        [{"nombre": p, "monto": round(mejor["fact"], 2),
          "detalle": _t("core.cru.prov_estrella_i", lang, dias=mejor["lead"],
                        n=len(mejor["arts"]))},
         {"nombre": e.get("descripcion"),
          "monto": round(ctx["fact_12m"].get(e.get("descripcion"), 0.0), 2),
          "detalle": _t("core.cru.prov_estrella_i2", lang, pos=mejor["pos"])}],
        _t("core.cru.prov_estrella_chat", lang, proveedor=p),
        "inventario", no_estructurado=True)


# =============================================================================
# 3 · CUENTAS × HISTORIAL DE PAGO × VENTAS
#     Le fías cada vez más al que cada vez tarda más en pagarte.
# =============================================================================

def _delays(c: dict) -> list[int]:
    """Los días que tardó en pagar, en orden. Sale de emparejar cada venta
    histórica con su pago (el historial saldado que ya vive en la cuenta)."""
    movs = sorted((c.get("movimientos") or []), key=lambda m: m.get("fecha") or "")
    out, pendiente = [], None
    for m in movs:
        f = m.get("fecha")
        if m.get("tipo") == "venta":
            pendiente = f
        elif m.get("tipo") in ("pago", "cobro") and pendiente:
            try:
                d = (datetime.date.fromisoformat(f) - datetime.date.fromisoformat(pendiente)).days
                if d >= 0:
                    out.append(d)
            except (TypeError, ValueError):
                pass
            pendiente = None
    return out


def _cruce_credito_creciente(lang, ctx) -> dict | None:
    if not ventas_cliente.hay_datos():
        return None
    mejor = None
    for c in ctx["clientes"]:
        ds = _delays(c)
        if len(ds) < 4:
            continue
        mitad = len(ds) // 2
        viejo = sum(ds[:mitad]) / mitad
        nuevo = sum(ds[mitad:]) / (len(ds) - mitad)
        if nuevo - viejo < DELAY_EMPEORA_DIAS:
            continue
        # ¿y mientras tanto le seguimos vendiendo MÁS?
        reg = ventas_cliente.de(c["id"]) or {}
        pedidos = sorted(reg.get("pedidos", []), key=lambda p: p.get("fecha") or "")
        if len(pedidos) < 4:
            continue
        m = len(pedidos) // 2
        comprado_viejo = sum(p["monto"] for p in pedidos[:m]) / m
        comprado_nuevo = sum(p["monto"] for p in pedidos[m:]) / (len(pedidos) - m)
        if comprado_nuevo <= comprado_viejo:
            continue
        limite = float(c.get("limite_credito") or 0)
        uso = (float(c.get("saldo") or 0) / limite) if limite else 0.0
        puntaje = (nuevo - viejo) * uso
        if not mejor or puntaje > mejor["puntaje"]:
            mejor = {"c": c, "viejo": viejo, "nuevo": nuevo, "uso": uso,
                     "puntaje": puntaje, "comprado_viejo": comprado_viejo,
                     "comprado_nuevo": comprado_nuevo, "n": len(ds)}
    if not mejor:
        return None

    c = mejor["c"]
    top = ventas_cliente.compras_de(c["id"], top=3)
    return _card(
        "cruce_credito_creciente", "riesgo",
        _t("core.cru.credito_t", lang, cliente=c["nombre"]),
        float(c.get("saldo") or 0),
        _t("core.cru.credito_r", lang, cliente=c["nombre"],
           viejo=round(mejor["viejo"]), nuevo=round(mejor["nuevo"]),
           pct=round(mejor["uso"] * 100)),
        ["cuentas", "pagos", "ventas"],
        [_t("core.opn.f_cuentas", lang), _t("core.opn.f_movs", lang),
         _t("core.cru.f_ventas_cliente", lang)],
        [_t("core.cru.credito_p1", lang, cliente=c["nombre"], n=mejor["n"],
            viejo=round(mejor["viejo"]), nuevo=round(mejor["nuevo"])),
         _t("core.cru.credito_p2", lang,
            viejo=_pesos(mejor["comprado_viejo"], lang),
            nuevo=_pesos(mejor["comprado_nuevo"], lang)),
         _t("core.cru.credito_p3", lang, saldo=_pesos(c.get("saldo"), lang),
            limite=_pesos(c.get("limite_credito"), lang),
            pct=round(mejor["uso"] * 100))],
        {"cliente": c["nombre"], "saldo": c.get("saldo"),
         "limite_credito": c.get("limite_credito"),
         "demora_antes": round(mejor["viejo"], 1), "demora_ahora": round(mejor["nuevo"], 1),
         "compra_antes": round(mejor["comprado_viejo"], 2),
         "compra_ahora": round(mejor["comprado_nuevo"], 2),
         "productos": [x["producto"] for x in top]},
        [{"nombre": c["nombre"], "monto": c.get("saldo"),
          "detalle": _t("core.cru.credito_i", lang, pct=round(mejor["uso"] * 100))}]
        + [{"nombre": x["producto"], "monto": x["monto"],
            "detalle": _t("core.cru.credito_i2", lang, pct=round(x["share"] * 100, 1))}
           for x in top],
        _t("core.cru.credito_chat", lang, cliente=c["nombre"]),
        "cuentas")


# =============================================================================
# 4 · NOTAS × VENTAS × LOGÍSTICA
#     Se quejó, y resulta que es de los que más te compran.
# =============================================================================

def _cruce_queja_cliente_clave(lang, ctx) -> dict | None:
    if not ventas_cliente.hay_datos():
        return None
    candidatas = [n for n in notas.listar(desde=_desde(VENTANA_NOTAS_DIAS),
                                          excluir=ctx["sin_notas"])
                  if n.get("tipo") in ("queja_cliente", "incidencia_entrega")
                  and n.get("cliente")]
    if not candidatas:
        return None

    # el ranking REAL de clientes por lo que compran (no por lo que deben)
    ranking = []
    for reg in ventas_cliente.por_cliente().values():
        total = sum(p["monto"] for p in reg.get("pedidos", []))
        ranking.append((total, reg["nombre"], reg["cliente_id"]))
    ranking.sort(reverse=True)
    pos = {nombre: i + 1 for i, (_, nombre, _) in enumerate(ranking)}
    monto_de = {nombre: total for total, nombre, _ in ranking}

    mejor = None
    for n in candidatas:
        p = pos.get(n["cliente"])
        if not p or p > CLIENTE_CLAVE_TOP:
            continue
        if not mejor or p < mejor["pos"]:
            mejor = {"nota": n, "pos": p, "monto": monto_de.get(n["cliente"], 0.0)}
    if not mejor:
        return None

    n = mejor["nota"]
    cli = next((c for c in ctx["clientes"] if c["nombre"] == n["cliente"]), None)
    entregas = [f for f in ctx["logistica"] if (f.get("cliente") or "") == n["cliente"]]
    pendientes = [f for f in entregas if (f.get("estado") or "") == "pendiente"]
    return _card(
        "cruce_queja_clave", "atender",
        _t("core.cru.queja_t", lang, cliente=n["cliente"]),
        mejor["monto"],
        _t("core.cru.queja_r", lang, cliente=n["cliente"], pos=mejor["pos"],
           autor=n["autor"]),
        ["notas", "ventas", "logistica"],
        [_t("core.cru.f_notas", lang), _t("core.cru.f_ventas_cliente", lang),
         _t("core.cru.f_logistica", lang)],
        [_t("core.cru.queja_p1", lang, autor=n["autor"], canal=n["canal"],
            fecha=n["fecha"], texto=notas.texto_en(n, lang)),
         _t("core.cru.queja_p2", lang, cliente=n["cliente"], pos=mejor["pos"],
            monto=_pesos(mejor["monto"], lang)),
         (_t("core.cru.queja_p3", lang, n=len(pendientes))
          if pendientes else _t("core.cru.queja_p3_sin", lang))]
        + ([_t("core.cru.queja_p4", lang, saldo=_pesos(cli["saldo"], lang),
               dias=cli["dias_sin_pagar"])] if cli and cli.get("saldo") else []),
        {"cliente": n["cliente"], "posicion_cliente": mejor["pos"],
         "facturado": round(mejor["monto"], 2),
         "entregas_pendientes": len(pendientes),
         "notas": [_nota_dict(n, lang)]},
        [{"nombre": n["cliente"], "monto": round(mejor["monto"], 2),
          "detalle": _t("core.cru.queja_i", lang, pos=mejor["pos"])}],
        _t("core.cru.queja_chat", lang, cliente=n["cliente"]),
        "cuentas", no_estructurado=True)


# =============================================================================
# 5 · NOTAS × CUENTAS × VENTAS
#     El repartidor lo vio cerrado dos veces — y se está atrasando.
# =============================================================================

def _cruce_cliente_en_problemas(lang, ctx) -> dict | None:
    campo: dict[str, list] = {}
    for n in notas.listar(tipo="observacion_campo", desde=_desde(VENTANA_NOTAS_DIAS),
                          excluir=ctx["sin_notas"]):
        if n.get("cliente"):
            campo.setdefault(n["cliente"], []).append(n)
    reincidentes = {k: v for k, v in campo.items() if len(v) >= REINCIDENCIA_MIN}
    if not reincidentes:
        return None

    mejor = None
    for nombre, ns in reincidentes.items():
        c = next((x for x in ctx["clientes"] if x["nombre"] == nombre), None)
        if not c:
            continue
        expuesto = float(c.get("saldo") or 0)
        if not mejor or expuesto > mejor["expuesto"]:
            mejor = {"c": c, "notas": ns, "expuesto": expuesto}
    if not mejor:
        return None

    c, ns = mejor["c"], sorted(mejor["notas"], key=lambda x: x["fecha"])
    top = ventas_cliente.compras_de(c["id"], top=3) if ventas_cliente.hay_datos() else []
    return _card(
        "cruce_cliente_problemas", "riesgo",
        _t("core.cru.problemas_t", lang, cliente=c["nombre"]),
        float(c.get("saldo") or 0),
        _t("core.cru.problemas_r", lang, cliente=c["nombre"], n=len(ns),
           dias=c.get("dias_sin_pagar")),
        ["notas", "cuentas", "ventas"],
        [_t("core.cru.f_notas", lang), _t("core.opn.f_cuentas", lang),
         _t("core.cru.f_ventas_cliente", lang)],
        [_t("core.cru.problemas_p1", lang, n=len(ns), autor=ns[0]["autor"],
            fechas=", ".join(x["fecha"] for x in ns)),
         _t("core.cru.problemas_p2", lang, texto=notas.texto_en(ns[-1], lang)),
         _t("core.cru.problemas_p3", lang, saldo=_pesos(c.get("saldo"), lang),
            dias=c.get("dias_sin_pagar"), plazo=c.get("plazo_dias"))],
        {"cliente": c["nombre"], "saldo": c.get("saldo"),
         "dias_sin_pagar": c.get("dias_sin_pagar"),
         "observaciones": len(ns),
         "productos": [x["producto"] for x in top],
         "notas": [_nota_dict(x, lang) for x in ns]},
        [{"nombre": c["nombre"], "monto": c.get("saldo"),
          "detalle": _t("core.cru.problemas_i", lang, n=len(ns))}],
        _t("core.cru.problemas_chat", lang, cliente=c["nombre"]),
        "cuentas", no_estructurado=True)


# =============================================================================
# 6 · NOTAS × DEPÓSITO × COMPRAS
#     "No entra más nada en la cámara" — y hay un pedido grande en camino.
# =============================================================================

def _cruce_espacio_camara(lang, ctx) -> dict | None:
    espacio = [n for n in notas.listar(tipo="estado_deposito", desde=_desde(VENTANA_NOTAS_DIAS),
                                       excluir=ctx["sin_notas"])
               if n.get("ubicacion")]
    por_ubi: dict[str, list] = {}
    for n in espacio:
        por_ubi.setdefault(n["ubicacion"], []).append(n)
    reincidentes = {k: v for k, v in por_ubi.items() if len(v) >= REINCIDENCIA_MIN}
    if not reincidentes:
        return None
    ubicacion, ns = max(reincidentes.items(), key=lambda kv: len(kv[1]))

    # cuánto hay HOY en esa ubicación, según el export del depósito
    filas = [f for f in deposito._filas() if (f.get("ubicacion") or "") == ubicacion]
    lotes = len(filas)
    if not lotes:
        return None
    # ¿y qué viene en camino para ese mismo frío?
    entrantes = []
    for oc in ctx["ordenes"]:
        if (oc.get("estado") or "") != "abierta":
            continue
        for it in (oc.get("items") or []):
            art = ctx["por_codigo"].get(it.get("codigo"))
            if not art:
                continue
            entrantes.append({"orden": oc.get("numero"), "proveedor": oc.get("proveedor"),
                              "producto": art.get("descripcion"),
                              "cantidad": it.get("cantidad"),
                              "categoria": art.get("tipo")})
    if not entrantes:
        return None
    vence_ahi = [f for f in ctx["vencen"] if any(
        x.get("ubicacion") == ubicacion for x in filas if x.get("codigo") == f.get("codigo"))]

    return _card(
        "cruce_espacio_camara", "operar",
        _t("core.cru.espacio_t", lang, ubicacion=ubicacion),
        sum(float(x.get("plata_en_riesgo") or 0) for x in vence_ahi),
        _t("core.cru.espacio_r", lang, ubicacion=ubicacion, n=len(ns),
           orden=entrantes[0]["orden"]),
        ["notas", "deposito", "compras"],
        [_t("core.cru.f_notas", lang), _t("core.cru.f_wms", lang),
         _t("core.cru.f_ordenes", lang)],
        [_t("core.cru.espacio_p1", lang, n=len(ns),
            quienes=", ".join(sorted({x["autor"] for x in ns})),
            ubicacion=ubicacion),
         _t("core.cru.espacio_p2", lang, lotes=lotes, ubicacion=ubicacion),
         _t("core.cru.espacio_p3", lang, orden=entrantes[0]["orden"],
            proveedor=entrantes[0]["proveedor"], n=len(entrantes))]
        + ([_t("core.cru.espacio_p4", lang, n=len(vence_ahi),
               plata=_pesos(sum(float(x.get("plata_en_riesgo") or 0) for x in vence_ahi), lang))]
           if vence_ahi else []),
        {"ubicacion": ubicacion, "lotes_en_ubicacion": lotes,
         "orden": entrantes[0]["orden"], "proveedor": entrantes[0]["proveedor"],
         "productos": [x["producto"] for x in entrantes[:4]],
         "vencen_ahi": len(vence_ahi),
         "notas": [_nota_dict(x, lang) for x in ns]},
        [{"nombre": entrantes[0]["proveedor"], "monto": None,
          "detalle": _t("core.cru.espacio_i", lang, orden=entrantes[0]["orden"])}]
        + [{"nombre": x["producto"], "monto": None,
            "detalle": _t("core.cru.espacio_i2", lang, cantidad=x.get("cantidad"))}
           for x in entrantes[:3]],
        _t("core.cru.espacio_chat", lang, ubicacion=ubicacion),
        "deposito", no_estructurado=True)


# =============================================================================
# 7 · OFERTA × ROTACIÓN × VIDA DEL LOTE × NOTAS DEL DEPÓSITO
#     El 18% de descuento que hay que rechazar, y las tres personas que ya
#     dijeron dónde no entra.
# =============================================================================
#
# POR QUÉ ESTE CRUCE EXISTE APARTE DE `sobrecompra`.
#
# `oportunidades_neg._card_sobrecompra` ya hace la cuenta dura y la hace bien:
# oferta × rotación real × vida del lote. Es una card de Oportunidades y su
# camino en el cerebro sale de dos semillas —el producto y el proveedor—, o
# sea que enciende COSAS.
#
# Este cruce agrega la capa que ninguna tabla tiene: las personas que dijeron
# que la cámara está llena, por tres canales distintos, y el mail del propio
# proveedor pidiendo que le avisemos si no hay lugar. Con eso las notas entran
# como SEMILLA (ver grafo.caminos) y el camino enciende GENTE — que es la
# única parte de esto que nadie más puede mostrar.
#
# LA CUENTA NO SE REHACE ACÁ. Los pesos salen citados de la card canónica vía
# `oportunidades_neg.card_por_id` (PRODUCT.md, The Counting Rule): dos sumas
# del mismo número terminan divergiendo, y ésta es plata que se dice en voz
# alta delante de alguien.
#
# HONESTIDAD SOBRE EL ALCANCE, y está acá para que no se diga de más: NO
# afirmamos que el pallet ofertado iría a esa cámara. El export del depósito no
# trae ubicación para todos los códigos del catálogo. Lo que sí está en el
# dato, y es lo que el texto dice, es que el MISMO proveedor tiene mercadería
# entrando a una ubicación que el equipo reporta sin lugar.

CAMARA_PISTAS = ("camara", "cámara")


def _es_camara(ubicacion: str | None) -> bool:
    u = (ubicacion or "").lower()
    return any(p in u for p in CAMARA_PISTAS)


def _cruce_oferta_camara(lang, ctx) -> dict | None:
    from . import oportunidades_neg
    try:
        sobre = oportunidades_neg.card_por_id("sobrecompra", lang)
    except Exception:  # noqa: BLE001 — sin la card canónica no hay cruce
        sobre = None
    if not sobre:
        return None
    d = sobre.get("datos") or {}
    proveedor, producto = d.get("proveedor"), d.get("producto")
    if not proveedor or not producto:
        return None

    # 1 · la capa NO estructurada del espacio: quién dijo que no entra más
    desde = _desde(VENTANA_NOTAS_DIAS)
    llenas: dict[str, list] = {}
    for n in notas.listar(tipo="estado_deposito", desde=desde,
                          excluir=ctx["sin_notas"]):
        if _es_camara(n.get("ubicacion")):
            llenas.setdefault(n["ubicacion"], []).append(n)
    # una sola persona diciéndolo una vez es una anécdota; dos es un hecho
    ubicacion, ns_espacio = None, []
    for u, ns in sorted(llenas.items(), key=lambda kv: -len(kv[1])):
        if len({x["autor"] for x in ns}) >= REINCIDENCIA_MIN:
            ubicacion, ns_espacio = u, ns
            break
    if not ubicacion:
        return None

    # 2 · lo que ese proveedor avisó por su cuenta (mail, voz, chat)
    ns_prov = notas.listar(proveedor=proveedor, desde=desde, excluir=ctx["sin_notas"])
    if not ns_prov:
        return None

    lotes = len([f for f in deposito._filas()
                 if (f.get("ubicacion") or "") == ubicacion])
    canales = sorted({n.get("canal") for n in ns_espacio if n.get("canal")})
    quienes = sorted({n["autor"] for n in ns_espacio})
    notas_todas = ns_espacio + [n for n in ns_prov
                                if n["id"] not in {x["id"] for x in ns_espacio}]

    return _card(
        "cruce_oferta_camara", "comprar",
        _t("core.cru.oferta_t", lang, proveedor=proveedor,
           desc=f"{d.get('descuento_pct'):g}" if d.get("descuento_pct") else "?"),
        # CITADO de la card canónica: lo que esa compra te haría tirar.
        sobre.get("monto"),
        _t("core.cru.oferta_r", lang, producto=producto,
           sug=d.get("cantidad_sugerida"), oferta=d.get("oferta"),
           n=len(quienes), ubicacion=ubicacion),
        ["proveedores", "inventario", "deposito", "notas"],
        [_t("core.cru.f_oferta", lang), _t("core.cru.f_ventas12", lang),
         _t("core.cru.f_wms", lang), _t("core.cru.f_notas", lang)],
        [_t("core.cru.oferta_p1", lang, proveedor=proveedor,
            oferta=d.get("oferta"), desc=f"{d.get('descuento_pct'):g}"
            if d.get("descuento_pct") else "?"),
         _t("core.cru.oferta_p2", lang, producto=producto,
            sug=d.get("cantidad_sugerida"), dias=d.get("dias_vida_lote"),
            meses=d.get("meses_para_venderlo")),
         _t("core.cru.oferta_p3", lang, n=len(quienes), quienes=_y(quienes, lang),
            canales=len(canales), ubicacion=ubicacion, lotes=lotes),
         _t("core.cru.oferta_p4", lang, proveedor=proveedor,
            autor=ns_prov[0]["autor"], canal=ns_prov[0].get("canal"))],
        {"producto": producto, "proveedor": proveedor,
         "oferta": d.get("oferta"), "descuento_pct": d.get("descuento_pct"),
         "cantidad_sugerida": d.get("cantidad_sugerida"),
         "dias_vida_lote": d.get("dias_vida_lote"),
         "ubicacion": ubicacion, "lotes_en_ubicacion": lotes,
         "canales": canales,
         # Las notas viajan acá porque `grafo.caminos` las toma como SEMILLA:
         # sin esto el camino enciende un producto y un proveedor, y la mitad
         # que prueba que el cruce tocó gente se pierde.
         "notas": [_nota_dict(x, lang) for x in notas_todas]},
        [{"nombre": proveedor, "monto": None,
          "detalle": _t("core.cru.oferta_i", lang, desc=f"{d.get('descuento_pct'):g}"
                        if d.get("descuento_pct") else "?")},
         {"nombre": producto, "monto": sobre.get("monto"),
          "detalle": _t("core.cru.oferta_i2", lang, sug=d.get("cantidad_sugerida"))}]
        + [{"nombre": x["autor"], "monto": None,
            "detalle": _t("core.cru.oferta_i3", lang, canal=x.get("canal"),
                          fecha=x.get("fecha"))}
           for x in ns_espacio[:3]],
        _t("core.cru.oferta_chat", lang, producto=producto),
        "inventario", no_estructurado=True)


def _y(nombres: list[str], lang) -> str:
    """«Ramón, Nahuel y Tomás» — la lista como la diría una persona."""
    if not nombres:
        return ""
    if len(nombres) == 1:
        return nombres[0]
    sep = " and " if lang == "en" else " y "
    return ", ".join(nombres[:-1]) + sep + nombres[-1]


# =============================================================================
# el set
# =============================================================================

_SET = (_cruce_deuda_vencimiento, _cruce_proveedor_estrella,
        _cruce_credito_creciente, _cruce_queja_cliente_clave,
        _cruce_cliente_en_problemas, _cruce_espacio_camara,
        _cruce_oferta_camara)


def _ctx(lang, sin_notas: frozenset | None = None) -> dict:
    """UNA pasada por los datos para todos los cruces.

    `sin_notas` viaja en el contexto y no en un global: es el contrafáctico
    («¿y si este dato no estuviera?») y quién lo pidió tiene que verse en la
    llamada. Vacío por default, que es el comportamiento de siempre."""
    from . import esquema
    ctx: dict = {"lang": lang, "clientes": [], "arts": [], "vencen": [],
                 "rank": [], "rank_pos": {}, "fact_12m": {}, "logistica": [],
                 "ordenes": [], "por_codigo": {},
                 "sin_notas": frozenset(sin_notas or ())}
    try:
        ctx["clientes"] = cuentas.listar()
    except Exception:  # noqa: BLE001
        pass
    try:
        ctx["arts"] = [a for a in store.raw_actual() if a.get("estado") == "activo"]
        ctx["por_codigo"] = {a.get("codigo"): a for a in ctx["arts"]}
    except Exception:  # noqa: BLE001
        pass
    try:
        v = vencimientos.en_riesgo(30)
        ctx["vencen"] = v.get("items") or [] if v.get("disponible") else []
    except Exception:  # noqa: BLE001
        pass
    try:
        rot = analisis.rotacion()
        del rot  # sólo para forzar el cache compartido del análisis
    except Exception:  # noqa: BLE001
        pass
    try:
        u12: dict[str, float] = {}
        corte = _desde(365)
        for f in esquema.filas("venta"):
            if f.get("codigo") is None:
                continue
            fecha, prod = f.get("fecha") or "", f.get("producto") or ""
            if fecha >= corte and prod:
                u12[prod] = u12.get(prod, 0.0) + float(f.get("cantidad") or 0) * float(f.get("precio") or 0)
        ctx["fact_12m"] = u12
        rank = sorted(u12.items(), key=lambda kv: -kv[1])
        ctx["rank"] = rank
        ctx["rank_pos"] = {p: i + 1 for i, (p, _) in enumerate(rank)}
    except Exception:  # noqa: BLE001
        pass
    try:
        ctx["logistica"] = esquema.filas("logistica")
        ctx["ordenes"] = esquema.filas("ordenes_compra")
    except Exception:  # noqa: BLE001
        pass
    return ctx


def cards(lang: str | None = None,
          sin_notas: frozenset | set | None = None) -> list[dict]:
    """Los cruces que HOY tienen datos para existir. Un cruce sin dato no se
    inventa: simplemente no aparece.

    `sin_notas` son ids de nota a leer como si no existieran. Es lo que hace
    demostrable la causalidad: sacás la nota de Kevin y el hallazgo se apaga,
    la devolvés y vuelve. Nada se borra — ver `notas.listar`."""
    ctx = _ctx(lang, sin_notas)
    out = []
    for fn in _SET:
        try:
            c = fn(lang, ctx)
        except Exception:  # noqa: BLE001 — un cruce roto no tira los demás
            c = None
        if c:
            out.append(c)
    return out


def resumen() -> dict:
    """Para la meta del cerebro: cuántos cruces hay y cuántos dominios tocan."""
    cs = cards()
    dominios = sorted({d for c in cs for d in c["dominios"]})
    return {"cruces": len(cs), "dominios": dominios,
            "con_no_estructurado": sum(1 for c in cs if c["no_estructurado"]),
            "notas": notas.resumen(), "ventas_cliente": ventas_cliente.resumen()}

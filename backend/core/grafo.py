"""
grafo.py · EL CEREBRO — las entidades reales del negocio y cómo se cruzan.

El mapa (P28–P41) muestra las FUENTES: ocho dominios y sus cortes. Este módulo
expone la capa de abajo: las ENTIDADES individuales —cada producto, cada
cliente, cada proveedor, cada lote— y las relaciones REALES que las unen. Al
correr el layout de fuerzas, las entidades muy conectadas migran solas al
centro: ese núcleo denso ES el negocio, no una decoración.

REGLA DE INTEGRIDAD (P30 sigue vigente acá): este módulo NO inventa ni recalcula
un solo número canónico. El riesgo del cliente sale de `cuentas` (score/en_mora),
el del lote de `deposito.vencimientos()`, el pago vencido de finanzas.json, los
hallazgos de `oportunidades_neg.cards()`. Acá se CRUZA lo que ya está decidido.

Lo único propio es estructural, y va declarado en `meta.derivados`:
  · `peso` de cada nodo = volumen agregado (facturación 12m, saldo, compras).
    Es para el TAMAÑO del punto, no es un número de negocio.
  · aristas producto↔producto por co-venta, medidas con LIFT sobre canastas
    diarias (fecha × boca). Es la única relación no explícita en los datos y
    está calculada, no inventada: sale de las 10.776 filas de venta.

Aditivo por diseño: el mapa de árbol no consume nada de este archivo.
"""
from __future__ import annotations

import datetime
import itertools
import json
import math
import os
import unicodedata

from . import paths
from . import cuentas, deposito, esquema, store
from .fechas import hoy, parse_fecha

DATA_DIR = paths.DATA_DIR
FINANZAS_JSON = os.path.join(DATA_DIR, "finanzas.json")
TRASLADOS_JSON = os.path.join(DATA_DIR, "traslados_internos.json")

# --- parámetros del cruce (explícitos, no mágicos) ---------------------------
VENTANA_MESES = 12          # de cuánto atrás se agrega la facturación por entidad
COVENTA_MIN_CANASTAS = 3    # un par tiene que repetirse para contar
COVENTA_LIFT_MIN = 1.15     # y venderse juntos MÁS de lo que el azar explicaría
COVENTA_TOP = 3             # cuántos vecinos de co-venta guarda cada producto
LOCAL_TOP = 40              # cuántos productos cuelga cada local (el resto satura)
VENCE_PRONTO_DIAS = 30      # misma ventana que vencimientos.VENTANA_DIAS
CLIENTE_TOP_PRODUCTOS = 6   # cuántos productos cuelga cada cliente (lo que de verdad lo define)


# --- el puente cliente↔producto: ANTES inferido, HOY dato --------------------
# Historia de este bloque, porque explica el grafo entero: qué compraba cada
# cliente NO estaba en los datos (las cuentas guardaban "Pedido mayorista" y un
# monto, nunca el producto), así que el puente se INFERÍA del rubro del nombre
# —una panadería no compra lo mismo que un kiosco— y viajaba marcado como
# hipótesis (`inferida: true`, línea punteada, la leyenda lo decía).
#
# Ahora los pedidos vienen abiertos en renglones (`ventas_cliente`), así que el
# puente es una relación REAL (`compra`, con su plata) y la inferencia queda de
# RESPALDO: sólo para el cliente que todavía no tenga pedidos abiertos. Tal cual
# estaba anotado que iba a pasar; nada más del grafo cambió.
AFINIDAD = [
    (("kiosco", "kiosko"), ("golosinas", "bebidas")),
    (("bar", "bufete", "club", "regatas"), ("bebidas", "fiambres", "golosinas")),
    (("rotiser", "comidas", "comedor", "hoster", "hotel", "granja", "fogon"),
     ("congelados", "aceites", "fiambres", "lacteos")),
    (("panader", "trigal"), ("lacteos", "almacen", "aceites")),
    # reventa (super, autoservicio, almacén, despensa, proveeduría): surtido ancho
    (("supermercado", "super", "autoservicio", "almacen", "despensa", "minimercado",
      "mercadito", "proveedur"),
     ("almacen", "lacteos", "bebidas", "limpieza", "golosinas", "fiambres")),
]


def _rubros_afines(nombre_cliente: str, rubros: dict[str, str]) -> list[str]:
    """rubros = {clave_normalizada_del_nombre: id_del_nodo}."""
    n = _norm(nombre_cliente)
    for claves, pistas in AFINIDAD:
        if any(k in n for k in claves):
            return [nid for norm, nid in rubros.items() if any(p in norm for p in pistas)]
    return []


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return "".join(c if c.isalnum() else "_" for c in s.lower()).strip("_")


def _json(ruta: str, default):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


# =============================================================================
# 1 · las entidades
# =============================================================================

def _productos() -> list[dict]:
    return [a for a in store.raw_actual() if (a.get("estado") or "activo") != "anulado"]


def _ventas_agregadas(desde: datetime.date):
    """Una sola pasada por las filas de venta: facturación por producto, por
    rubro y por local, y las canastas diarias para la co-venta.

    Dos ventanas distintas a propósito: la PLATA se agrega a 12 meses (es lo que
    el negocio mira), pero la co-venta usa el historial COMPLETO — que dos
    productos se vendan juntos es una relación estructural del surtido, y un año
    solo deja 841 canastas: muy pocas para que un par pase el umbral de lift."""
    por_producto: dict[int, float] = {}
    unidades: dict[int, float] = {}
    por_local: dict[str, float] = {}
    prod_local: dict[tuple[str, int], float] = {}
    canastas: dict[tuple[str, str], set[int]] = {}

    for f in esquema.filas("venta"):
        cod = f.get("codigo")
        if cod is None:
            continue
        fecha = parse_fecha(f.get("fecha"))
        if not fecha:
            continue
        cod = int(cod)
        boca = (f.get("boca") or "").strip() or "Casa Central"
        canastas.setdefault((f.get("fecha") or "", boca), set()).add(cod)
        if fecha < desde:
            continue
        cant = float(f.get("cantidad") or 0)
        precio = float(f.get("precio") or 0)
        monto = cant * precio if cant and precio else precio
        por_producto[cod] = por_producto.get(cod, 0.0) + monto
        unidades[cod] = unidades.get(cod, 0.0) + cant
        por_local[boca] = por_local.get(boca, 0.0) + monto
        prod_local[(boca, cod)] = prod_local.get((boca, cod), 0.0) + monto

    return {"producto": por_producto, "unidades": unidades, "local": por_local,
            "prod_local": prod_local, "canastas": canastas}


def _coventa(canastas: dict) -> list[tuple[int, int, int, float]]:
    """Pares (a, b, canastas_juntas, lift). Lift = cuánto MÁS aparecen juntos
    de lo que aparecerían si fueran independientes. Solo canastas de tamaño
    razonable: un día con 200 productos no dice nada de ningún par."""
    total = 0
    solo: dict[int, int] = {}
    par: dict[tuple[int, int], int] = {}
    for prods in canastas.values():
        if not 2 <= len(prods) <= 60:
            continue
        total += 1
        orden = sorted(prods)
        for c in orden:
            solo[c] = solo.get(c, 0) + 1
        for a, b in itertools.combinations(orden, 2):
            par[(a, b)] = par.get((a, b), 0) + 1
    if total < 10:
        return []

    salida = []
    for (a, b), n in par.items():
        if n < COVENTA_MIN_CANASTAS:
            continue
        esperado = (solo[a] / total) * (solo[b] / total) * total
        if esperado <= 0:
            continue
        lift = n / esperado
        if lift >= COVENTA_LIFT_MIN:
            salida.append((a, b, n, round(lift, 2)))

    # top-K por producto (mutuo): la unión, no la intersección, para que un
    # producto chico no quede huérfano por competir contra uno grande.
    mejores: dict[int, list] = {}
    for a, b, n, lift in salida:
        mejores.setdefault(a, []).append((lift, n, a, b))
        mejores.setdefault(b, []).append((lift, n, a, b))
    guardar = set()
    for _cod, lista in mejores.items():
        lista.sort(reverse=True)
        for _l, _n, a, b in lista[:COVENTA_TOP]:
            guardar.add((a, b))
    return [(a, b, n, lift) for a, b, n, lift in salida if (a, b) in guardar]


def _proveedores_riesgo() -> dict[str, dict]:
    """Pagos a proveedor vencidos / de la semana — la MISMA fuente que Alertas."""
    fin = _json(FINANZAS_JSON, {}) or {}
    ref = hoy()
    out: dict[str, dict] = {}
    for p in fin.get("pagos_proveedores", []):
        if (p.get("estado") or "") != "pendiente":
            continue
        nombre = p.get("proveedor") or ""
        v = parse_fecha(p.get("vencimiento"))
        d = out.setdefault(_norm(nombre), {"nombre": nombre, "pendiente": 0.0,
                                           "vencido": 0.0, "facturas": 0})
        d["pendiente"] += float(p.get("monto") or 0)
        d["facturas"] += 1
        if v and v < ref:
            d["vencido"] += float(p.get("monto") or 0)
    return out


def _lotes_en_riesgo() -> dict[int, dict]:
    """Vencidos + por vencer, tal cual los devuelve depósito (canónico)."""
    out: dict[int, dict] = {}
    try:
        vencidos = deposito.vencidos()
        proximos = deposito.vencimientos(VENCE_PRONTO_DIAS)
    except Exception:
        return out
    for f in vencidos:
        cod = f.get("codigo")
        if cod is not None:
            out[int(cod)] = {**f, "estado": "vencido"}
    for f in proximos:
        cod = f.get("codigo")
        if cod is not None and int(cod) not in out:
            out[int(cod)] = {**f, "estado": "por_vencer"}
    return out


# =============================================================================
# 2 · el grafo
# =============================================================================

def _nodo(nid, tipo, nombre, **extra) -> dict:
    return {"id": nid, "tipo": tipo, "nombre": nombre, "peso": 0.0,
            "riesgo": None, "metricas": [], **extra}


def construir() -> dict:
    """Nodos + aristas. Sin idioma: son entidades y relaciones, no textos."""
    ref = hoy()
    desde = ref - datetime.timedelta(days=365 * VENTANA_MESES // 12)

    arts = _productos()
    agg = _ventas_agregadas(desde)
    fact = agg["producto"]
    lotes = _lotes_en_riesgo()
    prov_riesgo = _proveedores_riesgo()

    nodos: dict[str, dict] = {}
    aristas: list[dict] = []
    grado: dict[str, int] = {}

    def add_arista(s, t, rel, **extra):
        if s not in nodos or t not in nodos or s == t:
            return
        aristas.append({"source": s, "target": t, "rel": rel, **extra})
        grado[s] = grado.get(s, 0) + 1
        grado[t] = grado.get(t, 0) + 1

    # --- productos, rubros, proveedores ---------------------------------------
    por_codigo: dict[int, str] = {}
    for a in arts:
        cod = int(a["codigo"])
        nid = f"prod:{cod}"
        por_codigo[cod] = nid
        f12 = fact.get(cod, 0.0)
        inmov = float(a.get("inmovilizado") or 0)
        lote = lotes.get(cod)
        riesgo = "riesgo" if (lote and lote["estado"] == "vencido") else \
                 "atencion" if lote else \
                 "atencion" if (inmov > 0 and f12 == 0) else "ok"
        nodos[nid] = _nodo(nid, "producto", a.get("descripcion") or f"#{cod}",
                           codigo=cod, riesgo=riesgo, peso=f12,
                           seccion="inventario",
                           metricas=[
                               {"k": "facturado12m", "v": round(f12, 2), "fmt": "pesos"},
                               {"k": "stock", "v": a.get("stock") or 0, "fmt": "num"},
                               {"k": "inmovilizado", "v": round(inmov, 2), "fmt": "pesos"},
                               {"k": "pvp", "v": a.get("pvp"), "fmt": "pesos"},
                           ],
                           **({"vence": lote.get("vencimiento"),
                               "lote": lote.get("lote"),
                               "ubicacion": lote.get("ubicacion")} if lote else {}))

        rubro = (a.get("tipo") or "").strip()
        if rubro:
            rid = f"rubro:{_norm(rubro)}"
            if rid not in nodos:
                nodos[rid] = _nodo(rid, "rubro", rubro, seccion="evolucion")
            nodos[rid]["peso"] += f12
            add_arista(nid, rid, "pertenece")

        prov = (a.get("proveedor") or "").strip()
        if prov:
            pid = f"prov:{_norm(prov)}"
            if pid not in nodos:
                r = prov_riesgo.get(_norm(prov)) or {}
                nodos[pid] = _nodo(
                    pid, "proveedor", prov, seccion="finanzas",
                    riesgo="riesgo" if r.get("vencido") else "atencion" if r.get("pendiente") else "ok",
                    metricas=[{"k": "a_pagar", "v": round(r.get("pendiente", 0), 2), "fmt": "pesos"},
                              {"k": "vencido", "v": round(r.get("vencido", 0), 2), "fmt": "pesos"}])
            nodos[pid]["peso"] += f12
            add_arista(pid, nid, "provee")

    # --- locales propios (la boca donde se vendió) -----------------------------
    for boca, monto in agg["local"].items():
        lid = f"local:{_norm(boca)}"
        nodos[lid] = _nodo(lid, "local", boca, peso=monto, seccion="caja",
                           metricas=[{"k": "facturado12m", "v": round(monto, 2), "fmt": "pesos"}])
    # solo los productos que ese local realmente mueve: el resto satura el centro
    por_local: dict[str, list] = {}
    for (boca, cod), monto in agg["prod_local"].items():
        por_local.setdefault(boca, []).append((monto, cod))
    for boca, lista in por_local.items():
        lista.sort(reverse=True)
        for monto, cod in lista[:LOCAL_TOP]:
            add_arista(f"local:{_norm(boca)}", por_codigo.get(cod, ""), "vende",
                       monto=round(monto, 2))

    # --- co-venta: la relación que hace el núcleo denso ------------------------
    pares = _coventa(agg["canastas"])
    for a, b, n, lift in pares:
        add_arista(por_codigo.get(a, ""), por_codigo.get(b, ""), "coventa",
                   canastas=n, lift=lift)

    # --- clientes y cuentas corrientes ----------------------------------------
    try:
        clientes = cuentas.listar()
    except Exception:
        clientes = []
    for c in clientes:
        cid = f"cli:{c['id']}"
        saldo = float(c.get("saldo") or 0)
        nodos[cid] = _nodo(
            cid, "cliente", c.get("nombre") or c["id"], peso=saldo, seccion="cuentas",
            riesgo={"riesgoso": "riesgo", "atencion": "atencion"}.get(c.get("score"), "ok"),
            metricas=[{"k": "saldo", "v": round(saldo, 2), "fmt": "pesos"},
                      {"k": "dias_sin_pagar", "v": c.get("dias_sin_pagar"), "fmt": "dias"},
                      {"k": "plazo", "v": c.get("plazo_dias"), "fmt": "dias"},
                      {"k": "disponible", "v": round(c.get("disponible") or 0, 2), "fmt": "pesos"}])
        if saldo > 0:
            ctaid = f"cuenta:{c['id']}"
            nodos[ctaid] = _nodo(
                ctaid, "cuenta", c.get("nombre") or c["id"], peso=saldo, seccion="cuentas",
                riesgo="riesgo" if c.get("en_mora") and c.get("score") == "riesgoso"
                       else "atencion" if c.get("en_mora") else "ok",
                metricas=[{"k": "saldo", "v": round(saldo, 2), "fmt": "pesos"},
                          {"k": "limite", "v": c.get("limite_credito"), "fmt": "pesos"},
                          {"k": "atraso_vs_promedio", "v": c.get("atraso_vs_promedio"), "fmt": "pct"}])
            add_arista(cid, ctaid, "debe", monto=round(saldo, 2))

    # --- QUÉ SE LLEVA CADA CLIENTE: el puente que antes se infería ------------
    # Cada arista `compra` es un renglón real de sus pedidos, con la plata que
    # movió. Es la relación que vuelve cruzables cuentas y depósito: sin ella,
    # "el que te debe se lleva justo lo que se vence" no se puede ni dibujar.
    rubros_idx = {_norm(n["nombre"]): nid for nid, n in nodos.items() if n["tipo"] == "rubro"}
    con_compras: set[str] = set()
    try:
        from . import ventas_cliente
        for reg in ventas_cliente.por_cliente().values():
            cid = f"cli:{reg['cliente_id']}"
            if cid not in nodos:
                continue
            top = ventas_cliente.compras_de(reg["cliente_id"], top=CLIENTE_TOP_PRODUCTOS)
            if not top:
                continue
            con_compras.add(cid)
            for x in top:
                add_arista(cid, por_codigo.get(int(x["codigo"]), ""), "compra",
                           monto=x["monto"], share=x["share"])
    except Exception:  # noqa: BLE001 — sin el archivo, queda la inferencia de abajo
        pass
    # respaldo: el cliente que todavía no tiene pedidos abiertos no queda aislado
    for nid, n in list(nodos.items()):
        if n["tipo"] != "cliente" or nid in con_compras:
            continue
        for rid in _rubros_afines(n["nombre"], rubros_idx):
            add_arista(nid, rid, "afinidad", inferida=True)

    por_cliente_nombre = {_norm(n["nombre"]): nid for nid, n in nodos.items()
                          if n["tipo"] == "cliente"}

    # --- remitos / pedidos en la calle ----------------------------------------
    for f in esquema.filas("logistica"):
        ped = (f.get("pedido") or "").strip()
        if not ped:
            continue
        rid = f"remito:{_norm(ped)}"
        estado = (f.get("estado") or "").strip()
        nodos[rid] = _nodo(rid, "remito", ped, seccion="logistica",
                           riesgo="atencion" if estado == "pendiente" else "ok",
                           metricas=[{"k": "estado", "v": estado, "fmt": "texto"},
                                     {"k": "fecha_prevista", "v": f.get("fecha_prevista"), "fmt": "fecha"},
                                     {"k": "transporte", "v": f.get("transporte"), "fmt": "texto"}])
        cli = por_cliente_nombre.get(_norm(f.get("cliente")))
        if cli:
            add_arista(rid, cli, "entrega")

    # --- órdenes de compra: proveedor ↔ productos pedidos ----------------------
    for f in esquema.filas("ordenes_compra"):
        num = (f.get("numero") or "").strip()
        if not num:
            continue
        oid = f"remito:{_norm(num)}"
        nodos[oid] = _nodo(oid, "remito", num, seccion="documentos",
                           riesgo="atencion" if (f.get("estado") or "") == "abierta" else "ok",
                           metricas=[{"k": "estado", "v": f.get("estado"), "fmt": "texto"},
                                     {"k": "fecha", "v": f.get("fecha"), "fmt": "fecha"}])
        prov = _norm(f.get("proveedor"))
        if prov and f"prov:{prov}" in nodos:
            add_arista(f"prov:{prov}", oid, "ordena")
        for it in (f.get("items") or []):
            cod = it.get("codigo")
            if cod is not None and por_codigo.get(int(cod)):
                add_arista(oid, por_codigo[int(cod)], "pide",
                           cantidad=it.get("cantidad"))

    # --- recepciones: el proveedor que DE VERDAD entregó ese producto ----------
    recep: dict[tuple[str, int], float] = {}
    for f in esquema.filas("recepciones"):
        cod, prov = f.get("codigo"), _norm(f.get("proveedor"))
        if cod is None or not prov:
            continue
        recep[(prov, int(cod))] = recep.get((prov, int(cod)), 0.0) + float(f.get("cantidad") or 0)
    vistos = {(a["source"], a["target"]) for a in aristas}
    for (prov, cod), cant in recep.items():
        s, t = f"prov:{prov}", por_codigo.get(cod, "")
        if s in nodos and t and (s, t) not in vistos:
            add_arista(s, t, "provee", recibido=cant)

    # --- traslados a locales propios ------------------------------------------
    tras = _json(TRASLADOS_JSON, {}) or {}
    mov: dict[tuple[str, int], float] = {}
    for f in tras.get("filas", []):
        cod, dest = f.get("codigo"), (f.get("destino") or "").strip()
        if cod is None or not dest:
            continue
        mov[(dest, int(cod))] = mov.get((dest, int(cod)), 0.0) + \
            float(f.get("cantidad") or 0) * float(f.get("precio") or 0)
    for dest in {d for d, _ in mov}:
        lid = f"local:{_norm(dest)}"
        if lid not in nodos:
            nodos[lid] = _nodo(lid, "local", dest, seccion="inventario")
    top_mov = sorted(mov.items(), key=lambda kv: -kv[1])[:LOCAL_TOP * 2]
    vistos = {(a["source"], a["target"]) for a in aristas}
    for (dest, cod), monto in top_mov:
        s, t = f"local:{_norm(dest)}", por_codigo.get(cod, "")
        if t and (s, t) not in vistos and (t, s) not in vistos:
            add_arista(s, t, "traslado", monto=round(monto, 2))

    # --- LO NO ESTRUCTURADO: lo que el equipo le contó a Ángela ---------------
    # Un tipo de entidad nuevo, y el único que no sale de una tabla: son notas
    # de personas (voz del piso, reportes, chat). Cuelgan de la entidad que
    # nombran, así que un camino puede ir de un cliente a lo que el repartidor
    # vio en la calle. Data sintética del demo, como el resto — NO es un canal
    # externo conectado (ver core/notas.py).
    try:
        from . import notas as _notas
        idx_prod = {_norm(n["nombre"]): nid for nid, n in nodos.items()
                    if n["tipo"] == "producto"}
        for nt in _notas.listar():
            nid = f"nota:{nt['id']}"
            nodos[nid] = _nodo(
                nid, "nota", f"{nt['autor']} · {nt['fecha'][5:]}", seccion="equipo",
                riesgo="atencion",
                texto=nt.get("texto"), texto_en=nt.get("texto_en"),
                metricas=[{"k": "autor", "v": nt.get("autor"), "fmt": "texto"},
                          {"k": "canal", "v": nt.get("canal"), "fmt": "texto"},
                          {"k": "fecha", "v": nt.get("fecha"), "fmt": "fecha"},
                          {"k": "tema", "v": nt.get("tipo"), "fmt": "texto"}])
            for campo, idx, tipos in (("cliente", por_cliente_nombre, ("cliente",)),
                                      ("producto", idx_prod, ("producto",)),
                                      ("proveedor", None, ("proveedor",))):
                valor = nt.get(campo)
                if not valor:
                    continue
                destino = (idx.get(_norm(valor)) if idx is not None
                           else _resolver(valor, nodos, tipos))
                if destino is None and idx is not None:
                    destino = _resolver(valor, nodos, tipos)
                if destino:
                    add_arista(nid, destino, "menciona")
    except Exception:  # noqa: BLE001 — sin notas, el grafo es el de siempre
        pass

    # --- lo que el dueño le enseñó a Ángela, pegado a su entidad ---------------
    try:
        from . import conocimiento
        for p in conocimiento.listar():
            ent = (p.get("entidad") or "").strip()
            if not ent:
                continue
            objetivo = next((nid for nid, n in nodos.items()
                             if n["tipo"] in ("producto", "cliente", "proveedor")
                             and _norm(ent) in _norm(n["nombre"])), None)
            if objetivo:
                nodos[objetivo].setdefault("conocimiento", []).append(p.get("id"))
    except Exception:
        pass

    for nid, n in nodos.items():
        n["grado"] = grado.get(nid, 0)

    return {"nodos": list(nodos.values()), "aristas": aristas,
            "_indice": nodos, "_por_codigo": por_codigo}


# =============================================================================
# 3 · el camino de un hallazgo: qué se cruzó para que Ángela lo viera
# =============================================================================

_SEMILLA_CAMPOS = ("producto", "cliente", "proveedor")


def _resolver(nombre: str, indice: dict, tipos: tuple) -> str | None:
    if not nombre:
        return None
    n = _norm(nombre)
    exacto = next((nid for nid, x in indice.items()
                   if x["tipo"] in tipos and _norm(x["nombre"]) == n), None)
    if exacto:
        return exacto
    return next((nid for nid, x in indice.items()
                 if x["tipo"] in tipos and (n in _norm(x["nombre"]) or _norm(x["nombre"]) in n)), None)


def caminos(g: dict, cards: list[dict]) -> list[dict]:
    """Para cada hallazgo real de Oportunidades: los nodos y aristas que lo
    produjeron. Determinista — sale de resolver las entidades que la card ya
    nombra y de expandir UN salto por las relaciones que existen."""
    indice = g["_indice"]
    vecinos: dict[str, list] = {}
    for a in g["aristas"]:
        vecinos.setdefault(a["source"], []).append(a)
        vecinos.setdefault(a["target"], []).append(a)

    salida = []
    for card in cards or []:
        datos = card.get("datos") or {}
        semillas: list[str] = []

        for campo in _SEMILLA_CAMPOS:
            v = datos.get(campo)
            if isinstance(v, str):
                nid = _resolver(v, indice, ("producto", "cliente", "proveedor"))
                if nid:
                    semillas.append(nid)
        for campo in ("clientes", "productos"):
            # ojo: `productos` a veces es un CONTEO (ventana_compra: 27), no una lista
            valores = datos.get(campo)
            for v in (valores if isinstance(valores, list) else []):
                if isinstance(v, str):
                    nid = _resolver(v, indice, ("producto", "cliente", "proveedor"))
                    if nid:
                        semillas.append(nid)
        for inv in (card.get("drill") or {}).get("involucrados", []) or []:
            nid = _resolver(inv.get("nombre"), indice, ("producto", "cliente", "proveedor"))
            if nid:
                semillas.append(nid)
        # Las notas del equipo que dispararon el hallazgo son SEMILLA, no vecinas:
        # si entraran sólo por expansión, un proveedor con 70 productos las tapa
        # (la expansión corta a 14 vecinos) y justo se perdería la parte que
        # prueba que el cruce tocó lo no estructurado.
        for nt in (datos.get("notas") or []):
            nid = f"nota:{nt.get('id')}" if isinstance(nt, dict) else f"nota:{nt}"
            if nid in indice:
                semillas.append(nid)

        semillas = list(dict.fromkeys(semillas))
        if not semillas:
            continue

        conjunto = set(semillas)
        for nid in semillas:
            # un salto: con quién se cruza esta entidad. Los locales quedan
            # afuera salvo que la semilla sea el propio local (son hubs de todo
            # y meterlos arrastra medio grafo al camino).
            for a in vecinos.get(nid, [])[:14]:
                otro = a["target"] if a["source"] == nid else a["source"]
                if indice[otro]["tipo"] == "local" and len(semillas) > 2:
                    continue
                conjunto.add(otro)
            if indice[nid]["tipo"] == "cliente":
                cta = nid.replace("cli:", "cuenta:")
                if cta in indice:
                    conjunto.add(cta)

        ids_aristas = [i for i, a in enumerate(g["aristas"])
                       if a["source"] in conjunto and a["target"] in conjunto]
        salida.append({
            "id": card.get("id"),
            "titulo": card.get("titulo"),
            "tipo": card.get("tipo"),
            "naturaleza": card.get("naturaleza"),
            "monto": (card.get("impacto") or {}).get("monto") if isinstance(card.get("impacto"), dict) else None,
            "semillas": semillas,
            "nodos": sorted(conjunto),
            "aristas": ids_aristas,
        })
    return salida


# =============================================================================
# 4 · la respuesta del endpoint
# =============================================================================

# Los hallazgos de Oportunidades que YA cruzan varias fuentes y por eso siguen
# entrando al cerebro. El resto de esa sección son ALERTAS de una sola fuente
# ("te quedan 7 días de gaseosa", "vendés esto al 1,7%"): valen como aviso y
# siguen en Oportunidades intactas, pero no son un cruce y acá ensuciaban la
# idea. El cerebro muestra cruces; la caja de plata sigue donde estaba.
CARDS_QUE_CRUZAN = {
    # el cliente que se enfría: su propio histórico × el ranking × el calendario
    "cliente_frio": ["clientes", "ventas", "tiempo"],
    # la ventana de compra: la lista del proveedor × lo que rota × el stock
    "ventana_compra": ["proveedores", "inventario", "precios"],
}


def completo(lang: str | None = None) -> dict:
    g = construir()
    # 1 · los cruces propios (3+ dominios, ver core/cruces.py)
    try:
        from . import cruces as _cruces
        hallazgos = _cruces.cards(lang)
    except Exception:  # noqa: BLE001
        hallazgos = []
    # 2 · los de Oportunidades que también cruzan de verdad
    try:
        from . import oportunidades_neg
        cards = oportunidades_neg.cards(lang)
        if isinstance(cards, dict):     # el shape {"cards": [...]} es el del endpoint
            cards = cards.get("cards") or []
        hallazgos += [c for c in cards if c.get("id") in CARDS_QUE_CRUZAN]
    except Exception:  # noqa: BLE001
        pass

    cam = caminos(g, hallazgos)
    # cada camino declara los dominios que cruzó — es lo que lo hace auditable
    por_id = {c.get("id"): c for c in hallazgos}
    for c in cam:
        origen = por_id.get(c["id"]) or {}
        c["dominios"] = origen.get("dominios") or CARDS_QUE_CRUZAN.get(c["id"]) or []
        c["cruce"] = bool(origen.get("cruce"))
        c["no_estructurado"] = bool(origen.get("no_estructurado"))
        c["resumen"] = origen.get("resumen")
        c["porque"] = (origen.get("drill") or {}).get("porque") or []
        c["accion_chat"] = origen.get("accion_chat")
        # los TIPOS de entidad que toca el camino: la prueba visual de que el
        # hallazgo salió de cruzar cosas que no se hablan entre sí
        c["tipos"] = sorted({g["_indice"][n]["tipo"] for n in c["nodos"]
                             if n in g["_indice"]})
    nodos, aristas = g["nodos"], g["aristas"]
    por_tipo: dict[str, int] = {}
    for n in nodos:
        por_tipo[n["tipo"]] = por_tipo.get(n["tipo"], 0) + 1
    por_rel: dict[str, int] = {}
    for a in aristas:
        por_rel[a["rel"]] = por_rel.get(a["rel"], 0) + 1

    grados = sorted(nodos, key=lambda n: -n.get("grado", 0))[:8]
    return {
        "disponible": len(nodos) > 0,
        "nodos": nodos,
        "aristas": aristas,
        "caminos": cam,
        "meta": {
            "generado": hoy().isoformat(),
            "nodos": len(nodos),
            "aristas": len(aristas),
            "por_tipo": por_tipo,
            "por_relacion": por_rel,
            "nucleo": [{"id": n["id"], "nombre": n["nombre"], "tipo": n["tipo"],
                        "grado": n.get("grado", 0)} for n in grados],
            # honestidad sobre qué es dato crudo y qué está calculado acá
            "derivados": {
                "coventa": {
                    "que": "producto ↔ producto",
                    "como": f"lift ≥ {COVENTA_LIFT_MIN} sobre canastas diarias (fecha × boca), "
                            f"mínimo {COVENTA_MIN_CANASTAS} canastas, top {COVENTA_TOP} por producto",
                    "pares": por_rel.get("coventa", 0),
                },
                "peso": "volumen agregado por entidad (12 meses) — define el tamaño del punto, "
                        "no es un número de negocio",
                "compra": {
                    "que": "cliente ↔ producto",
                    "como": "DATO: los renglones de cada pedido de la cuenta corriente "
                            f"(top {CLIENTE_TOP_PRODUCTOS} por cliente). El total de cada "
                            "pedido es el monto del movimiento, sin tocar",
                    "aristas": por_rel.get("compra", 0),
                    "inferida": False,
                },
                "afinidad": {
                    "que": "cliente ↔ rubro",
                    "como": "RESPALDO inferido del rubro del cliente, sólo para quien todavía "
                            "no tiene pedidos abiertos en renglones",
                    "aristas": por_rel.get("afinidad", 0),
                    "inferida": True,
                },
                "menciona": {
                    "que": "nota del equipo ↔ entidad",
                    "como": "la nota DECLARA a qué se refiere (el reporte del piso ya pide "
                            "producto y motivo): no se adivina con NLP",
                    "aristas": por_rel.get("menciona", 0),
                    "inferida": False,
                },
            },
            "recortes": {
                "local_top": LOCAL_TOP,
                "nota": f"cada local cuelga sus {LOCAL_TOP} productos de mayor facturación; "
                        "el resto existe como nodo pero no cuelga del local",
            },
        },
    }

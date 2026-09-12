"""
ventas_cliente.py — QUÉ SE LLEVA CADA CLIENTE.

El dato que faltaba. La cuenta corriente decía "Pedido mayorista $42.000.000" y
nada más: el renglón nunca contaba QUÉ se llevó. Con eso, media docena de cruces
no se podían ni plantear —"el que más te debe se lleva justo lo que se te está
por vencer"— y el grafo tenía que INFERIR el puente cliente↔rubro.

Acá se lee `ventas_por_cliente.json` (lo abre data-demo/generar.py a partir de
los MISMOS movimientos de la cuenta corriente: el total de cada pedido es el
monto del movimiento, intacto). Lectura pura: este módulo no calcula plata nueva
ni toca un canónico — agrega lo que ya está escrito.

El piloto todavía no tiene el archivo (sus facturas de venta por cliente no
están cargadas): sin archivo, `hay_datos()` es False y todo lo que depende de
esto se apaga solo, sin fingir.
"""
from __future__ import annotations

import json
import os
import unicodedata

from . import paths

VENTAS_CLIENTE_JSON = os.path.join(paths.DATA_DIR, "ventas_por_cliente.json")


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def _seed_inicial() -> dict:
    if not os.path.exists(VENTAS_CLIENTE_JSON):
        return {}
    try:
        with open(VENTAS_CLIENTE_JSON, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:  # noqa: BLE001 — sin archivo, el módulo se calla
        return {}


def _load() -> dict:
    from core.db import blob_repo
    from core.db import tenant as _tenant
    tid = _tenant.current_tenant_id()
    data = blob_repo.get_blob("client_sales_data", tid)
    if data is None:
        data = _seed_inicial()
        blob_repo.save_blob("client_sales_data", tid, data)
    return data


def hay_datos() -> bool:
    return bool(_load().get("clientes"))


def por_cliente() -> dict[str, dict]:
    """{cliente_id: registro}. El registro trae nombre, rubros y pedidos."""
    return {c["cliente_id"]: c for c in _load().get("clientes", [])}


def de(cliente_id: str) -> dict | None:
    return por_cliente().get(cliente_id)


def all_orders() -> list[dict]:
    """Every order from every customer, with `cliente_id`/`cliente` attached
    — the full basket, for cross-referencing which products travel together
    in the SAME order (core/patrones.py)."""
    return [{**p, "cliente_id": c["cliente_id"], "cliente": c["nombre"]}
            for c in _load().get("clientes", []) for p in c.get("pedidos", [])]


def _agregar(pedidos: list[dict]) -> tuple[dict, float]:
    """(por producto: {codigo: {...}}, total facturado)."""
    acc: dict[int, dict] = {}
    total = 0.0
    for p in pedidos:
        for it in p.get("items", []):
            cod = it.get("codigo")
            if cod is None:
                continue
            g = acc.setdefault(int(cod), {
                "codigo": int(cod), "producto": it.get("producto"),
                "categoria": it.get("categoria"), "monto": 0.0,
                "cantidad": 0.0, "pedidos": 0, "ultima": None})
            g["monto"] += float(it.get("monto") or 0)
            g["cantidad"] += float(it.get("cantidad") or 0)
            g["pedidos"] += 1
            f = p.get("fecha")
            if f and (g["ultima"] is None or f > g["ultima"]):
                g["ultima"] = f
            total += float(it.get("monto") or 0)
    return acc, total


def compras_de(cliente_id: str, top: int | None = 8,
               desde: str | None = None) -> list[dict]:
    """Lo que ESTE cliente se lleva, ordenado por plata. `desde` (YYYY-MM-DD)
    acota la ventana; sin él, toda su historia. `top=None` devuelve todo. Cada
    ítem trae `share`: qué parte de SU facturación explica ese producto."""
    reg = de(cliente_id)
    if not reg:
        return []
    pedidos = [p for p in reg.get("pedidos", [])
               if not desde or (p.get("fecha") or "") >= desde]
    acc, total = _agregar(pedidos)
    ordenados = sorted(acc.values(), key=lambda x: -x["monto"])
    salida = ordenados if top is None else ordenados[:top]
    for x in salida:
        x["monto"] = round(x["monto"], 2)
        x["cantidad"] = round(x["cantidad"], 2)
        x["share"] = round(x["monto"] / total, 4) if total else 0.0
    return salida


def compradores_de(codigo: int, desde: str | None = None) -> list[dict]:
    """Al revés: quiénes compran ESTE producto, ordenados por plata. Es la
    mitad que faltaba para cruzar un producto con la cuenta de quien se lo lleva."""
    out = []
    for c in _load().get("clientes", []):
        monto = cantidad = 0.0
        ultima = None
        for p in c.get("pedidos", []):
            if desde and (p.get("fecha") or "") < desde:
                continue
            for it in p.get("items", []):
                if int(it.get("codigo") or -1) != int(codigo):
                    continue
                monto += float(it.get("monto") or 0)
                cantidad += float(it.get("cantidad") or 0)
                f = p.get("fecha")
                if f and (ultima is None or f > ultima):
                    ultima = f
        if monto > 0:
            out.append({"cliente_id": c["cliente_id"], "nombre": c["nombre"],
                        "monto": round(monto, 2), "cantidad": round(cantidad, 2),
                        "ultima": ultima})
    return sorted(out, key=lambda x: -x["monto"])


def buscar_producto(texto: str) -> list[int]:
    """Códigos cuyo nombre matchea (para cruzar por nombre, no por código)."""
    t = _norm(texto)
    if not t:
        return []
    vistos: dict[int, None] = {}
    for c in _load().get("clientes", []):
        for p in c.get("pedidos", []):
            for it in p.get("items", []):
                if t in _norm(it.get("producto")):
                    vistos[int(it["codigo"])] = None
    return list(vistos)


def resumen() -> dict:
    d = _load()
    clientes = d.get("clientes", [])
    pedidos = sum(len(c.get("pedidos", [])) for c in clientes)
    renglones = sum(len(p.get("items", [])) for c in clientes for p in c.get("pedidos", []))
    return {"hay_datos": bool(clientes), "clientes": len(clientes),
            "pedidos": pedidos, "renglones": renglones}

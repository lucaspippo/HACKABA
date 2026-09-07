"""Deterministic generator for odoo_muestra.json — the Odoo connector's
sample transport (core/odoo_demo.py, core/conectores.ConectorOdooDemo).

Same philosophy as data-demo/comprobantes/generar_comprobantes.py: the sample
and the dataset cannot diverge because the sample is DERIVED from the dataset
in this very script. Products, suppliers and customers are the Litoral
catalog's own rows — linked products carry values identical to the catalog,
so the first sync is a pure provenance stamp; only a handful of rows are
genuinely new, to exercise the staging/review flow.

Shapes mirror conectores.ConectorOdoo.pull_* outputs exactly (the coercers in
core/staging.py are the contract). Run from this directory:

    python generar_odoo_muestra.py

No backend imports, no database: plain JSON in, plain JSON out, stable ids.
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(HERE, "odoo_muestra.json")

# The dataset's frozen "today" (see generar.py / POLPILOT_DEMO_TODAY). Sample
# dates hang off it so the synced rows read as recent activity.
HOY = "2026-07-07"

# Stable id ranges. Odoo ids are per-model, so overlap across models would
# be harmless — they are kept disjoint anyway so a demo source_id can be told
# apart at a glance in audits and tests (product tmpl ids reach ~8500).
TMPL_BASE = 7000          # product.template id = TMPL_BASE + codigo
PARTNER_BASE = 9100       # res.partner ids for suppliers
OC_IDS = (9701, 9702)     # purchase.order ids
SO_BASE = 9200            # sale.order ids
LINEA_BASE = 9300         # sale.order.line ids
MOVE_BASE = 9500          # stock.move ids

PRODUCTOS_VINCULADOS = 24  # top of the catalog by tied-up money
VENTA_ORDENES = 6          # confirmed sale orders in the sample


def _leer(nombre: str):
    with open(os.path.join(HERE, nombre), encoding="utf-8") as fh:
        return json.load(fh)


def _pull_producto(a: dict, incoming: float = 0.0) -> dict:
    """One product.template row, values byte-equal to the catalog row so the
    linked sync is a no-op update (plus provenance)."""
    return {
        "id": TMPL_BASE + int(a["codigo"]),
        "codigo": f"LIT-{a['codigo']}",
        "nombre": a.get("descripcion") or "",
        "categoria": a.get("categoria") or "",
        "precio": a.get("pvp"),
        "precio_lista": a.get("pvp"),
        "pricing_status": "ok" if a.get("pvp") else "needs_pricing",
        "precios_pricelist": [],
        "moneda": "ARS",
        "stock": a.get("stock") or 0,
        "costo": a.get("costo_iva") or 0,
        "free_qty": a.get("stock") or 0,
        "incoming_qty": incoming,
        "outgoing_qty": 0.0,
        "activo": True,
    }


def main() -> None:
    inventario = _leer("inventory.json")["articulos"]
    apartados = _leer("apartados.json")

    activos = [a for a in inventario
               if (a.get("estado") or "activo") == "activo"
               and (a.get("stock") or 0) > 0 and a.get("pvp") and a.get("costo_iva")]
    activos.sort(key=lambda a: -((a.get("stock") or 0) * (a.get("costo_iva") or 0)))
    vinculados = activos[:PRODUCTOS_VINCULADOS]
    por_codigo = {a["codigo"]: a for a in vinculados}

    # --- suppliers: the ones the dataset already receives from -------------
    recep = apartados["recepciones"]["filas"]
    conteo: dict[str, int] = {}
    for f in recep:
        p = f.get("proveedor")
        if p:
            conteo[p] = conteo.get(p, 0) + 1
    proveedores_nombres = [p for p, _ in
                          sorted(conteo.items(), key=lambda kv: (-kv[1], kv[0]))]
    proveedores = [
        {
            "id": PARTNER_BASE + i,
            "nombre": nombre,
            "cuit": f"30-9{i:02d}44556-{(i * 3) % 10}",
            "localidad": "Rosario",
            "telefono": f"341-49{i:02d}-2200",
            "email": ("compras@"
                      + "".join(c for c in nombre.lower() if c.isalnum())[:18]
                      + ".com.ar"),
        }
        for i, nombre in enumerate(proveedores_nombres, start=1)
    ]
    partner_de = {p["nombre"]: p["id"] for p in proveedores}

    # --- two open purchase orders against linked products ------------------
    def item_oc(codigo: int, cantidad: int, recibido: int) -> dict:
        a = por_codigo[codigo]
        return {
            "producto": a.get("descripcion") or "",
            "product_tmpl_id": TMPL_BASE + codigo,
            "cantidad": cantidad,
            "precio_unitario": a.get("costo_iva") or 0,
            "qty_received": recibido,
        }

    codigos = [a["codigo"] for a in vinculados]
    oc1_items = [item_oc(codigos[0], 60, 36), item_oc(codigos[2], 40, 40),
                 item_oc(codigos[4], 80, 0)]
    oc2_items = [item_oc(codigos[1], 50, 0), item_oc(codigos[3], 30, 0)]
    prov_oc1 = proveedores_nombres[0]
    prov_oc2 = proveedores_nombres[1]

    def orden(idx, numero, proveedor, items, fecha, open_backorder):
        total = round(sum(i["cantidad"] * i["precio_unitario"] for i in items), 2)
        return {
            "id": idx, "numero": numero, "proveedor": proveedor,
            "estado": "confirmada", "fecha": fecha,
            "total": total, "currency": "ARS", "total_company": total,
            "open_backorder": open_backorder,
            "items": items,
        }

    ordenes_compra = [
        orden(OC_IDS[0], "P00091", prov_oc1, oc1_items, "2026-06-28", True),
        orden(OC_IDS[1], "P00092", prov_oc2, oc2_items, "2026-07-03", False),
    ]

    # --- confirmed sale orders for real customers --------------------------
    cuentas = _leer("cuentas.json")
    clientes_nombres = [c["nombre"] for c in cuentas[:VENTA_ORDENES]]
    ordenes_venta = []
    linea_id = LINEA_BASE
    for i, cliente in enumerate(clientes_nombres):
        fecha = f"2026-07-{(i % 6) + 1:02d}"
        items = []
        for j in range(2 + (i % 3)):
            a = vinculados[(i * 5 + j * 7) % len(vinculados)]
            cantidad = 6 + ((i * 4 + j * 9) % 30)
            items.append({
                "id": linea_id,
                "producto": a.get("descripcion") or "",
                "product_tmpl_id": TMPL_BASE + a["codigo"],
                "cantidad": cantidad,
                "qty_delivered": cantidad,
                "precio_unitario": a.get("pvp") or 0,
                "precio_company": a.get("pvp") or 0,
            })
            linea_id += 1
        total = round(sum(x["cantidad"] * x["precio_unitario"] for x in items), 2)
        ordenes_venta.append({
            "id": SO_BASE + i, "numero": f"S002{40 + i}",
            "cliente": cliente, "estado": "confirmada", "fecha": fecha,
            "total": total, "currency": "ARS", "total_company": total,
            "pricelist": "Mayorista ARS", "open_backorder": False,
            "fulfillment": "complete",
            "items": items,
        })

    # --- receipts for P00091: done moves plus the open backorder remainder --
    recepciones = []
    move_id = MOVE_BASE
    for it in oc1_items:
        if it["qty_received"]:
            recepciones.append({
                "id": move_id, "picking_id": 501, "fecha": "2026-07-02",
                "producto": it["producto"],
                "product_tmpl_id": it["product_tmpl_id"],
                "partner": prov_oc1, "proveedor": prov_oc1,
                "cantidad": it["qty_received"], "qty_ordered": it["cantidad"],
                "deposito": "Depósito Central", "origen": "WH/IN/00091",
                "po_number": "P00091", "so_number": "",
                "estado": "done", "backorder_id": None, "es_backorder": False,
                "pendiente": False, "open_backorder": False,
            })
            move_id += 1
    for it in oc1_items:
        resto = it["cantidad"] - it["qty_received"]
        if resto > 0:
            recepciones.append({
                "id": move_id, "picking_id": 502, "fecha": "2026-07-09",
                "producto": it["producto"],
                "product_tmpl_id": it["product_tmpl_id"],
                "partner": prov_oc1, "proveedor": prov_oc1,
                "cantidad": 0, "qty_ordered": resto,
                "deposito": "Depósito Central", "origen": "WH/IN/00091",
                "po_number": "P00091", "so_number": "",
                "estado": "assigned", "backorder_id": 501, "es_backorder": True,
                "pendiente": True, "open_backorder": True,
            })
            move_id += 1

    # incoming per product, from the open order lines
    incoming: dict[int, float] = {}
    for o in ordenes_compra:
        for it in o["items"]:
            resto = it["cantidad"] - it["qty_received"]
            if resto > 0:
                incoming[it["product_tmpl_id"]] = (
                    incoming.get(it["product_tmpl_id"], 0) + resto)

    productos = [_pull_producto(a, incoming.get(TMPL_BASE + a["codigo"], 0.0))
                 for a in vinculados]
    # Two genuinely NEW products: they exercise the staging/review flow.
    # Names checked disjoint from the catalog below.
    nuevos = [
        {
            "id": 7901, "codigo": "LIT-N1",
            "nombre": "ACEITE DE OLIVA COSTA DULCE 500ML (X12U)",
            "categoria": "aceites y aderezos",
            "precio": 8900.0, "precio_lista": 8900.0, "pricing_status": "ok",
            "precios_pricelist": [], "moneda": "ARS",
            "stock": 0, "costo": 6300.0, "free_qty": 0,
            "incoming_qty": 0.0, "outgoing_qty": 0.0, "activo": True,
        },
        {
            "id": 7902, "codigo": "LIT-N2",
            "nombre": "GALLETITAS DE ARROZ LA RIBERA 150G (X30U)",
            "categoria": "galletitas y golosinas",
            "precio": 1450.0, "precio_lista": 1450.0, "pricing_status": "ok",
            "precios_pricelist": [], "moneda": "ARS",
            "stock": 0, "costo": 980.0, "free_qty": 0,
            "incoming_qty": 0.0, "outgoing_qty": 0.0, "activo": True,
        },
    ]
    nombres_catalogo = { (a.get("descripcion") or "").strip().upper()
                        for a in inventario }
    for n in nuevos:
        assert n["nombre"].upper() not in nombres_catalogo, \
            f"el producto nuevo {n['nombre']!r} colisiona con el catálogo"
    productos += nuevos

    muestra = {
        "_nota": (
            "Muestra determinista del conector de Odoo (transport de la demo). "
            "Derivada del dataset por generar_odoo_muestra.py — no editar a "
            "mano. La lee core/odoo_demo.py; las formas son el contrato de "
            "conectores.ConectorOdoo.pull_* y los coercers de core/staging.py."
        ),
        "vinculos": {
            "productos": [{"codigo": a["codigo"],
                           "source_id": TMPL_BASE + a["codigo"],
                           "sku": f"LIT-{a['codigo']}"} for a in vinculados],
            "proveedores": [],
        },
        "productos": productos,
        "proveedores": proveedores,
        "clientes": [],
        "ordenes_compra": ordenes_compra,
        "ordenes_venta": ordenes_venta,
        "recepciones": recepciones,
        "entregas": [],
        "deposito": [],
        "facturas": [],
        "pagos": [],
        "listas_precios": [],
        "monedas": [],
    }
    with open(SALIDA, "w", encoding="utf-8") as fh:
        json.dump(muestra, fh, ensure_ascii=False, indent=1)
    print(f"odoo_muestra.json: {len(productos)} productos "
          f"({len(vinculados)} vinculados + {len(nuevos)} nuevos), "
          f"{len(proveedores)} proveedores, {len(ordenes_compra)} OC, "
          f"{len(ordenes_venta)} ventas, {len(recepciones)} recepciones")


if __name__ == "__main__":
    main()

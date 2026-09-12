"""
Plan 11 · Arquitectura de conectores.

PolPilot nunca habla directo con Faro/Tango: habla con un CONECTOR que abstrae
la comunicación. Una sola interfaz (IConector), un conector por sistema.

Hoy:
  - ConectorCSV: export/import manual (Fase 1, funciona).
  - ConectorBCRA: contexto macro (ya construido en core/macro.py).
  - ConectorOdoo: cuenta Odoo propia del cliente, vía XML-RPC (Fase 3).
  - ConectorMCP: el slot vacío para cuando Faro/Tango expongan MCP (Fase 3).
"""
from __future__ import annotations

import xmlrpc.client
from abc import ABC, abstractmethod

from . import macro, sync
from core.db import odoo_connections_repo


class IConector(ABC):
    """Interfaz estándar. Todo sistema externo se conecta implementando esto."""
    nombre: str = "abstracto"

    @abstractmethod
    def pull_data(self, **kwargs) -> dict:
        """Trae datos del sistema externo hacia PolPilot."""

    @abstractmethod
    def push_action(self, accion: dict) -> dict:
        """Manda un cambio de PolPilot hacia el sistema externo."""

    @abstractmethod
    def get_schema(self) -> dict:
        """Describe qué datos expone el sistema."""


class ConectorCSV(IConector):
    """Fase 1: el usuario exporta/importa CSV. La Staging Area procesa la entrada;
    el delta export genera la salida."""
    nombre = "csv"

    def pull_data(self, csv_texto: str = "", **kwargs) -> dict:
        from . import staging
        return staging.crear_batch(kwargs.get("nombre", "import.csv"), csv_texto)

    def push_action(self, accion: dict) -> dict:
        return sync.generar_delta_export(accion.get("formato", "generico"))

    def get_schema(self) -> dict:
        return {"entrada": "CSV con encabezados", "salida": "delta CSV (solo cambios)"}


class ConectorBCRA(IConector):
    """Conector oficial al BCRA (cotizaciones). Ya implementado en core/macro.py."""
    nombre = "bcra"

    def pull_data(self, **kwargs) -> dict:
        return macro.consultar(kwargs.get("indicadores", ["dolar"]))

    def push_action(self, accion: dict) -> dict:
        return {"ok": False, "motivo": "el BCRA es solo lectura"}

    def get_schema(self) -> dict:
        return {"indicadores": ["dolar", "inflacion"]}


def _m2o_id(val):
    if not val:
        return None
    return val[0] if isinstance(val, (list, tuple)) else val


def _m2o_name(val, fallback: str = "") -> str:
    if not val:
        return fallback
    if isinstance(val, (list, tuple)) and len(val) > 1:
        return val[1] or fallback
    return fallback


def _date_part(val) -> str:
    if not val:
        return ""
    return str(val)[:10]


def probar_conexion_odoo(url: str, database: str, username: str, api_key: str) -> None:
    """Autentica contra Odoo sin guardar nada — usado antes de persistir una
    conexión nueva, para no guardar credenciales que no sirven."""
    try:
        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
        uid = common.authenticate(database, username, api_key, {})
    except Exception as e:
        raise ValueError(f"No se pudo conectar con Odoo: {e}") from e
    if not uid:
        raise ValueError("Odoo rechazó esas credenciales.")


class ConectorOdoo(IConector):
    """La cuenta Odoo propia del cliente (admin), vía XML-RPC — mismo protocolo
    que examples/xmlrpc_example.py en odoo-test-env. Arranca por res.partner
    (Contactos): es el módulo más simple para conectar — vive en el módulo
    `base` de Odoo (siempre instalado), sin depender de que la app de
    Contabilidad esté activa, y sin estados de flujo de negocio que resolver
    (a diferencia de account.move/facturas).

    pull_data() trae los contactos-cliente (customer_rank > 0) tal cual están
    en Odoo. A propósito NO los empuja a la Staging Area: ese pipeline (core/
    staging.py) hoy sólo sabe coercionar "venta", "deposito" y "logistica" —
    cualquier otro tipo, incluido "cliente", cae al branch default y se
    interpreta como filas de PRODUCTO (ver _coerce_y_analizar), lo que
    corrompería los nombres de clientes silenciosamente. Hasta que la Staging
    Area sepa coercionar "cliente" de verdad, esto es un preview de sólo
    lectura; mapear el resultado a customer_accounts (core/cuentas.py) queda
    como trabajo futuro explícito, no una integración a medias."""
    nombre = "odoo"

    def __init__(self, tenant_id: str | None = None):
        self.tenant_id = tenant_id
        self._conexion = odoo_connections_repo.get(tenant_id) if tenant_id else None

    def _execute_kw(self, model: str, method: str, *args, **kwargs):
        c = self._conexion
        common = xmlrpc.client.ServerProxy(f"{c['url']}/xmlrpc/2/common")
        uid = common.authenticate(c["database"], c["username"], c["api_key"], {})
        if not uid:
            raise ValueError("Odoo rechazó las credenciales guardadas para este tenant.")
        models = xmlrpc.client.ServerProxy(f"{c['url']}/xmlrpc/2/object")
        return models.execute_kw(c["database"], uid, c["api_key"], model, method, list(args), kwargs)

    def pull_data(self, **kwargs) -> dict:
        if not self._conexion:
            raise ValueError("No hay conexión con Odoo configurada para este tenant.")
        ids = self._execute_kw(
            "res.partner", "search", [["customer_rank", ">", 0]], limit=kwargs.get("limite", 500)
        )
        partners = self._execute_kw(
            "res.partner", "read", ids, fields=["name", "vat", "city", "phone", "email"]
        )
        clientes = [
            {
                "id": p["id"],
                "nombre": p.get("name") or "",
                "cuit": p.get("vat") or "",
                "localidad": p.get("city") or "",
                "telefono": p.get("phone") or "",
                "email": p.get("email") or "",
            }
            for p in partners
        ]
        return {"origen": "odoo", "modulo": "res.partner", "total": len(clientes), "clientes": clientes}

    def pull_productos(self, **kwargs) -> dict:
        """Trae el catálogo de productos activos con su stock disponible
        (product.template.qty_available, que Odoo calcula sumando los
        movimientos de todos los depósitos internos). Mismo criterio de
        sólo-lectura que pull_data(): esto es un preview, no toca
        core/store.py (el catálogo real de PolPilot) — ver la nota en la
        docstring de la clase."""
        if not self._conexion:
            raise ValueError("No hay conexión con Odoo configurada para este tenant.")
        ids = self._execute_kw(
            "product.template", "search",
            ["|", ["active", "=", True], ["qty_available", "!=", 0]],
            limit=kwargs.get("limite", 500),
            context={"active_test": False},
        )
        productos = self._execute_kw(
            "product.template", "read", ids,
            fields=["name", "default_code", "categ_id", "list_price",
                    "standard_price", "active"],
        )
        stock_by_tmpl = self._stock_by_template(ids)
        catalogo = [
            {
                "id": p["id"],
                "codigo": p.get("default_code") or "",
                "nombre": p.get("name") or "",
                "categoria": (p.get("categ_id") or [None, ""])[1],
                "precio": p.get("list_price") or 0,
                "stock": (stock_by_tmpl.get(p["id"]) or {}).get("qty_available") or 0,
                "costo": p.get("standard_price") or 0,
                "free_qty": (stock_by_tmpl.get(p["id"]) or {}).get("free_qty") or 0,
                "incoming_qty": (stock_by_tmpl.get(p["id"]) or {}).get("incoming_qty") or 0,
                "outgoing_qty": (stock_by_tmpl.get(p["id"]) or {}).get("outgoing_qty") or 0,
                "activo": bool(p.get("active", True)),
            }
            for p in productos
        ]
        return {"origen": "odoo", "modulo": "product.template", "total": len(catalogo), "productos": catalogo}

    def pull_proveedores(self, **kwargs) -> dict:
        """Trae los contactos-proveedor (supplier_rank > 0), la contraparte de
        pull_data() del lado compras. Mismo criterio de sólo-lectura: preview
        para comparar contra core/proveedores.py (la ficha real de proveedor
        en PolPilot), no lo reemplaza ni lo sincroniza automáticamente."""
        if not self._conexion:
            raise ValueError("No hay conexión con Odoo configurada para este tenant.")
        ids = self._execute_kw(
            "res.partner", "search", [["supplier_rank", ">", 0]], limit=kwargs.get("limite", 500)
        )
        partners = self._execute_kw(
            "res.partner", "read", ids, fields=["name", "vat", "city", "phone", "email"]
        )
        proveedores = [
            {
                "id": p["id"],
                "nombre": p.get("name") or "",
                "cuit": p.get("vat") or "",
                "localidad": p.get("city") or "",
                "telefono": p.get("phone") or "",
                "email": p.get("email") or "",
            }
            for p in partners
        ]
        return {"origen": "odoo", "modulo": "res.partner", "total": len(proveedores), "proveedores": proveedores}

    def pull_ordenes_compra(self, **kwargs) -> dict:
        """Trae las órdenes de compra (purchase.order) con sus líneas, la
        contraparte de pull_productos() del lado compras: mismo preview de
        sólo lectura, para comparar contra core/ordenes.py (las órdenes que
        Ángela prepara y el dueño aprueba en PolPilot) — no las importa ni
        las mezcla con esas."""
        if not self._conexion:
            raise ValueError("No hay conexión con Odoo configurada para este tenant.")
        ids = self._execute_kw(
            "purchase.order", "search", [], limit=kwargs.get("limite", 200)
        )
        ordenes = self._execute_kw(
            "purchase.order", "read", ids,
            fields=["name", "partner_id", "state", "date_order", "amount_total"],
        )
        lineas_por_orden: dict[int, list[dict]] = {o["id"]: [] for o in ordenes}
        if ordenes:
            linea_ids = self._execute_kw(
                "purchase.order.line", "search", [["order_id", "in", list(lineas_por_orden)]]
            )
            lineas = self._execute_kw(
                "purchase.order.line", "read", linea_ids,
                fields=["order_id", "product_id", "name",
                        "product_qty", "price_unit", "qty_received"],
            )
            tmpl_by_variant = self._template_id_by_variant(
                [_m2o_id(l.get("product_id")) for l in lineas]
            )
            for l in lineas:
                oid = _m2o_id(l.get("order_id"))
                if oid not in lineas_por_orden:
                    continue
                prod = l.get("product_id") or [None, l.get("name") or ""]
                lineas_por_orden[oid].append({
                    "producto": prod[1] if isinstance(prod, (list, tuple)) else (l.get("name") or ""),
                    "product_tmpl_id": tmpl_by_variant.get(_m2o_id(l.get("product_id"))),
                    "cantidad": l.get("product_qty") or 0,
                    "precio_unitario": l.get("price_unit") or 0,
                    "qty_received": l.get("qty_received") or 0,
                })
        _ESTADOS = {
            "draft": "borrador", "sent": "enviada", "purchase": "confirmada",
            "done": "cerrada", "cancel": "cancelada",
        }
        compras = [
            {
                "id": o["id"],
                "numero": o.get("name") or "",
                "proveedor": (o.get("partner_id") or [None, ""])[1],
                "estado": _ESTADOS.get(o.get("state"), o.get("state") or ""),
                "fecha": o.get("date_order") or "",
                "total": o.get("amount_total") or 0,
                "items": lineas_por_orden.get(o["id"], []),
            }
            for o in ordenes
        ]
        return {"origen": "odoo", "modulo": "purchase.order", "total": len(compras), "ordenes": compras}

    def pull_ordenes_venta(self, **kwargs) -> dict:
        """Preview of sale.order rows (all workflow states) with lines.
        Ingest filters to confirmed (`sale`/`done` → confirmada) elsewhere."""
        if not self._conexion:
            raise ValueError("No hay conexión con Odoo configurada para este tenant.")
        ids = self._execute_kw(
            "sale.order", "search", [], limit=kwargs.get("limite", 5000)
        )
        ordenes = self._execute_kw(
            "sale.order", "read", ids,
            fields=["name", "partner_id", "state", "date_order", "amount_total"],
        )
        lineas_por_orden: dict[int, list[dict]] = {o["id"]: [] for o in ordenes}
        if ordenes:
            linea_ids = self._execute_kw(
                "sale.order.line", "search", [["order_id", "in", list(lineas_por_orden)]]
            )
            lineas = self._execute_kw(
                "sale.order.line", "read", linea_ids,
                fields=["order_id", "product_id", "product_template_id", "name",
                        "product_uom_qty", "price_unit"],
            )
            for l in lineas:
                tmpl = l.get("product_template_id") or [None, ""]
                prod = l.get("product_id") or [None, l.get("name") or ""]
                lineas_por_orden[l["order_id"][0]].append({
                    "id": l["id"],
                    "producto": prod[1],
                    "product_tmpl_id": tmpl[0],
                    "cantidad": l.get("product_uom_qty") or 0,
                    "precio_unitario": l.get("price_unit") or 0,
                })
        _ESTADOS = {
            "draft": "borrador", "sent": "enviada", "sale": "confirmada",
            "done": "confirmada", "cancel": "cancelada",
        }
        ventas = [
            {
                "id": o["id"],
                "numero": o.get("name") or "",
                "cliente": (o.get("partner_id") or [None, ""])[1],
                "estado": _ESTADOS.get(o.get("state"), o.get("state") or ""),
                "fecha": o.get("date_order") or "",
                "total": o.get("amount_total") or 0,
                "items": lineas_por_orden.get(o["id"], []),
            }
            for o in ordenes
        ]
        return {"origen": "odoo", "modulo": "sale.order", "total": len(ventas), "ordenes": ventas}

    def _read_by_id(self, model: str, ids: list, fields: list[str]) -> dict:
        ids = [i for i in ids if i]
        if not ids:
            return {}
        rows = self._execute_kw(model, "read", ids, fields=fields)
        return {r["id"]: r for r in rows}

    def _stock_by_template(self, template_ids: list) -> dict:
        """Stock qty fields live on product.product in Odoo 17 (free_qty is not
        on product.template; reading it there raises Invalid field)."""
        if not template_ids:
            return {}
        variant_ids = self._execute_kw(
            "product.product", "search",
            [["product_tmpl_id", "in", list(template_ids)]],
            context={"active_test": False},
        )
        variants = self._execute_kw(
            "product.product", "read", variant_ids,
            fields=["product_tmpl_id", "qty_available", "free_qty",
                    "incoming_qty", "outgoing_qty"],
        ) if variant_ids else []
        out: dict = {}
        for v in variants:
            tid = _m2o_id(v.get("product_tmpl_id"))
            if tid is None:
                continue
            slot = out.setdefault(tid, {
                "qty_available": 0.0, "free_qty": 0.0,
                "incoming_qty": 0.0, "outgoing_qty": 0.0,
            })
            for key in ("qty_available", "free_qty", "incoming_qty", "outgoing_qty"):
                slot[key] += v.get(key) or 0
        return out

    def _template_id_by_variant(self, variant_ids: list) -> dict:
        """purchase.order.line has product_id only; sale.order.line has product_template_id."""
        rows = self._read_by_id("product.product", variant_ids, ["product_tmpl_id"])
        return {vid: _m2o_id(row.get("product_tmpl_id")) for vid, row in rows.items()}

    def pull_deposito(self, **kwargs) -> dict:
        """Internal stock.quant rows (qty ≠ 0). Locations and lots resolved."""
        if not self._conexion:
            raise ValueError("No hay conexión con Odoo configurada para este tenant.")
        ids = self._execute_kw(
            "stock.quant", "search",
            ["&", ["quantity", "!=", 0], ["location_id.usage", "=", "internal"]],
            limit=kwargs.get("limite", 2000),
        )
        quants = self._execute_kw(
            "stock.quant", "read", ids,
            fields=["product_id", "location_id", "quantity", "lot_id", "in_date",
                    "inventory_quantity", "inventory_quantity_set"],
        ) if ids else []
        loc_ids = sorted({_m2o_id(q.get("location_id")) for q in quants if _m2o_id(q.get("location_id"))})
        lot_ids = sorted({_m2o_id(q.get("lot_id")) for q in quants if _m2o_id(q.get("lot_id"))})
        var_ids = sorted({_m2o_id(q.get("product_id")) for q in quants if _m2o_id(q.get("product_id"))})
        locations = self._read_by_id("stock.location", loc_ids, ["complete_name"])
        lots = self._read_by_id("stock.lot", lot_ids, ["name", "expiration_date"])
        variants = self._read_by_id("product.product", var_ids, ["product_tmpl_id"])
        rows = []
        for q in quants:
            loc = locations.get(_m2o_id(q.get("location_id"))) or {}
            lot = lots.get(_m2o_id(q.get("lot_id"))) or {}
            var = variants.get(_m2o_id(q.get("product_id"))) or {}
            row = {
                "id": q["id"],
                "producto": _m2o_name(q.get("product_id")),
                "product_tmpl_id": _m2o_id(var.get("product_tmpl_id")),
                "ubicacion": loc.get("complete_name") or _m2o_name(q.get("location_id")),
                "lote": lot.get("name") or "",
                "vencimiento": _date_part(lot.get("expiration_date")),
                "cantidad": q.get("quantity") or 0,
                "in_date": _date_part(q.get("in_date")),
            }
            if q.get("inventory_quantity_set"):
                row["counted_qty"] = q.get("inventory_quantity") or 0
            rows.append(row)
        return {"origen": "odoo", "modulo": "stock.quant", "total": len(rows), "quants": rows}

    def pull_recepciones(self, **kwargs) -> dict:
        """Done incoming pickings, one row per stock.move."""
        if not self._conexion:
            raise ValueError("No hay conexión con Odoo configurada para este tenant.")
        picking_ids = self._execute_kw(
            "stock.picking", "search",
            [["picking_type_code", "=", "incoming"], ["state", "=", "done"]],
            limit=kwargs.get("limite", 500),
        )
        pickings = self._execute_kw(
            "stock.picking", "read", picking_ids,
            fields=["name", "partner_id", "date_done", "origin",
                    "location_dest_id", "state"],
        ) if picking_ids else []
        pick_by_id = {p["id"]: p for p in pickings}
        move_ids = self._execute_kw(
            "stock.move", "search",
            [["picking_id", "in", picking_ids], ["state", "=", "done"]],
        ) if picking_ids else []
        moves = self._execute_kw(
            "stock.move", "read", move_ids,
            fields=["picking_id", "product_id", "quantity", "location_dest_id",
                    "purchase_line_id", "state"],
        ) if move_ids else []
        loc_ids = sorted({_m2o_id(m.get("location_dest_id")) or _m2o_id(p.get("location_dest_id"))
                          for m in moves for p in [pick_by_id.get(_m2o_id(m.get("picking_id"))) or {}]
                          if _m2o_id(m.get("location_dest_id")) or _m2o_id(p.get("location_dest_id"))})
        var_ids = sorted({_m2o_id(m.get("product_id")) for m in moves if _m2o_id(m.get("product_id"))})
        pol_ids = sorted({_m2o_id(m.get("purchase_line_id")) for m in moves if _m2o_id(m.get("purchase_line_id"))})
        locations = self._read_by_id("stock.location", loc_ids, ["complete_name"])
        variants = self._read_by_id("product.product", var_ids, ["product_tmpl_id"])
        polines = self._read_by_id("purchase.order.line", pol_ids, ["order_id"])
        rows = []
        for m in moves:
            picking = pick_by_id.get(_m2o_id(m.get("picking_id"))) or {}
            loc_id = _m2o_id(m.get("location_dest_id")) or _m2o_id(picking.get("location_dest_id"))
            loc = locations.get(loc_id) or {}
            var = variants.get(_m2o_id(m.get("product_id"))) or {}
            pol = polines.get(_m2o_id(m.get("purchase_line_id"))) or {}
            po_number = _m2o_name(pol.get("order_id")) or (picking.get("origin") or "")
            qty = m.get("quantity")
            if qty is None:
                qty = m.get("quantity_done") or 0
            rows.append({
                "id": m["id"],
                "fecha": _date_part(picking.get("date_done")),
                "producto": _m2o_name(m.get("product_id")),
                "product_tmpl_id": _m2o_id(var.get("product_tmpl_id")),
                "proveedor": _m2o_name(picking.get("partner_id")),
                "cantidad": qty or 0,
                "deposito": loc.get("complete_name") or _m2o_name(picking.get("location_dest_id")),
                "origen": picking.get("name") or "",
                "po_number": po_number,
                "estado": picking.get("state") or "",
            })
        return {"origen": "odoo", "modulo": "stock.picking", "total": len(rows),
                "recepciones": rows}

    def push_action(self, accion: dict) -> dict:
        return {"ok": False, "motivo": "Conector Odoo: por ahora solo lectura (Contactos)."}

    def get_schema(self) -> dict:
        return {
            "modulo": "res.partner (Contactos) — el módulo más simple de Odoo para arrancar",
            "campos": ["name", "vat", "city", "phone", "email"],
            "requiere_conexion": ["url", "database", "username", "api_key"],
            "conectado": self._conexion is not None,
        }


class ConectorMCP(IConector):
    """Fase 3: slot para Model Context Protocol. Cuando Faro/Tango expongan un MCP
    server, se enchufan acá los métodos reales (1-2 días de trabajo)."""
    nombre = "mcp"

    def __init__(self, servidor: str | None = None):
        self.servidor = servidor

    def pull_data(self, **kwargs) -> dict:
        raise NotImplementedError("Conector MCP: pendiente de que el sistema externo exponga MCP.")

    def push_action(self, accion: dict) -> dict:
        raise NotImplementedError("Conector MCP: pendiente de que el sistema externo exponga MCP.")

    def get_schema(self) -> dict:
        return {"estado": "slot vacío", "fase": 3}


# Registro de conectores disponibles.
CONECTORES = {"csv": ConectorCSV, "bcra": ConectorBCRA, "odoo": ConectorOdoo, "mcp": ConectorMCP}


def disponibles(tenant_id: str | None = None) -> list[dict]:
    out = []
    for nombre, cls in CONECTORES.items():
        try:
            inst = cls(tenant_id) if nombre == "odoo" else cls()
            if nombre == "odoo":
                estado = "activo" if inst._conexion else "pendiente"
            else:
                estado = "activo" if nombre in ("csv", "bcra") else "pendiente"
            out.append({"nombre": nombre, "estado": estado, "schema": inst.get_schema()})
        except Exception:
            out.append({"nombre": nombre, "estado": "pendiente"})
    return out

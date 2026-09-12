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

from . import fechas, macro, odoo_fx, sync
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
    """The client's own Odoo account (admin), via XML-RPC.

    Preview (`pull_*`) is read-only. Real writes go through core/odoo_ingest.py.
    Amounts on sale.order / purchase.order / account.move honour each record's
    currency_id and dated res.currency.rate points — never a flat FX rate.
    Product catalog prices come from pricelist items, not from converting
    list_price; the charged sale price is sale.order.line.price_unit.
    """
    nombre = "odoo"

    def __init__(self, tenant_id: str | None = None):
        self.tenant_id = tenant_id
        self._conexion = odoo_connections_repo.get(tenant_id) if tenant_id else None
        self._uid = None
        self._models = None
        self._fx_cache = None
        self._pricelist_cache = None

    def _ensure_rpc(self):
        c = self._conexion
        if self._uid is not None:
            return
        common = xmlrpc.client.ServerProxy(f"{c['url']}/xmlrpc/2/common")
        uid = common.authenticate(c["database"], c["username"], c["api_key"], {})
        if not uid:
            raise ValueError("Odoo rechazó las credenciales guardadas para este tenant.")
        self._uid = uid
        self._models = xmlrpc.client.ServerProxy(f"{c['url']}/xmlrpc/2/object")

    def _execute_kw(self, model: str, method: str, *args, **kwargs):
        c = self._conexion
        self._ensure_rpc()
        return self._models.execute_kw(
            c["database"], self._uid, c["api_key"], model, method, list(args), kwargs)

    def _try_kw(self, model: str, method: str, *args, **kwargs):
        """Optional models (pricelists, accounting, extra rate fields). Auth
        failures still raise; missing models / unknown fields return empty."""
        try:
            return self._execute_kw(model, method, *args, **kwargs)
        except ValueError:
            raise
        except Exception:
            if method == "search":
                return []
            if method == "read":
                return []
            return None

    def _company_and_rates(self) -> tuple[dict, list[dict]]:
        if self._fx_cache is not None:
            return self._fx_cache
        company = {"currency": "ARS", "country": "", "name": ""}
        rows = self._try_kw("res.company", "search", [], limit=1) or []
        if rows:
            recs = self._try_kw(
                "res.company", "read", rows,
                fields=["name", "currency_id", "country_id"],
            ) or []
            if recs:
                rec = recs[0]
                company = {
                    "id": rec["id"],
                    "name": rec.get("name") or "",
                    "currency": odoo_fx._iso_code(rec.get("currency_id")) or "ARS",
                    "country": _m2o_name(rec.get("country_id")),
                }
        rate_ids = self._try_kw("res.currency.rate", "search", [], limit=500) or []
        raw_rates = self._try_kw(
            "res.currency.rate", "read", rate_ids,
            fields=["name", "rate", "currency_id", "company_rate", "inverse_company_rate"],
        ) if rate_ids else []
        cur_ids = sorted({
            _m2o_id(r.get("currency_id")) for r in (raw_rates or [])
            if _m2o_id(r.get("currency_id"))
        })
        currencies = self._try_kw(
            "res.currency", "read", cur_ids, fields=["name", "symbol"],
        ) if cur_ids else []
        names = {c["id"]: odoo_fx._iso_code(c.get("name")) for c in (currencies or [])}
        rates = odoo_fx.normalize_rates(raw_rates or [], names)
        self._fx_cache = (company, rates)
        return self._fx_cache

    def _pricelists_and_items(self) -> tuple[list[dict], list[dict]]:
        if self._pricelist_cache is not None:
            return self._pricelist_cache
        ids = self._try_kw("product.pricelist", "search", [], limit=50) or []
        lists = self._try_kw(
            "product.pricelist", "read", ids, fields=["name", "currency_id"],
        ) if ids else []
        item_ids = self._try_kw(
            "product.pricelist.item", "search",
            [["pricelist_id", "in", ids]] if ids else [],
            limit=5000,
        ) if ids else []
        items = self._try_kw(
            "product.pricelist.item", "read", item_ids,
            fields=["pricelist_id", "applied_on", "compute_price", "fixed_price",
                    "percent_price", "price_discount", "categ_id",
                    "product_tmpl_id", "product_id", "min_quantity"],
        ) if item_ids else []
        self._pricelist_cache = (lists or [], items or [])
        return self._pricelist_cache

    def _convert(self, amount, currency, when) -> float:
        company, rates = self._company_and_rates()
        return odoo_fx.to_company_amount(
            amount, currency, when, rates, company.get("currency") or "ARS")

    def _currency_of(self, record: dict, company_currency: str) -> str:
        return odoo_fx._iso_code(record.get("currency_id")) or company_currency

    def _open_backorder_origins(self, picking_type_code: str) -> set[str]:
        ids = self._try_kw(
            "stock.picking", "search",
            [["picking_type_code", "=", picking_type_code],
             ["state", "in", list(odoo_fx.PENDING_PICKING_STATES)],
             ["backorder_id", "!=", False]],
            limit=2000,
        ) or []
        if not ids:
            return set()
        rows = self._try_kw(
            "stock.picking", "read", ids,
            fields=["origin", "backorder_id", "state"],
        ) or []
        return {
            r.get("origin") for r in rows
            if r.get("origin")
            and _m2o_id(r.get("backorder_id"))
            and odoo_fx.is_pending_picking(r.get("state"))
        }

    def pull_data(self, **kwargs) -> dict:
        if not self._conexion:
            raise ValueError("No hay conexión con Odoo configurada para este tenant.")
        ids = self._execute_kw(
            "res.partner", "search", [["customer_rank", ">", 0]], limit=kwargs.get("limite", 500)
        )
        partners = self._execute_kw(
            "res.partner", "read", ids,
            fields=["name", "vat", "city", "phone", "email", "property_product_pricelist"],
        )
        clientes = [
            {
                "id": p["id"],
                "nombre": p.get("name") or "",
                "cuit": p.get("vat") or "",
                "localidad": p.get("city") or "",
                "telefono": p.get("phone") or "",
                "email": p.get("email") or "",
                "pricelist_id": _m2o_id(p.get("property_product_pricelist")),
                "pricelist": _m2o_name(p.get("property_product_pricelist")),
            }
            for p in partners
        ]
        return {"origen": "odoo", "modulo": "res.partner", "total": len(clientes), "clientes": clientes}

    def pull_productos(self, **kwargs) -> dict:
        """Active (or in-stock) product.template rows with stock rollup and
        pricelist-resolved prices. `list_price` is the retail/reference
        price; `precio` is the sellable price (mayorista item when the
        product is wholesale-only; None when it genuinely needs pricing).
        USD pricelist `fixed` items are native quotes, not FX of list_price.
        """
        if not self._conexion:
            raise ValueError("No hay conexión con Odoo configurada para este tenant.")
        company, rates = self._company_and_rates()
        pricelists, pl_items = self._pricelists_and_items()
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
        catalogo = []
        for p in productos:
            pricing = odoo_fx.resolve_product_pricing(p, pricelists, pl_items)
            precio = pricing["precio"]
            if precio is None and pricing.get("usd_fixed"):
                precio = odoo_fx.to_company_amount(
                    pricing["usd_fixed"], pricing.get("usd_currency"),
                    fechas.hoy(), rates, company.get("currency") or "ARS")
            catalogo.append({
                "id": p["id"],
                "codigo": p.get("default_code") or "",
                "nombre": p.get("name") or "",
                "categoria": (p.get("categ_id") or [None, ""])[1],
                "precio": precio,
                "precio_lista": pricing["precio_lista"],
                "pricing_status": pricing["pricing_status"],
                "precios_pricelist": pricing["precios_pricelist"],
                "moneda": company.get("currency") or "ARS",
                "stock": (stock_by_tmpl.get(p["id"]) or {}).get("qty_available") or 0,
                "costo": p.get("standard_price") or 0,
                "free_qty": (stock_by_tmpl.get(p["id"]) or {}).get("free_qty") or 0,
                "incoming_qty": (stock_by_tmpl.get(p["id"]) or {}).get("incoming_qty") or 0,
                "outgoing_qty": (stock_by_tmpl.get(p["id"]) or {}).get("outgoing_qty") or 0,
                "activo": bool(p.get("active", True)),
            })
        return {"origen": "odoo", "modulo": "product.template", "total": len(catalogo),
                "moneda_compania": company.get("currency") or "ARS",
                "productos": catalogo}

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
            fields=["name", "partner_id", "state", "date_order", "amount_total",
                    "currency_id"],
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
        company, _rates = self._company_and_rates()
        company_cur = company.get("currency") or "ARS"
        open_origins = self._open_backorder_origins("incoming")
        compras = []
        for o in ordenes:
            items = lineas_por_orden.get(o["id"], [])
            currency = self._currency_of(o, company_cur)
            fecha = o.get("date_order") or ""
            open_bo = (o.get("name") or "") in open_origins
            compras.append({
                "id": o["id"],
                "numero": o.get("name") or "",
                "proveedor": (o.get("partner_id") or [None, ""])[1],
                "estado": _ESTADOS.get(o.get("state"), o.get("state") or ""),
                "fecha": fecha,
                "total": o.get("amount_total") or 0,
                "currency": currency,
                "total_company": self._convert(o.get("amount_total") or 0, currency, fecha),
                "open_backorder": open_bo,
                "fulfillment": odoo_fx.lines_fulfillment(items, open_backorder=open_bo),
                "items": items,
            })
        return {"origen": "odoo", "modulo": "purchase.order", "total": len(compras),
                "moneda_compania": company_cur, "ordenes": compras}

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
            fields=["name", "partner_id", "state", "date_order", "amount_total",
                    "currency_id", "pricelist_id"],
        )
        lineas_por_orden: dict[int, list[dict]] = {o["id"]: [] for o in ordenes}
        if ordenes:
            linea_ids = self._execute_kw(
                "sale.order.line", "search", [["order_id", "in", list(lineas_por_orden)]]
            )
            lineas = self._execute_kw(
                "sale.order.line", "read", linea_ids,
                fields=["order_id", "product_id", "product_template_id", "name",
                        "product_uom_qty", "price_unit", "qty_delivered"],
            )
            for l in lineas:
                tmpl = l.get("product_template_id") or [None, ""]
                prod = l.get("product_id") or [None, l.get("name") or ""]
                oid = _m2o_id(l.get("order_id"))
                if oid not in lineas_por_orden:
                    continue
                lineas_por_orden[oid].append({
                    "id": l["id"],
                    "producto": prod[1] if isinstance(prod, (list, tuple)) else (l.get("name") or ""),
                    "product_tmpl_id": tmpl[0] if isinstance(tmpl, (list, tuple)) else tmpl,
                    "cantidad": l.get("product_uom_qty") or 0,
                    "qty_delivered": l.get("qty_delivered") or 0,
                    "precio_unitario": l.get("price_unit") or 0,
                })
        _ESTADOS = {
            "draft": "borrador", "sent": "enviada", "sale": "confirmada",
            "done": "confirmada", "cancel": "cancelada",
        }
        company, _rates = self._company_and_rates()
        company_cur = company.get("currency") or "ARS"
        open_origins = self._open_backorder_origins("outgoing")
        ventas = []
        for o in ordenes:
            currency = self._currency_of(o, company_cur)
            fecha = o.get("date_order") or ""
            items = []
            for it in lineas_por_orden.get(o["id"], []):
                item = dict(it)
                item["precio_company"] = self._convert(
                    it.get("precio_unitario") or 0, currency, fecha)
                items.append(item)
            open_bo = (o.get("name") or "") in open_origins
            ventas.append({
                "id": o["id"],
                "numero": o.get("name") or "",
                "cliente": (o.get("partner_id") or [None, ""])[1],
                "estado": _ESTADOS.get(o.get("state"), o.get("state") or ""),
                "fecha": fecha,
                "total": o.get("amount_total") or 0,
                "currency": currency,
                "total_company": self._convert(o.get("amount_total") or 0, currency, fecha),
                "pricelist": _m2o_name(o.get("pricelist_id")),
                "open_backorder": open_bo,
                "fulfillment": odoo_fx.lines_fulfillment(
                    items, done_key="qty_delivered", open_backorder=open_bo),
                "items": items,
            })
        return {"origen": "odoo", "modulo": "sale.order", "total": len(ventas),
                "moneda_compania": company_cur, "ordenes": ventas}

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

    def _pull_pickings_as_moves(self, picking_type_code: str, limite: int) -> list[dict]:
        """Incoming or outgoing pickings in done OR still-open states, one
        row per stock.move. Open backorders (backorder_id set, pending state)
        are included — cancelled backorders are not."""
        picking_ids = self._execute_kw(
            "stock.picking", "search",
            [["picking_type_code", "=", picking_type_code],
             ["state", "in", list(odoo_fx.OPEN_PICKING_STATES)]],
            limit=limite,
        )
        pickings = self._execute_kw(
            "stock.picking", "read", picking_ids,
            fields=["name", "partner_id", "date_done", "scheduled_date", "origin",
                    "location_dest_id", "state", "backorder_id", "picking_type_code"],
        ) if picking_ids else []
        pick_by_id = {p["id"]: p for p in pickings}
        move_ids = self._execute_kw(
            "stock.move", "search",
            [["picking_id", "in", picking_ids]],
        ) if picking_ids else []
        moves = self._execute_kw(
            "stock.move", "read", move_ids,
            fields=["picking_id", "product_id", "quantity", "product_uom_qty",
                    "location_dest_id", "purchase_line_id", "sale_line_id", "state"],
        ) if move_ids else []
        loc_ids = sorted({
            _m2o_id(m.get("location_dest_id")) or _m2o_id(
                (pick_by_id.get(_m2o_id(m.get("picking_id"))) or {}).get("location_dest_id"))
            for m in moves
            if _m2o_id(m.get("location_dest_id")) or _m2o_id(
                (pick_by_id.get(_m2o_id(m.get("picking_id"))) or {}).get("location_dest_id"))
        })
        var_ids = sorted({_m2o_id(m.get("product_id")) for m in moves if _m2o_id(m.get("product_id"))})
        pol_ids = sorted({_m2o_id(m.get("purchase_line_id")) for m in moves if _m2o_id(m.get("purchase_line_id"))})
        locations = self._read_by_id("stock.location", loc_ids, ["complete_name"])
        variants = self._read_by_id("product.product", var_ids, ["product_tmpl_id"])
        polines = self._read_by_id("purchase.order.line", pol_ids, ["order_id"]) if pol_ids else {}
        rows = []
        for m in moves:
            picking = pick_by_id.get(_m2o_id(m.get("picking_id"))) or {}
            loc_id = _m2o_id(m.get("location_dest_id")) or _m2o_id(picking.get("location_dest_id"))
            loc = locations.get(loc_id) or {}
            var = variants.get(_m2o_id(m.get("product_id"))) or {}
            pol = polines.get(_m2o_id(m.get("purchase_line_id"))) or {}
            po_number = _m2o_name(pol.get("order_id")) or (picking.get("origin") or "")
            qty_done = m.get("quantity")
            if qty_done is None:
                qty_done = m.get("quantity_done") or 0
            qty_ordered = m.get("product_uom_qty")
            if qty_ordered in (None, False):
                qty_ordered = qty_done or 0
            state = picking.get("state") or ""
            backorder_id = _m2o_id(picking.get("backorder_id"))
            fecha = _date_part(picking.get("date_done")) or _date_part(picking.get("scheduled_date"))
            rows.append({
                "id": m["id"],
                "picking_id": picking.get("id"),
                "fecha": fecha,
                "producto": _m2o_name(m.get("product_id")),
                "product_tmpl_id": _m2o_id(var.get("product_tmpl_id")),
                "partner": _m2o_name(picking.get("partner_id")),
                "proveedor": _m2o_name(picking.get("partner_id")),
                "cantidad": qty_done or 0,
                "qty_ordered": qty_ordered or 0,
                "deposito": loc.get("complete_name") or _m2o_name(picking.get("location_dest_id")),
                "origen": picking.get("name") or "",
                "po_number": po_number,
                "so_number": picking.get("origin") or "" if picking_type_code == "outgoing" else "",
                "estado": state,
                "backorder_id": backorder_id,
                "es_backorder": bool(backorder_id),
                "pendiente": odoo_fx.is_pending_picking(state),
                "open_backorder": bool(backorder_id) and odoo_fx.is_pending_picking(state),
            })
        return rows

    def pull_recepciones(self, **kwargs) -> dict:
        """Incoming pickings (done and still-open), one row per stock.move."""
        if not self._conexion:
            raise ValueError("No hay conexión con Odoo configurada para este tenant.")
        rows = self._pull_pickings_as_moves("incoming", kwargs.get("limite", 500))
        return {"origen": "odoo", "modulo": "stock.picking", "total": len(rows),
                "recepciones": rows}

    def pull_entregas(self, **kwargs) -> dict:
        """Outgoing pickings (done and still-open sale deliveries), including
        real open backorders."""
        if not self._conexion:
            raise ValueError("No hay conexión con Odoo configurada para este tenant.")
        rows = self._pull_pickings_as_moves("outgoing", kwargs.get("limite", 500))
        for r in rows:
            r["cliente"] = r.get("partner") or ""
        return {"origen": "odoo", "modulo": "stock.picking", "total": len(rows),
                "entregas": rows}

    def pull_listas_precios(self, **kwargs) -> dict:
        if not self._conexion:
            raise ValueError("No hay conexión con Odoo configurada para este tenant.")
        lists, items = self._pricelists_and_items()
        by_pl: dict[int, list[dict]] = {}
        for it in items:
            pid = _m2o_id(it.get("pricelist_id"))
            by_pl.setdefault(pid, []).append({
                "id": it["id"],
                "applied_on": it.get("applied_on") or "",
                "compute_price": it.get("compute_price") or "",
                "fixed_price": it.get("fixed_price"),
                "price_discount": it.get("price_discount"),
                "categ_id": _m2o_id(it.get("categ_id")),
                "categoria": _m2o_name(it.get("categ_id")),
                "product_tmpl_id": _m2o_id(it.get("product_tmpl_id")),
                "producto": _m2o_name(it.get("product_tmpl_id")) or _m2o_name(it.get("product_id")),
            })
        listas = [{
            "id": pl["id"],
            "nombre": pl.get("name") or "",
            "currency": odoo_fx._iso_code(pl.get("currency_id")) or "ARS",
            "items": by_pl.get(pl["id"], []),
        } for pl in lists]
        return {"origen": "odoo", "modulo": "product.pricelist", "total": len(listas),
                "listas": listas}

    def pull_monedas(self, **kwargs) -> dict:
        if not self._conexion:
            raise ValueError("No hay conexión con Odoo configurada para este tenant.")
        company, rates = self._company_and_rates()
        return {
            "origen": "odoo", "modulo": "res.currency.rate",
            "moneda_compania": company.get("currency") or "ARS",
            "pais": company.get("country") or "",
            "empresa": company.get("name") or "",
            "total": len(rates),
            "tipos_cambio": [
                {"currency": r["currency"], "fecha": r["date"].isoformat(),
                 "inverse_company_rate": r.get("inverse_company_rate"),
                 "rate": r.get("rate")}
                for r in sorted(rates, key=lambda x: x["date"])
            ],
        }

    def pull_facturas(self, **kwargs) -> dict:
        """Posted customer invoices and vendor bills, with payment aging
        against the seed's invoice 'today' (2026-07-20)."""
        if not self._conexion:
            raise ValueError("No hay conexión con Odoo configurada para este tenant.")
        company, _rates = self._company_and_rates()
        company_cur = company.get("currency") or "ARS"
        as_of = odoo_fx.hoy_facturas()
        ids = self._try_kw(
            "account.move", "search",
            [["move_type", "in", ["out_invoice", "in_invoice"]],
             ["state", "=", "posted"]],
            limit=kwargs.get("limite", 5000),
        ) or []
        moves = self._try_kw(
            "account.move", "read", ids,
            fields=["name", "partner_id", "move_type", "invoice_date",
                    "invoice_date_due", "amount_total", "amount_residual",
                    "amount_untaxed", "payment_state", "currency_id",
                    "invoice_origin", "state"],
        ) if ids else []
        rows = []
        for m in moves or []:
            currency = self._currency_of(m, company_cur)
            fecha = _date_part(m.get("invoice_date"))
            residual = m.get("amount_residual")
            if residual in (None, False):
                residual = m.get("amount_total") or 0
            aging = odoo_fx.classify_invoice_aging(
                m.get("payment_state"), m.get("invoice_date_due"), as_of, residual)
            rows.append({
                "id": m["id"],
                "numero": m.get("name") or "",
                "partner": _m2o_name(m.get("partner_id")),
                "partner_id": _m2o_id(m.get("partner_id")),
                "move_type": m.get("move_type") or "",
                "tipo": "factura" if m.get("move_type") == "out_invoice" else "factura_compra",
                "fecha": fecha,
                "vencimiento": _date_part(m.get("invoice_date_due")),
                "total": m.get("amount_total") or 0,
                "residual": residual or 0,
                "untaxed": m.get("amount_untaxed") or 0,
                "currency": currency,
                "total_company": self._convert(m.get("amount_total") or 0, currency, fecha),
                "residual_company": self._convert(residual or 0, currency, fecha),
                "origen": m.get("invoice_origin") or "",
                "estado": m.get("state") or "",
                **aging,
            })
        return {"origen": "odoo", "modulo": "account.move", "total": len(rows),
                "as_of": as_of.isoformat(), "moneda_compania": company_cur,
                "facturas": rows}

    def pull_pagos(self, **kwargs) -> dict:
        if not self._conexion:
            raise ValueError("No hay conexión con Odoo configurada para este tenant.")
        company, _rates = self._company_and_rates()
        company_cur = company.get("currency") or "ARS"
        ids = self._try_kw(
            "account.payment", "search",
            [["state", "=", "posted"]],
            limit=kwargs.get("limite", 5000),
        ) or []
        pays = self._try_kw(
            "account.payment", "read", ids,
            fields=["name", "partner_id", "amount", "date", "payment_type",
                    "partner_type", "currency_id", "ref", "state"],
        ) if ids else []
        rows = []
        for p in pays or []:
            currency = self._currency_of(p, company_cur)
            fecha = _date_part(p.get("date"))
            rows.append({
                "id": p["id"],
                "numero": p.get("name") or "",
                "partner": _m2o_name(p.get("partner_id")),
                "partner_id": _m2o_id(p.get("partner_id")),
                "monto": p.get("amount") or 0,
                "monto_company": self._convert(p.get("amount") or 0, currency, fecha),
                "fecha": fecha,
                "payment_type": p.get("payment_type") or "",
                "partner_type": p.get("partner_type") or "",
                "currency": currency,
                "ref": p.get("ref") or "",
                "estado": p.get("state") or "",
            })
        return {"origen": "odoo", "modulo": "account.payment", "total": len(rows),
                "moneda_compania": company_cur, "pagos": rows}

    def push_action(self, accion: dict) -> dict:
        return {"ok": False, "motivo": "Conector Odoo: por ahora solo lectura (Contactos)."}

    def get_schema(self) -> dict:
        return {
            "modulo": "res.partner, product.template, sale.order, purchase.order, "
                      "stock.quant, stock.picking, account.move, product.pricelist",
            "campos": ["name", "vat", "city", "phone", "email", "currency_id",
                       "payment_state", "backorder_id", "in_date"],
            "requiere_conexion": ["url", "database", "username", "api_key"],
            "conectado": self._conexion is not None,
            "moneda_compania": "ARS",
        }


class ConectorOdooDemo(ConectorOdoo):
    """The Odoo connector over the demo's SAMPLE transport (core/odoo_demo.py).

    Same class, same pull_* contract, same ingest pipeline downstream — only
    `_execute_kw`'s XML-RPC is replaced by the deterministic payloads in
    data-demo/odoo_muestra.json. It is NEVER chosen implicitly: see
    conector_odoo() below — a configured real connection always wins, and
    without the owner having explicitly connected the sample this class is
    unreachable. Domains the sample doesn't cover return their honest empty
    payload (total 0), not invented rows.
    """
    nombre = "odoo"

    def __init__(self):
        # Deliberately NOT calling super().__init__: no tenant row is read
        # and no credentials exist. `_conexion` is set so the pull_* guards
        # ("no hay conexión configurada") pass — there IS a connection, to
        # the sample.
        self.tenant_id = None
        self._conexion = {"url": "muestra://odoo", "database": "litoral_demo",
                          "username": "demo", "api_key": ""}
        self._uid = None
        self._models = None
        self._fx_cache = None
        self._pricelist_cache = None
        from . import odoo_demo
        self._payloads = odoo_demo.payloads()

    def _ensure_rpc(self):  # pragma: no cover - guard, the sample never RPCs
        raise RuntimeError("ConectorOdooDemo never opens XML-RPC.")

    def _pull(self, clave: str, modulo: str, lista: str) -> dict:
        rows = list(self._payloads.get(clave) or [])
        return {"origen": "odoo", "modulo": modulo, "total": len(rows),
                "moneda_compania": "ARS", lista: rows}

    def pull_data(self, **kwargs) -> dict:
        return self._pull("clientes", "res.partner", "clientes")

    def pull_productos(self, **kwargs) -> dict:
        return self._pull("productos", "product.template", "productos")

    def pull_proveedores(self, **kwargs) -> dict:
        return self._pull("proveedores", "res.partner", "proveedores")

    def pull_ordenes_compra(self, **kwargs) -> dict:
        return self._pull("ordenes_compra", "purchase.order", "ordenes")

    def pull_ordenes_venta(self, **kwargs) -> dict:
        return self._pull("ordenes_venta", "sale.order", "ordenes")

    def pull_recepciones(self, **kwargs) -> dict:
        return self._pull("recepciones", "stock.picking", "recepciones")

    def pull_entregas(self, **kwargs) -> dict:
        return self._pull("entregas", "stock.picking", "entregas")

    def pull_deposito(self, **kwargs) -> dict:
        return self._pull("deposito", "stock.quant", "quants")

    def pull_facturas(self, **kwargs) -> dict:
        return self._pull("facturas", "account.move", "facturas")

    def pull_pagos(self, **kwargs) -> dict:
        return self._pull("pagos", "account.payment", "pagos")

    def pull_listas_precios(self, **kwargs) -> dict:
        return self._pull("listas_precios", "product.pricelist", "listas")

    def pull_monedas(self, **kwargs) -> dict:
        return self._pull("monedas", "res.currency", "monedas")

    def get_schema(self) -> dict:
        base = super().get_schema()
        return {**base, "conectado": True, "demo": True}


def conector_odoo(tenant_id: str | None) -> ConectorOdoo:
    """The ONE place that decides which transport serves the Odoo pulls.

    A real configured connection always wins. The sample transport applies
    only when the owner explicitly connected it (core/odoo_demo.py's marker)
    and no real connection exists — it is a deliberate demo mode, never a
    fallback for a failing real one (that one keeps failing loudly, on
    purpose)."""
    real = ConectorOdoo(tenant_id)
    if real._conexion:
        return real
    from . import odoo_demo
    if odoo_demo.activo():
        return ConectorOdooDemo()
    return real


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
            # Odoo goes through the factory: a connected sample (demo) reads
            # as activo the same way a real connection does, and says so.
            inst = conector_odoo(tenant_id) if nombre == "odoo" else cls()
            if nombre == "odoo":
                estado = "activo" if inst._conexion else "pendiente"
            else:
                estado = "activo" if nombre in ("csv", "bcra") else "pendiente"
            entrada = {"nombre": nombre, "estado": estado, "schema": inst.get_schema()}
            if nombre == "odoo" and isinstance(inst, ConectorOdooDemo):
                entrada["demo"] = True
            out.append(entrada)
        except Exception:
            out.append({"nombre": nombre, "estado": "pendiente"})
    return out

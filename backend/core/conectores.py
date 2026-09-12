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
            "product.template", "search", [["active", "=", True]], limit=kwargs.get("limite", 500)
        )
        productos = self._execute_kw(
            "product.template", "read", ids,
            fields=["name", "default_code", "categ_id", "list_price", "qty_available"],
        )
        catalogo = [
            {
                "id": p["id"],
                "codigo": p.get("default_code") or "",
                "nombre": p.get("name") or "",
                "categoria": (p.get("categ_id") or [None, ""])[1],
                "precio": p.get("list_price") or 0,
                "stock": p.get("qty_available") or 0,
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
                fields=["order_id", "product_id", "name", "product_qty", "price_unit"],
            )
            for l in lineas:
                lineas_por_orden[l["order_id"][0]].append({
                    "producto": (l.get("product_id") or [None, l.get("name") or ""])[1],
                    "cantidad": l.get("product_qty") or 0,
                    "precio_unitario": l.get("price_unit") or 0,
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

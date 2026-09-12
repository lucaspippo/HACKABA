"""
Staging Area — la "zona de revisión".

Los datos nuevos NO entran directo al sistema: van a una cuarentena. Ángela los
analiza, detecta lo que no cierra (duplicados, precio a pérdida, sin precio, stock
anormal), y el dueño resuelve con REGLAS en lenguaje natural (no caso por caso).
Recién cuando aprueba, se integran al inventario oficial — con backup.

Flujo: crear_batch → analizar → resolver(obs, regla) → preview → integrar/descartar.
"""
from __future__ import annotations

import csv
import datetime
import io
import secrets
import unicodedata

from . import store, importer, esquema, recordatorios, normalizacion
from .fechas import parse_fecha, hoy

OUTLIER_STOCK = 10000  # umbral simple de "stock anormalmente alto"


def _num(v):
    """Parseo numérico delegado a la FRONTERA (core/normalizacion.py). Lo ambiguo
    ("1.234": ¿miles o decimal?) NO se interpreta solo: devuelve None y el dato
    espera la decisión del dueño en la card 'numero_ambiguo'. Antes esto hacía
    float("1.234")=1.234 en silencio — el bug que el Nivel 2 ahora evita."""
    valor, _ = normalizacion.normalizar_numero(v)
    return None if valor is normalizacion.AMBIGUO else valor


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()


def _t(key: str, lang: str | None = None, **params) -> str:
    import i18n
    return i18n.t(key, lang, **params)


def _tenant_id_actual() -> str:
    from core.db import tenant as _tenant
    return _tenant.current_tenant_id()


def _load() -> list[dict]:
    from core.db import blob_repo
    from core.db import tenant as _tenant
    return blob_repo.get_blob("staging_batches", _tenant.current_tenant_id()) or []


def _save(batches: list[dict]) -> None:
    from core.db import blob_repo
    from core.db import tenant as _tenant
    blob_repo.save_blob("staging_batches", _tenant.current_tenant_id(), batches)


def _coerce_producto(mapeo: dict, fila_dict: dict) -> dict:
    g = lambda campo: fila_dict.get(mapeo.get(campo)) if mapeo.get(campo) else None
    return {
        "codigo": int(_num(g("codigo"))) if _num(g("codigo")) is not None else None,
        "descripcion": str(g("descripcion") or "").strip(),
        "estado": "activo",
        "stock": _num(g("stock")) or 0.0,
        "costo_iva": _num(g("costo")),
        "pvp": _num(g("pvp")),
        "venta_x_peso": bool(g("venta_x_peso")),
    }


def _coerce_venta(mapeo: dict, fila_dict: dict) -> dict:
    g = lambda campo: fila_dict.get(mapeo.get(campo)) if mapeo.get(campo) else None
    art = str(g("articulo") or "").strip()
    return {
        "fecha": str(g("fecha") or "").strip(),
        "producto": art,
        "codigo": int(_num(art)) if _num(art) is not None else None,
        "cantidad": _num(g("cantidad")) or 0.0,
        "precio": _num(g("precio")),
    }


def _coerce_deposito(mapeo: dict, fila_dict: dict) -> dict:
    g = lambda campo: fila_dict.get(mapeo.get(campo)) if mapeo.get(campo) else None
    return {
        "codigo": int(_num(g("codigo"))) if _num(g("codigo")) is not None else None,
        "producto": str(g("producto") or "").strip(),
        "ubicacion": str(g("ubicacion") or "").strip(),
        "lote": str(g("lote") or "").strip(),
        "vencimiento": str(g("vencimiento") or "").strip(),
        "cantidad": _num(g("cantidad")) or 0.0,
    }


def _coerce_logistica(mapeo: dict, fila_dict: dict) -> dict:
    g = lambda campo: fila_dict.get(mapeo.get(campo)) if mapeo.get(campo) else None
    return {
        "pedido": str(g("pedido") or "").strip(),
        "cliente": str(g("cliente") or "").strip(),
        "direccion": str(g("direccion") or "").strip(),
        "estado": str(g("estado") or "pendiente").strip(),
        "fecha_prevista": str(g("fecha_prevista") or "").strip(),
        "transporte": str(g("transporte") or "").strip(),
    }


def coerce_producto_odoo(p: dict) -> dict:
    return {
        "codigo": None,
        "descripcion": str(p.get("nombre") or "").strip(),
        "estado": "activo",
        "stock": p.get("stock") or 0.0,
        "costo_iva": None,
        "pvp": p.get("precio"),
        "venta_x_peso": False,
        "sku": p.get("codigo") or None,
        "source": "odoo",
        "source_id": str(p["id"]),
    }


def coerce_proveedor_odoo(p: dict) -> dict:
    return {
        "nombre": str(p.get("nombre") or "").strip(),
        "contacto": "",
        "telefono": p.get("telefono") or "",
        "email": p.get("email") or "",
        "notas": "",
        "cuit": p.get("cuit") or "",
        "source": "odoo",
        "source_id": str(p["id"]),
    }


def _analizar_proveedores(filas: list[dict], lang: str | None = None) -> list[dict]:
    from . import proveedores as proveedores_mod
    existentes = {_norm(p["nombre"]) for p in proveedores_mod.listar() if not p.get("source")}
    dups = [i for i, f in enumerate(filas) if _norm(f["nombre"]) in existentes]
    if not dups:
        return []
    return [{
        "id": "duplicado", "tipo": "duplicado",
        "titulo": _t("core.staging.obs_duplicado", lang),
        "descripcion": f"{len(dups)} proveedores parecen ya existir en tu sistema con el mismo nombre.",
        "items": len(dups), "indices": dups, "impacto_pesos": 0,
        "opciones": [{"label": "No agregarlos (ya existen)", "accion": "unificar", "params": {}},
                     {"label": "Agregarlos igual (son distintos)", "accion": "mantener", "params": {}}],
        "resuelta": False, "resolucion": None,
    }]


def coerce_cliente_odoo(c: dict) -> dict:
    return {
        "id": f"odoo-{c['id']}",
        "nombre": str(c.get("nombre") or "").strip(),
        "saldo": 0, "limite_credito": 0, "plazo_dias": 30,
        "dias_sin_pagar": 0, "promedio_pago_dias": None,
        "vat": c.get("cuit") or "", "city": c.get("localidad") or "",
        "phone": c.get("telefono") or "", "email": c.get("email") or "",
        "source": "odoo", "source_id": str(c["id"]),
    }


def _analizar_clientes(filas: list[dict], lang: str | None = None) -> list[dict]:
    from . import cuentas as cuentas_mod
    existentes = {_norm(c["nombre"]) for c in cuentas_mod.listar() if not c.get("source")}
    dups = [i for i, f in enumerate(filas) if _norm(f["nombre"]) in existentes]
    if not dups:
        return []
    return [{
        "id": "duplicado", "tipo": "duplicado",
        "titulo": _t("core.staging.obs_duplicado", lang),
        "descripcion": f"{len(dups)} clientes parecen ya existir en tu sistema con el mismo nombre.",
        "items": len(dups), "indices": dups, "impacto_pesos": 0,
        "opciones": [{"label": "No agregarlos (ya existen)", "accion": "unificar", "params": {}},
                     {"label": "Agregarlos igual (son distintos)", "accion": "mantener", "params": {}}],
        "resuelta": False, "resolucion": None,
    }]


_ESTADO_ORDEN_COMPRA_ODOO = {
    "borrador": "borrador", "enviada": "borrador",
    "confirmada": "aprobada", "cerrada": "recibida", "cancelada": "cancelada",
}


def coerce_orden_compra_odoo(o: dict) -> dict:
    estado_odoo = o.get("estado") or "borrador"
    return {
        "numero": o.get("numero") or "",
        "proveedor": o.get("proveedor") or "",
        "fecha": o.get("fecha") or "",
        "total": o.get("total") or 0,
        "items": o.get("items") or [],
        "estado": _ESTADO_ORDEN_COMPRA_ODOO.get(estado_odoo, "borrador"),
        "source": "odoo",
        "source_id": str(o["id"]),
        "source_status": estado_odoo,
    }


def _analizar_ordenes_compra(filas: list[dict], lang: str | None = None) -> list[dict]:
    # No duplicate heuristic: an Odoo purchase order never collides by name
    # with a hand-entered one — Odoo's own id (source_id) is already the key,
    # and crear_batch_odoo only ever receives rows that are not linked yet.
    return []


# ---------------------------------------------------------------------------
# P24·G4 — la pantalla de revisión habla el idioma del USUARIO QUE MIRA, no el
# del que creó el batch: descripciones y opciones se re-localizan AL LEER, por
# el `tipo` estable de cada observación (los textos guardados quedan de
# fallback para formatos viejos). Barrido completo, ambos idiomas.
# ---------------------------------------------------------------------------

_DESC_KEY = {
    ("deposito", "producto_inexistente"): "core.staging.d_prod_inexistente_dep",
    ("deposito", "lote_vencido"): "core.staging.d_lote_vencido",
    ("logistica", "entrega_atrasada"): "core.staging.d_entrega_atrasada",
    ("logistica", "sin_cliente"): "core.staging.d_sin_cliente",
    ("venta", "producto_inexistente"): "core.staging.d_prod_inexistente_ventas",
    ("*", "numero_ambiguo"): "core.staging.d_numero_ambiguo",
    ("*", "precio_perdida"): "core.staging.d_precio_perdida",
    ("*", "sin_precio"): "core.staging.d_sin_precio",
    # Odoo-sourced cliente/proveedor batches reuse the "duplicado" card, so
    # they need their own noun — otherwise the generic ("*", "duplicado")
    # entry re-localizes them as "N products …" on read.
    ("cliente", "duplicado"): "core.staging.d_duplicado_clientes",
    ("proveedor", "duplicado"): "core.staging.d_duplicado_proveedores",
    ("*", "duplicado"): "core.staging.d_duplicado",
    ("*", "stock_outlier"): "core.staging.d_stock_outlier",
}

_OPCION_KEY = {
    ("producto_inexistente", "unificar"): "core.staging.op_descartar",
    ("producto_inexistente", "mantener"): "core.staging.op_integrar_igual",
    ("lote_vencido", "confirmar"): "core.staging.op_integrar_revisar",
    ("lote_vencido", "unificar"): "core.staging.op_descartar",
    ("entrega_atrasada", "confirmar"): "core.staging.op_integrar_alertar",
    ("sin_cliente", "unificar"): "core.staging.op_descartar",
    ("sin_cliente", "mantener"): "core.staging.op_integrar_igual",
    ("numero_ambiguo", "interpretar_miles"): "core.staging.op_miles",
    ("numero_ambiguo", "interpretar_decimal"): "core.staging.op_decimales",
    ("precio_perdida", "set_margen"): "core.staging.op_margen",
    ("sin_precio", "set_margen"): "core.staging.op_margen_costo",
    ("sin_precio", "mantener"): "core.staging.op_dejar_sin_precio",
    ("duplicado", "unificar"): "core.staging.op_no_agregar",
    ("duplicado", "mantener"): "core.staging.op_agregar_igual",
    ("stock_outlier", "confirmar"): "core.staging.op_dejarlo",
}


def localizar_batch(b: dict, lang: str | None = None) -> dict:
    """Devuelve una COPIA del batch con descripciones/opciones en `lang`."""
    import copy
    out = copy.deepcopy(b)
    tipo_dato = out.get("tipo") or "*"
    for o in out.get("observaciones", []):
        key = _DESC_KEY.get((tipo_dato, o.get("tipo"))) or _DESC_KEY.get(("*", o.get("tipo")))
        if key:
            o["descripcion"] = _t(key, lang, n=o.get("items", 0), umbral=f"{OUTLIER_STOCK:,}")
        for op in o.get("opciones", []):
            ok = _OPCION_KEY.get((o.get("tipo"), op.get("accion")))
            if ok:
                op["label"] = _t(ok, lang, margen=(op.get("params") or {}).get("margen", ""))
    return out


def _analizar_deposito(filas: list[dict], lang: str | None = None) -> list[dict]:
    """Lo que no cierra en un export de depósito: referencias rotas y lotes vencidos."""
    obs = []
    val = esquema.validar_referencias_producto(filas)
    if val["huerfanas"]:
        obs.append({
            "id": "producto_inexistente", "tipo": "producto_inexistente",
            "titulo": _t("core.staging.obs_producto_inexistente_deposito", lang),
            "descripcion": f"{len(val['huerfanas'])} lotes referencian un producto que no existe en "
                           f"tu inventario. No los integro a ciegas: ¿faltan dar de alta o son "
                           f"códigos viejos del depósito?",
            "items": len(val["huerfanas"]), "indices": val["huerfanas"], "impacto_pesos": 0,
            "opciones": [{"label": "Descartar esos lotes", "accion": "unificar", "params": {}},
                         {"label": "Integrarlos igual", "accion": "mantener", "params": {}}],
            "resuelta": False, "resolucion": None,
        })
    vencidos = [i for i, f in enumerate(filas)
                if (v := parse_fecha(f.get("vencimiento"))) and v < hoy()]
    if vencidos:
        obs.append({
            "id": "lote_vencido", "tipo": "lote_vencido",
            "titulo": _t("core.staging.obs_lote_vencido", lang),
            "descripcion": f"{len(vencidos)} lotes del archivo tienen el vencimiento pasado. "
                           f"Los integro igual para que quede el registro, pero conviene "
                           f"revisarlos físicamente y darlos de baja.",
            "items": len(vencidos), "indices": vencidos, "impacto_pesos": 0,
            "opciones": [{"label": "Integrarlos y revisarlos", "accion": "confirmar", "params": {}},
                         {"label": "Descartarlos", "accion": "unificar", "params": {}}],
            "resuelta": False, "resolucion": None,
        })
    return obs


def _analizar_logistica(filas: list[dict], lang: str | None = None) -> list[dict]:
    """Lo que no cierra en un export de envíos: entregas ya atrasadas y filas sin cliente."""
    obs = []
    atrasadas = [i for i, f in enumerate(filas)
                 if (v := parse_fecha(f.get("fecha_prevista"))) and v < hoy()
                 and "entregad" not in _norm(f.get("estado"))]
    if atrasadas:
        obs.append({
            "id": "entrega_atrasada", "tipo": "entrega_atrasada",
            "titulo": _t("core.staging.obs_entrega_atrasada", lang),
            "descripcion": f"{len(atrasadas)} entregas del archivo tienen la fecha prevista pasada "
                           f"y no figuran como entregadas. Las integro para que Ángela las alerte.",
            "items": len(atrasadas), "indices": atrasadas, "impacto_pesos": 0,
            "opciones": [{"label": "Integrarlas y alertar", "accion": "confirmar", "params": {}}],
            "resuelta": False, "resolucion": None,
        })
    sin_cliente = [i for i, f in enumerate(filas) if not f.get("cliente")]
    if sin_cliente:
        obs.append({
            "id": "sin_cliente", "tipo": "sin_cliente",
            "titulo": _t("core.staging.obs_sin_cliente", lang),
            "descripcion": f"{len(sin_cliente)} envíos llegan sin cliente asignado. "
                           f"Sin cliente no puedo responder «¿salió el pedido de X?».",
            "items": len(sin_cliente), "indices": sin_cliente, "impacto_pesos": 0,
            "opciones": [{"label": "Descartar esos envíos", "accion": "unificar", "params": {}},
                         {"label": "Integrarlos igual", "accion": "mantener", "params": {}}],
            "resuelta": False, "resolucion": None,
        })
    return obs


def _analizar_ventas(filas: list[dict], lang: str | None = None) -> list[dict]:
    """Integridad referencial: ventas que apuntan a un producto inexistente."""
    val = esquema.validar_integridad_ventas(filas)
    obs = []
    if val["huerfanas"]:
        obs.append({
            "id": "producto_inexistente", "tipo": "producto_inexistente",
            "titulo": _t("core.staging.obs_producto_inexistente_ventas", lang),
            "descripcion": f"{len(val['huerfanas'])} ventas referencian un producto que no existe en "
                           f"tu inventario. No las integro a ciegas: ¿son productos que faltan agregar "
                           f"o códigos viejos?",
            "items": len(val["huerfanas"]), "indices": val["huerfanas"], "impacto_pesos": 0,
            "opciones": [{"label": "Descartar esas ventas", "accion": "unificar", "params": {}},
                         {"label": "Integrarlas igual", "accion": "mantener", "params": {}}],
            "resuelta": False, "resolucion": None,
        })
    return obs


# Qué campo del CSV termina en qué clave de la fila coercionada, por tipo de dato
# (para aplicar la decisión del dueño sobre números ambiguos).
_COERCED_KEY = {
    "producto": {"codigo": "codigo", "stock": "stock", "costo": "costo_iva", "pvp": "pvp"},
    "venta": {"cantidad": "cantidad", "precio": "precio"},
    "deposito": {"codigo": "codigo", "cantidad": "cantidad"},
    "logistica": {},
}


def _card_numeros_ambiguos(ambiguos: list[dict], lang: str | None = None) -> dict:
    """Nivel 2: los números que el Nivel 1 NO quiso interpretar solo."""
    ejemplos = ", ".join(f"«{a['valor']}»" for a in ambiguos[:3])
    return {
        "id": "numero_ambiguo", "tipo": "numero_ambiguo",
        "titulo": _t("core.staging.obs_numero_ambiguo", lang),
        "descripcion": f"{len(ambiguos)} valores como {ejemplos} se pueden leer como miles "
                       f"(1.234 = mil doscientos treinta y cuatro) o como decimales (uno coma "
                       f"dos). No lo decido sola: elegí y los aplico a todos. Mientras tanto "
                       f"quedan sin valor — no invento números.",
        "items": len(ambiguos), "indices": sorted({a["fila"] for a in ambiguos}),
        "impacto_pesos": 0,
        "opciones": [{"label": "Son miles (1.234 = 1234)", "accion": "interpretar_miles", "params": {}},
                     {"label": "Son decimales (1.234 = 1,234)", "accion": "interpretar_decimal", "params": {}}],
        "resuelta": False, "resolucion": None,
    }


def _analizar(filas: list[dict], excluir_sin_precio: set | None = None,
              lang: str | None = None) -> list[dict]:
    existentes = {_norm(d["descripcion"]) for d in store.raw_actual()}
    excluir_sin_precio = excluir_sin_precio or set()
    obs = []

    def card(tipo, titulo, descripcion, idxs, opciones):
        impacto = round(sum((filas[i].get("stock") or 0) * (filas[i].get("costo_iva") or 0) for i in idxs), 2)
        return {"id": tipo, "tipo": tipo, "titulo": titulo, "descripcion": descripcion,
                "items": len(idxs), "indices": idxs, "impacto_pesos": impacto,
                "opciones": opciones, "resuelta": False, "resolucion": None}

    perdida = [i for i, f in enumerate(filas) if f.get("costo_iva") and f.get("pvp") and f["costo_iva"] > f["pvp"]]
    if perdida:
        obs.append(card("precio_perdida", _t("core.staging.obs_precio_perdida", lang),
                        f"{len(perdida)} productos tienen el costo más alto que el precio de venta. "
                        f"En el Excel esto pasa desapercibido.", perdida,
                        [{"label": "Poner margen del 30%", "accion": "set_margen", "params": {"margen": 30}},
                         {"label": "Margen del 40%", "accion": "set_margen", "params": {"margen": 40}}]))

    # Los ambiguos del Nivel 1 no cuentan como "sin precio": tienen precio, sólo
    # que espera la interpretación del dueño (card numero_ambiguo).
    sin_precio = [i for i, f in enumerate(filas)
                  if not f.get("pvp") and i not in excluir_sin_precio]
    if sin_precio:
        obs.append(card("sin_precio", _t("core.staging.obs_sin_precio", lang),
                        f"{len(sin_precio)} productos llegan sin precio. ¿Les pongo uno según el costo?",
                        sin_precio,
                        [{"label": "Margen del 30% sobre el costo", "accion": "set_margen", "params": {"margen": 30}},
                         {"label": "Dejarlos sin precio por ahora", "accion": "mantener", "params": {}}]))

    dups = [i for i, f in enumerate(filas) if _norm(f["descripcion"]) in existentes]
    if dups:
        obs.append(card("duplicado", _t("core.staging.obs_duplicado", lang),
                        f"{len(dups)} productos parecen ya existir en tu sistema con el mismo nombre.",
                        dups,
                        [{"label": "No agregarlos (ya existen)", "accion": "unificar", "params": {}},
                         {"label": "Agregarlos igual (son distintos)", "accion": "mantener", "params": {}}]))

    outliers = [i for i, f in enumerate(filas) if (f.get("stock") or 0) > OUTLIER_STOCK]
    if outliers:
        obs.append(card("stock_outlier", _t("core.staging.obs_stock_outlier", lang),
                        f"{len(outliers)} productos tienen un stock muy alto (más de {OUTLIER_STOCK:,} u). "
                        f"¿Es correcto o hay un error de tipeo?".replace(",", "."), outliers,
                        [{"label": "Está bien, dejarlo", "accion": "confirmar", "params": {}}]))

    obs.sort(key=lambda o: o["impacto_pesos"], reverse=True)
    return obs


def _coerce_y_analizar(tipo: str, headers: list[str], cuerpo: list[list],
                       ambiguos: list[dict] | None = None,
                       lang: str | None = None):
    """Del CSV crudo a filas canónicas + observaciones (Nivel 2). Se usa al crear
    el batch y al revertir la normalización (misma lógica, un solo lugar)."""
    ambiguos = ambiguos or []
    if tipo == "venta":
        mapeo = importer.inferir_mapeo(headers, "venta_historica")["mapeo"]
        filas = [_coerce_venta(mapeo, dict(zip(headers, r))) for r in cuerpo]
        filas = [f for f in filas if f["producto"]]
        observaciones = _analizar_ventas(filas, lang)
    elif tipo == "deposito":
        mapeo = importer.inferir_mapeo(headers, "deposito")["mapeo"]
        filas = [_coerce_deposito(mapeo, dict(zip(headers, r))) for r in cuerpo]
        filas = [f for f in filas if f["producto"] or f["codigo"] is not None]
        observaciones = _analizar_deposito(filas, lang)
    elif tipo == "logistica":
        mapeo = importer.inferir_mapeo(headers, "logistica")["mapeo"]
        filas = [_coerce_logistica(mapeo, dict(zip(headers, r))) for r in cuerpo]
        filas = [f for f in filas if f["cliente"] or f["pedido"]]
        observaciones = _analizar_logistica(filas, lang)
    else:
        tipo = "producto"
        mapeo = importer.inferir_mapeo(headers, "producto")["mapeo"]
        filas = [_coerce_producto(mapeo, dict(zip(headers, r))) for r in cuerpo]
        filas = [f for f in filas if f["descripcion"]]
        # las filas con precio ambiguo no son "sin precio": esperan al dueño
        pvp_header = mapeo.get("pvp")
        excluir = {a["fila"] for a in ambiguos if a["columna"] == pvp_header}
        observaciones = _analizar(filas, excluir_sin_precio=excluir, lang=lang)
    if ambiguos:
        observaciones.insert(0, _card_numeros_ambiguos(ambiguos, lang))
    return tipo, mapeo, filas, observaciones


def crear_batch(nombre: str, csv_texto: str, lang: str | None = None) -> dict:
    rows = list(csv.reader(io.StringIO(csv_texto)))
    if not rows:
        raise ValueError("El archivo está vacío.")
    headers = [str(c) for c in rows[0]]
    deteccion = esquema.detectar_tipo(headers)
    tipo = deteccion["tipo"]
    cuerpo = [r for r in rows[1:] if any(r)]

    # NIVEL 1 — normalización automática al entrar: sólo lo que no altera el
    # significado comercial, con registro reversible y resumen visible. Lo
    # ambiguo NO se toca: baja al Nivel 2 como card para el dueño.
    cuerpo_original = [list(r) for r in cuerpo]
    cuerpo, norm = normalizacion.normalizar_tabla(headers, cuerpo)
    hubo_nivel1 = bool(norm["total_cambios"] or norm["ambiguos"])
    if norm["total_cambios"]:
        store.audit.record(
            actor="sistema", accion="normalizacion_nivel1",
            antes={"archivo": nombre},
            despues={"cambios": norm["total_cambios"], "filas": norm["filas_afectadas"],
                     "por_regla": norm["por_regla"], "ambiguos": len(norm["ambiguos"])})

    tipo, mapeo, filas, observaciones = _coerce_y_analizar(tipo, headers, cuerpo,
                                                           norm["ambiguos"], lang)

    batch = {
        "id": "b" + secrets.token_hex(3),
        "nombre": nombre,
        "fecha": datetime.datetime.now().isoformat(timespec="seconds"),
        "estado": "revision",
        "tipo": tipo,
        "plan": esquema.plan_integracion(tipo, lang),
        "mapeo": mapeo,
        "filas": filas,
        "observaciones": observaciones,
        # Nivel 1: el registro completo (reversible) + el crudo original.
        "normalizaciones": {
            "total_cambios": norm["total_cambios"],
            "filas_afectadas": norm["filas_afectadas"],
            "por_regla": norm["por_regla"],
            "cambios": norm["cambios"][:200],  # detalle visible, acotado
            "resumen": normalizacion.resumen_en_criollo(norm, lang),
        } if hubo_nivel1 else None,
        "ambiguos": norm["ambiguos"],
        "crudo": {"headers": headers, "filas": cuerpo_original} if hubo_nivel1 else None,
    }
    batches = _load()
    batches.append(batch)
    _save(batches)
    # Evento "llegó un archivo/remito": dispara los recordatorios que lo esperaban
    # ("cuando llegue un remito de X, avisame"). Best-effort: no frena la carga.
    try:
        recordatorios.evento_batch(tipo, nombre)
    except Exception:
        pass
    return _resumen(batch)


def _resumen(batch: dict) -> dict:
    return {
        "id": batch["id"], "nombre": batch["nombre"], "fecha": batch["fecha"],
        "estado": batch["estado"], "total_filas": len(batch["filas"]),
        "tipo": batch.get("tipo", "producto"), "plan": batch.get("plan"),
        "observaciones": batch["observaciones"],
        "resueltas": sum(1 for o in batch["observaciones"] if o["resuelta"]),
        "normalizaciones": batch.get("normalizaciones"),
    }


def listar() -> list[dict]:
    return [_resumen(b) for b in _load()]


def _find(batches, batch_id):
    return next((b for b in batches if b["id"] == batch_id), None)


def resolver(batch_id: str, obs_id: str, accion: str, params: dict | None = None) -> dict:
    params = params or {}
    batches = _load()
    b = _find(batches, batch_id)
    if not b:
        raise KeyError("batch inexistente")
    obs = next((o for o in b["observaciones"] if o["id"] == obs_id), None)
    if not obs:
        raise KeyError("observación inexistente")

    if accion in ("interpretar_miles", "interpretar_decimal"):
        # La decisión del dueño sobre los números ambiguos del Nivel 1: recién acá
        # el valor se escribe (con su interpretación explícita), nunca antes.
        inv_mapeo = {v: k for k, v in (b.get("mapeo") or {}).items() if v}
        claves = _COERCED_KEY.get(b.get("tipo", "producto"), {})
        for a in b.get("ambiguos", []):
            campo = inv_mapeo.get(a["columna"])
            clave = claves.get(campo)
            if not clave or a["fila"] >= len(b["filas"]):
                continue
            crudo = a["valor"].replace("$", "").replace(" ", "")
            valor = float(crudo.replace(".", "")) if accion == "interpretar_miles" else float(crudo)
            b["filas"][a["fila"]][clave] = valor
    else:
        for i in obs["indices"]:
            f = b["filas"][i]
            if accion == "set_margen" and f.get("costo_iva"):
                f["pvp"] = round(f["costo_iva"] * (1 + params.get("margen", 30) / 100), 2)
            elif accion == "unificar":
                f["_descartar"] = True
            elif accion == "corregir" and "valor" in params:
                f["stock"] = _num(params["valor"]) or 0
            # "mantener"/"confirmar": no cambia el dato
    obs["resuelta"] = True
    obs["resolucion"] = accion
    _save(batches)
    return _resumen(b)


def preview(batch_id: str) -> dict:
    b = _find(_load(), batch_id)
    if not b:
        raise KeyError("batch inexistente")
    a_integrar = [f for f in b["filas"] if not f.get("_descartar")]
    cambios = []
    for o in b["observaciones"]:
        if o["resuelta"] and o["resolucion"] not in (None, "mantener", "confirmar"):
            cambios.append(f"{o['titulo']}: {o['items']} resueltos ({o['resolucion']})")
    return {
        "id": b["id"], "a_integrar": len(a_integrar), "descartados": len(b["filas"]) - len(a_integrar),
        "cambios": cambios,
        "pendientes": [o["titulo"] for o in b["observaciones"] if not o["resuelta"]],
    }


def integrar(batch_id: str, actor: str = "dueño", lang: str | None = None) -> dict:
    batches = _load()
    b = _find(batches, batch_id)
    if not b:
        raise KeyError("batch inexistente")
    tipo = b.get("tipo", "producto")
    a_integrar = [f for f in b["filas"] if not f.get("_descartar")]

    if tipo == "proveedor" and b.get("fuente") == "odoo":
        from . import proveedores as proveedores_mod
        res = proveedores_mod.upsert_desde_conector(a_integrar, actor)
        batches = [x for x in batches if x["id"] != batch_id]
        _save(batches)
        return {"ok": True, "nuevos": res["nuevos"], "tipo": tipo,
                "mensaje": f"{res['nuevos']} proveedores nuevos, {res['actualizados']} actualizados."}

    if tipo == "cliente" and b.get("fuente") == "odoo":
        from core.db import customer_accounts_repo
        for f in a_integrar:
            customer_accounts_repo.upsert_account(_tenant_id_actual(), f)
        batches = [x for x in batches if x["id"] != batch_id]
        _save(batches)
        return {"ok": True, "nuevos": len(a_integrar), "tipo": tipo,
                "mensaje": f"{len(a_integrar)} clientes nuevos."}

    if tipo == "orden_compra" and b.get("fuente") == "odoo":
        from core.db import purchase_orders_repo
        tid = _tenant_id_actual()
        for f in a_integrar:
            purchase_orders_repo.upsert_from_odoo(tid, f)
        batches = [x for x in batches if x["id"] != batch_id]
        _save(batches)
        return {"ok": True, "nuevos": len(a_integrar), "tipo": tipo,
                "mensaje": f"{len(a_integrar)} órdenes de compra nuevas."}

    if tipo != "producto":
        # Generic CSV/apartado path (ventas, depósito, logística, …): creates
        # the apartado and wires up its relations. Odoo-sourced batches never
        # reach here — they early-return in the branches above.
        res = esquema.crear_apartado(tipo, a_integrar)
        plan = b.get("plan", {})
        store.audit.record(actor=actor, accion="crear_apartado",
                           antes={"batch": b["nombre"]}, despues={"tipo": tipo, "nuevas": res["nuevas"]})
        batches = [x for x in batches if x["id"] != batch_id]
        _save(batches)
        activado = ""
        if plan.get("activa"):
            activado = _t("core.staging.integrar_activa", lang,
                          lista=", ".join(plan["activa"]))
        rel = (_t("core.staging.integrar_rel", lang,
                  lista=_t("core.staging.join_y", lang).join(plan["relaciona_con"]))
               if plan.get("relaciona_con") else "")
        extra = ""
        if tipo == "venta":
            # EL VALIDADOR DE MONTOS: antes de mostrar cualquier número calculado
            # de estas ventas, el dueño confirma el total de un mes. Evita el error
            # de factor 1000 (total leído como precio unitario) en plena reunión.
            from . import ventas
            v = ventas.iniciar_validacion(lang)
            if v.get("estado") == "pendiente":
                extra = _t("core.staging.integrar_validador", lang, pregunta=v["pregunta"])
        return {"ok": True, "nuevos": res["nuevas"], "tipo": tipo, "apartado": plan.get("nombre", tipo),
                "mensaje": _t("core.staging.integrar_apartado", lang,
                              nombre=plan.get("nombre", tipo), n=res["nuevas"],
                              rel=rel, activado=activado, extra=extra)}

    # Products: they join the official inventory. Connector-sourced rows
    # (b["fuente"] == "odoo") go through upsert_desde_conector so they keep
    # sku/source/source_id; CSV-sourced rows follow the original path.
    raw = store.raw_actual()
    backup = store.versiones.save({"articulos": raw}, motivo=f"Backup antes de integrar «{b['nombre']}»", autor=actor)
    if b.get("fuente") == "odoo":
        for f in a_integrar:
            store.upsert_desde_conector(f, actor)
        nuevos = len(a_integrar)
    else:
        siguiente = max([d.get("codigo", 0) for d in raw] + [0]) + 1
        nuevos = 0
        for f in a_integrar:
            codigo = f["codigo"] or siguiente
            siguiente = max(siguiente, codigo) + 1
            inmov = round((f["stock"] or 0) * (f["costo_iva"] or 0), 2) if (f["stock"] or 0) > 0 else 0.0
            raw.append({
                "codigo": codigo, "descripcion": f["descripcion"], "estado": f.get("estado", "activo"),
                "stock": f["stock"], "costo_iva": f.get("costo_iva"), "pvp": f.get("pvp"),
                "venta_x_peso": f.get("venta_x_peso", False), "inmovilizado": inmov,
            })
            nuevos += 1
        store.guardar(raw)
    store.audit.record(actor=actor, accion="integrar_staging",
                       antes={"batch": b["nombre"]}, despues={"nuevos": nuevos, "version_backup": backup["id"]})
    batches = [x for x in batches if x["id"] != batch_id]
    _save(batches)
    return {"ok": True, "nuevos": nuevos, "version_backup": backup["id"],
            "mensaje": _t("core.staging.integrar_productos", lang, n=nuevos)}


def revertir_normalizacion(batch_id: str, actor: str = "dueño",
                           lang: str | None = None) -> dict:
    """Deshace el Nivel 1 completo del batch: re-procesa desde el crudo original
    (sin normalizar) y re-analiza. Automático nunca es irreversible."""
    batches = _load()
    b = _find(batches, batch_id)
    if not b:
        raise KeyError("batch inexistente")
    crudo = b.get("crudo")
    if not crudo:
        raise ValueError("Este batch no tiene normalizaciones para revertir.")
    tipo, mapeo, filas, observaciones = _coerce_y_analizar(
        b.get("tipo", "producto"), crudo["headers"], crudo["filas"], lang=lang)
    b.update({"tipo": tipo, "mapeo": mapeo, "filas": filas,
              "observaciones": observaciones, "normalizaciones": None,
              "ambiguos": [], "crudo": None})
    _save(batches)
    store.audit.record(actor=actor, accion="revertir_normalizacion_nivel1",
                       antes={"batch": b["nombre"]}, despues={"filas": len(filas)})
    return _resumen(b)


def descartar(batch_id: str) -> dict:
    batches = [x for x in _load() if x["id"] != batch_id]
    _save(batches)
    return {"ok": True}


_COERCERS_ODOO = {
    "producto": coerce_producto_odoo,
    "proveedor": coerce_proveedor_odoo,
    "cliente": coerce_cliente_odoo,
    "orden_compra": coerce_orden_compra_odoo,
}

# Which field makes a coerced row "usable", per tipo — an Odoo row missing it
# (e.g. a contact with no name) is dropped instead of creating an empty
# record; same criterion as the CSV filtering in _coerce_y_analizar
# (the "filas = [f for f in filas if f[...]]" lines).
_REQUERIDO_ODOO = {"producto": "descripcion", "proveedor": "nombre",
                    "cliente": "nombre", "orden_compra": "numero"}


def crear_batch_odoo(tipo: str, filas_odoo: list[dict], nombre: str | None = None,
                      lang: str | None = None) -> dict:
    """Like crear_batch(), but for rows that already arrive structured from a
    connector (Odoo) instead of a raw CSV: no parsing, no Nivel-1
    normalization (that exists for ambiguous hand-typed text; the connector
    already delivers correct types). It must only receive rows that are NOT
    linked yet — core/odoo_ingest.py filters out the ones whose source_id is
    already known, and those are updated directly without coming through
    here."""
    coerce = _COERCERS_ODOO[tipo]
    filas = [coerce(f) for f in filas_odoo]
    filas = [f for f in filas if f.get(_REQUERIDO_ODOO[tipo])]
    if tipo == "producto":
        observaciones = _analizar(filas)
    elif tipo == "proveedor":
        observaciones = _analizar_proveedores(filas, lang)
    elif tipo == "cliente":
        observaciones = _analizar_clientes(filas, lang)
    elif tipo == "orden_compra":
        observaciones = _analizar_ordenes_compra(filas, lang)
    else:
        raise ValueError(f"tipo sin coercer/analizador Odoo: {tipo}")
    batch = {
        "id": "b" + secrets.token_hex(3),
        "nombre": nombre or f"Odoo · {tipo}",
        "fecha": datetime.datetime.now().isoformat(timespec="seconds"),
        "estado": "revision",
        "tipo": tipo,
        "fuente": "odoo",
        "plan": esquema.plan_integracion(tipo, lang),
        "mapeo": {},
        "filas": filas,
        "observaciones": observaciones,
        "normalizaciones": None,
        "ambiguos": [],
        "crudo": None,
    }
    batches = _load()
    batches.append(batch)
    _save(batches)
    return _resumen(batch)

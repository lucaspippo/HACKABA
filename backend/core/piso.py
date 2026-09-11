"""
piso.py — lo que el empleado REPORTA desde el piso, y cómo eso se vuelve
inteligencia del negocio (P39·2 y P39·3).

El diferencial: hoy el de depósito dice "llegaron 8 cajas de aceite falladas y
las separé" en un grupo de WhatsApp y eso se pierde. Acá ese mismo dato ENTRA al
sistema: queda atribuido a la persona, el dueño lo ve en su panel, y Ángela lo
CRUZA con el stock y la orden de compra para proponerle al dueño el reclamo al
proveedor por la diferencia.

Regla de la casa, sin excepción: reportar NO modifica el stock ni el ERP. El
reporte es un hecho del piso; lo que sale de cruzarlo es una PROPUESTA que el
dueño aprueba o descarta. Ángela detecta y propone, nunca ejecuta sola.

Cinco cosas que el piso reporta, cada una con su acción en la vista del rol:
  · faltante   — diferencia/rotura al recibir o al entregar (depósito, reparto)
  · conteo     — conteo cíclico de un producto (depósito)
  · entrega    — confirmación de una parada de la ruta (reparto)
  · reposicion — pedido de mercadería de una sucursal al depósito central
  · pedido     — pedido levantado en la calle por el preventista

Un `pedido` acá NO es una orden de venta: la facturación sigue siendo del ERP.
Es el registro de que el preventista lo levantó, para que el dueño lo vea y
Ángela lo cruce — igual que el resto.

Todo se persiste en piso.json y se audita con el slug de su tipo, que es lo que
lee "qué resolvió esta semana" del panel del dueño (main._TRABAJO_EXTRA).
"""
from __future__ import annotations

import base64
import json
import os
import secrets

from . import fechas, paths
from .audit import AuditLog

PISO_JSON = os.path.join(paths.DATA_DIR, "piso.json")
# P41·4 — la PRUEBA de una entrega (foto del remito firmado, firma en pantalla).
# Mismo criterio que las fotos de perfil: archivo local, sin servicios externos.
ADJUNTOS_DIR = os.path.join(paths.DATA_DIR, "piso_adjuntos")
MAX_ADJUNTO_BYTES = 2_000_000
_audit = AuditLog(paths.DATA_DIR)

# tipo de reporte → slug de auditoría (el mismo que cuenta el panel del dueño)
ACCION = {
    "faltante": "reportar_faltante",
    "conteo": "marcar_conteo",
    "entrega": "confirmar_entrega",
    "reposicion": "pedir_reposicion",
    "pedido": "registrar_pedido",
}
TIPOS = tuple(ACCION)

# Motivos válidos de un faltante. Son IDs: el texto visible sale de i18n
# (core.piso.motivo_*), nunca se guarda traducido.
MOTIVOS = ("roto", "faltante", "vencido", "no_pedido")


def _load() -> list[dict]:
    try:
        with open(PISO_JSON, encoding="utf-8") as f:
            return json.load(f) or []
    except Exception:  # noqa: BLE001
        return []


def _save(items: list[dict]) -> None:
    os.makedirs(paths.DATA_DIR, exist_ok=True)
    with open(PISO_JSON, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)


def _ahora() -> str:
    import datetime
    return datetime.datetime.now().isoformat(timespec="seconds")


def _guardar_adjunto(rid: str, data_url: str) -> str:
    """La prueba de la entrega: data-URL → archivo local. Devuelve el nombre.

    No es decorativo: es lo que el repartidor muestra si un cliente dice que no
    recibió. Se guarda tal cual llegó, sin recomprimir, y se sirve por endpoint
    (nunca se devuelve el base64 en los listados: pesan y no se usan ahí)."""
    try:
        header, b64 = data_url.split(",", 1)
        ext = "png" if "png" in header else "jpg"
        crudo = base64.b64decode(b64)
    except Exception:  # noqa: BLE001
        raise ValueError("La prueba no llegó en un formato que entienda.")
    if not crudo:
        raise ValueError("La prueba llegó vacía.")
    if len(crudo) > MAX_ADJUNTO_BYTES:
        raise ValueError("La imagen es muy pesada (máximo 2 MB).")
    os.makedirs(ADJUNTOS_DIR, exist_ok=True)
    nombre = f"{rid}.{ext}"
    with open(os.path.join(ADJUNTOS_DIR, nombre), "wb") as f:
        f.write(crudo)
    return nombre


def adjunto_path(rid: str) -> str | None:
    """La ruta del archivo de prueba de un reporte (None si no tiene)."""
    r = next((x for x in _load() if x["id"] == rid), None)
    nombre = (r or {}).get("adjunto")
    if not nombre:
        return None
    path = os.path.join(ADJUNTOS_DIR, nombre)
    return path if os.path.exists(path) else None


# --- reportar (el empleado) -----------------------------------------------------

def reportar(tipo: str, actor: str, datos: dict | None = None) -> dict:
    """Guarda un hecho del piso. NO toca stock ni ERP — es un reporte, no un ajuste.

    `datos` cambia por tipo, pero todos comparten lo que hace falta para cruzar:
    codigo/producto cuando aplica, cantidad, y el texto libre de la persona.
    """
    if tipo not in TIPOS:
        raise ValueError(f"tipo de reporte desconocido: {tipo!r}")
    d = dict(datos or {})
    if tipo == "faltante":
        if not (d.get("producto") or d.get("codigo")):
            raise ValueError("Un faltante necesita el producto.")
        if (d.get("motivo") or "faltante") not in MOTIVOS:
            raise ValueError(f"motivo desconocido: {d.get('motivo')!r}")
        d.setdefault("motivo", "faltante")
    if tipo == "conteo" and d.get("contado") is None:
        raise ValueError("Un conteo necesita cuánto contaste.")
    if tipo in ("entrega", "pedido") and not d.get("cliente"):
        raise ValueError("Falta el cliente.")
    if tipo == "reposicion" and not (d.get("producto") or d.get("nota")):
        raise ValueError("Decí qué necesitás reponer.")

    # P41·4 — la PRUEBA de la entrega (foto del remito firmado o firma en
    # pantalla) viaja como data-URL en `datos.prueba`, se guarda como archivo y
    # NO queda dentro del reporte: en el JSON queda sólo el nombre del archivo.
    prueba = d.pop("prueba", None)

    rid = "p" + secrets.token_hex(3)
    r = {
        "id": rid,
        "tipo": tipo,
        "actor": actor,
        "cuando": _ahora(),
        "fecha": fechas.hoy().isoformat(),
        "estado": "nuevo",          # nuevo → resuelto (lo cierra el dueño)
        "datos": d,
    }
    if prueba:
        r["adjunto"] = _guardar_adjunto(rid, prueba)
    items = _load()
    items.append(r)
    _save(items)
    _audit.record(actor, ACCION[tipo], None,
                  {k: v for k, v in d.items() if k in
                   ("producto", "codigo", "cantidad", "contado", "motivo",
                    "cliente", "local", "nota")})
    return r


def listar(tipo: str | None = None, estado: str | None = None,
           actor: str | None = None) -> list[dict]:
    items = _load()
    if tipo:
        items = [r for r in items if r["tipo"] == tipo]
    if estado:
        items = [r for r in items if r["estado"] == estado]
    if actor:
        items = [r for r in items if r["actor"] == actor]
    return sorted(items, key=lambda r: r["cuando"], reverse=True)


def resolver(rid: str, actor: str, nota: str = "") -> dict:
    items = _load()
    r = next((x for x in items if x["id"] == rid), None)
    if not r:
        raise KeyError("reporte inexistente")
    r["estado"] = "resuelto"
    r["resuelto_por"] = actor
    r["resuelto"] = _ahora()
    if nota:
        r["nota_dueno"] = nota
    _save(items)
    _audit.record(actor, "resolver_reporte_piso",
                  antes={"reporte": rid, "tipo": r["tipo"]}, despues={"estado": "resuelto"})
    return r


# --- el cruce (Ángela) ----------------------------------------------------------

def _t(key: str, lang: str | None = None, **params) -> str:
    import i18n
    return i18n.t(key, lang, **params)


def _pesos(n, lang) -> str:
    import i18n
    return i18n.pesos(n or 0, lang)


def _nombre(username: str) -> str:
    """El nombre con el que la persona figura en el equipo (no su usuario): lo
    que el dueño lee es "Nahuel", no "nahuel"."""
    import auth
    return (auth.USUARIOS.get(username) or {}).get("nombre") or username


def _articulo(r: dict) -> dict | None:
    """El artículo del catálogo que matchea el reporte (por código o nombre)."""
    from . import store
    cod = (r.get("datos") or {}).get("codigo")
    nom = ((r.get("datos") or {}).get("producto") or "").strip().lower()
    for a in store.raw_actual():
        if cod is not None and a.get("codigo") == cod:
            return a
        if nom and (a.get("descripcion") or "").strip().lower() == nom:
            return a
    return None


def _orden_abierta(proveedor: str) -> dict | None:
    """La orden de compra abierta de ese proveedor (el remito cruza contra ella)."""
    from . import esquema
    for oc in esquema.filas("ordenes_compra"):
        if oc.get("estado") == "abierta" and (oc.get("proveedor") or "") == proveedor:
            return oc
    return None


def propuestas(lang: str | None = None) -> list[dict]:
    """P39·3 — lo que el equipo reportó, CRUZADO, convertido en decisiones para
    el dueño. Hoy: los faltantes sin resolver se agrupan por proveedor y salen
    como un reclamo con el monto real (cantidad × costo del catálogo) y, cuando
    existe, la orden de compra contra la que se controla.

    Sin faltantes no hay propuesta: la tarjeta no se fuerza nunca.
    """
    pendientes = [r for r in listar("faltante", estado="nuevo")]
    if not pendientes:
        return []

    por_prov: dict[str, dict] = {}
    for r in pendientes:
        a = _articulo(r)
        prov = (a or {}).get("proveedor") or _t("core.piso.prov_desconocido", lang)
        costo = (a or {}).get("costo_iva") or 0
        cant = float((r.get("datos") or {}).get("cantidad") or 0)
        g = por_prov.setdefault(prov, {"monto": 0.0, "items": [], "reportes": [],
                                       "actores": set()})
        g["monto"] += cant * costo
        g["reportes"].append(r["id"])
        g["actores"].add(r["actor"])
        g["items"].append({
            "nombre": (a or {}).get("descripcion") or (r["datos"].get("producto") or ""),
            "monto": round(cant * costo, 2) or None,
            "detalle": _t(f"core.piso.motivo_{r['datos'].get('motivo', 'faltante')}",
                          lang, n=f"{cant:g}"),
        })

    out = []
    for prov, g in sorted(por_prov.items(), key=lambda kv: -kv[1]["monto"]):
        oc = _orden_abierta(prov)
        quien = ", ".join(sorted(_nombre(a) for a in g["actores"]))
        n = len(g["reportes"])
        suf = "_1" if n == 1 else ""
        porque = [
            _t(f"core.piso.reclamo_q1{suf}", lang, quien=quien, n=n,
               proveedor=prov, monto=_pesos(g["monto"], lang)),
            _t("core.piso.reclamo_q2", lang),
        ]
        if oc:
            porque.append(_t("core.piso.reclamo_q3", lang, oc=oc.get("numero") or ""))
        out.append({
            "id": "reclamo_" + prov.lower().replace(" ", "_")[:24],
            "tipo": "reclamar",
            "titulo": _t("core.piso.reclamo_t", lang, proveedor=prov),
            "monto": round(g["monto"], 2),
            "resumen": _t(f"core.piso.reclamo_r{suf}", lang, n=n, quien=quien),
            "origen": "piso",
            "reportes": g["reportes"],
            "orden_compra": (oc or {}).get("numero"),
            "accion_chat": _t("core.piso.reclamo_chat", lang, proveedor=prov),
            "fuentes": [_t("core.piso.f_reportes", lang), _t("core.piso.f_stock", lang)]
                       + ([_t("core.piso.f_oc", lang)] if oc else []),
            "drill": {"porque": porque, "grafico": None, "involucrados": g["items"][:8],
                      "supuestos": [_t("core.piso.reclamo_s1", lang)]},
        })
    return out

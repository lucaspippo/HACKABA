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

Seis cosas que el piso reporta, cada una con su acción en la vista del rol:
  · faltante    — diferencia/rotura al recibir o al entregar (depósito, reparto)
  · conteo      — conteo cíclico de un producto (depósito)
  · entrega     — confirmación de una parada de la ruta (reparto)
  · reposicion  — pedido de mercadería de una sucursal al depósito central
  · pedido      — pedido levantado en la calle por el preventista, O por el
                  bot de WhatsApp de cara al cliente (ver `datos.canal`)
  · presupuesto — cotización que un cliente pidió por WhatsApp, sin
                  confirmar todavía compra

Un `pedido` acá NO es una orden de venta: la facturación sigue siendo del ERP.
Es el registro de que alguien (preventista, o el bot de WhatsApp hablando con
un cliente) lo levantó, para que el dueño lo vea y Ángela lo cruce — igual
que el resto. Un `presupuesto` es un escalón atrás: el cliente todavía está
decidiendo: nunca se etiqueta ni se cuenta como pedido en curso.

Todo se persiste en piso.json y se audita con el slug de su tipo, que es lo que
lee "qué resolvió esta semana" del panel del dueño (main._TRABAJO_EXTRA).
"""
from __future__ import annotations

import base64
import os
import secrets

from . import fechas, insight as ins, paths
from .audit import AuditLog

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
    "presupuesto": "registrar_presupuesto",
}
TIPOS = tuple(ACCION)

# Motivos válidos de un faltante. Son IDs: el texto visible sale de i18n
# (core.piso.motivo_*), nunca se guarda traducido.
MOTIVOS = ("roto", "faltante", "vencido", "no_pedido")

# Estados de un reporte. `visto` es el acuse, y existe porque sin él "no lo
# tomó nadie" y "lo tomó alguien y todavía no lo abrió" se leen igual desde el
# lado del que reportó — y esa diferencia es la que lo hace volver al WhatsApp.
ESTADOS = ("nuevo", "visto", "resuelto")

# A QUIÉN LE LLEGA CADA COSA, por OFICIO y no por nombre.
#
# Nadie en la cámara de frío tiene que elegir un destinatario de una lista de
# catorce nombres: Ángela propone y la persona confirma con un toque. Esto es
# la propuesta, y por eso es determinista y chica — el modelo no elige a quién
# le llega un reclamo de plata.
#
# El match es contra el TEXTO del rol, igual que lib/roles.js: una persona
# nueva con el mismo oficio hereda los avisos sin tocar código, y un tenant que
# nombre distinto sus puestos cae en el dueño en vez de romperse.
DESTINO = {
    "faltante": r"compras",
    "conteo": r"encargad[oa].*dep[oó]sito|jefe.*dep[oó]sito",
    "entrega": r"encargad[oa].*dep[oó]sito|jefe.*dep[oó]sito",
    "reposicion": r"encargad[oa].*dep[oó]sito|jefe.*dep[oó]sito",
    "pedido": r"administraci",
    "presupuesto": r"administraci",
}


def _load() -> list[dict]:
    from core.db import floor_reports_repo
    from core.db import tenant as _tenant
    return floor_reports_repo.list_all(_tenant.current_tenant_id())


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

def destinatario_sugerido(tipo: str) -> str | None:
    """El username que Ángela PROPONE para este tipo de aviso, o el dueño.

    Nunca se manda solo: el que reporta lo confirma o lo cambia. Si Ángela se
    equivoca y nadie lo ve, el aviso se muere en silencio y la persona no vuelve
    a usar la app — que es exactamente lo que pasaba cuando no había
    destinatario en absoluto.
    """
    import re
    import auth
    patron = DESTINO.get(tipo)
    gente = [(u, d) for u, d in auth.USUARIOS.items() if not d.get("interno")]
    if patron:
        for username, d in gente:
            if re.search(patron, d.get("rol") or "", re.I):
                return username
    # Sin nadie con ese oficio, el dueño. Es la única caída que no pierde el
    # aviso, y es honesta: alguien lo va a leer.
    return next((u for u, d in gente if d.get("es_admin")), None)


def reportar(tipo: str, actor: str, datos: dict | None = None,
             destinatario: str | None = None) -> dict:
    """Guarda un hecho del piso. NO toca stock ni ERP — es un reporte, no un ajuste.

    `datos` cambia por tipo, pero todos comparten lo que hace falta para cruzar:
    codigo/producto cuando aplica, cantidad, y el texto libre de la persona.

    `destinatario` es a quién le llega. Va explícito y no por default: lo elige
    quien reporta, confirmando lo que Ángela le propuso. Un reporte sin
    destinatario sigue siendo válido —es el pozo común de siempre, que el dueño
    ve— pero es el caso viejo, no el que la interfaz produce.
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
    if tipo in ("entrega", "pedido", "presupuesto") and not d.get("cliente"):
        raise ValueError("Falta el cliente.")
    if tipo == "presupuesto" and not d.get("items"):
        raise ValueError("Un presupuesto necesita al menos un producto.")
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
        "estado": "nuevo",          # nuevo → visto → resuelto
        "datos": d,
    }
    if destinatario:
        r["destinatario"] = destinatario
    if prueba:
        r["adjunto"] = _guardar_adjunto(rid, prueba)
    from core.db import floor_reports_repo
    from core.db import tenant as _tenant
    floor_reports_repo.create(_tenant.current_tenant_id(), r)
    _audit.record(actor, ACCION[tipo], None,
                  {k: v for k, v in d.items() if k in
                   ("producto", "codigo", "cantidad", "contado", "motivo",
                    "cliente", "local", "nota", "canal", "telefono", "items")})
    if destinatario:
        _avisar(destinatario, "piso.recibido", rid,
                quien=_nombre(actor), tipo=tipo)
    return r


def _avisar(para: str, clave: str, rid: str, **params) -> None:
    """Un evento por la campanita, sin que un fallo de entrega tire el reporte.

    El hecho ya está guardado cuando esto corre: si la notificación falla, se
    perdió el aviso, no el dato. Al revés sería inaceptable.
    """
    try:
        import i18n
        from . import notificaciones, perfiles
        lang = perfiles.idioma_de(para)
        notificaciones.emitir(
            para=para,
            titulo=i18n.t(clave + "_t", lang, **params),
            cuerpo=i18n.t(clave + "_c", lang, **params),
            tipo="piso_reporte", ref=rid)
    except Exception:  # noqa: BLE001 — la entrega nunca rompe el registro
        pass


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


def ver(rid: str, actor: str) -> dict:
    """El destinatario lo abrió. Esto es el acuse, y le vuelve al que reportó.

    Es la mitad más barata de todo el circuito y la que más cambia: "Celeste lo
    vio a las 9:31" es la diferencia entre haber cargado algo y haberlo tirado
    a un pozo.
    """
    from core.db import floor_reports_repo
    from core.db import tenant as _tenant
    previo = floor_reports_repo.get(_tenant.current_tenant_id(), rid)
    if previo is None:
        raise KeyError("reporte inexistente")
    r = floor_reports_repo.mark_seen(_tenant.current_tenant_id(), rid, actor,
                                     _ahora())
    # Sólo la primera vez: el aviso de "lo vieron" se manda una vez, y volver a
    # abrirlo no le llena la campanita al que reportó.
    if not previo.get("visto") and r.get("actor") != actor:
        _avisar(r["actor"], "piso.visto", rid, quien=_nombre(actor))
    return r


def resolver(rid: str, actor: str, nota: str = "") -> dict:
    """Se cerró. Y ACÁ VUELVE AL QUE LO ORIGINÓ, que es el punto donde este
    producto se gana o se pierde: sin el resultado de vuelta, el que reportó no
    confía y sigue preguntando por WhatsApp."""
    from core.db import floor_reports_repo
    from core.db import tenant as _tenant
    if floor_reports_repo.get(_tenant.current_tenant_id(), rid) is None:
        raise KeyError("reporte inexistente")
    r = floor_reports_repo.resolve(_tenant.current_tenant_id(), rid, actor,
                                    nota, _ahora())
    _audit.record(actor, "resolver_reporte_piso",
                  antes={"reporte": rid, "tipo": r["tipo"]}, despues={"estado": "resuelto"})
    if r.get("actor") != actor:
        _avisar(r["actor"], "piso.resuelto", rid, quien=_nombre(actor),
                nota=nota or "")
    return r


def mios(username: str, incluir_resueltos: bool = True) -> dict:
    """Lo que esta persona mandó y lo que le mandaron, separado.

    Las dos preguntas que se hace alguien del piso, y son distintas: "¿qué pasó
    con lo que dije?" y "¿qué está esperando por mí?".
    """
    todos = listar()
    return {
        "reporte": [r for r in todos if r["actor"] == username
                    and (incluir_resueltos or r["estado"] != "resuelto")],
        "me_mandaron": [r for r in todos if r.get("destinatario") == username
                        and r["actor"] != username
                        and (incluir_resueltos or r["estado"] != "resuelto")],
    }


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
            "codigo": (a or {}).get("codigo"),
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
        claim_method = {"key": "core.method.floor_report_claim",
                        "label": _t("core.method.floor_report_claim", lang)}
        evidence = [
            ins.records(
                "floor_reports", label=_t(f"core.piso.reclamo_r{suf}", lang, n=n, quien=quien),
                weight="primary", method=claim_method,
                rows=[ins.record(kind="product", id=it.get("codigo"), name=it["nombre"],
                                 amount=it["monto"], detail=it["detalle"])
                      for it in g["items"][:8]]),
        ]
        if oc:
            evidence.append(ins.metric(
                "purchase_order_check",
                label=_t("core.piso.reclamo_q3", lang, oc=oc.get("numero") or ""),
                value=None, unit=None, weight="supporting",
                method={"key": "core.method.floor_report_po_check",
                        "label": _t("core.method.floor_report_po_check", lang)}))
        insight_val = ins.build(
            # What the team reported, not a computed finding — a report is an
            # observation, so there's no hypothesis for it (see test below).
            pattern=ins.pattern(
                _t(f"core.piso.reclamo_q1{suf}", lang, quien=quien, n=n,
                   proveedor=prov, monto=_pesos(g["monto"], lang)),
                scope={"kind": "supplier", "count": 1}),
            evidence=evidence,
            assumptions=[ins.assumption(_t("core.piso.reclamo_s1", lang))],
            recommendation=ins.recommendation(
                detail=_t("core.piso.reclamo_q2", lang), navigate=None,
                chat=_t("core.piso.reclamo_chat", lang, proveedor=prov)),
        )
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
            "insight": insight_val,
        })
    return out

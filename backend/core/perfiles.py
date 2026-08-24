"""
Perfiles autoadministrados — el empleado describe, Ángela propone, el dueño decide.

Los usuarios base viven en auth.USUARIOS (el seed, en código). Acá vive el
ESTADO VIVO por usuario (data/perfiles.json):
  - descripcion propia (texto libre, editable por él mismo — scope usuario)
  - foto (archivo local en data/fotos/)
  - features_habilitadas / features_deshabilitadas (overrides que SOLO el dueño
    toca — scope organización; auth.perfil_publico() las mergea con la base)
  - solicitudes de módulos (pendiente → aprobada/rechazada, con motivo)

Las sugerencias de módulos son heurísticas por señales en castellano (mismo
patrón que esquema.py) — deterministas, gratis y testeables. Sólo proponen
módulos que EXISTEN en auth.MODULOS y que el usuario todavía no tiene.
# TODO IA: con la API key, refinar el matcheo con Claude para descripciones ambiguas.
"""
from __future__ import annotations

import base64
import datetime
import json
import os
import secrets
import unicodedata

from . import paths
from . import notificaciones

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = paths.DATA_DIR  # por-tenant: env POLPILOT_DATA_DIR o data/ (ver core/paths.py)
PERFILES_JSON = os.path.join(DATA_DIR, "perfiles.json")
FOTOS_DIR = os.path.join(DATA_DIR, "fotos")

# Señales → módulo sugerido, con el porqué en una línea (lo que ve el empleado).
# Las señales matchean POR PALABRA (prefijo con borde \b), nunca por substring:
# "venta" ya no dispara "vend", "proveedores grandes" del dueño no dispara
# administración. Sólo módulos operativos pedibles.
#
# P11·B5 — señal ambigua afuera: MENCIONAR una palabra no es HACER ese trabajo.
# "vencimientos de pago a proveedores" (administración) sugería Depósito;
# "el orden de los pasillos" sugería Documentos; "cargar los camiones" (armado
# de pedidos) sugería Logística al que no sigue entregas. Cada señal que queda
# apunta al TRABAJO del módulo, no a su vocabulario vecino: mejor sugerir menos
# que sugerir cualquier cosa.
SUGERENCIAS = [
    ("cuentas", ["cobr", "deud", "fiado", "fiar", "moroso", "credito",
                 "cuenta corriente", "cuentas corrientes"],
     "Describís cobranzas y seguimiento de deudas de clientes."),
    ("cobranzas", ["cobr", "preventista", "vendedor", "mostrador", "fiado"],
     "Trabajás cobrando a clientes en el día a día."),
    ("caja", ["caja", "arqueo", "efectivo"],
     "Mencionás el manejo de la caja diaria."),
    ("deposito", ["pallet", "picking", "recepcion", "lote"],
     "Describís trabajo de depósito: recepción, lotes y control físico."),
    ("logistica", ["reparto", "entrega", "chofer", "ruta", "envio"],
     "Mencionás reparto y seguimiento de entregas."),
    ("inventario", ["inventario", "gondola", "precio", "catalogo", "reposicion", "repongo"],
     "Trabajás con los productos y sus precios."),
    ("saneamiento", ["planilla", "excel", "corrig", "conteo", "duplicado"],
     "Mencionás trabajo con datos que hay que mantener limpios."),
    ("administracion", ["factura", "boleta", "oficina", "administra", "concili"],
     "Describís tareas administrativas y de oficina."),
    ("documentos", ["carta", "documento", "orden de pedido", "orden de compra",
                    "resumen ejecutivo", "presupuesto"],
     "Vas a necesitar generar documentos (órdenes, resúmenes)."),
    ("alertas", ["alerta", "vencimiento", "quiebre"],
     "Te sirven las alertas del negocio para lo que controlás."),
]

# Módulos que NO se sugieren si el usuario ya tiene la capacidad equivalente
# (cobranzas es la superficie mobile de cuentas; administración solapa caja+documentos).
_EQUIVALENTES = {
    "cobranzas": {"cuentas"},
    "administracion": {"caja", "documentos"},
    "cuentas": {"cobranzas"},
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def _ahora() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _load() -> dict:
    try:
        return json.load(open(PERFILES_JSON, encoding="utf-8"))
    except Exception:
        return {"usuarios": {}, "solicitudes": []}


def _save(d: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    json.dump(d, open(PERFILES_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def _audit(actor: str, accion: str, antes=None, despues=None) -> None:
    # Import perezoso para no crear ciclos (store importa medio mundo).
    from . import store
    store.audit.record(actor=actor, accion=accion, antes=antes, despues=despues)


def _u(d: dict, username: str) -> dict:
    return d["usuarios"].setdefault(username, {
        "descripcion": None, "foto": None, "idioma": None,
        "features_habilitadas": [], "features_deshabilitadas": [],
    })


def overrides(username: str) -> dict:
    """Lo que auth.perfil_publico() mergea sobre el seed."""
    return dict(_load()["usuarios"].get(username) or {})


# --- Fase B · perfil editable (scope usuario) ---------------------------------

def set_descripcion(username: str, texto: str) -> dict:
    d = _load()
    u = _u(d, username)
    # el override puede existir sin "descripcion" (p. ej. solo trae features):
    # setdefault no rellena claves de una entrada ya creada
    antes = u.get("descripcion")
    u["descripcion"] = (texto or "").strip()
    _save(d)
    _audit(username, "editar_descripcion_perfil",
           antes={"descripcion": antes}, despues={"descripcion": u["descripcion"]})
    return {"ok": True, "sugerencias": sugerir_modulos(username)}


def set_foto(username: str, data_url: str) -> dict:
    """Guarda la foto local (data-URL base64 → archivo). Simple, sin servicios."""
    try:
        header, b64 = data_url.split(",", 1)
        ext = "png" if "png" in header else "jpg"
        crudo = base64.b64decode(b64)
    except Exception:
        raise ValueError("La imagen no llegó en un formato que entienda.")
    if len(crudo) > 2_000_000:
        raise ValueError("La foto es muy pesada (máximo 2 MB).")
    os.makedirs(FOTOS_DIR, exist_ok=True)
    path = os.path.join(FOTOS_DIR, f"{username}.{ext}")
    # limpiar la extensión anterior si cambió
    for otra in ("png", "jpg"):
        viejo = os.path.join(FOTOS_DIR, f"{username}.{otra}")
        if otra != ext and os.path.exists(viejo):
            os.remove(viejo)
    open(path, "wb").write(crudo)
    d = _load()
    _u(d, username)["foto"] = f"{username}.{ext}"
    _save(d)
    _audit(username, "cambiar_foto_perfil", despues={"foto": f"{username}.{ext}"})
    return {"ok": True, "foto": f"{username}.{ext}"}


def foto_path(username: str) -> str | None:
    nombre = (_load()["usuarios"].get(username) or {}).get("foto")
    if not nombre:
        return None
    path = os.path.join(FOTOS_DIR, nombre)
    return path if os.path.exists(path) else None


# --- Idioma por usuario (scope usuario) ----------------------------------------
# UN solo lugar decide en qué idioma se le habla a cada persona: la web lo lee
# acá, y mañana WhatsApp (o cualquier canal) lo lee acá también, sin que la
# interfaz esté abierta. Si el usuario nunca eligió, rige el default del tenant.

def set_idioma(username: str, idioma: str) -> dict:
    idioma = (idioma or "").strip().lower()
    if idioma not in paths.IDIOMAS:
        raise ValueError(f"idioma desconocido: {idioma!r} (válidos: {', '.join(paths.IDIOMAS)})")
    d = _load()
    u = _u(d, username)
    antes = u.get("idioma")
    u["idioma"] = idioma
    _save(d)
    _audit(username, "cambiar_idioma", antes={"idioma": antes}, despues={"idioma": idioma})
    return {"ok": True, "idioma": idioma}


def idioma_de(username: str) -> str:
    """El idioma en que se le habla a este usuario, desde cualquier canal."""
    elegido = (_load()["usuarios"].get(username) or {}).get("idioma")
    return elegido if elegido in paths.IDIOMAS else paths.DEFAULT_LANG


# --- Fase C · Ángela sugiere módulos según la descripción ---------------------

def sugerir_modulos(username: str) -> list[dict]:
    """Módulos que le corresponderían según SU descripción real. Sólo módulos
    que existen y que le FALTAN; nunca inventa. Reglas duras:
      - Al dueño/admin no se le sugiere pedir nada: ya administra los módulos.
      - Matching por PALABRA (prefijo con borde), no substring.
      - No se sugiere un módulo si ya tiene la capacidad equivalente."""
    import re
    import auth
    base = auth.USUARIOS.get(username)
    if not base or base.get("es_admin"):
        return []
    ov = overrides(username)
    descripcion = ov.get("descripcion") or base.get("descripcion") or ""
    texto = _norm(descripcion)
    ya_tiene = set(features_efectivas(username))
    pendientes = {s["modulo"] for s in solicitudes(usuario=username, estado="pendiente")}
    out = []
    for modulo, senales, motivo in SUGERENCIAS:
        if modulo not in auth.MODULOS or modulo in ya_tiene or modulo in pendientes:
            continue
        if _EQUIVALENTES.get(modulo, set()) & ya_tiene:
            continue
        if any(re.search(rf"\b{re.escape(s)}", texto) for s in senales):
            out.append({"modulo": modulo, "label": auth.MODULOS[modulo], "motivo": motivo})
    return out


def features_efectivas(username: str) -> list[str]:
    """base del seed + habilitadas − deshabilitadas (el orden del seed primero)."""
    import auth
    base = list((auth.USUARIOS.get(username) or {}).get("features", []))
    ov = overrides(username)
    extra = [f for f in ov.get("features_habilitadas", []) if f not in base]
    quitadas = set(ov.get("features_deshabilitadas", []))
    return [f for f in base + extra if f not in quitadas]


# --- Fase D · solicitudes + notificación al dueño -----------------------------

def _dueno_username() -> str:
    import auth
    return next((u for u, v in auth.USUARIOS.items()
                 if v.get("es_admin") and not v.get("interno")), "emilio")


def crear_solicitud(username: str, modulo: str, motivo_angela: str = "",
                    motivo_empleado: str = "") -> dict:
    """El empleado PIDE acceso a un módulo que necesita para trabajar.
    `motivo_empleado` son SUS palabras (P39·1.2): el dueño decide con el porqué
    a la vista. `motivo_angela` es el matcheo por descripción, cuando lo hubo.
    Aprobarla tilda la celda en «Quién ve qué» (ver resolver_solicitud)."""
    import auth
    if modulo not in auth.MODULOS:
        raise ValueError(f"El módulo «{modulo}» no existe.")
    if modulo in features_efectivas(username):
        raise ValueError("Ese módulo ya lo tenés habilitado.")
    d = _load()
    if any(s["usuario"] == username and s["modulo"] == modulo and s["estado"] == "pendiente"
           for s in d["solicitudes"]):
        raise ValueError("Ya hay una solicitud pendiente por ese módulo.")
    s = {
        "id": "s" + secrets.token_hex(3),
        "usuario": username,
        "nombre": (auth.USUARIOS.get(username) or {}).get("nombre", username),
        "modulo": modulo,
        "label": auth.MODULOS[modulo],
        "motivo_angela": motivo_angela,
        "motivo_empleado": (motivo_empleado or "").strip(),
        "estado": "pendiente",
        "motivo_dueno": None,
        "creada": _ahora(),
        "resuelta": None,
    }
    d["solicitudes"].append(s)
    _save(d)
    _audit(username, "solicitar_modulo", despues={"modulo": modulo})
    # La notificación la emite PolPilot en nombre del sistema, no el empleado —
    # y le habla al RECEPTOR en su idioma (P8: la preferencia vive por usuario).
    import i18n
    dueno = _dueno_username()
    lang = idioma_de(dueno)
    label_mod = i18n.t(f"modulo.{modulo}", lang)
    cuerpo = (i18n.t("notif.solicitud_cuerpo_pedido", lang, nombre=s["nombre"],
                     label=label_mod, motivo=s["motivo_empleado"])
              if s["motivo_empleado"]
              else i18n.t("notif.solicitud_cuerpo", lang, nombre=s["nombre"],
                          label=label_mod))
    notificaciones.emitir(
        para=dueno,
        titulo=i18n.t("notif.solicitud_titulo", lang, nombre=s["nombre"]),
        cuerpo=cuerpo,
        tipo="solicitud_modulo", ref=s["id"],
    )
    return s


def solicitudes(usuario: str | None = None, estado: str | None = None) -> list[dict]:
    items = _load()["solicitudes"]
    if usuario:
        items = [s for s in items if s["usuario"] == usuario]
    if estado:
        items = [s for s in items if s["estado"] == estado]
    return sorted(items, key=lambda s: s["creada"], reverse=True)


def resolver_solicitud(sid: str, aprobar: bool, actor: str, motivo: str = "") -> dict:
    """SOLO la llama un endpoint/tool ya validado como dueño (scope organización)."""
    d = _load()
    s = next((x for x in d["solicitudes"] if x["id"] == sid), None)
    if not s:
        raise KeyError("solicitud inexistente")
    if s["estado"] != "pendiente":
        raise ValueError("Esa solicitud ya está resuelta.")
    s["estado"] = "aprobada" if aprobar else "rechazada"
    s["motivo_dueno"] = (motivo or "").strip() or None
    s["resuelta"] = _ahora()
    if aprobar:
        u = _u(d, s["usuario"])
        if s["modulo"] not in u["features_habilitadas"]:
            u["features_habilitadas"].append(s["modulo"])
        u["features_deshabilitadas"] = [f for f in u["features_deshabilitadas"] if f != s["modulo"]]
    _save(d)
    _audit(actor, "resolver_solicitud_modulo",
           antes={"solicitud": sid, "modulo": s["modulo"]},
           despues={"estado": s["estado"], "motivo": s["motivo_dueno"]})
    # La notificación sale en el idioma del DESTINATARIO y con el nombre del
    # dueño real del tenant (P9·C1): nada de "Emilio" para todos.
    import auth
    import i18n
    lang = idioma_de(s["usuario"])
    dueno = auth.nombre_dueno()
    detalle = i18n.t("notif.sol_motivo", lang, motivo=s["motivo_dueno"]) if s["motivo_dueno"] else ""
    estado_palabra = i18n.t(f"notif.sol_estado_{s['estado']}", lang)
    cuerpo_key = "notif.sol_cuerpo_aprobada" if aprobar else "notif.sol_cuerpo_rechazada"
    notificaciones.emitir(
        para=s["usuario"],
        titulo=i18n.t("notif.sol_titulo", lang, label=s["label"], estado=estado_palabra),
        cuerpo=i18n.t(cuerpo_key, lang, dueno=dueno, label=s["label"]) + detalle,
        tipo="solicitud_resuelta", ref=sid,
    )
    return s


# --- Fase E · matriz y cambio directo (scope organización, sólo dueño) --------

def set_feature(username: str, modulo: str, habilitar: bool, actor: str) -> dict:
    """Cambio directo del dueño (con o sin solicitud). El guard de rol vive en
    el endpoint/tool que llama; acá se persiste, audita y notifica."""
    import auth
    if modulo not in auth.MODULOS:
        raise ValueError(f"El módulo «{modulo}» no existe.")
    if username not in auth.USUARIOS:
        raise ValueError(f"El usuario «{username}» no existe.")
    d = _load()
    u = _u(d, username)
    antes = modulo in features_efectivas(username)
    if habilitar:
        if modulo not in u["features_habilitadas"]:
            u["features_habilitadas"].append(modulo)
        u["features_deshabilitadas"] = [f for f in u["features_deshabilitadas"] if f != modulo]
    else:
        u["features_habilitadas"] = [f for f in u["features_habilitadas"] if f != modulo]
        if modulo not in u["features_deshabilitadas"]:
            u["features_deshabilitadas"].append(modulo)
    _save(d)
    _audit(actor, "cambiar_modulo_empleado",
           antes={"usuario": username, "modulo": modulo, "habilitado": antes},
           despues={"habilitado": habilitar})
    # Idioma del destinatario + nombre del dueño real del tenant (P9·C1).
    import i18n
    lang = idioma_de(username)
    nombre_mod = auth.modulos_labels(lang).get(modulo, auth.MODULOS[modulo])
    sufijo = "on" if habilitar else "off"
    notificaciones.emitir(
        para=username,
        titulo=i18n.t(f"notif.mod_titulo_{sufijo}", lang, modulo=nombre_mod),
        cuerpo=i18n.t(f"notif.mod_cuerpo_{sufijo}", lang, dueno=auth.nombre_dueno(),
                      modulo=nombre_mod),
        tipo="modulo_cambiado",
    )
    return {"ok": True, "usuario": username, "modulo": modulo, "habilitado": habilitar}


def matriz() -> list[dict]:
    """Cada empleado × cada módulo (para el panel del dueño)."""
    import auth
    filas = []
    for username, v in auth.USUARIOS.items():
        if v.get("interno"):
            continue
        efectivas = set(features_efectivas(username))
        filas.append({
            "username": username, "nombre": v["nombre"], "rol": v["rol"],
            "es_admin": v.get("es_admin", False), "color": v.get("color"),
            "modulos": {m: (m in efectivas) for m in auth.MODULOS},
        })
    return filas

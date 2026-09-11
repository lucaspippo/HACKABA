"""
auth.py · Login y perfiles multi-usuario de PolPilot
====================================================
Cada persona de Horizonte entra con su usuario y ve SU PolPilot. La clave
conceptual: las features son MÓDULOS ACTIVABLES por usuario. Hoy el switch es
manual (lo seteamos por rol). Mañana Ángela lee la descripción del usuario y
activa/desactiva módulos sola — la personalización es por RESTA: todos parten
del sistema completo y se poda lo que cada rol no necesita.

# TODO FUTURO: personalización dinámica por IA.
#   usuario escribe descripción -> Ángela la interpreta -> setea features.
#   El mecanismo es el mismo; sólo cambia quién aprieta el switch.

Las contraseñas se guardan hasheadas (sha256). Los plaintext se generan una vez
y se le pasan a Lucas (no quedan en el repo en claro).
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import time

from core import paths as _paths

HERE = os.path.dirname(os.path.abspath(__file__))
# Credenciales POR TENANT: cada instancia (piloto/demo) tiene las suyas, en su
# directorio de datos. El piloto conserva el archivo histórico en backend/ para
# no invalidar las contraseñas que ya tiene Lucas.
CREDS_FILE = (os.path.join(HERE, "credenciales.json")
              if _paths.TENANT == "piloto"
              else os.path.join(_paths.DATA_DIR, "credenciales.json"))

# ---------------------------------------------------------------------------
# Catálogo maestro de MÓDULOS del sistema (el "PolPilot completo").
# Cada rol enciende un subconjunto. id -> etiqueta legible.
# ---------------------------------------------------------------------------
MODULOS = {
    "panel": "Panel principal",
    "mapa": "El mapa de tu negocio",
    "inventario": "Inventario inteligente",
    "saneamiento": "Saneamiento de datos",
    "finanzas": "Caja y finanzas",
    "cuentas": "Cuentas corrientes",
    "caja": "Caja diaria",
    "documentos": "Documentos",
    "alertas": "Alertas",
    "oportunidades": "Oportunidades",
    "equipo": "Mi equipo",
    "cargar": "Cargar datos",
    "gestion_equipo": "Gestión de equipo (maestro)",
    "cobranzas": "Cobranzas",
    "auditoria": "Registro de auditoría",
    "administracion": "Administración",
    "deposito": "Depósito",
    "logistica": "Logística y reparto",
    "evolucion": "Evolución (histórico ajustado por inflación)",
    "perfil": "Mi perfil",
    "angela": "Ángela",
    "admin_contexto": "Contexto externo (admin)",
}


def modulos_labels(lang: str | None = None) -> dict[str, str]:
    """Los labels de MODULOS en el idioma pedido. El dict MODULOS queda como está
    (es el default ES); acá se resuelve la traducción vía i18n ("modulo.<id>").
    Si a un módulo le falta la clave traducida, cae al label ES del seed —
    nunca muestra el key pelado."""
    import i18n
    lang = lang if lang in _paths.IDIOMAS else _paths.DEFAULT_LANG
    return {mid: (i18n.CATALOGO.get(f"modulo.{mid}", {}).get(lang) or label)
            for mid, label in MODULOS.items()}


def _hash(pw: str) -> str:
    # DEUDA (anotada 15/07/2026, P9·C6/M10): SHA-256 sin salt alcanza para el
    # piloto y el demo (passwords generadas, no elegidas por humanos), pero
    # ANTES del primer cliente nuevo esto pasa a bcrypt/argon2 con salt y se
    # dejan de guardar los plaintext en credenciales.json. Ver PENDIENTES.md.
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Usuarios precargados de Horizonte.
# Las contraseñas plaintext se generan abajo (generar_credenciales) y se le
# pasan a Lucas; acá guardamos sólo el hash.
# ---------------------------------------------------------------------------
USUARIOS = {
    "emilio": {
        "username": "emilio",
        "nombre": "Emilio",
        "rol": "Dueño",
        "es_admin": True,
        "telefono": "+5491100000001",  # WhatsApp: número → empleado → rol
        "color": "#e0241b",
        "superficies": ["desktop", "mobile"],
        "descripcion": (
            "Soy el dueño. Conduzco toda la operación de Horizonte: la distribuidora, "
            "los locales y las franquicias. Quiero dejar de operar y empezar a dirigir. "
            "Necesito ver la salud del negocio, la plata parada, las alertas y oportunidades, "
            "y qué está haciendo cada uno del equipo. Tengo que ver todo."
        ),
        "features": [
            "panel", "mapa", "inventario", "saneamiento", "finanzas", "cuentas", "caja", "deposito",
            "logistica", "evolucion", "alertas", "oportunidades", "equipo", "gestion_equipo",
            "cargar", "documentos", "cobranzas", "auditoria", "perfil", "angela",
        ],
    },
    "paula": {
        "username": "paula",
        "nombre": "Paula",
        "rol": "Administración",
        "es_admin": False,
        "telefono": "+5491100000002",  # WhatsApp: número → empleado → rol
        "color": "#e8a317",
        "superficies": ["desktop", "mobile"],
        "descripcion": (
            "Trabajo en la oficina. Cargo las boletas y las facturas de proveedores, armo las "
            "órdenes de compra y hago los cierres de caja diarios. Tengo que acordarme de "
            "reclamar lo que falta llegar de los proveedores y de las tareas administrativas. "
            "No me meto con la estrategia ni con la rentabilidad: eso es de Emilio."
        ),
        "features": ["administracion", "cuentas", "caja", "saneamiento", "alertas", "equipo", "perfil", "angela"],
    },
    "vendedor": {
        "username": "vendedor",
        "nombre": "Vendedor",
        "rol": "Ventas y cobranzas",
        "es_admin": False,
        "color": "#3e7d63",
        "superficies": ["mobile", "desktop"],
        "descripcion": (
            "Atiendo a mis clientes de la distribuidora y les cobro. Necesito saber a quién "
            "tengo que cobrarle hoy y cuánto, y hasta cuánto le puedo financiar a cada uno "
            "según su cuenta corriente. No necesito ver el inventario completo ni las finanzas "
            "de la empresa."
        ),
        # P9·C3 (M5): su trabajo declarado es cobrar — necesita `cuentas`
        # (los datos de deudores viven detrás de esa feature), igual que los
        # preventistas del demo (diego/lucia). `cobranzas` queda como su vista.
        "features": ["cobranzas", "cuentas", "perfil", "angela"],
    },
    "deposito": {
        "username": "deposito",
        "nombre": "Encargado de depósito",
        "rol": "Depósito",
        "es_admin": False,
        "color": "#15727e",
        "superficies": ["mobile", "desktop"],
        "descripcion": (
            "Estoy a cargo del depósito. Recibo la mercadería, controlo lo que entra y armo los "
            "pedidos. Tengo que evitar los quiebres de stock y que no se venza nada por mala "
            "rotación. Me sirve saber qué productos están mal cargados (fantasma o en negativo) "
            "para resolverlos físicamente. También sigo el reparto: qué camión sale y qué "
            "entregas quedan. No veo cobranzas ni finanzas."
        ),
        "features": ["deposito", "logistica", "perfil", "angela"],
    },
    "polpilot": {
        "username": "polpilot",
        "nombre": "Equipo PolPilot",
        "rol": "PolPilot",
        "es_admin": True,
        "interno": True,  # equipo PolPilot, no es staff de Horizonte
        "color": "#1b8190",
        "superficies": ["desktop"],
        "descripcion": "Equipo PolPilot. Carga el contexto externo (economía, legal, precios) "
                       "que alimenta a Ángela hasta conectar las APIs.",
        "features": ["admin_contexto", "angela", "perfil"],
    },
}

# El tenant demo (Distribuidora del Litoral, ficticia) usa SU equipo. El seed
# de Horizonte queda intacto arriba: sin env, nada cambia para el piloto.
if _paths.TENANT == "demo":
    from usuarios_demo import USUARIOS as _USUARIOS_DEMO
    USUARIOS = _USUARIOS_DEMO

# --- Antigüedad: quién recién entró (P·onboarding) ----------------------------
# La rotación en trabajo físico es alta y el que entra tarda semanas en aprender
# dónde está cada cosa. Que una persona sea NUEVA no es una etiqueta que alguien
# prende a mano: sale de su fecha de ingreso contra el "hoy" de referencia del
# sistema (congelado en el demo, real en el piloto). Sin `ingreso` en el perfil,
# no hay antigüedad y nada cambia — es aditivo para los 13 de siempre.
UMBRAL_NUEVO_DIAS = 90   # los primeros tres meses: el período de prueba real


def antiguedad(username: str) -> dict | None:
    """Cuánto hace que esta persona trabaja acá. None si no declara ingreso."""
    u = USUARIOS.get((username or "").strip().lower())
    if not u or not u.get("ingreso"):
        return None
    from core.fechas import hoy, parse_fecha
    ingreso = parse_fecha(u["ingreso"])
    if not ingreso:
        return None
    dias = max(0, (hoy() - ingreso).days)
    return {
        "ingreso": ingreso.isoformat(),
        "dias": dias,
        "semanas": dias // 7,
        "meses": dias // 30,
        "nuevo": dias <= UMBRAL_NUEVO_DIAS,
    }


def puesto(username: str) -> dict | None:
    """El detalle del puesto (sector, turno, contrato) con el MENTOR resuelto a
    una persona real del equipo — no un nombre suelto que puede no existir.

    Los campos con sufijo `_en` (sector_en, turno_en, contrato_en) viajan tal
    cual: la vista elige el idioma. El nombre del mentor NO se traduce."""
    u = USUARIOS.get((username or "").strip().lower())
    p = (u or {}).get("puesto")
    if not p:
        return None
    out = {k: v for k, v in p.items() if k != "mentor"}
    m = USUARIOS.get(p.get("mentor") or "")
    if m:
        out["mentor"] = {"username": m["username"], "nombre": m["nombre"], "rol": m["rol"]}
    return out


def dueno() -> dict:
    """El dueño del TENANT actual (emilio en el piloto, aldo en el demo).
    Para saludos, notificaciones y derivaciones — nada de nombres hardcodeados."""
    for u in USUARIOS.values():
        if u.get("rol") == "Dueño":
            return u
    return next(iter(USUARIOS.values()))


def nombre_dueno() -> str:
    return dueno()["nombre"]


# Hashes de contraseñas y plaintext (cargados/generados al iniciar).
_PASS_HASHES: dict[str, str] = {}
_PASS_PLAIN: dict[str, str] = {}

# Tokens de sesión en memoria, CON vencimiento (P9·C6, M10): token ->
# {username, expira}. TTL configurable por env (horas); un token vencido es
# un token que no existe. Default 12 h: cubre una jornada, no un mes.
TOKEN_TTL_SEGUNDOS = float(os.environ.get("POLPILOT_TOKEN_TTL_HORAS", "12")) * 3600
_SESIONES: dict[str, dict] = {}


def _purgar_sesiones() -> None:
    ahora = time.time()
    vencidos = [t for t, s in _SESIONES.items() if s["expira"] <= ahora]
    for t in vencidos:
        _SESIONES.pop(t, None)


def cargar_o_generar_credenciales() -> dict[str, str]:
    """
    Carga las credenciales del archivo local si existen (estables entre
    reinicios). Si no, las genera una vez y las guarda. Devuelve los plaintext
    para reportárselos a Lucas.
    """
    global _PASS_HASHES, _PASS_PLAIN
    if os.path.exists(CREDS_FILE):
        try:
            data = json.load(open(CREDS_FILE, encoding="utf-8"))
            _PASS_PLAIN = data.get("plain", {})
            _PASS_HASHES = {u: _hash(pw) for u, pw in _PASS_PLAIN.items()}
            # Cubrir usuarios nuevos que no estuvieran en el archivo viejo.
            faltan = [u for u in USUARIOS if u not in _PASS_PLAIN]
            if not faltan:
                return dict(_PASS_PLAIN)
        except Exception:
            pass

    palabras = ["pilar", "manteca", "cheddar", "fiambre", "remito", "gondola", "balanza"]
    for user in USUARIOS:
        if user in _PASS_PLAIN:
            continue
        pw = f"{secrets.choice(palabras)}-{secrets.randbelow(9000) + 1000}"
        _PASS_PLAIN[user] = pw
    _PASS_HASHES = {u: _hash(pw) for u, pw in _PASS_PLAIN.items()}
    try:
        json.dump({"plain": _PASS_PLAIN}, open(CREDS_FILE, "w", encoding="utf-8"), indent=2)
    except Exception:
        pass
    return dict(_PASS_PLAIN)


def credenciales_actuales() -> dict[str, str]:
    return dict(_PASS_PLAIN)


def perfil_publico(username: str, lang: str | None = None) -> dict | None:
    """El perfil visible de una persona. `idioma` es SIEMPRE el suyo (es su
    preferencia, y por ahí le habla Ángela). `lang` sólo cambia el idioma de los
    LABELS de módulos: cuando el dueño mira la ficha de un empleado, los módulos
    se leen en el idioma DEL QUE MIRA — un panel en español no puede listar
    "Main panel / Daily register" porque el otro tenga el suyo en inglés (P39·1)."""
    u = USUARIOS.get(username)
    if not u:
        return None
    # El seed vive en código; el estado vivo (descripción propia, foto, módulos
    # aprobados por el dueño) vive en core/perfiles.py y se mergea acá.
    from core import perfiles
    ov = perfiles.overrides(username)
    features = perfiles.features_efectivas(username)
    idioma = perfiles.idioma_de(username)
    labels = modulos_labels(lang or idioma)
    return {
        "username": u["username"],
        "nombre": u["nombre"],
        "rol": u["rol"],
        "es_admin": u["es_admin"],
        "interno": u.get("interno", False),
        "color": u["color"],
        "superficies": u["superficies"],
        "descripcion": ov.get("descripcion") or u["descripcion"],
        # La misma descripción en inglés, para que una pantalla en inglés no
        # muestre un párrafo en castellano. Viajan las DOS y la vista elige —
        # igual que el conocimiento del negocio y las notas del equipo.
        # None cuando la persona reescribió la suya: eso son SUS palabras, se
        # muestran tal cual las escribió y no se traducen a sus espaldas.
        "descripcion_en": None if ov.get("descripcion") else u.get("descripcion_en"),
        "foto": ov.get("foto"),
        "idioma": idioma,
        # P·onboarding — datos del vínculo laboral: cuánto hace que está (de ahí
        # el chip "Nuevo") y su puesto con mentor. None para quien no los declara.
        "antiguedad": antiguedad(username),
        "puesto": puesto(username),
        "features": features,
        "modulos_labels": {f: labels.get(f, MODULOS.get(f, f)) for f in features},
    }


def login(username: str, password: str) -> dict | None:
    username = (username or "").strip().lower()
    u = USUARIOS.get(username)
    # Comparación en TIEMPO CONSTANTE y sin return temprano (P9·C6, M10): la
    # demora de la respuesta no revela si el usuario existe (enumeración por
    # timing). Usuario inexistente → se compara igual contra un hash señuelo.
    hash_guardado = _PASS_HASHES.get(username) or _hash("~~jamas-coincide~~")
    ok = secrets.compare_digest(hash_guardado, _hash(password or ""))
    if not (u and ok):
        return None
    _purgar_sesiones()
    token = secrets.token_urlsafe(24)
    _SESIONES[token] = {"username": username,
                        "expira": time.time() + TOKEN_TTL_SEGUNDOS}
    return {"token": token, "usuario": perfil_publico(username)}


def usuario_por_token(token: str) -> dict | None:
    s = _SESIONES.get(token or "")
    if not s:
        return None
    if s["expira"] <= time.time():  # vencido = inexistente (M10)
        _SESIONES.pop(token, None)
        return None
    return perfil_publico(s["username"])


def autologin_activo() -> bool:
    """Feature flag P11·B8: SOLO el tenant demo se levanta con
    POLPILOT_DEMO_AUTOLOGIN=1 — abrir la URL entra directo con la sesión del
    DUEÑO, sin pantalla de login (los partners de YC no pelean credenciales).
    En el piloto la var no existe: el endpoint da 404 y nada cambia."""
    return os.environ.get("POLPILOT_DEMO_AUTOLOGIN") == "1"


def role_switch_activo() -> bool:
    """Feature flag del "View as / Ver como" (P9·E) — SOLO el tenant demo se
    levanta con POLPILOT_DEMO_ROLE_SWITCH=1. En el piloto la var no existe:
    ni el botón ni el endpoint — un empleado real jamás se ve como el dueño.
    Se lee por llamada para que los tests lo mockeen sin reimportar."""
    return os.environ.get("POLPILOT_DEMO_ROLE_SWITCH") == "1"


def sesion_para(username: str) -> dict | None:
    """Emite una sesión LEGÍTIMA del usuario destino (mismo shape que login).
    La llama ÚNICAMENTE el endpoint /api/demo/ver-como, detrás del feature
    flag de tenant y de una sesión ya válida."""
    u = USUARIOS.get((username or "").strip().lower())
    if not u or u.get("interno"):
        return None
    _purgar_sesiones()
    token = secrets.token_urlsafe(24)
    _SESIONES[token] = {"username": u["username"],
                        "expira": time.time() + TOKEN_TTL_SEGUNDOS}
    return {"token": token, "usuario": perfil_publico(u["username"])}


def usuario_por_numero(telefono: str) -> dict | None:
    """WhatsApp: asocia un número de teléfono a su cuenta de empleado (con su rol).
    Lo que cada uno hace por WhatsApp queda trackeado con su cuenta."""
    tel = (telefono or "").strip()
    for u, v in USUARIOS.items():
        if v.get("telefono") == tel:
            return perfil_publico(u)
    return None


def listar_perfiles(lang: str | None = None) -> list[dict]:
    """Vista maestra (sólo el dueño): los perfiles del equipo del tenant
    (excluye usuarios internos de PolPilot). `lang` = idioma del que MIRA."""
    return [perfil_publico(u, lang) for u, v in USUARIOS.items() if not v.get("interno")]

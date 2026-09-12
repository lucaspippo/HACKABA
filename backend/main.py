"""
main.py · API REST de PolPilot (Sprint 0)
=========================================
Expone los datos del consolidado de Horizonte y el chat de Ángela.

Correr en local:
    cd backend
    uvicorn main:app --reload --port 8000

Endpoints:
    GET  /api/health                  estado del servicio
    GET  /api/inventario              resumen + alertas + top inmovilizado
    GET  /api/inventario/top?n=10     top productos por plata inmovilizada
    GET  /api/grupo/{nombre}          listado de un grupo de problemas
    GET  /api/buscar?q=texto          búsqueda de artículos
    POST /api/angela                  conversación con Ángela
    /mcp                              servidor MCP de sólo lectura para LLMs
                                       externos — ver mcp_server.py y MCP.md
"""

from __future__ import annotations

import json
import os
import sys
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

import angela
import auth
import authz
import config
import data_store as ds
import i18n
import mcp_server
from authz import (require_admin, require_all_features, require_any_feature,
                   require_feature, usuario_actual)
from core import (store, saneamiento, fase, memoria, importer, staging, anomalias,
                  organizacion, documentos, cuentas, caja, sync, conectores,
                  deposito, logistica, recordatorios, perfiles, notificaciones,
                  evolucion, ventas, pagos, paths, conocimiento, piso, onboarding,
                  whatsapp_channel, patrones, app_events)
import whatsapp_bot


def _lang(u: dict | None = None) -> str:
    """El idioma del usuario resuelto SERVER-SIDE (perfil → default del tenant).
    Sin usuario conocido (401 pre-sesión) rige el default del tenant."""
    return perfiles.idioma_de(u["username"]) if u else paths.DEFAULT_LANG


def _usuario_de(token: str) -> dict:
    """Sesión válida o 401. El username sale del token, nunca del body."""
    u = auth.usuario_por_token(token)
    if not u:
        raise HTTPException(status_code=401, detail=i18n.t("api.sesion_invalida"))
    return u


def _admin_de(token: str) -> dict:
    """Sólo el dueño (scope organización) o 403."""
    u = _usuario_de(token)
    if not u.get("es_admin"):
        raise HTTPException(status_code=403,
                            detail=i18n.t("authz.solo_dueno", _lang(u)))
    return u


@asynccontextmanager
async def lifespan(app: FastAPI):
    auth.cargar_o_generar_credenciales()
    # Los hashes viven en Postgres (auth_credentials); NUNCA se persiste el
    # plaintext. Un tenant sembrado por data-demo/seed_db.py usa la contraseña
    # fija de seed_db.demo_password() (POLPILOT_DEMO_PASSWORD, default
    # "demo-password") — es la que sirve para entrar en desarrollo.
    # cargar_o_generar_credenciales() sólo genera una al azar para el usuario
    # que TODAVÍA no tenga fila, y ese plaintext existe únicamente en memoria
    # de este proceso: POLPILOT_PRINT_CREDS=1 lo imprime.
    #
    # Sin `except: pass` a propósito. Este bloque tenía uno, y se tragó en
    # silencio un AttributeError (auth.CREDS_FILE, borrado al migrar las
    # credenciales a Postgres) durante meses: el mensaje de arranque no salía
    # nunca y la desincronización de contraseñas quedaba invisible.
    if os.environ.get("POLPILOT_PRINT_CREDS") == "1":
        creds = auth.credenciales_actuales()
        lineas = ["", "=== CREDENCIALES (solo con POLPILOT_PRINT_CREDS=1) ==="]
        for u, pw in creds.items():
            lineas.append(f"  {u:10s} -> {pw}")
        if not creds:
            lineas.append("  (ninguna generada en este proceso: todos los "
                          "usuarios ya tenían credencial)")
        lineas.append("=" * 51)
        print("\n".join(lineas), flush=True)
    else:
        generadas = len(auth.credenciales_actuales())
        print(f"[polpilot] credenciales hasheadas en Postgres (auth_credentials); "
              f"{generadas} generada(s) al azar en este arranque. Tenant sembrado "
              f"por seed_db: entrar con la contraseña fija "
              f"(POLPILOT_DEMO_PASSWORD). POLPILOT_PRINT_CREDS=1 para ver las "
              f"generadas.", flush=True)
    # P11·B4: precálculo de análisis al arrancar — la primera entrada a
    # Oportunidades/Alertas ya sale del cache (clave con YC en la URL pública).
    try:
        from core import analisis_cache
        analisis_cache.precalentar()
    except Exception:
        pass  # sin precalc el endpoint computa on-demand: nunca rompe el arranque
    # The MCP server (/mcp) needs its task group alive for the whole process
    # (StreamableHTTPSessionManager.run()) — nested here so it shares the
    # rest of the app's startup/shutdown lifecycle.
    async with mcp_server.session_manager.run():
        yield


app = FastAPI(title="PolPilot", version="0.2.0", lifespan=lifespan)

# El frontend (Vite) corre en otro puerto durante desarrollo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Read-only MCP server (Claude Desktop, claude.ai, any MCP client) — see
# mcp_server.py and MCP.md. Each request carries its own identity in
# Authorization: Bearer <token>; none of this goes through browser CORS
# (remote MCP clients call server-to-server), so it's kept separate from the
# middleware above.
app.mount("/mcp", mcp_server.mcp_asgi_app)


class ChatTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatTurn] | None = None
    token: str | None = None
    # rol/nombre stay ONLY for legacy compatibility (WhatsApp, tests): when a
    # token is present, identity comes from the token and these are IGNORED
    # (the role cannot be spoofed from the request). See /api/angela.
    rol: str | None = None
    nombre: str | None = None
    # Which surface this turn came from — for transcript tagging only (see
    # core/angela_transcripts.py); never changes how the turn is answered.
    # Not free-form: an unrecognized value is just treated as "chat", the
    # same as not sending it at all.
    channel: str | None = None


_ANGELA_CHANNELS = {"chat", "voz"}


def _channel(req: "ChatRequest") -> str:
    return req.channel if req.channel in _ANGELA_CHANNELS else "chat"


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/login")
def login(req: LoginRequest):
    res = auth.login(req.username, req.password)
    if not res:
        raise HTTPException(status_code=401, detail=i18n.t("api.login_incorrecto"))
    return res


@app.get("/api/me")
def me(token: str):
    u = auth.usuario_por_token(token)
    if not u:
        raise HTTPException(status_code=401, detail=i18n.t("api.sesion_invalida"))
    return u


@app.get("/api/perfiles")
def perfiles_equipo(token: str):
    # OJO: no llamar "perfiles" a esta función — pisa el módulo core.perfiles.
    dueno = _admin_de(token)
    # Los labels de módulo, en el idioma del que MIRA (P39·1): la ficha de cada
    # empleado se lee entera en un solo idioma, el del dueño.
    return {"perfiles": auth.listar_perfiles(_lang(dueno))}


class VerComoRequest(BaseModel):
    username: str


@app.post("/api/demo/ver-como")
def demo_ver_como(req: VerComoRequest, _u: dict = Depends(usuario_actual)):
    """"View as / Ver como" del TENANT DEMO (P9·E): los reviewers de YC ven el
    producto desde los ojos de cada empleado sin pelear con logins. Emite una
    sesión legítima del usuario destino (server-side), detrás del feature flag
    POLPILOT_DEMO_ROLE_SWITCH y de una sesión ya válida. En el piloto el flag
    no existe → 404: para un empleado real de Horizonte este endpoint
    directamente NO EXISTE."""
    if not auth.role_switch_activo():
        raise HTTPException(status_code=404, detail="Not Found")
    s = auth.sesion_para(req.username)
    if not s:
        raise HTTPException(status_code=404, detail="usuario inexistente")
    return s


@app.post("/api/demo/autologin")
def demo_autologin():
    """Entrada directa del link de YC (P11·B8): con POLPILOT_DEMO_AUTOLOGIN=1,
    abrir la URL mintea una sesión LEGÍTIMA del DUEÑO (server-side, mismo riel
    que ver-como); desde "View as" se cambia de rol. El logout lleva al login
    normal, que sigue existiendo detrás. En el piloto el flag no existe →
    404: este endpoint directamente NO EXISTE."""
    if not auth.autologin_activo():
        raise HTTPException(status_code=404, detail="Not Found")
    s = auth.sesion_para(auth.dueno()["username"])
    if not s:
        raise HTTPException(status_code=404, detail="Not Found")
    return s


@app.get("/api/equipo/nombres")
def equipo_nombres(_u: dict = Depends(usuario_actual)):
    """Nombre y rol del equipo del tenant (sin datos sensibles): lo usa
    "Adoptar objetivo" para asignar un responsable REAL (P9·C2, M3)."""
    # P11·B9: `superficies` viaja con cada empleado — el selector "View as"
    # de desktop filtra a los roles cuyo trabajo no es de escritorio
    # (reparto/camión y depósito operativo van por mobile/WhatsApp); acá
    # siguen TODOS: Objetivos y Equipo los necesitan completos.
    # P·onboarding: viaja también la ANTIGÜEDAD (None para quien no declara
    # ingreso). Con eso la lista del equipo puede distinguir de un vistazo al que
    # recién entró de los que llevan años, sin pedir otra vuelta al servidor.
    return {"equipo": [{"username": u["username"], "nombre": u["nombre"], "rol": u["rol"],
                        "superficies": u.get("superficies", []),
                        "antiguedad": auth.antiguedad(u["username"])}
                       for u in auth.USUARIOS.values() if not u.get("interno")]}


@app.get("/api/onboarding")
def onboarding_guia(u: dict = Depends(usuario_actual)):
    """La guía del que recién entró: ubicaciones del depósito, cada cuánto repone
    cada proveedor, los procesos paso a paso, las reglas del dueño que le aplican
    y a quién avisarle. TODO sale de datos que ya existen (ver core/onboarding.py)
    y viene recortado a las features de quien pregunta — la misma matriz «Quién ve
    qué» de siempre. Cualquiera puede consultarla: no hay nada acá que la persona
    no pudiera ver por su cuenta; lo que cambia es que está junto y explicado."""
    return onboarding.guia(u)


# --- Carga de comprobantes por FOTO (P10): visión → confirmación → rieles ---

class FacturaLeerRequest(BaseModel):
    imagen: str                       # base64 (sin encabezado data:)
    media_type: str = "image/jpeg"


class FacturaConfirmarRequest(BaseModel):
    extraccion: dict                  # lo extraído, con las correcciones del humano


class RemitoReclamarRequest(BaseModel):
    """Lo que faltó de un remito, para reclamárselo al proveedor."""
    proveedor: str
    items: list[dict]                 # [{producto, falta, ...}] de reclamo_sugerido
    oc: str | None = None


@app.post("/api/remito/reclamar")
def remito_reclamar(req: RemitoReclamarRequest,
                    u: dict = Depends(require_feature("cargar"))):
    """El segundo SÍ: Ángela propuso el reclamo al confirmar el remito y el
    humano lo acepta acá. Cada faltante entra por el MISMO riel que usa el
    depósito cuando reporta a mano (core/piso), así que sale agrupado por
    proveedor en las propuestas de Equipo — un solo camino, no dos."""
    from core import piso
    lang = _lang(u)
    creados = []
    for it in req.items:
        falta = float(it.get("falta") or 0)
        if falta <= 0 or not it.get("producto"):
            continue
        creados.append(piso.reportar("faltante", u["username"], {
            "producto": it["producto"], "cantidad": falta, "motivo": "faltante",
            "nota": i18n.t("core.comp.reclamo_prop", lang, n=1,
                           proveedor=req.proveedor),
            "origen_remito": req.oc,
        })["id"])
    if not creados:
        raise HTTPException(status_code=422, detail=i18n.t("api.nada_que_reclamar", lang))
    return {"ok": True, "reportes": creados,
            "mensaje": i18n.t("core.comp.reclamo_hecho", lang,
                              n=len(creados), proveedor=req.proveedor)}


@app.post("/api/factura/leer")
def factura_leer(req: FacturaLeerRequest, request: Request,
                 u: dict = Depends(require_feature("cargar"))):
    """Foto → extracción estructurada + chequeos automáticos + el CRUCE del
    circuito de compra (remito↔OC, factura↔remito) — todo ANTES de confirmar.
    Acá no se persiste nada: la tesis es ejecución con aprobación humana."""
    from core import comprobantes, extraccion
    lang = _lang(u)
    # (B) Freno de gasto por IP (visión = LLM, solo demo): mismo cap que el chat.
    # El endpoint ya exige token (feature cargar), pero autologin lo regala: el
    # cap por IP sobrevive al re-login. En piloto _cap_ip()=0 → no aplica.
    # Un comprobante de MUESTRA se resuelve sin LLM (core/extraccion): no gasta,
    # así que el cap no lo frena — el cap existe para el gasto, no para la demo.
    if not extraccion.es_muestra(req.imagen) and \
            _ip_excedido(_client_ip(request), _cap_ip()):
        return {"ok": False, "motivo": i18n.t("angela.cap_alcanzado", lang)}
    r = extraccion.extraer(req.imagen, req.media_type, lang)
    if not r.get("ok"):
        return r
    ext = r["extraccion"]
    r["chequeos"] = comprobantes.chequeos(ext, lang)
    if ext.get("tipo_comprobante") == "remito":
        r["cruce"] = comprobantes.cruzar_remito(ext)
    elif ext.get("tipo_comprobante") == "factura":
        r["cruce"] = comprobantes.cruzar_factura(ext)
    elif ext.get("tipo_comprobante") == "lista_precios":
        # P22·A — el diff contra el catálogo REAL: subas, saltos sospechosos y
        # códigos pisados, ANTES del OK. El validador hace el trabajo.
        from core import lista_precios
        r["cruce"] = lista_precios.diff(ext, lang)
    return r


@app.post("/api/factura/confirmar")
def factura_confirmar(req: FacturaConfirmarRequest,
                      u: dict = Depends(require_feature("cargar"))):
    """El SÍ explícito del humano: recién acá el comprobante entra al dominio
    real (stock/recepciones/compras/cuenta del proveedor/cobro del cliente),
    con backup + audit. El tramo al ERP queda en cola SIMULADA y declarada."""
    from core import comprobantes
    try:
        r = comprobantes.confirmar(req.extraccion, actor=u["nombre"], lang=_lang(u))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    # El texto que Ángela dice en pantalla se arma en el FRONTEND, en el idioma
    # que el usuario está mirando. Acá viajan la decisión y los números.
    if r.get("ok"):
        r["mensaje_angela_partes"] = comprobantes.mensaje_proactivo_partes(
            r, req.extraccion)
    # Si cargó un EMPLEADO, el dueño se entera por la campanita (con el mismo
    # análisis que dijo Ángela). El dueño cargando no se auto-notifica.
    if r.get("ok") and not u.get("es_admin"):
        try:
            d = auth.dueno()
            lang_dueno = _lang({"username": d["username"]})
            notificaciones.emitir(
                para=d["username"],
                titulo=i18n.t("notif.comprobante_t", lang_dueno, actor=u["nombre"]),
                cuerpo=comprobantes.mensaje_proactivo(r, req.extraccion, lang_dueno),
                tipo="comprobante", ref=req.extraccion.get("numero"))
        except Exception:
            pass  # la carga ya está hecha: una notificación fallida no la rompe
    return r


_MUESTRAS = ("remito", "factura", "recibo", "lista")  # el orden CUENTA la historia


@app.get("/api/comprobantes/muestras")
def comprobantes_muestras(u: dict = Depends(require_feature("cargar"))):
    """Los comprobantes de muestra — SOLO TENANT DEMO (los reviewers de YC no
    tienen una factura argentina a mano). La imagen viene provista; de ahí en
    más el pipeline es EXACTAMENTE el real (la visión los lee de verdad)."""
    if paths.TENANT != "demo":
        raise HTTPException(status_code=404, detail="Not Found")
    # Sin `titulo`/`descripcion` renderizados: el texto lo arma el frontend con
    # su propio idioma (muestras.<id>_t / _d). El backend manda el ID, que es un
    # identificador y no se traduce.
    return {"muestras": [
        {"id": mid, "url": f"/api/comprobantes/muestras/{mid}.png"}
        for mid in _MUESTRAS
    ]}


@app.get("/api/comprobantes/muestras/{mid}.png")
def comprobante_muestra_png(mid: str, _u: dict = Depends(require_feature("cargar"))):
    if paths.TENANT != "demo" or mid not in _MUESTRAS:
        raise HTTPException(status_code=404, detail="Not Found")
    ruta = os.path.join(paths.DATA_DIR, "comprobantes", f"{mid}.png")
    if not os.path.exists(ruta):
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse(ruta, media_type="image/png")


class ObjetivoRequest(BaseModel):
    nombre: str
    responsable: str | None = None
    fecha: str | None = None
    id: str | None = None  # uid del tablero del cliente (mezcla idempotente)


class ObjetivoEstadoRequest(BaseModel):
    estado: str


@app.get("/api/objetivos")
def objetivos_listar(_u: dict = Depends(usuario_actual)):
    """Objetivos del equipo, SERVER-SIDE (P9·C5, M9): lo que Ángela o el dueño
    crean lo ve todo el equipo, no solo el localStorage de quien lo pidió."""
    from core import objetivos
    return {"objetivos": objetivos.listar()}


@app.post("/api/objetivos")
def objetivos_crear(req: ObjetivoRequest, u: dict = Depends(usuario_actual)):
    from core import objetivos
    if not req.nombre.strip():
        raise HTTPException(status_code=422, detail="nombre vacío")
    return objetivos.crear(req.nombre, req.responsable, req.fecha,
                           creado_por=u["nombre"], oid=req.id)


@app.post("/api/objetivos/{oid}/estado")
def objetivos_estado(oid: str, req: ObjetivoEstadoRequest,
                     _u: dict = Depends(usuario_actual)):
    from core import objetivos
    try:
        return objetivos.cambiar_estado(oid, req.estado)
    except KeyError:
        raise HTTPException(status_code=404, detail="objetivo inexistente")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


def _cuerpo_actividad():
    """Lo que PolPilot hizo DE VERDAD en este tenant (P9·C2, M4): la franja de
    ahorro y el feed de Inicio se alimentan de acá — nada de texto fijo.
    Correcciones = eventos de auditoría; staging = integraciones; alertas =
    notificaciones emitidas. Todo contado de los registros reales."""
    from core import notificaciones as notif_mod, ventas as ventas_mod, fechas
    # P36·E1 — VERDAD LITERAL en el feed: solo eventos de NEGOCIO de Ángela, y
    # NUNCA posteriores a la fecha congelada del tenant (el trabajo de dev/seed
    # queda fuera). Tres guardas: por tipo (admin+técnico), por fecha, y dedup.
    hoy_iso = fechas.hoy().isoformat()
    # Eventos administrativos (perfil, idioma, permisos): quedan en la auditoría
    # cruda (/api/audit) pero NO son "trabajo de Ángela".
    administrativos = {"editar_descripcion_perfil", "cambiar_foto_perfil",
                       "cambiar_idioma", "solicitar_modulo",
                       "resolver_solicitud_modulo", "cambiar_modulo_empleado",
                       "consulta_angela"}
    # Técnicos/seed: `crear_apartado` (nuevas:0) lo emite el seed en cada boot —
    # NO es una acción de negocio; se excluye del feed por tipo.
    tecnicos = {"crear_apartado"}
    integraciones = {"integrar_staging"}   # el ÚNICO "archivo procesado" real

    def _negocio(e):
        acc = e.get("accion")
        return (acc not in administrativos and acc not in tecnicos
                and (e.get("cuando") or "")[:10] <= hoy_iso)  # guarda dura de fecha

    eventos = [e for e in store.audit.list() if _negocio(e)]
    correcciones = [e for e in eventos if e["accion"] not in integraciones]
    procesados = [e for e in eventos if e["accion"] in integraciones]

    # Feed: por fecha DESC, deduplicado (mismo tipo+día+desc colapsa con `veces`).
    ordenados = sorted(eventos, key=lambda e: e.get("cuando") or "", reverse=True)
    feed, indice = [], {}
    for e in ordenados:
        clave = (e["accion"], (e.get("cuando") or "")[:10], repr(e.get("despues")))
        if clave in indice:
            feed[indice[clave]]["veces"] += 1
            continue
        indice[clave] = len(feed)
        feed.append({
            "tipo": "staging" if e["accion"] in integraciones else "correccion",
            "accion": e["accion"], "actor": e["actor"], "cuando": e["cuando"],
            "veces": 1,
            # P36·E2 — el detalle real para expandir la línea (del audit ya existente)
            "detalle": {"antes": e.get("antes"), "despues": e.get("despues")},
        })
    feed = feed[:5]

    return {
        # Contadores calculados bajo EXACTAMENTE el mismo filtro que el feed.
        "correcciones": len(correcciones),
        "staging_procesados": len(procesados),
        "alertas_emitidas": notif_mod.total_emitidas(hasta_iso=hoy_iso),
        "hay_ventas": ventas_mod.hay_datos(),
        "hoy": hoy_iso,   # P36·E2 — la fecha de referencia para las fechas RELATIVAS del feed
        "feed": feed,
    }


@app.get("/api/actividad")
def actividad(_u: dict = Depends(usuario_actual)):
    return _cuerpo_actividad()


@app.get("/api/inicio")
def inicio(u: dict = Depends(usuario_actual)):
    """El resumen ejecutivo del Home en UNA llamada (P13): agregación pura de
    fuentes que YA existen, cada una respetando el gating por feature de su
    endpoint original (un rol sin el módulo recibe null, no datos filtrados).
    Cero lógica de dominio nueva: solo selección y empaquetado."""
    from core import analisis, analisis_cache, autonomia
    lang = _lang(u)
    feats = perfiles.features_efectivas(u["username"])
    analisis_objetivos = None
    if "oportunidades" in feats:
        completo = analisis_cache.get_o_computar("analisis", lang,
                                                 lambda: analisis.completo(lang))
        if completo.get("disponible"):
            analisis_objetivos = completo.get("objetivos") or []
    return {
        "staging": {"batches": staging.listar()} if "cargar" in feats else None,
        "calidad": store.libro_triado(lang) if "saneamiento" in feats else None,
        "solicitudes": perfiles.solicitudes(estado="pendiente") if u.get("es_admin") else [],
        "actividad": _cuerpo_actividad(),
        "analisis_objetivos": analisis_objetivos,
        # Bloque F·3 — contra la fatiga de aprobación: el nivel que el dueño
        # eligió decide si la cola de decisión pide de a una o agrupa lo
        # rutinario y reversible. Va acá para no sumar una llamada al Home.
        "autonomia_datos": autonomia.nivel_de("datos"),
        "fase": fase.actual(lang),
    }


@app.get("/api/objetivos-medidos")
def objetivos_medidos_endpoint(u: dict = Depends(usuario_actual)):
    """P36·E4 — Objetivos que Ángela MIDE contra datos reales. El `actual` de
    cada objetivo sale del MISMO cálculo que ya alimenta el resto de la app (una
    sola fuente de verdad); el baseline+historial son sintéticos (solo demo). El
    progreso se calcula, nunca se hardcodea. Permisos server-side: el dueño ve
    todos; cada empleado, sólo los suyos (sin bypass)."""
    from core import analisis, analisis_cache, objetivos_medidos, oportunidades_neg, fechas
    lang = _lang(u)
    completo = analisis_cache.get_o_computar("analisis", lang, lambda: analisis.completo(lang))
    k = (completo or {}).get("kpis") or {}
    dormido = (k.get("dormido") or {}).get("monto")
    sin_pvp = (k.get("margen_teorico") or {}).get("sin_pvp")
    # concentración top-3: de la card REAL de oportunidades (misma cuenta que el mapa)
    pct_top3 = None
    try:
        cards = analisis_cache.get_o_computar("oportunidades", lang,
                                              lambda: oportunidades_neg.cards(lang))
        if isinstance(cards, dict):
            cards = cards.get("cards", [])
        conc = next((c for c in (cards or []) if c.get("id") == "concentracion"), None)
        pct_top3 = ((conc or {}).get("datos") or {}).get("pct_top3")
    except Exception:
        pass
    try:
        total_issues = store.libro_triado(lang).get("total_issues")
    except Exception:
        total_issues = None
    # P41·3.3 — la mora viva ($): el MISMO total que ya muestran Alertas, el
    # panel y la card de morosos. Se LEE, no se recalcula.
    mora = None
    try:
        mora = (cuentas.alertas() or {}).get("impacto_pesos")
    except Exception:
        pass
    # P41·3.3 — productos por quebrar: los que tienen menos cobertura que el
    # umbral del hallazgo de quiebre, sobre el detalle de rotación ya calculado.
    por_quebrar = None
    try:
        det = ((completo or {}).get("rotacion") or {}).get("detalle") or []
        umbral = objetivos_medidos.COBERTURA_QUIEBRE_DIAS
        por_quebrar = sum(1 for x in det
                          if x.get("dias_rotacion") is not None and 0 < x["dias_rotacion"] <= umbral)
    except Exception:
        pass
    base_dormido = objetivos_medidos.DEFS["liberar_dormido"]["baseline_dormido"]
    actuales = {
        "dias_cobro": k.get("cobro_dias"),
        "datos_corregir": total_issues,
        "liberar_dormido": (base_dormido - dormido) if dormido is not None else None,
        "pvp_margen": sin_pvp,
        "concentracion": pct_top3,
        "cobrar_morosos": mora,
        "reponer_quiebres": por_quebrar,
    }
    objs = objetivos_medidos.construir(actuales, fechas.hoy().isoformat())
    if not u.get("es_admin"):
        objs = [o for o in objs if o["responsable"] == u["username"]]
    return {"objetivos": objs, "resumen": objetivos_medidos.resumen(objs)}


@app.get("/api/health")
def health():
    from core import fechas
    return {
        "ok": True,
        "servicio": "polpilot-app",  # the service, not the tenant — `tenant` below says which
        "angela_online": config.model_disponible(),
        "modo_angela": config.modo(),          # "claude" or "offline", evaluated at runtime
        "modelo_angela": config.modelo_para(),  # el modelo que usaría ahora mismo
        "routing_modelos": config.ROUTING_ACTIVO,  # apagado durante validación
        "idioma_default": paths.DEFAULT_LANG,  # default del tenant (Login lo usa pre-sesión)
        "hoy": fechas.hoy().isoformat(),  # frozen demo date or the real today
        "tenant": paths.TENANT,  # el frontend elige seeds/copys por config, no por nombre
        "role_switch": auth.role_switch_activo(),  # "View as" del demo (P9·E)
        "autologin": auth.autologin_activo(),      # entrada directa del demo (P11·B8)
        # P37 — el logo del cliente lo decide el BACKEND por tenant (el frontend
        # ya no hardcodea ningún cliente): el piloto se sirve de su data dir.
        "meta": {**ds.meta(), "logo": paths.LOGO},
    }


@app.get("/api/marca/logo")
def marca_logo():
    """P37 (incidente de privacidad) — el logo del cliente del TENANT ACTIVO,
    servido desde SU data dir (`{DATA_DIR}/logo.*`), NUNCA empaquetado en el
    frontend. El logo del piloto vive solo en data/ (en la imagen del piloto);
    la imagen de la demo no lo tiene. Así el bundle público jamás incluye el
    logo/nombre de otro tenant."""
    import glob
    tipos = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
             "svg": "image/svg+xml", "webp": "image/webp"}
    for ext, mt in tipos.items():
        hit = glob.glob(os.path.join(paths.DATA_DIR, f"logo.{ext}"))
        if hit:
            return FileResponse(hit[0], media_type=mt)
    raise HTTPException(status_code=404, detail="sin logo de marca")


@app.get("/api/organizacion")
def organizacion_get(_u: dict = Depends(usuario_actual)):
    """Config del tenant (margen mínimo, balanzas por peso). Base multi-tenant.
    Lectura para cualquier usuario logueado; cambiarla es scope organización (Ángela)."""
    return organizacion.get()


# --- P17·E1 · PDF real. Rutas fijas ANTES de la paramétrica /{tipo} ---------

class PdfRequest(BaseModel):
    documento: dict


@app.post("/api/documentos/pdf")
async def documentos_pdf(req: PdfRequest, u: dict = Depends(require_feature("documentos"))):
    """Renderiza el documento EDITADO por el usuario (la única copia con sus
    cambios vive en el cliente) a PDF real, lo guarda en Documentos y lo
    devuelve para descargar. No calcula nada: maqueta lo que el draft dice."""
    from core import pdf as pdf_mod
    if not pdf_mod.disponible():
        raise HTTPException(status_code=503, detail=i18n.t("api.pdf_no_disponible", _lang(u)))
    import asyncio
    import io
    try:
        # write_pdf es síncrono y CPU-bound: fuera del event loop.
        pdf_bytes, meta = await asyncio.to_thread(
            pdf_mod.render_y_guardar, req.documento, _lang(u),
            u.get("nombre", u["username"]), u["username"])
    except Exception:
        raise HTTPException(status_code=500, detail=i18n.t("api.pdf_error", _lang(u)))
    from fastapi.responses import StreamingResponse
    nombre = f"{meta['tipo']}-{meta['fecha']}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


@app.get("/api/carpeta")
def carpeta_lista(u: dict = Depends(require_feature("documentos"))):
    """The deliveries a folder can be opened for."""
    from core import carpeta
    return {"pedidos": carpeta.pedidos()}


@app.get("/api/carpeta/{numero}")
def carpeta_de(numero: str, u: dict = Depends(require_feature("documentos"))):
    from core import carpeta
    r = carpeta.carpeta(numero, _lang(u))
    if not r:
        raise HTTPException(status_code=404, detail="pedido inexistente")
    return r


@app.get("/api/carpeta/{numero}/{doc_id}")
def carpeta_documento(numero: str, doc_id: str,
                      u: dict = Depends(require_feature("documentos"))):
    """One document, pre-filled — with its gaps marked, never hidden."""
    from core import carpeta
    d = carpeta.documento(numero, doc_id, _lang(u))
    if not d:
        raise HTTPException(status_code=404, detail="documento inexistente")
    return d


@app.get("/api/documentos/listado")
def documentos_listado(u: dict = Depends(require_feature("documentos"))):
    """Los PDFs ya generados. P24·A1: POR USUARIO, server-side — cada uno ve
    solo los suyos; el dueño ve los de todo el equipo (con 'pedido por X').

    P43·C5.3 — el LABEL sigue el idioma de quien mira, el ARCHIVO no. `titulo`
    quedó congelado en el idioma en que se generó (y está bien: es el nombre del
    documento, que adentro está escrito en ese idioma). Pero mostrar "Inventory
    executive summary" en una lista en castellano parece un bug de traducción.
    Se manda `label` traducido desde `tipo` —que es una key estable, no texto— y
    `lang` para que la pantalla avise cuando el PDF está en otro idioma."""
    from core import pdf as pdf_mod
    lang = _lang(u)
    docs = []
    for d in pdf_mod.listado(u["username"], u.get("es_admin", False)):
        d = dict(d)
        clave = f"doc.tipo.{d.get('tipo', 'documento')}"
        d["label"] = i18n.t(clave, lang) if clave in i18n.CATALOGO else d.get("titulo")
        docs.append(d)
    return {"documentos": docs, "pdf_disponible": pdf_mod.disponible(), "lang": lang}


@app.get("/api/documentos/archivo/{doc_id}")
def documentos_archivo(doc_id: str, u: dict = Depends(require_feature("documentos"))):
    from core import pdf as pdf_mod
    # P24·A1 — mismo guard en la DESCARGA: un id ajeno da 404, ni existe.
    if not pdf_mod.puede_ver(doc_id, u["username"], u.get("es_admin", False)):
        raise HTTPException(status_code=404, detail="Not Found")
    path = pdf_mod.archivo_path(doc_id)
    if not path:
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse(path, media_type="application/pdf")


@app.get("/api/documentos/{tipo}")
def documento_get(tipo: str, proveedor: str | None = None, dias: int | None = None,
                  u: dict = Depends(require_feature("documentos"))):
    """Genera el contenido de un documento desde los datos reales del negocio."""
    try:
        return documentos.generar(tipo, {"proveedor": proveedor, "dias": dias},
                                  _lang(u))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Plan 6 · Cuentas corrientes de clientes (datos de clientes → feature "cuentas") ---

@app.get("/api/cuentas")
def cuentas_listar(_u: dict = Depends(require_feature("cuentas"))):
    # `totales` no es nuevo: existe desde P11·B12 y su docstring dice por qué
    # ("los agregados monetarios los calcula EL CORE, una sola vez"). Faltaba
    # mandarlo, y la pantalla se sumaba los saldos sola.
    return {"clientes": cuentas.listar(), "alertas": cuentas.alertas(),
            "totales": cuentas.totales()}


@app.get("/api/cuentas/{cliente_id}")
def cuentas_get(cliente_id: str, u: dict = Depends(require_feature("cuentas"))):
    c = cuentas.get(cliente_id)
    if not c:
        raise HTTPException(status_code=404,
                            detail=i18n.t("api.cliente_inexistente", _lang(u)))
    return c


@app.get("/api/cuentas/{cliente_id}/recordatorio")
def cuentas_recordatorio(cliente_id: str, u: dict = Depends(require_feature("cuentas"))):
    m = cuentas.mensaje_cobro(cliente_id, _lang(u))
    if not m:
        raise HTTPException(status_code=404,
                            detail=i18n.t("api.cliente_inexistente", _lang(u)))
    return m


class CobroRequest(BaseModel):
    monto: float


@app.post("/api/cuentas/{cliente_id}/cobro")
def cuentas_cobro(cliente_id: str, req: CobroRequest,
                  u: dict = Depends(require_feature("cuentas"))):
    try:
        return cuentas.registrar_cobro(cliente_id, req.monto)
    except KeyError:
        raise HTTPException(status_code=404,
                            detail=i18n.t("api.cliente_inexistente", _lang(u)))


# --- Plan 7 · Caja y tesorería (plata → feature "caja") ---

@app.get("/api/caja")
def caja_estado(_u: dict = Depends(require_feature("caja"))):
    return caja.estado()


class CajaAbrirRequest(BaseModel):
    saldo_inicial: float = 0


class MovimientoRequest(BaseModel):
    tipo: str
    medio: str
    monto: float
    detalle: str = ""


class CierreRequest(BaseModel):
    declarado: float | None = None


@app.post("/api/caja/abrir")
def caja_abrir(req: CajaAbrirRequest, _u: dict = Depends(require_feature("caja"))):
    return caja.abrir(req.saldo_inicial)


@app.post("/api/caja/movimiento")
def caja_movimiento(req: MovimientoRequest, _u: dict = Depends(require_feature("caja"))):
    return caja.movimiento(req.tipo, req.medio, req.monto, req.detalle)


@app.post("/api/caja/cerrar")
def caja_cerrar(req: CierreRequest, u: dict = Depends(require_feature("caja"))):
    return caja.cerrar(req.declarado, _lang(u))


# --- Perfiles autoadministrados: el empleado describe, Ángela propone, el dueño decide ---

class DescripcionRequest(BaseModel):
    token: str
    texto: str


class IdiomaRequest(BaseModel):
    token: str
    idioma: str


class FotoRequest(BaseModel):
    token: str
    imagen: str  # data-URL base64


class SolicitudRequest(BaseModel):
    token: str
    modulos: list[str]
    motivo: str = ""          # P39·1.2 — por qué la necesita, en sus palabras


class ResolverSolicitudRequest(BaseModel):
    token: str
    aprobar: bool
    motivo: str = ""


class FeatureRequest(BaseModel):
    token: str
    usuario: str
    modulo: str
    habilitar: bool


class UsuarioCrearRequest(BaseModel):
    token: str
    username: str
    nombre: str
    rol: str
    es_admin: bool = False
    color: str | None = None
    telefono: str | None = None
    descripcion: str | None = None
    descripcion_en: str | None = None
    features: list[str] = []
    superficies: list[str] | None = None


class UsuarioEditarRequest(BaseModel):
    token: str
    nombre: str | None = None
    rol: str | None = None
    es_admin: bool | None = None
    color: str | None = None
    telefono: str | None = None
    descripcion: str | None = None
    descripcion_en: str | None = None
    features: list[str] | None = None
    superficies: list[str] | None = None


class UsuarioEstadoRequest(BaseModel):
    token: str


# Módulos de fábrica: no se piden ni se tildan (son parte del piso mínimo o del
# equipo PolPilot). Mismo criterio que las columnas de la matriz «Quién ve qué».
_MODULOS_NO_PEDIBLES = {"angela", "perfil", "admin_contexto", "gestion_equipo",
                        # el registro de auditoría y los conectores son scope
                        # organización, como gestion_equipo: no se piden, se
                        # tienen por ser dueño.
                        "auditoria", "conectores"}


@app.get("/api/perfil/{usuario}")
def perfil_get(usuario: str, u: dict = Depends(usuario_actual)):
    p = auth.perfil_publico(usuario, _lang(u))   # labels en el idioma del que MIRA
    if not p:
        raise HTTPException(status_code=404,
                            detail=i18n.t("api.usuario_inexistente", _lang(u)))
    p["sugerencias"] = perfiles.sugerir_modulos(usuario)
    p["solicitudes"] = perfiles.solicitudes(usuario=usuario)
    # P39·1.2 — TODO lo que puede pedir, no sólo lo que Ángela le sugirió: el
    # empleado sabe qué necesita para trabajar. Mismas columnas que la matriz
    # «Quién ve qué» (los módulos de fábrica no se piden), menos lo que ya tiene
    # y lo que ya está esperando respuesta.
    if not p.get("es_admin"):
        labels = auth.modulos_labels(_lang(u))
        tiene = set(p.get("features") or [])
        esperando = {s["modulo"] for s in p["solicitudes"] if s["estado"] == "pendiente"}
        p["pedibles"] = [{"modulo": m, "label": labels.get(m, l)}
                         for m, l in auth.MODULOS.items()
                         if m not in _MODULOS_NO_PEDIBLES and m not in tiene
                         and m not in esperando]
    return p


@app.post("/api/perfil/{usuario}/descripcion")
def perfil_descripcion(usuario: str, req: DescripcionRequest):
    quien = _usuario_de(req.token)
    # Scope usuario: cada uno edita SU descripción (el dueño también puede).
    if quien["username"] != usuario and not quien.get("es_admin"):
        raise HTTPException(status_code=403,
                            detail=i18n.t("perfil.solo_propio", _lang(quien)))
    if not req.texto.strip():
        raise HTTPException(status_code=400,
                            detail=i18n.t("api.descripcion_vacia", _lang(quien)))
    return perfiles.set_descripcion(usuario, req.texto)


@app.post("/api/perfil/{usuario}/idioma")
def perfil_idioma(usuario: str, req: IdiomaRequest):
    quien = _usuario_de(req.token)
    # Scope usuario: cada uno elige SU idioma (el dueño también puede setearlo).
    if quien["username"] != usuario and not quien.get("es_admin"):
        raise HTTPException(status_code=403, detail=i18n.t("perfil.solo_propio",
                                                           perfiles.idioma_de(quien["username"])))
    try:
        return perfiles.set_idioma(usuario, req.idioma)
    except ValueError:
        raise HTTPException(status_code=400,
                            detail=i18n.t("perfil.idioma_invalido",
                                          perfiles.idioma_de(quien["username"]),
                                          validos=", ".join(paths.IDIOMAS)))


@app.post("/api/perfil/{usuario}/foto")
def perfil_foto_subir(usuario: str, req: FotoRequest):
    quien = _usuario_de(req.token)
    if quien["username"] != usuario and not quien.get("es_admin"):
        raise HTTPException(status_code=403,
                            detail=i18n.t("perfil.solo_propio", _lang(quien)))
    try:
        return perfiles.set_foto(usuario, req.imagen)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/perfil/{usuario}/foto")
def perfil_foto(usuario: str):
    """La foto de perfil, o 204 si esa persona no subió ninguna.

    P43·C5.4 — sin foto la respuesta era 404, y como el Avatar pide la foto
    SIEMPRE a propósito (el servidor decide si existe, así una sesión vieja no
    esconde una foto recién subida), la consola se llenaba de 404 rojos por cada
    empleado sin foto. 204 dice lo mismo sin parecer un error: la persona existe,
    su avatar no tiene contenido. El `onError` del <img> sigue disparando y
    caemos a las iniciales igual que antes."""
    path = perfiles.foto_path(usuario)
    if not path:
        return Response(status_code=204)
    return FileResponse(path)


@app.post("/api/solicitudes")
def solicitudes_crear(req: SolicitudRequest):
    quien = _usuario_de(req.token)  # el solicitante sale del token, no del body
    sugeridas = {s["modulo"]: s["motivo"] for s in perfiles.sugerir_modulos(quien["username"])}
    creadas, errores = [], []
    for m in req.modulos:
        try:
            if m in _MODULOS_NO_PEDIBLES:
                raise ValueError(i18n.t("api.modulo_no_pedible", _lang(quien)))
            creadas.append(perfiles.crear_solicitud(
                quien["username"], m, sugeridas.get(m, ""), motivo_empleado=req.motivo))
        except ValueError as e:
            errores.append({"modulo": m, "error": str(e)})
    return {"creadas": creadas, "errores": errores}


@app.get("/api/solicitudes")
def solicitudes_listar(token: str, estado: str | None = None):
    quien = _usuario_de(token)
    if quien.get("es_admin"):
        return {"solicitudes": perfiles.solicitudes(estado=estado)}
    return {"solicitudes": perfiles.solicitudes(usuario=quien["username"], estado=estado)}


@app.post("/api/solicitudes/{sid}/resolver")
def solicitudes_resolver(sid: str, req: ResolverSolicitudRequest):
    dueno = _admin_de(req.token)  # habilitar módulos = configuración de negocio
    try:
        return perfiles.resolver_solicitud(sid, req.aprobar, actor=dueno["username"], motivo=req.motivo)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/admin/matriz")
def admin_matriz(token: str):
    _admin_de(token)
    return {"matriz": perfiles.matriz(), "modulos": auth.MODULOS}


@app.post("/api/admin/feature")
def admin_feature(req: FeatureRequest):
    dueno = _admin_de(req.token)
    try:
        return perfiles.set_feature(req.usuario, req.modulo, req.habilitar, actor=dueno["username"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/admin/usuarios")
def admin_usuarios_crear(req: UsuarioCrearRequest):
    """Alta de un empleado real — sólo el dueño. Devuelve una contraseña
    inicial generada (nunca persistida en claro) para pasarle a la persona;
    la puede cambiar su cuenta más adelante."""
    dueno = _admin_de(req.token)
    try:
        u = auth.crear_usuario(
            username=req.username, nombre=req.nombre, rol=req.rol,
            es_admin=req.es_admin, color=req.color, telefono=req.telefono,
            descripcion=req.descripcion, descripcion_en=req.descripcion_en,
            features=req.features, superficies=req.superficies,
            actor=dueno["username"],
        )
    except auth.UsuarioInvalido as e:
        raise HTTPException(status_code=400, detail=str(e))
    creds = auth.cargar_o_generar_credenciales()
    return {"usuario": u, "password_inicial": creds.get(req.username)}


@app.patch("/api/admin/usuarios/{usuario}")
def admin_usuarios_editar(usuario: str, req: UsuarioEditarRequest):
    dueno = _admin_de(req.token)
    cambios = req.model_dump(exclude={"token"}, exclude_none=True)
    try:
        return auth.editar_usuario(usuario, cambios, actor=dueno["username"])
    except KeyError:
        raise HTTPException(status_code=404,
                            detail=i18n.t("api.usuario_inexistente", _lang(dueno)))


@app.post("/api/admin/usuarios/{usuario}/desactivar")
def admin_usuarios_desactivar(usuario: str, req: UsuarioEstadoRequest):
    dueno = _admin_de(req.token)
    try:
        return auth.desactivar_usuario(usuario, actor=dueno["username"])
    except KeyError:
        raise HTTPException(status_code=404,
                            detail=i18n.t("api.usuario_inexistente", _lang(dueno)))
    except auth.UsuarioInvalido as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/admin/usuarios/{usuario}/reactivar")
def admin_usuarios_reactivar(usuario: str, req: UsuarioEstadoRequest):
    dueno = _admin_de(req.token)
    try:
        return auth.reactivar_usuario(usuario, actor=dueno["username"])
    except KeyError:
        raise HTTPException(status_code=404,
                            detail=i18n.t("api.usuario_inexistente", _lang(dueno)))


class AvisoRequest(BaseModel):
    para: str
    titulo: str
    cuerpo: str = ""


@app.post("/api/notificaciones/avisar")
def notificaciones_avisar(req: AvisoRequest, u: dict = Depends(require_admin)):
    """El dueño manda un aviso a un empleado por el sistema de notificaciones
    real (le llega a SU campanita, no al localStorage del navegador del dueño)."""
    import auth as _auth
    if req.para not in _auth.USUARIOS:
        raise HTTPException(status_code=404,
                            detail=i18n.t("api.empleado_inexistente", _lang(u)))
    return notificaciones.emitir(para=req.para, titulo=req.titulo,
                                 cuerpo=req.cuerpo, tipo="aviso_dueno")


@app.get("/api/notificaciones")
def notificaciones_listar(token: str):
    quien = _usuario_de(token)
    # P24·D6 — el poll de la campanita re-evalúa las condiciones latentes
    # (umbral de dormida, atraso de clientes, programados) contra los datos
    # vivos: si una se cumplió, la notificación aparece en ESTE mismo fetch.
    try:
        recordatorios.evaluar()
    except Exception:  # noqa: BLE001 — la campanita nunca se cae por esto
        pass
    items = notificaciones.listar(quien["username"])
    return {"notificaciones": items,
            "no_leidas": sum(1 for n in items if not n["leida"]),
            "destinos": notificaciones.destinos_registrados()}


@app.post("/api/notificaciones/{nid}/leida")
def notificaciones_leida(nid: str, token: str):
    quien = _usuario_de(token)
    try:
        return notificaciones.marcar_leida(nid)
    except KeyError:
        raise HTTPException(status_code=404,
                            detail=i18n.t("api.notificacion_inexistente", _lang(quien)))


# --- Ventas: rotación + margen real + quiebre (despiertan con el CSV, tras validar montos) ---

class ValidacionRequest(BaseModel):
    esperado: float | None = None
    confirmar: bool = False


@app.get("/api/ventas")
def ventas_get(u: dict = Depends(require_feature("inventario"))):
    """Rotación/excedente, margen real y quiebre. disponible=False hasta que haya
    ventas Y el dueño confirme el validador de montos."""
    return ventas.panorama(_lang(u))


@app.get("/api/ventas/validacion")
def ventas_validacion(u: dict = Depends(usuario_actual)):
    return ventas.validacion(_lang(u))


@app.post("/api/ventas/validacion")
def ventas_validar(req: ValidacionRequest, u: dict = Depends(require_admin)):
    """Confirmar el total del mes es decir 'la verdad del negocio': sólo el dueño."""
    try:
        return ventas.confirmar_validacion(req.esperado, req.confirmar,
                                           actor=u["username"], lang=_lang(u))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class DryRunRequest(BaseModel):
    csv: str


@app.post("/api/ventas/dryrun")
def ventas_dryrun(req: DryRunRequest, _u: dict = Depends(require_feature("cargar"))):
    """Probar un CSV de ventas SIN comprometer nada: qué se detecta y qué activaría."""
    if not req.csv.strip():
        raise HTTPException(status_code=400,
                            detail=i18n.t("api.archivo_vacio", _lang(_u)))
    try:
        return ventas.dry_run(req.csv)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Evolución: comparación histórica ajustada por IPC (despierta con las ventas) ---

@app.get("/api/evolucion")
def evolucion_get(u: dict = Depends(require_feature("evolucion"))):
    # P11·B4: mismo cache que /api/analisis — las alertas de negocio salen de acá.
    from core import analisis_cache
    lang = _lang(u)
    return analisis_cache.get_o_computar("evolucion", lang,
                                         lambda: evolucion.panorama(lang))


@app.get("/api/forecast")
def forecast_get(u: dict = Depends(require_feature("evolucion"))):
    from core import forecast as forecast_mod
    return forecast_mod.forecast_demand(_lang(u))


@app.get("/api/imported")
def imported_get(_u: dict = Depends(require_feature("inventario"))):
    """Raw loaded rows: catalog, sales, receipts, warehouse positions."""
    from core import imported as imported_mod
    return imported_mod.overview()


# --- Depósito y logística (capa sobre el WMS/TMS: consultas, no picking ni rutas) ---

@app.get("/api/deposito")
def deposito_get(dias: int = 15, _u: dict = Depends(require_feature("deposito"))):
    disc_k = deposito.discrepancias_conocimiento()
    return {
        "resumen": deposito.resumen(),
        "vencimientos": deposito.vencimientos(dias),
        "vencidos": deposito.vencidos(),
        # C7 — la diferencia llega con lo que el equipo dijo de esa ubicación:
        # el ERP dice "faltan 6,5", nosotros podemos decir por qué.
        "discrepancias": deposito.explicaciones(disc_k["visibles"]),
        "discrepancias_suprimidas": disc_k["suprimidas"],  # Piece 12 — "vela acá"
        "aging": deposito.aging(),
    }


@app.get("/api/pagos")
def pagos_get(u: dict = Depends(require_feature("finanzas"))):
    """Pagos y liquidez (P16): lo por pagar, lo que acredita y los cheques.
    Sin datos (piloto) devuelve vacío honesto y la UI muestra su placeholder.
    P24·F1: + la proyección 30/60/90 (trabajo de PolPilot, no data a cargar)."""
    return {
        "resumen": pagos.resumen(),
        "pagos_por_vencer": pagos.pagos_por_vencer(14),
        "pagos_vencidos": pagos.pagos_vencidos(),
        "tarjeta_por_acreditar": pagos.tarjeta_por_acreditar(30),
        "cheques": pagos.cheques_en_cartera(),
        "proyeccion": pagos.proyeccion_flujo(_lang(u)),
    }


@app.get("/api/logistica")
def logistica_get(_u: dict = Depends(require_feature("logistica"))):
    return {
        "reparto": logistica.resumen_reparto(),
        "hoy": logistica.de_hoy(),
        "atrasados": logistica.atrasados(),
    }


@app.get("/api/parada")
def parada_get(cliente: str, u: dict = Depends(require_feature("logistica"))):
    """La parada de una persona: quién es, qué debe, qué dijeron de él y qué se
    vence que él compre.

    QUIÉN VE LA DEUDA, Y POR QUÉ NO LO DECIDO ACÁ. Ver saldos es `cuentas`, y
    el chofer no lo tiene: tiene `logistica`. Así que la parada le llega SIN el
    bloque de deuda, y con las otras dos preguntas completas — que ya es la
    mitad de lo que hoy no tiene.

    Darle al chofer el saldo del cliente que está por visitar es una decisión
    de producto razonable y probablemente correcta (es la plata que puede
    cobrar, del cliente que tiene enfrente), pero **cambia qué ve un rol** y
    eso no se resuelve dentro de un PR de pantallas. Queda anotado en
    `design/mobile/03-CRUCES.md` §3 y lo decide el dueño del permiso.

    El recorte va del lado del SERVIDOR: mandar el saldo y esconderlo en el
    front sería regalarlo en la respuesta.
    """
    from core import parada
    p = parada.de(cliente, _lang(u))
    if "cuentas" not in perfiles.features_efectivas(u["username"]):
        p["deuda"] = None
        p["deuda_oculta"] = True
    return p


@app.get("/api/parada/proximas")
def parada_proximas(transporte: str | None = None,
                    u: dict = Depends(require_feature("logistica"))):
    """Las paradas que le quedan a alguien, sin entregar, en orden."""
    from core import parada
    return {"paradas": parada.proximas(transporte)}


@app.get("/api/logistica/exposicion")
def logistica_exposicion(
        _u: dict = Depends(require_all_features("logistica", "cuentas"))):
    """Cuánta plata en la calle lleva cada camión que está por salir.

    DOS MÓDULOS, NO UNO. Ver esto es ver rutas Y ver saldos, y el gate sale de
    esa frase en vez de inventarse: el encargado de depósito tiene `logistica`
    pero no `cuentas` (no le corresponde el saldo de un cliente), y el
    preventista tiene `cuentas` pero no `logistica` (no le corresponde la flota).
    Quien tenga una sola de las dos mitades no ve el cruce.

    El total es deuda que YA existe; el cruce la hace visible y no la cobra.
    """
    from core import cobranza
    return {"dias": cobranza.exposicion_en_ruta()}


# --- P39 · lo que el piso REPORTA (y el cruce que produce) ---------------------
# El empleado reporta un hecho (faltante, conteo, entrega, reposición). No mueve
# stock ni ERP: eso sigue siendo decisión del dueño sobre una PROPUESTA.

class ReporteRequest(BaseModel):
    tipo: str
    datos: dict = {}
    # A quién le llega. Opcional en el contrato y obligatorio en la práctica:
    # la interfaz siempre manda uno (el que Ángela propuso y la persona
    # confirmó), pero un reporte viejo sin destinatario sigue siendo válido.
    destinatario: str | None = None


class ResolverReporteRequest(BaseModel):
    nota: str = ""


@app.post("/api/piso/reporte")
def piso_reportar(req: ReporteRequest, u: dict = Depends(usuario_actual)):
    """Cada tipo pide el módulo del trabajo que reporta: un faltante o un conteo
    es depósito; confirmar una entrega es logística; pedir reposición, caja de
    la sucursal. Sin ese módulo, la acción no existe para ese rol."""
    requiere = {"faltante": "deposito", "conteo": "deposito",
                "entrega": "logistica", "reposicion": "inventario",
                "pedido": "cuentas"}.get(req.tipo)
    if requiere and requiere not in (u.get("features") or []):
        raise HTTPException(status_code=403,
                            detail=i18n.t("authz.sin_feature", _lang(u), feature=requiere))
    try:
        return piso.reportar(req.tipo, u["username"], req.datos,
                             destinatario=req.destinatario)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/piso/avisos-oficio")
def piso_avisos_oficio(u: dict = Depends(usuario_actual)):
    """Los avisos que ESTE oficio deja, listos para pintar como botones.

    El oficio sale del TEXTO del rol de quien pregunta, no de su username: una
    persona nueva con el mismo puesto hereda sus avisos sin tocar código. No va
    detrás de ninguna feature — no es un dato del negocio, es la lista de cosas
    que esta persona puede decir, y decir siempre puede.

    Cada aviso viene con el destinatario ya resuelto a un username REAL, o
    vacío: la pantalla no inventa a quién le llega.
    """
    from core import avisos_oficio
    import auth
    r = avisos_oficio.de(u.get("rol"), _lang(u))
    for a in r["avisos"]:
        d = auth.USUARIOS.get(a["destinatario"] or "") or {}
        a["destinatario"] = ({"username": a["destinatario"], "nombre": d.get("nombre"),
                              "rol": d.get("rol") or ""} if d else None)
    return r


@app.get("/api/piso/destinatario")
def piso_destinatario(tipo: str, u: dict = Depends(usuario_actual)):
    """A quién PROPONE Ángela mandar este tipo de aviso.

    Se consulta antes de mandar para poder mostrar «esto lo ve Celeste, ¿lo
    mando?». La propuesta es determinista (core/piso.DESTINO): el modelo no
    elige a quién le llega un reclamo con plata adentro.
    """
    username = piso.destinatario_sugerido(tipo)
    if not username:
        return {"sugerido": None}
    import auth
    d = auth.USUARIOS.get(username) or {}
    return {"sugerido": {"username": username, "nombre": d.get("nombre") or username,
                         "rol": d.get("rol") or ""}}


class VozRequest(BaseModel):
    """Una nota de voz del piso. Llega transcrita por el navegador (Web Speech)
    o como audio para el camino de muestras."""
    texto: str | None = None
    audio: str | None = None          # base64
    media_type: str = "audio/webm"


@app.post("/api/voz/escuchar")
def voz_escuchar(req: VozRequest, request: Request,
                 u: dict = Depends(usuario_actual)):
    """Voz → lo que Ángela ENTENDIÓ y lo que PROPONE. No persiste nada.

    El empleado tiene las manos ocupadas: habla en vez de tipear. Pero un
    número o un producto que salen de una voz pasan por el MISMO peaje
    determinista que los de un remito (core/validacion), y lo que quede dudoso
    vuelve marcado para que lo resuelva una persona."""
    from core import transcripcion, voz
    lang = _lang(u)
    if not req.texto and _ip_excedido(_client_ip(request), _cap_ip()):
        return {"ok": False, "motivo": i18n.t("angela.cap_alcanzado", lang)}
    t = transcripcion.transcribir(texto=req.texto, audio_b64=req.audio, lang=lang)
    if not t.get("ok"):
        return {"ok": False, "motivo": t.get("motivo")}
    p = voz.proponer(t["texto"], actor=u["username"], lang=lang)
    p["ok"] = True
    p["origen_transcripcion"] = t["origen"]
    return p


@app.get("/api/voz/muestras")
def voz_muestras(u: dict = Depends(usuario_actual)):
    """Las notas de voz preparadas — SOLO TENANT DEMO. El plan B honesto para
    cuando el navegador no tiene Web Speech (Safari/iOS) o la sala no tiene red:
    recorren EXACTAMENTE la misma tubería que una voz real."""
    if paths.TENANT != "demo":
        return {"muestras": []}
    from core import transcripcion
    datos = transcripcion.muestras_crudas().get("muestras") or {}
    return {"muestras": [{"id": k, "rol": m.get("rol"),
                          "titulo": m.get("titulo"), "texto": m.get("texto")}
                         for k, m in datos.items()]}


class VozConfirmarRequest(BaseModel):
    """El sí del humano, con las correcciones que haya hecho."""
    tipo: str
    datos: dict
    transcripcion: str | None = None


@app.post("/api/voz/confirmar")
def voz_confirmar(req: VozConfirmarRequest, u: dict = Depends(usuario_actual)):
    """El reporte dictado entra por el MISMO riel que el cargado a mano
    (core/piso) — no hay un camino paralelo para la voz. Se revalida acá, sobre
    lo que el humano confirma, no sobre lo que se le mostró antes."""
    from core import voz as _voz
    lang = _lang(u)
    if req.tipo not in _voz.INTENCIONES or req.tipo == "consulta":
        raise HTTPException(status_code=422,
                            detail=i18n.t("core.voz.falta_producto", lang))
    datos = dict(req.datos or {})
    if req.transcripcion:
        # queda la frase textual: es la prueba de qué se dijo
        datos["dictado"] = req.transcripcion
    return piso_reportar(ReporteRequest(tipo=req.tipo, datos=datos), u)


@app.get("/api/piso/reportes")
def piso_reportes(tipo: str | None = None, estado: str | None = None,
                  u: dict = Depends(usuario_actual)):
    """El dueño ve todo; cada empleado ve lo suyo Y lo que le dirigieron.

    Antes filtraba sólo por autor, así que a un destinatario no le llegaba nada:
    el reporte le estaba dirigido y no lo podía leer. Mismo criterio que
    `recordatorios.listar`, que ya mira `para` y `creado_por`.
    """
    if u.get("es_admin"):
        return {"reportes": piso.listar(tipo=tipo, estado=estado)}
    yo = u["username"]
    return {"reportes": [r for r in piso.listar(tipo=tipo, estado=estado)
                         if r["actor"] == yo or r.get("destinatario") == yo]}


@app.get("/api/piso/mios")
def piso_mios(u: dict = Depends(usuario_actual)):
    """Lo que mandé y lo que me mandaron, con lo que salió de cada cosa.

    ESTE ENDPOINT ES EL PUNTO DEL PRODUCTO. `api.piso.reportes` existía y
    ninguna pantalla lo llamaba, así que el que reportaba ocho cajas rotas no
    se enteraba nunca de que se reclamaron: volvía al grupo de WhatsApp, donde
    por lo menos alguien contesta.
    """
    from core import mis_avisos
    return mis_avisos.de(u["username"], _lang(u))


@app.post("/api/piso/reportes/{rid}/visto")
def piso_visto(rid: str, u: dict = Depends(usuario_actual)):
    """El destinatario lo abrió. Sólo él o el dueño: un acuse de un tercero no
    acusa nada."""
    r = next((x for x in piso.listar() if x["id"] == rid), None)
    if not r:
        raise HTTPException(status_code=404,
                            detail=i18n.t("api.reporte_inexistente", _lang(u)))
    if not u.get("es_admin") and r.get("destinatario") != u["username"]:
        raise HTTPException(status_code=403,
                            detail=i18n.t("api.reporte_ajeno", _lang(u)))
    return piso.ver(rid, u["username"])


@app.post("/api/piso/reportes/{rid}/resolver")
def piso_resolver(rid: str, req: ResolverReporteRequest,
                  u: dict = Depends(usuario_actual)):
    """Lo cierra el dueño, o la persona a la que se lo dirigieron.

    NO ES UN NIVEL DE PERMISO NUEVO — es la misma dueñez de fila que ya tiene
    `recordatorios.completar` ("una tarea la cierra SU destinatario, o el
    dueño"). Un aviso dirigido a Celeste que sólo Aldo puede cerrar convierte
    al dueño en el cuello de botella que el producto vino a sacar, y deja al
    que reportó esperando por alguien que ni siquiera es el que lo tiene.

    Lo que NO se toca acá: que el encargado de depósito pueda decidir sobre
    SU dominio —diferencias, faltantes de su gente— sigue necesitando un
    tercer nivel en `authz`, y ese es un cambio de seguridad que decide
    Agustín. Está diseñado (design/mobile/00-MODELO-FLUJO.md) y no construido.
    """
    r = next((x for x in piso.listar() if x["id"] == rid), None)
    if not r:
        raise HTTPException(status_code=404,
                            detail=i18n.t("api.reporte_inexistente", _lang(u)))
    if not u.get("es_admin") and r.get("destinatario") != u["username"]:
        raise HTTPException(status_code=403,
                            detail=i18n.t("api.reporte_ajeno", _lang(u)))
    try:
        return piso.resolver(rid, u["username"], req.nota)
    except KeyError:
        raise HTTPException(status_code=404,
                            detail=i18n.t("api.reporte_inexistente", _lang(u)))


@app.get("/api/piso/reportes/{rid}/prueba")
def piso_prueba(rid: str, u: dict = Depends(usuario_actual)):
    """P41·4 — la prueba de una entrega. La ve quien la sacó y el dueño: es el
    respaldo de esa persona si un cliente dice que no recibió."""
    r = next((x for x in piso.listar() if x["id"] == rid), None)
    if not r or (not u.get("es_admin") and r["actor"] != u["username"]):
        raise HTTPException(status_code=404,
                            detail=i18n.t("api.reporte_inexistente", _lang(u)))
    path = piso.adjunto_path(rid)
    if not path:
        raise HTTPException(status_code=404,
                            detail=i18n.t("api.reporte_inexistente", _lang(u)))
    return FileResponse(path)


@app.get("/api/piso/propuestas")
def piso_propuestas(u: dict = Depends(require_admin)):
    """P39·3 — lo que el equipo reportó, cruzado con stock y órdenes de compra,
    convertido en decisiones del dueño (con su aprobación, nunca sin ella)."""
    return {"propuestas": piso.propuestas(_lang(u))}


# --- Recordatorios (transversal: simples, por condición de datos y por evento) ---

class RecordatorioRequest(BaseModel):
    texto: str
    para: str | None = None
    creado_por: str | None = None
    condicion: dict | None = None


@app.get("/api/recordatorios")
def recordatorios_listar(para: str | None = None,
                         u: dict = Depends(usuario_actual)):
    # Scope: cada uno ve los suyos; el dueño puede mirar los de otro con ?para=.
    objetivo = para if u.get("es_admin") else u["username"]
    return {"recordatorios": recordatorios.listar(objetivo)}


@app.post("/api/recordatorios")
def recordatorios_crear(req: RecordatorioRequest, u: dict = Depends(usuario_actual)):
    if not req.texto.strip():
        raise HTTPException(status_code=400,
                            detail=i18n.t("api.recordatorio_vacio", _lang(u)))
    # el creador sale del token; asignar a otro es potestad del dueño
    creado_por = u["username"]
    para = req.para if (u.get("es_admin") and req.para) else creado_por
    return recordatorios.crear(req.texto, para, creado_por, req.condicion)


@app.post("/api/recordatorios/{rid}/completar")
def recordatorios_completar(rid: str, u: dict = Depends(usuario_actual)):
    # P41·4 — una tarea la cierra SU destinatario (o el dueño). Antes cualquier
    # sesión válida podía marcar hecha la tarea de otro: el scope de lectura ya
    # existía, el de escritura faltaba.
    try:
        mia = next((r for r in recordatorios.listar(u["username"]) if r["id"] == rid), None)
        if not mia and not u.get("es_admin"):
            raise HTTPException(status_code=403,
                                detail=i18n.t("api.recordatorio_ajeno", _lang(u)))
        return recordatorios.completar(rid)
    except KeyError:
        raise HTTPException(status_code=404,
                            detail=i18n.t("api.recordatorio_inexistente", _lang(u)))


# --- P24·E4 — "Lo que pasó con tu equipo": agregador de actividad REAL --------

# P34·2 — el trabajo REAL que registra el audit, por familia. Los slugs son los
# que efectivamente se graban (audit.record en core/*); antes la lista blanca
# tenía nombres muertos ("confirmar_remito"…) y subcontaba el trabajo real.
_CARGAS_ACC = {"cargar_orden_compra", "cargar_remito", "cargar_factura",
               "cargar_recibo", "integrar_staging", "crear_apartado"}
_CORRECCIONES_EXTRA = {"aplicar_lista_precios", "corregir_precio_perdida"}
# Las correcciones de saneamiento son `sanear_<lo que sea>` (fantasma, balanza,
# costo_viejo, fantasma_custom…): se cuentan por prefijo, robusto a categorías.


def _familia_evento(acc: str) -> str | None:
    if acc == "consulta_angela":
        return "consulta"
    if acc in _CARGAS_ACC:
        return "carga"
    if acc.startswith("sanear_") or acc in _CORRECCIONES_EXTRA:
        return "correccion"
    return None


# P39·1.3 — trabajo REAL que no cae en carga/corrección pero sí es "algo que
# esta persona resolvió" (validó los montos del mes, dejó una orden armada, y
# lo que reporta el de a pie desde el piso). Se suma a lo de arriba para el
# bloque "qué resolvió esta semana" de la ficha.
_TRABAJO_EXTRA = {"validacion_montos_ventas", "preparar_orden_compra",
                  "reportar_faltante", "marcar_conteo", "confirmar_entrega",
                  "cerrar_tarea_piso", "pedir_reposicion", "registrar_pedido",
                  "registrar_presupuesto", "avisar_costo_viejo",
                  "avisar_desde_el_piso"}
# `preguntar_referente` NO está acá a propósito: preguntar no es trabajo
# resuelto, y contarlo le inflaría el número justo al que recién entró — que es
# el que más pregunta y el que menos tiene para mostrar. Queda en el registro
# con su propio sello, como las consultas a Ángela.


def _es_trabajo(acc: str) -> bool:
    return _familia_evento(acc) in ("carga", "correccion") or acc in _TRABAJO_EXTRA


@app.get("/api/equipo/actividad")
def equipo_actividad(u: dict = Depends(require_admin)):
    """Panel de gestión: por CADA empleado del tenant, lo que el sistema
    registró de verdad — consultas a Ángela (TEMAS = tools, jamás el texto de la
    conversación), cargas por foto/archivo, correcciones con backup, recencia y
    objetivos. Es un AGREGADOR de la auditoría real: cero actividad inventada; un
    empleado sin eventos se muestra vacío, no relleno. WhatsApp jamás aparece
    acá (futuro declarado en pantalla). Solo el dueño (require_admin)."""
    import auth as _auth
    import datetime as _dt
    from core import objetivos as obj_mod, fechas
    hoy = fechas.hoy()

    def _dias_desde(cuando: str | None) -> int | None:
        if not cuando:
            return None
        try:
            d = _dt.date.fromisoformat(cuando[:10])
        except (ValueError, TypeError):
            return None
        # clamp >=0: el audit graba con reloj REAL; un evento en vivo (fecha real
        # posterior a la congelada del demo) no debe dar "hace -N días".
        return max(0, (hoy - d).days)

    # Un bucket por CADA persona del tenant (no-interno): los inactivos también
    # son información — se listan con actividad en cero.
    # P39·1.1 — el dueño ENTRA a la lista: la nómina es UNA sola y la misma en
    # "Ver como", "Lo que pasó con tu equipo" y "Quién ve qué" (antes acá se
    # excluía a los admin y daban 12 contra 13 de la matriz).
    por_usuario: dict[str, dict] = {}
    for username, base in _auth.USUARIOS.items():
        if base.get("interno"):
            continue
        por_usuario[username] = {
            "username": username, "nombre": base["nombre"], "rol": base["rol"],
            "es_admin": base.get("es_admin", False),
            "consultas": 0, "temas": {}, "cargas": 0, "correcciones": 0,
            "resueltos": {}, "ultima": None,
        }

    for e in store.audit.list():
        b = por_usuario.get(e.get("actor") or "")
        if b is None:
            continue
        accion = e.get("accion") or ""
        # "Qué resolvió esta semana": lo concreto de los últimos 7 días, contado
        # por acción (3 remitos, 2 productos corregidos…). Nada agregado a mano.
        dd = _dias_desde(e.get("cuando"))
        if _es_trabajo(accion) and dd is not None and dd <= 7:
            b["resueltos"][accion] = b["resueltos"].get(accion, 0) + 1
        fam = _familia_evento(accion)
        if fam == "consulta":
            b["consultas"] += 1
            for tema in (e.get("despues") or {}).get("tools", []):
                b["temas"][tema] = b["temas"].get(tema, 0) + 1
        elif fam == "carga":
            b["cargas"] += 1
        elif fam == "correccion":
            b["correcciones"] += 1
        elif not _es_trabajo(accion):
            continue    # administrativo puro (idioma, foto): no es "actividad"
        if not b["ultima"] or (e.get("cuando") or "") > b["ultima"]:
            b["ultima"] = e.get("cuando")

    objetivos = obj_mod.listar()
    obj_por_nombre: dict[str, list] = {}
    for o in objetivos:
        obj_por_nombre.setdefault(o.get("responsable"), []).append(o)

    filas = []
    temas_equipo: dict[str, int] = {}
    for b in por_usuario.values():
        temas = b.pop("temas")
        for k, v in temas.items():
            temas_equipo[k] = temas_equipo.get(k, 0) + v
        b["temas_top"] = sorted(temas.items(), key=lambda kv: -kv[1])[:3]
        b["acciones"] = b["cargas"] + b["correcciones"]
        # (slug, n) ordenado por volumen — el frontend le pone las palabras
        b["resueltos"] = sorted(b.pop("resueltos").items(), key=lambda kv: -kv[1])[:6]
        b["dias_desde"] = _dias_desde(b["ultima"])
        mios = obj_por_nombre.get(b["nombre"], [])
        b["objetivos_en_curso"] = sum(1 for o in mios if o.get("estado") != "listo")
        b["objetivos_listos"] = sum(1 for o in mios if o.get("estado") == "listo")
        filas.append(b)
    # más activos primero; los sin actividad (dias_desde None) al final
    filas.sort(key=lambda f: (f["consultas"] + f["acciones"], -(f["dias_desde"] if f["dias_desde"] is not None else 10**6)), reverse=True)

    # Resumen del equipo (2.C), todo derivado de lo real:
    resumen = {
        "personas": len(filas),
        "activos_semana": sum(1 for f in filas if f["dias_desde"] is not None and f["dias_desde"] <= 7),
        "acciones_total": sum(f["acciones"] for f in filas),
        "consultas_total": sum(f["consultas"] for f in filas),
        "objetivos_en_curso": sum(1 for o in objetivos if o.get("estado") != "listo"),
        "objetivos_listos": sum(1 for o in objetivos if o.get("estado") == "listo"),
        "tema_top": (sorted(temas_equipo.items(), key=lambda kv: -kv[1])[0][0]
                     if temas_equipo else None),
    }
    return {"actividad": filas, "resumen": resumen,
            "objetivos": [{"nombre": o.get("nombre"), "responsable": o.get("responsable"),
                           "estado": o.get("estado")} for o in objetivos]}


# --- Sync bidireccional con sistemas externos (Fase 1: delta export) ---

@app.get("/api/sync/delta")
def sync_delta(formato: str = "generico", _u: dict = Depends(require_admin)):
    """Genera el CSV con SOLO los registros corregidos (UPDATE), para re-importar en Faro/Tango."""
    return sync.generar_delta_export(formato)


@app.get("/api/sync/config")
def sync_config(_u: dict = Depends(require_admin)):
    """Quién gana por campo (resolución de conflictos) + conflictos detectados."""
    return {"source_of_truth": sync.SOURCE_OF_TRUTH, "conflictos": sync.detectar_conflictos()}


@app.get("/api/conectores")
def conectores_listar(_u: dict = Depends(require_admin)):
    """Plan 11: conectores disponibles (CSV/BCRA activos, Odoo según config del
    tenant, MCP slot pendiente)."""
    from core.db import tenant as _tenant
    return {"conectores": conectores.disponibles(_tenant.current_tenant_id())}


class OdooConexionRequest(BaseModel):
    url: str
    database: str
    username: str
    api_key: str


@app.get("/api/conectores/odoo")
def odoo_config_ver(_u: dict = Depends(require_admin)):
    """Config de Odoo guardada para este tenant. La api_key nunca vuelve al
    frontend (write-only una vez guardada)."""
    from core import odoo_demo
    from core.db import odoo_connections_repo, tenant as _tenant
    c = odoo_connections_repo.get(_tenant.current_tenant_id())
    if c:
        return {"conectado": True, "url": c["url"], "database": c["database"],
                "username": c["username"], "actualizado": c["updated_at"]}
    if odoo_demo.activo():
        e = odoo_demo.estado()
        return {"conectado": True, "demo": True, "url": "muestra://odoo",
                "database": "litoral_demo", "username": "demo",
                "actualizado": e.get("activado")}
    # Only the demo tenant, and only when it actually ships the sample, gets
    # the extra key — a tenant that cannot be offered the one-click connection
    # sees the plain {"conectado": False} it always saw. Advertising a
    # capability that does not exist there would be a lie the UI then has to
    # handle.
    if _es_demo() and odoo_demo.disponible():
        return {"conectado": False, "demo_disponible": True}
    return {"conectado": False}


@app.put("/api/conectores/odoo")
def odoo_config_guardar(req: OdooConexionRequest, _u: dict = Depends(require_admin)):
    """Prueba la conexión contra Odoo (autenticación real) antes de guardar —
    nunca persiste credenciales que no sirven."""
    from core.db import odoo_connections_repo, tenant as _tenant
    try:
        conectores.probar_conexion_odoo(req.url, req.database, req.username, req.api_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    odoo_connections_repo.save(_tenant.current_tenant_id(), req.url, req.database,
                                req.username, req.api_key)
    return {"ok": True}


@app.delete("/api/conectores/odoo")
def odoo_config_borrar(u: dict = Depends(require_admin)):
    from core import odoo_demo
    from core.db import odoo_connections_repo, tenant as _tenant
    odoo_connections_repo.delete(_tenant.current_tenant_id())
    # Disconnecting also turns the demo sample off (and unlinks exactly what
    # it linked): "desconectar" leaves the tenant with NO Odoo, of any kind.
    if odoo_demo.activo():
        odoo_demo.desactivar(u["username"])
    return {"ok": True}


@app.post("/api/conectores/odoo/conectar-demo")
def odoo_conectar_demo(u: dict = Depends(require_admin)):
    """DEMO ONLY: connect the Odoo connector to the bundled sample and run
    the first sync end to end (link + direct updates + staging batches for
    what's new). 404s on any other tenant, same belt-and-braces as
    /api/admin/reset-demo — and it is NOT a fallback: a real connection,
    once configured, always wins (core/conectores.conector_odoo)."""
    from core import odoo_demo, odoo_ingest
    if not _es_demo() or not odoo_demo.disponible():
        raise HTTPException(status_code=404, detail="Not Found")
    actor = u["username"]
    vinculado = odoo_demo.activar(actor)
    resultados = {
        "productos": odoo_ingest.ingest_productos(actor),
        "proveedores": odoo_ingest.ingest_proveedores(actor),
        "ordenes_compra": odoo_ingest.ingest_ordenes_compra(actor),
        "ventas": odoo_ingest.ingest_ventas(actor),
        "recepciones": odoo_ingest.ingest_recepciones(actor),
    }
    return {"ok": True, "vinculado": vinculado, "resultados": resultados}


@app.post("/api/conectores/odoo/sync")
def odoo_sync(_u: dict = Depends(require_admin)):
    """Trae los contactos-cliente de Odoo (res.partner) como preview de sólo
    lectura — ver core/conectores.ConectorOdoo para por qué todavía no se
    integra directo a la Staging Area."""
    from core.db import tenant as _tenant
    conector = conectores.conector_odoo(_tenant.current_tenant_id())
    try:
        return conector.pull_data()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/conectores/odoo/sync-productos")
def odoo_sync_productos(_u: dict = Depends(require_admin)):
    """Trae el catálogo de productos de Odoo (product.template) con su stock
    disponible, como preview de sólo lectura — mismo criterio que odoo_sync()."""
    from core.db import tenant as _tenant
    conector = conectores.conector_odoo(_tenant.current_tenant_id())
    try:
        return conector.pull_productos()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/conectores/odoo/ingest-productos")
def odoo_ingest_productos(_u: dict = Depends(require_admin)):
    """Real ingestion: already-linked Odoo products are updated directly;
    new ones land in a Staging batch for review."""
    from core import odoo_ingest
    try:
        return odoo_ingest.ingest_productos(actor=_u["username"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/conectores/odoo/sync-proveedores")
def odoo_sync_proveedores(_u: dict = Depends(require_admin)):
    """Trae los contactos-proveedor de Odoo (res.partner, supplier_rank > 0)
    como preview de sólo lectura — mismo criterio que odoo_sync()."""
    from core.db import tenant as _tenant
    conector = conectores.conector_odoo(_tenant.current_tenant_id())
    try:
        return conector.pull_proveedores()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/conectores/odoo/ingest-proveedores")
def odoo_ingest_proveedores(_u: dict = Depends(require_admin)):
    """Real ingestion: already-linked Odoo vendors are updated directly;
    new ones land in a Staging batch for review."""
    from core import odoo_ingest
    try:
        return odoo_ingest.ingest_proveedores(actor=_u["username"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/conectores/odoo/ingest-contactos")
def odoo_ingest_contactos(_u: dict = Depends(require_admin)):
    """Real ingestion: already-linked Odoo customers are updated directly;
    new ones land in a Staging batch for review."""
    from core import odoo_ingest
    try:
        return odoo_ingest.ingest_clientes(actor=_u["username"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/conectores/odoo/sync-ordenes-compra")
def odoo_sync_ordenes_compra(_u: dict = Depends(require_admin)):
    """Trae las órdenes de compra de Odoo (purchase.order) con sus líneas,
    como preview de sólo lectura — mismo criterio que odoo_sync()."""
    from core.db import tenant as _tenant
    conector = conectores.conector_odoo(_tenant.current_tenant_id())
    try:
        return conector.pull_ordenes_compra()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/conectores/odoo/ingest-ordenes-compra")
def odoo_ingest_ordenes_compra(_u: dict = Depends(require_admin)):
    """Real ingestion: already-linked Odoo purchase orders are updated
    directly; new ones land in a Staging batch for review."""
    from core import odoo_ingest
    try:
        return odoo_ingest.ingest_ordenes_compra(actor=_u["username"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/conectores/odoo/sync-ventas")
def odoo_sync_ventas(_u: dict = Depends(require_admin)):
    """Preview of Odoo sale.order rows (all states) with lines."""
    from core.db import tenant as _tenant
    conector = conectores.conector_odoo(_tenant.current_tenant_id())
    try:
        return conector.pull_ordenes_venta()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/conectores/odoo/ingest-ventas")
def odoo_ingest_ventas(_u: dict = Depends(require_admin)):
    """Confirmed sale lines: linked rows auto-upsert; new ones go to Staging."""
    from core import odoo_ingest
    try:
        return odoo_ingest.ingest_ventas(actor=_u["username"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/conectores/odoo/sync-deposito")
def odoo_sync_deposito(_u: dict = Depends(require_admin)):
    from core.db import tenant as _tenant
    conector = conectores.conector_odoo(_tenant.current_tenant_id())
    try:
        return conector.pull_deposito()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/conectores/odoo/ingest-deposito")
def odoo_ingest_deposito(_u: dict = Depends(require_admin)):
    from core import odoo_ingest
    try:
        return odoo_ingest.ingest_deposito(actor=_u["username"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/conectores/odoo/sync-recepciones")
def odoo_sync_recepciones(_u: dict = Depends(require_admin)):
    from core.db import tenant as _tenant
    conector = conectores.conector_odoo(_tenant.current_tenant_id())
    try:
        return conector.pull_recepciones()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/conectores/odoo/ingest-recepciones")
def odoo_ingest_recepciones(_u: dict = Depends(require_admin)):
    from core import odoo_ingest
    try:
        return odoo_ingest.ingest_recepciones(actor=_u["username"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/conectores/odoo/sync-entregas")
def odoo_sync_entregas(_u: dict = Depends(require_admin)):
    from core.db import tenant as _tenant
    conector = conectores.conector_odoo(_tenant.current_tenant_id())
    try:
        return conector.pull_entregas()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/conectores/odoo/ingest-entregas")
def odoo_ingest_entregas(_u: dict = Depends(require_admin)):
    from core import odoo_ingest
    try:
        return odoo_ingest.ingest_entregas(actor=_u["username"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/conectores/odoo/sync-facturas")
def odoo_sync_facturas(_u: dict = Depends(require_admin)):
    from core.db import tenant as _tenant
    conector = conectores.conector_odoo(_tenant.current_tenant_id())
    try:
        return conector.pull_facturas()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/conectores/odoo/ingest-facturas")
def odoo_ingest_facturas(_u: dict = Depends(require_admin)):
    from core import odoo_ingest
    try:
        return odoo_ingest.ingest_facturas(actor=_u["username"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/conectores/odoo/sync-pagos")
def odoo_sync_pagos(_u: dict = Depends(require_admin)):
    from core.db import tenant as _tenant
    conector = conectores.conector_odoo(_tenant.current_tenant_id())
    try:
        return conector.pull_pagos()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/conectores/odoo/ingest-pagos")
def odoo_ingest_pagos(_u: dict = Depends(require_admin)):
    from core import odoo_ingest
    try:
        return odoo_ingest.ingest_pagos(actor=_u["username"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/conectores/odoo/sync-listas-precios")
def odoo_sync_listas_precios(_u: dict = Depends(require_admin)):
    from core.db import tenant as _tenant
    conector = conectores.conector_odoo(_tenant.current_tenant_id())
    try:
        return conector.pull_listas_precios()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/conectores/odoo/sync-monedas")
def odoo_sync_monedas(_u: dict = Depends(require_admin)):
    from core.db import tenant as _tenant
    conector = conectores.conector_odoo(_tenant.current_tenant_id())
    try:
        return conector.pull_monedas()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# FASE 2 — Webhook receiver (hook listo, todavía no procesa): responde 200 OK.
# EXCEPCIÓN documentada: es máquina-a-máquina (Faro/Tango), NO lleva token de
# sesión de humano. Cuando procese de verdad necesitará auth de webhook (secret/
# HMAC en el header), no login. Hoy no hace nada, así que queda abierto e inocuo.
@app.post("/api/sync/webhook/{origen}")
def sync_webhook(origen: str, payload: dict | None = None):
    return {"ok": True, "origen": origen, "procesado": False}


# --- WhatsApp (canal sobre el mismo cerebro): número → empleado → rol → Ángela ---

class WhatsAppRequest(BaseModel):
    numero: str
    mensaje: str


# EXCEPCIÓN documentada: canal máquina-a-máquina (Twilio). Identifica al empleado
# por su número (usuario_por_numero), no por token de sesión. Cuando se conecte la
# Business API real necesitará validar la firma del webhook de Twilio, no login.
@app.post("/api/whatsapp")
def whatsapp_in(req: WhatsAppRequest):
    u = auth.usuario_por_numero(req.numero)
    if not u:
        return {"autorizado": False,
                "answer": i18n.t("api.whatsapp_sin_cuenta")}
    # Mismo filtro anti-fuga que el chat web: el WhatsApp de cada empleado ve sólo
    # los módulos de su rol (las features salen de su cuenta, no del mensaje).
    r = angela.responder(req.mensaje, [], rol=u.get("rol"), nombre=u.get("username"),
                         features=u.get("features"))
    return {"autorizado": True, "usuario": u.get("nombre"), "rol": u.get("rol"),
            "answer": r["answer"], "actions": r.get("actions", [])}


# --- WhatsApp Bot: canal de VENTAS de cara al cliente -------------------------
# Distinto del bloque de arriba (ese es el WhatsApp del EMPLEADO hablando con
# la misma Ángela interna). Acá el tenant conecta su propio número de WhatsApp
# Business (Meta Cloud API) para que sus CLIENTES puedan pedir catálogo,
# armar un pedido o pedir un presupuesto por chat. Ver core/whatsapp_channel.py
# y backend/whatsapp_bot.py.

class WhatsAppBotConfigRequest(BaseModel):
    phone_number_id: str
    access_token: str
    app_secret: str
    greeting_message: str = ""
    enabled: bool = True


@app.get("/api/whatsapp-bot/config")
def whatsapp_bot_config_ver(_u: dict = Depends(require_admin)):
    """Config guardada del bot de ventas. El token/secret nunca vuelven al
    frontend — mismo criterio que /api/conectores/odoo."""
    from core.db import tenant as _tenant
    c = whatsapp_channel.obtener_config(_tenant.current_tenant_id())
    if not c:
        return {"conectado": False}
    return {"conectado": True, **c}


@app.put("/api/whatsapp-bot/config")
def whatsapp_bot_config_guardar(req: WhatsAppBotConfigRequest, _u: dict = Depends(require_admin)):
    """Prueba las credenciales contra la Graph API de Meta antes de guardar —
    nunca persiste un token/phone_number_id que no sirve."""
    from core.db import tenant as _tenant
    try:
        return {"conectado": True, **whatsapp_channel.guardar_config(
            _tenant.current_tenant_id(),
            phone_number_id=req.phone_number_id, access_token=req.access_token,
            app_secret=req.app_secret, greeting_message=req.greeting_message,
            enabled=req.enabled,
        )}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/whatsapp-bot/config")
def whatsapp_bot_config_borrar(_u: dict = Depends(require_admin)):
    from core.db import tenant as _tenant
    whatsapp_channel.borrar_config(_tenant.current_tenant_id())
    return {"ok": True}


@app.get("/api/whatsapp-bot/conversaciones")
def whatsapp_bot_conversaciones(_u: dict = Depends(require_admin)):
    from core.db import tenant as _tenant
    return {"conversaciones": whatsapp_channel.listar_conversaciones(_tenant.current_tenant_id())}


@app.get("/api/whatsapp-bot/conversaciones/{conversation_id}/mensajes")
def whatsapp_bot_mensajes(conversation_id: str, _u: dict = Depends(require_admin)):
    from core.db import tenant as _tenant
    return {"mensajes": whatsapp_channel.historial_conversacion(
        _tenant.current_tenant_id(), conversation_id)}


# EXCEPCIÓN documentada: máquina-a-máquina (Meta), no lleva sesión de humano.
# El handshake de verificación es GET con hub.mode/hub.verify_token/hub.challenge
# — lo manda Meta UNA vez al guardar la config del webhook en su panel.
@app.get("/api/webhooks/whatsapp")
def whatsapp_webhook_verificar(
    hub_mode: str = Query("", alias="hub.mode"),
    hub_verify_token: str = Query("", alias="hub.verify_token"),
    hub_challenge: str = Query("", alias="hub.challenge"),
):
    from core.db import tenant as _tenant
    tid = _tenant.current_tenant_id()
    if whatsapp_channel.verificar_handshake(tid, hub_mode, hub_verify_token):
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="verify_token inválido")


# EXCEPCIÓN documentada: máquina-a-máquina (Meta). Se autentica con la firma
# HMAC del body (X-Hub-Signature-256, con el app secret guardado del tenant),
# no con un token de sesión — mismo criterio que el resto de los webhooks.
@app.post("/api/webhooks/whatsapp")
async def whatsapp_webhook_recibir(request: Request):
    from core.db import tenant as _tenant
    tid = _tenant.current_tenant_id()
    body = await request.body()
    config = whatsapp_channel.config_con_secretos(tid)
    if not config:
        return {"ok": True}
    if not whatsapp_channel.verificar_firma(
        config["app_secret"], body, request.headers.get("x-hub-signature-256"),
    ):
        raise HTTPException(status_code=401, detail="firma inválida")
    try:
        payload = json.loads(body or b"{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="payload inválido")
    whatsapp_bot.procesar_webhook(tid, payload)
    return {"ok": True}


@app.get("/api/inventario")
def inventario(u: dict = Depends(require_feature("inventario"))):
    data = ds.resumen(_lang(u))
    data["top_inmovilizado"] = ds.top_inmovilizado(10)
    data["grupos_disponibles"] = ds.grupos_disponibles(_lang(u))
    return data


@app.get("/api/inventario/top")
def inventario_top(n: int = 10, _u: dict = Depends(require_feature("inventario"))):
    return {"items": ds.top_inmovilizado(n)}


@app.get("/api/grupo/{nombre}")
def grupo(nombre: str, limit: int | None = None,
          u: dict = Depends(require_feature("inventario"))):
    if nombre not in ds.GRUPOS_LABEL:
        raise HTTPException(status_code=404,
                            detail=i18n.t("api.grupo_desconocido", _lang(u),
                                          nombre=nombre))
    items = ds.listar_grupo(nombre, limit)
    return {
        "grupo": nombre,
        "label": ds.grupo_label(nombre, _lang(u)),
        "total": len(items),
        "items": items,
    }


@app.get("/api/buscar")
def buscar(q: str, _u: dict = Depends(require_feature("inventario"))):
    return {"query": q, "items": ds.buscar_productos(q)}


@app.get("/api/buscar-global")
def buscar_global(q: str, u: dict = Depends(usuario_actual)):
    """Every entity this person may see, with where each one lives.

    Open to anyone logged in on purpose: the gate is per RESULT TYPE, not on
    the endpoint (see core/buscador.py). Someone with `cuentas` and no
    `inventario` searches customers and gets no products."""
    from core import buscador
    features = perfiles.features_efectivas(u["username"])
    return {"query": q, "items": buscador.buscar(q, features),
            "parece_pregunta": buscador.parece_pregunta(q)}


# Freno de gasto del TENANT DEMO (P9·F): límite blando de mensajes de Ángela
# por sesión (token). Solo si POLPILOT_DEMO_MSG_CAP está seteada — el piloto,
# sin la var, no cambia en nada. Contador en memoria: muere con el proceso,
# igual que las sesiones.
_CHAT_POR_SESION: dict[str, int] = {}


def _cap_mensajes() -> int:
    try:
        return int(os.environ.get("POLPILOT_DEMO_MSG_CAP", "0"))
    except ValueError:
        return 0


# --- Freno de gasto por IP (deploy público, SOLO tenant demo) ----------------
# El cap por sesión (token) se evade re-logueando (autologin mintea token nuevo)
# y no toca el path sin token. Este freno cuenta por IP real del visitante, con
# ventana DIARIA (epoch real, no la fecha congelada del demo) y limpieza de
# entradas viejas para no crecer en memoria. En el PILOTO (tenant != demo) el
# cap es 0: nada nuevo aplica. El techo duro real lo pone el spend limit de
# Anthropic (fuera de la app).
_IP_CONTEO: dict[str, tuple[int, int]] = {}  # ip -> (llamadas_hoy, dia_epoch)


def _es_demo() -> bool:
    return paths.TENANT == "demo"


def _cap_ip() -> int:
    if not _es_demo():
        return 0
    try:
        return int(os.environ.get("POLPILOT_DEMO_IP_CAP", "60"))
    except ValueError:
        return 60


def _client_ip(request: Request) -> str:
    """La IP REAL del visitante detrás del proxy de Render: el primer valor de
    X-Forwarded-For (cliente, proxy1, …); si no está, la IP directa."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        primera = xff.split(",")[0].strip()
        if primera:
            return primera
    return request.client.host if request.client else "desconocida"


def _ip_excedido(ip: str, cap: int) -> bool:
    """Cuenta UNA llamada de esta IP en el día actual; True si ya superó el cap.
    Con cap<=0 nunca frena (piloto). Ventana diaria real; purga entradas de días
    previos cuando el dict crece, para acotar la memoria."""
    if cap <= 0:
        return False
    hoy = int(time.time() // 86400)  # día epoch REAL (no fechas.hoy() congelada)
    if len(_IP_CONTEO) > 10000:
        for k in [k for k, (_, d) in _IP_CONTEO.items() if d != hoy]:
            _IP_CONTEO.pop(k, None)
    n, dia = _IP_CONTEO.get(ip, (0, hoy))
    if dia != hoy:
        n = 0
    if n >= cap:
        _IP_CONTEO[ip] = (n, hoy)  # se mantiene topado hasta que cambie el día
        return True
    _IP_CONTEO[ip] = (n + 1, hoy)
    return False


def _mensaje_cap(request: Request, token: str | None) -> dict:
    """El mismo mensaje amable del cap de sesión, en el idioma del usuario si
    hay token; si no, el default del tenant."""
    u = auth.usuario_por_token(token) if token else None
    return {"answer": i18n.t("angela.cap_alcanzado", _lang(u)),
            "mode": "cap", "tools_used": [], "actions": [], "options": []}


@app.post("/api/angela")
def chat(req: ChatRequest, request: Request):
    historial = [t.model_dump() for t in (req.history or [])]
    # (B) Freno de gasto por IP (deploy público, solo demo): antes de cualquier
    # llamada al modelo. En piloto _cap_ip()=0 → no aplica.
    if _ip_excedido(_client_ip(request), _cap_ip()):
        return _mensaje_cap(request, req.token)
    # La identidad SALE DEL TOKEN, no del body. Un rol/nombre falso en el request
    # se IGNORA: no da acceso a nada. Con token → rol/nombre/features reales del
    # usuario logueado; las features acotan qué puede ver por chat (anti-fuga).
    if req.token:
        u = auth.usuario_por_token(req.token)
        if not u:
            raise HTTPException(status_code=401, detail=i18n.t("api.sesion_invalida"))
        cap = _cap_mensajes()
        if cap > 0:
            usados = _CHAT_POR_SESION.get(req.token, 0)
            if usados >= cap:
                return {"answer": i18n.t("angela.cap_alcanzado", _lang(u)),
                        "mode": "cap", "tools_used": [], "actions": [], "options": []}
            _CHAT_POR_SESION[req.token] = usados + 1
        import time as _time
        _t0 = _time.monotonic()
        r = angela.responder(req.message, historial, rol=u.get("rol"),
                             nombre=u.get("username"), features=u.get("features"))
        _ms = round((_time.monotonic() - _t0) * 1000)
        # P24·F4 — telemetría simple de latencia por tipo de pedido (log local):
        # para saber qué esperar en la grabación, sin servicios externos.
        print(f"[angela] {_ms}ms tools={','.join(r.get('tools_used') or []) or '-'} "
              f"user={u['username']}", flush=True)
        # P24·E4 — registro LIVIANO de la interacción (tema = tools usadas, sin
        # transcripciones): alimenta "Lo que pasó con tu equipo". Es un evento
        # administrativo: no infla el feed del Home (filtrado en _cuerpo_actividad).
        try:
            store.audit.record(actor=u["username"], accion="consulta_angela",
                               despues={"tools": (r.get("tools_used") or [])[:4],
                                        "ms": _ms})
        except Exception:  # noqa: BLE001
            pass
        # The RAW transcript — full text, not the summary above — so it can
        # be looked back at. See core/angela_transcripts.py.
        try:
            from core import angela_transcripts
            angela_transcripts.record_turn(
                u["username"], req.message, r.get("answer") or "",
                tools_used=r.get("tools_used"), channel=_channel(req))
        except Exception:  # noqa: BLE001
            pass
        return r
    # (A) Sin token en el DEMO público: se rechaza limpio, SIN llamar a Claude.
    # La UI siempre manda token (autologin), así que esto solo frena el abuso
    # directo del endpoint. En el PILOTO se mantiene el anónimo restringido de
    # siempre (NO confía en req.rol/req.nombre; features=[] → nada sensible).
    if _es_demo():
        raise HTTPException(status_code=401, detail=i18n.t("api.sesion_requerida"))
    return angela.responder(req.message, historial, rol="invitado", nombre=None, features=[])


@app.post("/api/angela/stream")
def chat_stream(req: ChatRequest, request: Request):
    """Same as /api/angela but streaming (NDJSON: one line = one JSON event)
    for the assistant-ui chat — live text and each tool call visible as soon
    as it runs. Same identity/auth/cap as /api/angela; only the transport
    changes."""
    from fastapi.responses import StreamingResponse

    history = [t.model_dump() for t in (req.history or [])]

    def line(event: dict) -> str:
        return json.dumps(event, ensure_ascii=False, default=str) + "\n"

    def cap_events(u) -> str:
        """The cap is a NOTICE plus a done — never a done alone.

        v1 emitted only `done`, so the frontend built zero content parts and
        rendered an empty bubble: the user hit their limit and was told
        nothing. See the design doc, D5.
        """
        return (
            line({"type": "notice", "kind": "cap"})
            + line({"type": "done", "result": {
                "mode": "cap", "tools_used": [], "actions": [], "options": []}})
        )

    if _ip_excedido(_client_ip(request), _cap_ip()):
        u = auth.usuario_por_token(req.token) if req.token else None
        return StreamingResponse(iter([cap_events(u)]), media_type="application/x-ndjson")

    if req.token:
        u = auth.usuario_por_token(req.token)
        if not u:
            raise HTTPException(status_code=401, detail=i18n.t("api.sesion_invalida"))
        cap = _cap_mensajes()
        if cap > 0:
            used = _CHAT_POR_SESION.get(req.token, 0)
            if used >= cap:
                return StreamingResponse(iter([cap_events(u)]), media_type="application/x-ndjson")
            _CHAT_POR_SESION[req.token] = used + 1

        def generate():
            import time as _time
            _t0 = _time.monotonic()
            result = None
            # The `done` event carries no text (D5: redundant with the text
            # parts already emitted) — the transcript needs it assembled
            # here, from the same deltas the client already received.
            answer_chunks = []
            for ev in angela.stream_response(
                req.message, history, role=u.get("rol"),
                name=u.get("username"), features=u.get("features"),
            ):
                if ev.get("type") == "text":
                    answer_chunks.append(ev.get("delta") or "")
                elif ev.get("type") == "done":
                    result = ev.get("result") or {}
                yield line(ev)
            _ms = round((_time.monotonic() - _t0) * 1000)
            result = result or {}
            print(f"[angela/stream] {_ms}ms tools={','.join(result.get('tools_used') or []) or '-'} "
                  f"user={u['username']}", flush=True)
            try:
                store.audit.record(actor=u["username"], accion="consulta_angela",
                                   despues={"tools": (result.get("tools_used") or [])[:4],
                                            "ms": _ms})
            except Exception:  # noqa: BLE001
                pass
            try:
                from core import angela_transcripts
                angela_transcripts.record_turn(
                    u["username"], req.message, "".join(answer_chunks),
                    tools_used=result.get("tools_used"), channel=_channel(req))
            except Exception:  # noqa: BLE001
                pass

        return StreamingResponse(generate(), media_type="application/x-ndjson")

    if _es_demo():
        raise HTTPException(status_code=401, detail=i18n.t("api.sesion_requerida"))

    def generate_guest():
        for ev in angela.stream_response(req.message, history, role="invitado",
                                         name=None, features=[]):
            yield line(ev)

    return StreamingResponse(generate_guest(), media_type="application/x-ndjson")


# --- Ángela's raw transcript, for audit ---------------------------------------
# Same gate as /api/auditoria: only someone with the feature sees the FULL
# history (their own, or anyone's — it's an audit tool, not "my history").
# See core/angela_transcripts.py.

@app.get("/api/angela/conversaciones")
def angela_conversations(actor: str | None = None, channel: str | None = None,
                         limit: int = 100, u: dict = Depends(require_feature("auditoria"))):
    from core import angela_transcripts
    return {"conversations": angela_transcripts.list_conversations(
        actor=actor, channel=channel, limit=max(1, min(limit, 500)))}


@app.get("/api/angela/conversaciones/{conversation_id}")
def angela_conversation(conversation_id: str, u: dict = Depends(require_feature("auditoria"))):
    from core import angela_transcripts
    conv = angela_transcripts.get_transcript(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="conversación inexistente")
    return conv


@app.get("/api/oportunidades")
def oportunidades(u: dict = Depends(usuario_actual)):
    # P27·A — el set CERRADO de tarjetas con drill-down (cards), servido por el
    # MISMO cache que el resto del análisis (se invalida cuando los datos
    # cambian). El shape legacy (concretas/pendientes) se mantiene por compat.
    from core import analisis_cache, oportunidades_neg
    lang = _lang(u)
    r = ds.oportunidades(lang)
    todas = analisis_cache.get_o_computar(
        "oportunidades", lang, lambda: oportunidades_neg.cards(lang))
    # P43·C3 — cada rol ve los hallazgos de SU incumbencia. El cálculo es el
    # mismo para todos (y sigue siendo el canónico, cacheado una sola vez); el
    # recorte se aplica acá, por los módulos que la matriz «Quién ve qué» ya le
    # dio a esta persona. Al de depósito le llegaban los $85,7M de cobranza y la
    # exposición de clientes: no es su trabajo ni su información.
    r["cards"] = oportunidades_neg.visibles_para(
        todas, perfiles.features_efectivas(u["username"]))
    # P·counting — LOS MONTOS SALEN DE ACÁ, no de un `reduce` en la pantalla.
    # El mapa sumaba las tarjetas `recuperable` en el cliente, que es
    # exactamente de donde salió el «$900M»: la suma canónica ya vivía en
    # `opn.recuperable()` y una de las dos pantallas seguía haciéndose la suya.
    # Se calculan DESPUÉS del recorte por rol, igual que en `priorities.inbox`,
    # para que cada uno vea el total de lo que le corresponde ver.
    r["recuperable"] = oportunidades_neg.recuperable(cards_=r["cards"], lang=lang)
    r["exposicion"] = oportunidades_neg.exposicion(cards_=r["cards"], lang=lang)
    return r


@app.get("/api/prioridades")
def prioridades_get(u: dict = Depends(require_any_feature("alertas", "oportunidades"))):
    """Ranked “what should I do now” inbox. Same payload for desktop, mobile,
    the sidebar badge and Ángela — merge and sort live in core/priorities.
    inbox() caches the unfiltered compose (`prioridades`) and cuts by role."""
    from core import priorities
    return priorities.inbox(_lang(u), perfiles.features_efectivas(u["username"]))


class PatternFeedbackRequest(BaseModel):
    card_id: str
    action: str
    note: str | None = None


# --- Narrating a decision back to Ángela (core/app_events.py) ---------------
# Only decisions go here, never data changes: `core/` recalculates every
# figure, so she already sees a corrected row or a recorded payment. What she
# cannot see is that someone CHOSE something — dismissed a finding, taught a
# rule, dropped a widget. Params come from what the endpoint did, never from
# the request body, and the sentence is an i18n key rendered in the language
# of whichever conversation reads it.

# The whole vocabulary: the three buttons on a finding card
# (frontend/src/components/CardNegocio.jsx) and `pattern_feedback.learn`'s
# "accepted". `action` is a bare str on the request, hence the fallback key.
_FEEDBACK_EVENT = {
    "accepted": "core.app_events.finding_accepted",
    "already_knew": "core.app_events.finding_already_knew",
    "dismissed": "core.app_events.finding_dismissed",
}


def _who(u: dict) -> str:
    return u.get("nombre") or u.get("username") or "—"


def _finding_title(row: dict, card_id: str) -> str:
    """The finding's own title, which `pattern_feedback` snapshots when it
    records the reaction; its id is the fallback."""
    snapshot = (row or {}).get("snapshot") or {}
    return snapshot.get("titulo") or card_id


def _feedback_sources():
    """Every source of findings that can receive feedback through the one
    endpoint below: (module-gating dict, record_feedback function). Checked
    in order; the first source whose gating dict declares this card_id
    wins. core/patrones.py (learned patterns) and core/oportunidades_neg.py
    (the fixed rule set) share the same underlying mechanism
    (core/pattern_feedback.py) — this is just where the two get dispatched
    from one API surface."""
    from core import oportunidades_neg
    return (
        (patrones.MODULES_BY_ID, patrones.record_feedback),
        (oportunidades_neg.DOMINIO, oportunidades_neg.record_feedback),
    )


@app.post("/api/patrones/feedback")
def patrones_feedback(req: PatternFeedbackRequest, u: dict = Depends(usuario_actual)):
    """Owner's reaction (accepted/dismissed/already knew) to a finding, from
    any source — persisted so the same instance doesn't resurface. Gated by
    the finding's own domain, not a fixed feature, since each id declares
    its own modules."""
    for modules_by_id, record_fn in _feedback_sources():
        if req.card_id not in modules_by_id:
            continue
        needed = set(modules_by_id[req.card_id])
        if not needed <= set(perfiles.features_efectivas(u["username"])):
            raise HTTPException(status_code=403,
                                detail=i18n.t("authz.sin_feature", _lang(u), feature=req.card_id))
        try:
            row = record_fn(req.card_id, req.action, actor=u["username"],
                            note=req.note, lang=_lang(u))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except KeyError:
            raise HTTPException(status_code=404,
                                detail=i18n.t("api.patron_inexistente", _lang(u)))
        app_events.record(
            u["username"],
            _FEEDBACK_EVENT.get(req.action, "core.app_events.finding_feedback_other"),
            who=_who(u), title=_finding_title(row, req.card_id), action=req.action)
        return row
    raise HTTPException(status_code=404, detail=i18n.t("api.patron_inexistente", _lang(u)))


class HallazgoAprenderRequest(BaseModel):
    card_id: str
    tipo: str
    ambito: str
    nodo: str
    efecto: str
    entidad: str | None = None
    texto: str | None = None
    texto_en: str | None = None
    params: dict | None = None
    note: str | None = None


def _learn_sources():
    """Same dispatch as `_feedback_sources()`, for "Enseñar a Ángela":
    promoting a live finding into a durable core/conocimiento.py piece
    instead of just muting it. Any finding source that already has a
    record_feedback() gets this for free the moment it adds its own
    record_learn() wrapper (see core/patrones.py, core/oportunidades_neg.py)
    — no new code needed here or in core/conocimiento.py for a future source."""
    from core import oportunidades_neg
    return (
        (patrones.MODULES_BY_ID, patrones.record_learn),
        (oportunidades_neg.DOMINIO, oportunidades_neg.record_learn),
    )


@app.post("/api/patrones/aprender")
def patrones_aprender(req: HallazgoAprenderRequest, u: dict = Depends(require_admin)):
    """"Enseñar a Ángela": promote a live finding (from any source in
    _learn_sources()) into durable business knowledge. Owner-only — picking
    `efecto` changes what Ángela does going forward, the same bar
    POST /api/conocimiento already holds a hand-taught piece to. Statistics
    can say a deviation is real; only the owner decides what Ángela should
    DO about it, so tipo/ambito/nodo/efecto are never inferred here."""
    for modules_by_id, learn_fn in _learn_sources():
        if req.card_id not in modules_by_id:
            continue
        try:
            pieza = learn_fn(
                req.card_id, actor=u["username"], tipo=req.tipo, ambito=req.ambito,
                nodo=req.nodo, efecto=req.efecto, entidad=req.entidad, texto=req.texto,
                texto_en=req.texto_en, params=req.params, note=req.note, lang=_lang(u))
        except conocimiento.ConocimientoInvalido as e:
            raise HTTPException(status_code=400, detail=str(e))
        except KeyError:
            raise HTTPException(status_code=404,
                                detail=i18n.t("api.patron_inexistente", _lang(u)))
        app_events.record(u["username"], "core.app_events.rule_taught",
                          who=_who(u), effect=req.efecto, node=req.nodo,
                          text=(pieza or {}).get("texto") or req.card_id)
        return {"ok": True, "pieza": pieza}
    raise HTTPException(status_code=404, detail=i18n.t("api.patron_inexistente", _lang(u)))


@app.get("/api/patrones/historial")
def patrones_historial(u: dict = Depends(usuario_actual)):
    """What Ángela has flagged — from any source — and what the owner said
    back (core/pattern_feedback.py) — the Aprendizaje page's memory."""
    from core import pattern_feedback
    return {"historial": pattern_feedback.history()}


@app.get("/api/margenes")
def margenes_get(grupo: str | None = None, u: dict = Depends(require_feature("inventario"))):
    """P38·C — cuánto ganás por grupo, en los DOS canales (mayorista y
    mostrador), y el detalle producto por producto adentro de un grupo.
    Cacheado como el resto del análisis: se invalida cuando los datos cambian."""
    from core import analisis_cache, margenes
    lang = _lang(u)
    if grupo:
        return analisis_cache.get_o_computar(
            f"margenes_detalle_{grupo}", lang, lambda: margenes.detalle(grupo, lang))
    return analisis_cache.get_o_computar("margenes", lang, lambda: margenes.completo(lang))


@app.get("/api/traslados-internos")
def traslados_internos(u: dict = Depends(require_feature("inventario"))):
    """P38·F — lo que se movió a locales PROPIOS, separado de la venta real.
    Devuelve las dos lecturas del ranking: la cruda del ERP y la verdadera."""
    from core import analisis_cache, traslados
    lang = _lang(u)
    return analisis_cache.get_o_computar("traslados", lang,
                                         lambda: traslados.resumen(lang))


class VencimientoGestionRequest(BaseModel):
    codigo: int
    lote: str | None = None
    tipo: str                         # promocion | locales
    cantidad: float | None = None
    nota: str | None = None


@app.post("/api/vencimientos/gestionar")
def vencimientos_gestionar(req: VencimientoGestionRequest,
                           u: dict = Depends(require_feature("deposito"))):
    """The human's yes on the expiry card: persisted, audited, and the lot
    leaves the at-risk list. Before this the button set local state."""
    from core import vencimientos
    try:
        return vencimientos.gestionar(req.codigo, req.lote, req.tipo, actor=u["nombre"],
                                      cantidad=req.cantidad, nota=req.nota)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/api/vencimientos")
def vencimientos_get(dias: int = 30, u: dict = Depends(require_feature("deposito"))):
    """P38·H — vencimiento × ritmo real de venta: qué NO llegás a vender antes
    de que se venza, cuánta plata es y qué hacer con eso."""
    from core import vencimientos
    lang = _lang(u)
    r = vencimientos.en_riesgo(dias, lang)
    if r.get("disponible"):
        r["propuesta"] = vencimientos.propuesta(lang, dias)
    return r


@app.get("/api/cierres-locales")
def cierres_locales(dias: int = 7, u: dict = Depends(require_feature("caja"))):
    """P38·E — el reporte comparativo de cierres por local. Lo que una empleada
    imputa a mano en un Excel toda la semana, ya calculado."""
    from core import mostrador
    r = mostrador.comparativo(dias)
    if not r.get("disponible"):
        raise HTTPException(404, i18n.t("api.sin_mostrador", _lang(u)))
    return r


@app.get("/api/mostrador/costos-viejos")
def mostrador_costos_viejos(u: dict = Depends(require_feature("inventario"))):
    """Los productos del mostrador cuyo precio de venta salió de un costo viejo.

    Va sobre `inventario` —el permiso de mirar el catálogo— y no sobre `caja`:
    el que atiende el mostrador tiene el primero y no siempre el segundo, y es
    él quien mira ese precio todos los días. El dato ya existía en el libro
    triado del dueño; lo que faltaba era que llegara a la persona que puede
    hacer algo con él.
    """
    from core import mostrador
    return mostrador.costos_viejos(_lang(u))


class OrdenCompraRequest(BaseModel):
    codigo: int | None = None
    producto: str
    proveedor: str = ""
    cantidad: float = 0
    motivo: str = ""
    origen: str = "quiebre_inminente"


@app.post("/api/orden-compra/preparar")
def orden_compra_preparar(req: OrdenCompraRequest,
                          u: dict = Depends(require_feature("inventario"))):
    """P38·B — el dueño APRUEBA la orden que Ángela dejó armada. Aprobar no la
    manda al proveedor: la deja en borrador, firmada y auditada, lista para
    salir. Human-in-the-loop de punta a punta."""
    from core import ordenes
    orden = ordenes.preparar(producto=req.producto, codigo=req.codigo,
                             cantidad=req.cantidad, proveedor=req.proveedor,
                             actor=u.get("nombre") or u.get("username") or "dueño",
                             motivo=req.motivo, origen=req.origen)
    return {"ok": True, "orden": orden,
            "mensaje": i18n.t("api.oc_preparada", _lang(u), numero=orden["numero"],
                              proveedor=orden["proveedor"] or "—")}


@app.get("/api/ordenes-preparadas")
def ordenes_preparadas(_u: dict = Depends(require_feature("inventario"))):
    from core import ordenes
    return {"ordenes": ordenes.listar()}


class OrdenCompraManualRequest(BaseModel):
    proveedor: str
    ubicacion: str = ""
    fecha: str = ""
    motivo: str = ""
    items: list[dict]


@app.post("/api/ordenes-compra")
def ordenes_compra_crear(req: OrdenCompraManualRequest,
                         u: dict = Depends(require_feature("inventario"))):
    """La orden que el dueño arma a mano, sin esperar a que Ángela detecte un
    quiebre — mismo almacenamiento que orden_compra_preparar, otro origen."""
    from core import ordenes
    try:
        orden = ordenes.crear_manual(
            proveedor=req.proveedor, ubicacion=req.ubicacion, fecha=req.fecha,
            items=req.items, motivo=req.motivo,
            actor=u.get("nombre") or u.get("username") or "dueño")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True, "orden": orden}


class OrdenCompraEstadoRequest(BaseModel):
    estado: str


@app.post("/api/ordenes-compra/{numero}/estado")
def ordenes_compra_estado(numero: str, req: OrdenCompraEstadoRequest,
                          u: dict = Depends(require_feature("inventario"))):
    from core import ordenes
    try:
        orden = ordenes.actualizar_estado(
            numero, req.estado, actor=u.get("nombre") or u.get("username") or "dueño")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="Not Found")
    return {"ok": True, "orden": orden}


# --- Ubicaciones, proveedores y lotes: entidades reales del depósito ---

class UbicacionRequest(BaseModel):
    nombre: str
    nota: str = ""


@app.get("/api/ubicaciones")
def ubicaciones_listar(_u: dict = Depends(require_feature("inventario"))):
    from core import ubicaciones
    return {"ubicaciones": ubicaciones.listar()}


@app.post("/api/ubicaciones")
def ubicaciones_crear(req: UbicacionRequest, u: dict = Depends(require_feature("inventario"))):
    from core import ubicaciones
    try:
        return ubicaciones.crear(req.nombre, u.get("nombre") or u.get("username"), nota=req.nota)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/api/ubicaciones/{id}/actualizar")
def ubicaciones_actualizar(id: str, req: UbicacionRequest,
                           u: dict = Depends(require_feature("inventario"))):
    from core import ubicaciones
    try:
        return ubicaciones.actualizar(id, req.model_dump(), u.get("nombre") or u.get("username"))
    except KeyError:
        raise HTTPException(status_code=404, detail="Not Found")


@app.post("/api/ubicaciones/{id}/eliminar")
def ubicaciones_eliminar(id: str, u: dict = Depends(require_feature("inventario"))):
    from core import ubicaciones
    try:
        ubicaciones.eliminar(id, u.get("nombre") or u.get("username"))
    except KeyError:
        raise HTTPException(status_code=404, detail="Not Found")
    return {"ok": True}


class ProveedorRequest(BaseModel):
    nombre: str
    contacto: str = ""
    telefono: str = ""
    email: str = ""
    notas: str = ""


@app.get("/api/proveedores")
def proveedores_listar(_u: dict = Depends(require_feature("inventario"))):
    from core import proveedores
    return {"proveedores": proveedores.listar()}


@app.post("/api/proveedores")
def proveedores_crear(req: ProveedorRequest, u: dict = Depends(require_feature("inventario"))):
    from core import proveedores
    try:
        return proveedores.crear(req.model_dump(), u.get("nombre") or u.get("username"))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/api/proveedores/{id}/actualizar")
def proveedores_actualizar(id: str, req: ProveedorRequest,
                           u: dict = Depends(require_feature("inventario"))):
    from core import proveedores
    try:
        return proveedores.actualizar(id, req.model_dump(), u.get("nombre") or u.get("username"))
    except KeyError:
        raise HTTPException(status_code=404, detail="Not Found")


@app.post("/api/proveedores/{id}/eliminar")
def proveedores_eliminar(id: str, u: dict = Depends(require_feature("inventario"))):
    from core import proveedores
    try:
        proveedores.eliminar(id, u.get("nombre") or u.get("username"))
    except KeyError:
        raise HTTPException(status_code=404, detail="Not Found")
    return {"ok": True}


class LoteRequest(BaseModel):
    codigo: int | None = None
    producto: str = ""
    ubicacion: str
    lote: str = ""
    vencimiento: str | None = None
    cantidad: float = 0
    in_date: str | None = None
    counted_qty: float | None = None


@app.get("/api/lotes")
def lotes_listar(_u: dict = Depends(require_feature("inventario"))):
    from core import lotes
    return {"lotes": lotes.listar()}


@app.post("/api/lotes")
def lotes_crear(req: LoteRequest, u: dict = Depends(require_feature("inventario"))):
    from core import lotes
    try:
        return lotes.crear(req.model_dump(), u.get("nombre") or u.get("username"))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/api/lotes/{id}/actualizar")
def lotes_actualizar(id: str, req: LoteRequest, u: dict = Depends(require_feature("inventario"))):
    from core import lotes
    try:
        return lotes.actualizar(id, req.model_dump(), u.get("nombre") or u.get("username"))
    except KeyError:
        raise HTTPException(status_code=404, detail="Not Found")


@app.post("/api/lotes/{id}/eliminar")
def lotes_eliminar(id: str, u: dict = Depends(require_feature("inventario"))):
    from core import lotes
    try:
        lotes.eliminar(id, u.get("nombre") or u.get("username"))
    except KeyError:
        raise HTTPException(status_code=404, detail="Not Found")
    return {"ok": True}


def _csv_file(body: str, filename: str) -> Response:
    return Response(
        content=body.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class SaleRequest(BaseModel):
    fecha: str = ""
    producto: str
    codigo: int | None = None
    cantidad: float = 0
    precio: float | None = None
    source: str | None = None
    source_id: str | None = None
    source_status: str | None = None


@app.get("/api/sales")
def sales_list(q: str = "", sort: str | None = "fecha", dir: str = "desc",
               offset: int = 0, limit: int = 50, source: str | None = None,
               date_from: str | None = None, date_to: str | None = None,
               _u: dict = Depends(require_feature("inventario"))):
    from core import sales as sales_mod
    return sales_mod.list_page(q=q, sort=sort, direction=dir, offset=offset,
                               limit=limit, source=source, date_from=date_from,
                               date_to=date_to)


@app.get("/api/sales/export.csv")
def sales_export(q: str = "", sort: str | None = "fecha", dir: str = "desc",
                 source: str | None = None, date_from: str | None = None,
                 date_to: str | None = None,
                 _u: dict = Depends(require_feature("inventario"))):
    from core import sales as sales_mod
    return _csv_file(sales_mod.export_csv(
        q=q, sort=sort, direction=dir, source=source,
        date_from=date_from, date_to=date_to), "ventas.csv")


@app.post("/api/sales")
def sales_create(req: SaleRequest, u: dict = Depends(require_feature("inventario"))):
    from core import sales as sales_mod
    try:
        return sales_mod.create(req.model_dump(), u.get("nombre") or u.get("username"))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/api/sales/{id}/actualizar")
def sales_update(id: str, req: SaleRequest, u: dict = Depends(require_feature("inventario"))):
    from core import sales as sales_mod
    try:
        cambios = {k: v for k, v in req.model_dump().items() if v is not None}
        return sales_mod.update(id, cambios, u.get("nombre") or u.get("username"))
    except KeyError:
        raise HTTPException(status_code=404, detail="Not Found")


@app.post("/api/sales/{id}/eliminar")
def sales_delete(id: str, u: dict = Depends(require_feature("inventario"))):
    from core import sales as sales_mod
    try:
        sales_mod.delete(id, u.get("nombre") or u.get("username"))
    except KeyError:
        raise HTTPException(status_code=404, detail="Not Found")
    return {"ok": True}


class ReceiptRequest(BaseModel):
    fecha: str = ""
    producto: str
    codigo: int | None = None
    proveedor: str = ""
    cantidad: float = 0
    deposito: str = ""
    origen: str = ""
    po_number: str = ""
    source: str | None = None
    source_id: str | None = None
    source_status: str | None = None


@app.get("/api/receipts")
def receipts_list(q: str = "", sort: str | None = "fecha", dir: str = "desc",
                  offset: int = 0, limit: int = 50, source: str | None = None,
                  date_from: str | None = None, date_to: str | None = None,
                  proveedor: str | None = None, deposito: str | None = None,
                  po_number: str | None = None, sin_po: int = 0,
                  _u: dict = Depends(require_feature("inventario"))):
    from core import receipts as receipts_mod
    return receipts_mod.list_page(q=q, sort=sort, direction=dir, offset=offset,
                                  limit=limit, source=source, date_from=date_from,
                                  date_to=date_to, proveedor=proveedor,
                                  deposito=deposito, po_number=po_number,
                                  sin_po=bool(sin_po))


@app.get("/api/receipts/export.csv")
def receipts_export(q: str = "", sort: str | None = "fecha", dir: str = "desc",
                    source: str | None = None, date_from: str | None = None,
                    date_to: str | None = None, proveedor: str | None = None,
                    deposito: str | None = None, po_number: str | None = None,
                    sin_po: int = 0,
                    _u: dict = Depends(require_feature("inventario"))):
    from core import receipts as receipts_mod
    return _csv_file(receipts_mod.export_csv(
        q=q, sort=sort, direction=dir, source=source,
        date_from=date_from, date_to=date_to, proveedor=proveedor,
        deposito=deposito, po_number=po_number, sin_po=bool(sin_po)),
        "recepciones.csv")


@app.post("/api/receipts")
def receipts_create(req: ReceiptRequest, u: dict = Depends(require_feature("inventario"))):
    from core import receipts as receipts_mod
    try:
        return receipts_mod.create(req.model_dump(), u.get("nombre") or u.get("username"))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/api/receipts/{id}/actualizar")
def receipts_update(id: str, req: ReceiptRequest,
                    u: dict = Depends(require_feature("inventario"))):
    from core import receipts as receipts_mod
    try:
        cambios = {k: v for k, v in req.model_dump().items() if v is not None}
        return receipts_mod.update(id, cambios, u.get("nombre") or u.get("username"))
    except KeyError:
        raise HTTPException(status_code=404, detail="Not Found")


@app.post("/api/receipts/{id}/eliminar")
def receipts_delete(id: str, u: dict = Depends(require_feature("inventario"))):
    from core import receipts as receipts_mod
    try:
        receipts_mod.delete(id, u.get("nombre") or u.get("username"))
    except KeyError:
        raise HTTPException(status_code=404, detail="Not Found")
    return {"ok": True}


@app.get("/api/productos")
def productos_list(q: str = "", sort: str | None = "descripcion", dir: str = "asc",
                   offset: int = 0, limit: int = 50, source: str | None = None,
                   filtro: str | None = None, err: str | None = None,
                   tipo: str | None = None, proveedor: str | None = None,
                   _u: dict = Depends(require_feature("inventario"))):
    return store.list_page(q=q, sort=sort, direction=dir, offset=offset, limit=limit,
                           source=source, filtro=filtro, err=err,
                           tipo=tipo, proveedor=proveedor)


@app.get("/api/productos/export.csv")
def productos_export(q: str = "", sort: str | None = "descripcion", dir: str = "asc",
                     source: str | None = None, filtro: str | None = None,
                     err: str | None = None, tipo: str | None = None,
                     proveedor: str | None = None,
                     _u: dict = Depends(require_feature("inventario"))):
    return _csv_file(store.export_csv(
        q=q, sort=sort, direction=dir, source=source, filtro=filtro, err=err,
        tipo=tipo, proveedor=proveedor),
        "productos.csv")


@app.post("/api/articulos/{codigo}/eliminar")
def articulos_eliminar(codigo: int, u: dict = Depends(require_feature("inventario"))):
    try:
        store.eliminar_articulo(codigo, u.get("nombre") or u.get("username"))
    except KeyError:
        raise HTTPException(status_code=404, detail="Not Found")
    return {"ok": True}


@app.get("/api/movimientos")
def movimientos_list(q: str = "", sort: str | None = "producto", dir: str = "asc",
                     offset: int = 0, limit: int = 50, source: str | None = None,
                     discrepancia: int = 0, date_from: str | None = None,
                     date_to: str | None = None, ubicacion: str | None = None,
                     proximos: int = 0,
                     _u: dict = Depends(require_feature("inventario"))):
    from core import lotes
    return lotes.list_page(q=q, sort=sort, direction=dir, offset=offset,
                           limit=limit, source=source,
                           discrepancia=bool(discrepancia),
                           date_from=date_from, date_to=date_to,
                           ubicacion=ubicacion,
                           proximos=proximos or None)


@app.get("/api/movimientos/export.csv")
def movimientos_export(q: str = "", sort: str | None = "producto", dir: str = "asc",
                       source: str | None = None, discrepancia: int = 0,
                       date_from: str | None = None, date_to: str | None = None,
                       ubicacion: str | None = None, proximos: int = 0,
                       _u: dict = Depends(require_feature("inventario"))):
    from core import lotes
    return _csv_file(lotes.export_csv(q=q, sort=sort, direction=dir, source=source,
                                      discrepancia=bool(discrepancia),
                                      date_from=date_from, date_to=date_to,
                                      ubicacion=ubicacion,
                                      proximos=proximos or None),
                     "movimientos.csv")


@app.get("/api/conciliacion")
def conciliacion_list(u: dict = Depends(require_feature("deposito"))):
    from core import conciliacion
    return conciliacion.resumen(lang=_lang(u))


@app.post("/api/conciliacion/{id}/aceptar")
def conciliacion_aceptar(id: str, u: dict = Depends(require_feature("deposito"))):
    from core import conciliacion
    try:
        return conciliacion.aceptar(id, u.get("nombre") or u.get("username"))
    except KeyError:
        raise HTTPException(status_code=404, detail="Not Found")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


class ArticuloRequest(BaseModel):
    codigo: int
    descripcion: str
    tipo: str = ""
    proveedor: str = ""
    stock: float = 0
    costo_iva: float | None = None
    pvp: float | None = None


@app.post("/api/articulos")
def articulos_crear(req: ArticuloRequest, u: dict = Depends(require_feature("inventario"))):
    from core import store
    try:
        return store.crear_articulo(req.model_dump(), u.get("nombre") or u.get("username"))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


class ArticuloActualizarRequest(BaseModel):
    descripcion: str | None = None
    tipo: str | None = None
    proveedor: str | None = None
    stock: float | None = None
    costo_iva: float | None = None
    pvp: float | None = None
    estado: str | None = None


@app.post("/api/articulos/{codigo}/actualizar")
def articulos_actualizar(codigo: int, req: ArticuloActualizarRequest,
                         u: dict = Depends(require_feature("inventario"))):
    from core import store
    cambios = {k: v for k, v in req.model_dump().items() if v is not None}
    try:
        return store.actualizar_articulo(codigo, cambios, u.get("nombre") or u.get("username"))
    except KeyError:
        raise HTTPException(status_code=404, detail="Not Found")


@app.get("/api/macro")
def macro_get(u: dict = Depends(require_feature("mapa"))):
    """P28 — el nodo 'Contexto económico' del mapa: IPC y dólar REALES ya
    cargados (core/macro trae su propio cache y su fallback honesto:
    disponible=False cuando no hay dato — el nodo lo dice, no inventa)."""
    from core import macro
    return macro.consultar(["inflacion", "dolar"], _lang(u))


@app.get("/api/cobranza")
def cobranza_get(u: dict = Depends(require_feature("cuentas"))):
    """A QUIÉN COBRAR PRIMERO — sobre la deuda que YA existe.

    No es credit scoring: no decide a quién darle crédito ni a quién cortárselo.
    Ordena por `saldo × días de más respecto del promedio de ESE cliente`, que
    es la plata que te están financiando fuera de su propia costumbre. La mora
    la sigue calculando cuentas.py; acá no se recalcula nada."""
    from core import cobranza
    return cobranza.prioridad()


@app.get("/api/cobranza/{cliente_id}/propuesta")
def cobranza_propuesta(cliente_id: str, u: dict = Depends(require_feature("cuentas"))):
    """El recordatorio listo para mandar. NO manda nada: es la propuesta."""
    from core import cobranza
    r = cobranza.proponer(cliente_id, _lang(u))
    if not r:
        raise HTTPException(status_code=404, detail="cliente inexistente")
    return r


class CobranzaRegistrarRequest(BaseModel):
    cliente_id: str
    estado: str                       # recordado | promesa | pagado | sin_respuesta
    nota: str | None = None
    promesa_fecha: str | None = None  # ISO, cuando el cliente se comprometió
    mensaje: str | None = None        # lo que se mandó, con las ediciones del dueño


@app.post("/api/cobranza/registrar")
def cobranza_registrar(req: CobranzaRegistrarRequest,
                       u: dict = Depends(require_feature("cuentas"))):
    """El sí del humano: recién acá la gestión existe, y queda auditada."""
    from core import carpeta, cobranza
    try:
        r = cobranza.registrar(req.cliente_id, req.estado, actor=u["nombre"],
                               nota=req.nota, promesa_fecha=req.promesa_fecha,
                               mensaje=req.mensaje)
        # Propose → approve, applied to paperwork: right after chasing a
        # customer, the statement is the next thing that person needs. It is
        # OFFERED, never generated: `sugerencia` writes nothing.
        if "documentos" in perfiles.features_efectivas(u["username"]):
            r["sugerencia"] = carpeta.sugerencia("cobranza", cliente=r.get("cliente"),
                                                 lang=_lang(u))
        return r
    except KeyError:
        raise HTTPException(status_code=404, detail="cliente inexistente")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/api/inventario/viz")
def inventario_viz(u: dict = Depends(require_feature("inventario"))):
    """Cuts of idle capital, rotation, expiry, seasonality, GMROI, aging and
    lead-time truth. Cached like the other analyses; numbers still come from
    core/, never from the model."""
    from core import analisis_cache, stock_viz
    lang = _lang(u)
    return analisis_cache.get_o_computar("stock_viz", lang, lambda: stock_viz.pack(lang))


@app.get("/api/inventario/burn/{codigo}")
def inventario_burn(codigo: int, u: dict = Depends(require_feature("inventario"))):
    """60-day projected stock for one SKU: on-hand decaying at daily rate,
    inbound PO as a step at the supplier lead."""
    from core import stock_viz
    return stock_viz.product_burn(codigo, _lang(u))


@app.get("/api/ficha/producto/{codigo}")
def ficha_producto(codigo: int, u: dict = Depends(require_feature("inventario"))):
    """La ficha de UN producto: dónde está, cuánto hay, a cuánto se vende, qué
    se vence, quién lo compra y qué dijo el equipo de él.

    En el teléfono no se llega acá por una lista de 430 filas —nadie la
    scrollea con guantes— sino por una búsqueda, un escaneo o una tarea que ya
    lo trae enfocado. Todos los números salen de su motor y se citan; no hay
    ninguno nuevo y no hay ningún total.
    """
    from core import ficha
    f = ficha.producto(codigo, _lang(u))
    if not f:
        # Escanear algo que no está en el catálogo es un caso REAL del
        # depósito. Se dice, no se inventa una ficha vacía.
        raise HTTPException(404, i18n.t("api.producto_inexistente", _lang(u)))
    return f


@app.get("/api/reponer")
def reponer_get(u: dict = Depends(require_feature("inventario"))):
    """QUÉ REPONER PRIMERO — el ranking, no un solo hallazgo.

    La card de quiebre muestra el peor producto del top-15 por facturación.
    Esto contesta la pregunta que sigue: "¿y qué más?". Ordenado por la plata
    que se deja de facturar (días sin stock × venta diaria) y agrupado por
    proveedor, que es como se compra de verdad: una orden, N renglones.

    Determinista: acá no opina el modelo, y la cobertura sale de la MISMA
    derivación que rotación."""
    from core import analisis_cache, reponer
    return analisis_cache.get_o_computar("reponer", None, lambda: reponer.analizar())


@app.get("/api/grafo")
def grafo_get(u: dict = Depends(require_feature("mapa"))):
    """EL CEREBRO — las ENTIDADES del negocio (productos, clientes, proveedores,
    remitos, cuentas, locales, rubros) y las relaciones reales que las cruzan.

    Aditivo: el mapa de árbol (P28–P41) no consume este endpoint y no cambia.
    Acá no nace ningún número canónico — core/grafo.py cruza lo que cuentas,
    depósito, finanzas y oportunidades ya decidieron. Cacheado como el resto
    del análisis: el cruce completo se paga una vez por idioma."""
    from core import analisis_cache, grafo
    lang = _lang(u)
    return analisis_cache.get_o_computar("grafo", lang, lambda: grafo.completo(lang))


@app.get("/api/mapa-operacion")
def mapa_operacion_get(u: dict = Depends(require_feature("mapa"))):
    """THE OPERATION MAP — the physical chain: where goods come from, where
    they are and where they go, plus the context layer no ERP captures (team
    heads-ups, house rules, what returns to the system).

    Additive: neither the sources map (/api/grafo's tree) nor the brain
    consume this. No canonical number is born here — core/mapa_operacion.py
    reads deposito/recepciones/logistica/ordenes_compra and crosses what
    cuentas, conocimiento and the audit log already decided. Cached per
    language like every analysis (core/analisis_cache)."""
    from core import mapa_operacion
    return mapa_operacion.mapa(_lang(u))


@app.get("/api/mapa-operacion/nodo/{nid}")
def mapa_operacion_nodo(nid: str, u: dict = Depends(require_feature("mapa"))):
    """One node's panel: what is going on, where it came from, what can be
    done, and — folded at the bottom — the row listing. Read-only; the
    "do it" button asks Ángela through the normal propose→approve rail."""
    from core import mapa_operacion
    d = mapa_operacion.detalle(nid, _lang(u))
    if d is None:
        raise HTTPException(status_code=404, detail="Not Found")
    return d


@app.get("/api/analisis")
def analisis_completo(u: dict = Depends(require_feature("oportunidades"))):
    """Los cruces (P7): rotación×inmovilizado, estacionalidad decenal, push/pull
    y objetivos propuestos. Sin ventas validadas → disponible=False con motivo.
    P11·B4: cacheado por tenant e idioma — entrar a Oportunidades es instantáneo
    y gratis; se recomputa solo cuando los datos cambian."""
    from core import analisis, analisis_cache
    lang = _lang(u)
    return analisis_cache.get_o_computar("analisis", lang,
                                         lambda: analisis.completo(lang))


@app.get("/api/widget-datos/plata-parada")
def widget_plata_parada(dias: int = 120, u: dict = Depends(require_feature("inventario"))):
    """P19·C — el dato de las cards a pedido ('plata en productos de 120+ días'):
    corte por umbral sobre la MISMA derivación de rotación. Se recalcula en cada
    carga; si no hay ventas validadas responde disponible=False con motivo."""
    from core import analisis
    return analisis.plata_parada_mas_de(dias, _lang(u))


class ConsultaRequest(BaseModel):
    consulta: dict


@app.post("/api/consulta-serie")
def consulta_serie(req: ConsultaRequest, u: dict = Depends(usuario_actual)):
    """P21 — el dato de los widgets generativos: LECTURA pura contra el contrato
    validado de core/consultas.py, recalculada en cada entrada. El gate es por
    FUENTE (cada fuente pertenece a su módulo)."""
    from core import consultas, perfiles
    fuente = str(req.consulta.get("fuente") or "ventas").strip().lower()
    fuente = consultas.FUENTE_ALIAS.get(fuente, fuente)  # el gate ve la fuente real
    feature = {"ventas": "evolucion", "inventario": "inventario",
               "cuentas": "cuentas", "caja": "caja"}.get(fuente)
    if feature and feature not in perfiles.features_efectivas(u["username"]):
        raise HTTPException(status_code=403,
                            detail=i18n.t("authz.sin_feature", _lang(u), feature=feature))
    return consultas.consultar(req.consulta, _lang(u))


@app.get("/api/fase")
def fase_actual(u: dict = Depends(usuario_actual)):
    """La fase del negocio: el sistema define qué mostrar según la etapa."""
    return fase.actual(_lang(u))


@app.get("/api/articulos")
def articulos(_u: dict = Depends(require_feature("inventario"))):
    """Todos los artículos con su estado de calidad (tabla 'ver todo')."""
    return {"items": store.articulos_con_estado()}


@app.get("/api/balanzas")
def balanzas(_u: dict = Depends(require_feature("inventario"))):
    """Productos de balanza (venta por peso): su propia categoría con kg y $/kg."""
    items = store.articulos_balanza()
    return {"items": items, "total": len(items)}


# --- Memoria del usuario (Plan 4) ---

def _propio_o_admin(usuario: str, u: dict):
    """La memoria/preferencias son del propio usuario (o el dueño)."""
    if u["username"] != usuario and not u.get("es_admin"):
        raise HTTPException(status_code=403,
                            detail=i18n.t("api.solo_preferencias", _lang(u)))


@app.get("/api/memoria/{usuario}")
def memoria_get(usuario: str, u: dict = Depends(usuario_actual)):
    _propio_o_admin(usuario, u)
    return memoria.get(usuario)


class PrefRequest(BaseModel):
    clave: str
    valor: object


@app.post("/api/memoria/{usuario}")
def memoria_set(usuario: str, req: PrefRequest, u: dict = Depends(usuario_actual)):
    _propio_o_admin(usuario, u)
    return memoria.set_pref(usuario, req.clave, req.valor)


# --- P19·A — preferencias de vista (transparencia total: se ven y se borran) ---
# El MISMO espacio que escribe Ángela por chat (memoria.json → vista): acá el
# frontend lo hidrata al entrar, Mi perfil lo lista, y cada preferencia se
# borra una por una. Siempre del PROPIO usuario (el token decide, no la URL).

@app.get("/api/preferencias")
def preferencias_get(u: dict = Depends(usuario_actual)):
    m = memoria.get(u["username"])
    return {"vista": m.get("vista", {}), "notas": m.get("preferencias", {})}


@app.post("/api/preferencias")
def preferencias_set(req: PrefRequest, u: dict = Depends(usuario_actual)):
    """Escritura directa del frontend (la X de un widget, deshacer un orden).
    Mismas validaciones que la tool de Ángela: catálogo cerrado."""
    try:
        vista = memoria.set_vista(u["username"], req.clave, req.valor)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    app_events.record(u["username"], "core.app_events.view_pref_set",
                      who=_who(u), key=req.clave)
    return {"ok": True, "vista": vista}


@app.delete("/api/preferencias/{clave}")
def preferencias_del(clave: str, u: dict = Depends(usuario_actual)):
    borrada = memoria.borrar_vista(u["username"], clave)
    if not borrada:
        raise HTTPException(status_code=404, detail="esa preferencia no existe")
    app_events.record(u["username"], "core.app_events.view_pref_removed",
                      who=_who(u), key=clave)
    m = memoria.get(u["username"])
    return {"ok": True, "vista": m.get("vista", {}), "notas": m.get("preferencias", {})}


# --- Business knowledge ("what Aldo taught Ángela") ---
# The unstructured layer: rules, exceptions, protocols, and context no ERP
# has. Reading is role-scoped (the owner sees everything; an employee sees
# their own scope). Creating/pausing/deleting a CONFIRMED piece is still
# owner-only (require_admin). But any user can PROPOSE one via Ángela's chat
# (proponer_conocimiento in angela.py) — it's born in "pendiente" state, with
# no effect, until someone with that node approves or rejects it (/aprobar,
# /rechazar — same scope as visibles_para, not admin-only).
# Persists per-tenant in business_knowledge_pieces (core/db/business_knowledge_repo.py).

def _con_procedencia(piezas: list[dict]) -> list[dict]:
    """Flattens origen.{quien,cuando} onto each piece, on top of every other
    field — the panel and the chat citation card (KnowledgePanel.tsx,
    KnowledgeCite.tsx) read piece.quien/piece.cuando directly, but the raw
    piece dict only carries them nested under `origen`."""
    out = []
    for p in piezas:
        origen = p.get("origen") or {}
        out.append({**p, "quien": origen.get("quien"), "cuando": origen.get("cuando")})
    return out


@app.get("/api/conocimiento")
def conocimiento_listar(nodo: str | None = None, tipo: str | None = None,
                        entidad: str | None = None, ambito: str | None = None,
                        u: dict = Depends(usuario_actual)):
    piezas = conocimiento.listar(nodo=nodo, tipo=tipo, entidad=entidad, ambito=ambito)
    piezas = conocimiento.visibles_para(u, piezas)
    return {"piezas": _con_procedencia(piezas), "total": len(piezas)}


@app.get("/api/conocimiento/pendientes")
def conocimiento_pendientes(nodo: str | None = None, u: dict = Depends(usuario_actual)):
    """Proposals someone left via chat (proponer_conocimiento) that haven't
    been activated or rejected yet — THIS user's review queue: same
    node/feature scope that already governs which active knowledge each
    user sees (`visibles_para`), not a separate permission. Declared BEFORE
    /{pid} — otherwise "pendientes" would match there as if it were an id."""
    piezas = conocimiento.visibles_para(u, conocimiento.pendientes(nodo=nodo))
    return {"piezas": _con_procedencia(piezas), "total": len(piezas)}


@app.get("/api/conocimiento/{pid}")
def conocimiento_detalle(pid: str, u: dict = Depends(usuario_actual)):
    p = conocimiento.detalle(pid)
    if not p or p not in conocimiento.visibles_para(u, [p]):
        raise HTTPException(status_code=404, detail=i18n.t("api.conocimiento_inexistente", _lang(u)))
    return p


@app.get("/api/conocimiento/{pid}/historial")
def conocimiento_historial(pid: str, u: dict = Depends(usuario_actual)):
    p = conocimiento.detalle(pid)
    if not p or p not in conocimiento.visibles_para(u, [p]):
        raise HTTPException(status_code=404, detail=i18n.t("api.conocimiento_inexistente", _lang(u)))
    from core.audit import AuditLog
    return {"eventos": AuditLog().list_for(pid)}


class ConocimientoNuevo(BaseModel):
    texto: str
    tipo: str
    ambito: str
    nodo: str
    efecto: str
    entidad: str | None = None
    params: dict | None = None


class KnowledgeProposal(BaseModel):
    texto: str
    nodo: str
    tipo: str = "contexto"
    ambito: str = "global"
    efecto: str = "contexto_para_angela"
    entidad: str | None = None


def _can_activate(u: dict, nodo: str, ambito: str) -> bool:
    """Whether this user's confirmation activates a piece outright or only
    queues it. A global piece reaches everyone, so it stays admin-only —
    `visibles_para` would wave it through for any employee."""
    if u.get("es_admin"):
        return True
    if ambito == "global":
        return False
    from core import perfiles
    return conocimiento.NODO_FEATURE.get(nodo) in set(perfiles.features_efectivas(u["username"]))


@app.post("/api/conocimiento/confirm")
def conocimiento_confirm(req: KnowledgeProposal, u: dict = Depends(usuario_actual)):
    """The user taps 'keep' on a chip Ángela proposed (angela.py's
    proponer_conocimiento writes nothing). Lands active when they could have
    reviewed it anyway, pending otherwise."""
    from core import fechas
    try:
        proposal = conocimiento.validate_proposal(
            texto=req.texto, tipo=req.tipo, ambito=req.ambito, nodo=req.nodo,
            efecto=req.efecto, entidad=req.entidad)
    except conocimiento.ConocimientoInvalido as e:
        raise HTTPException(status_code=400, detail=str(e))

    existing = conocimiento.find_duplicate(texto=proposal["texto"], nodo=proposal["nodo"],
                                           entidad=proposal["entidad"])
    if existing:
        return {"ok": True, "piece": existing, "state": existing["estado"], "already_existed": True}

    state = "activo" if _can_activate(u, proposal["nodo"], proposal["ambito"]) else "pendiente"
    piece = conocimiento.crear(
        **proposal, estado=state,
        origen={"quien": u["username"], "cuando": fechas.hoy().isoformat()})
    return {"ok": True, "piece": piece, "state": state, "already_existed": False}


@app.post("/api/conocimiento")
def conocimiento_crear(req: ConocimientoNuevo, u: dict = Depends(require_admin)):
    from core import fechas
    try:
        pieza = conocimiento.crear(
            texto=req.texto, tipo=req.tipo, ambito=req.ambito, nodo=req.nodo,
            efecto=req.efecto, entidad=req.entidad, params=req.params,
            origen={"quien": u["username"], "cuando": fechas.hoy().isoformat()})
    except conocimiento.ConocimientoInvalido as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "pieza": pieza}


class ConocimientoEstado(BaseModel):
    estado: str


@app.post("/api/conocimiento/{pid}/estado")
def conocimiento_estado(pid: str, req: ConocimientoEstado, u: dict = Depends(require_admin)):
    try:
        pieza = conocimiento.set_estado(pid, req.estado)
    except conocimiento.ConocimientoInvalido as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not pieza:
        raise HTTPException(status_code=404, detail=i18n.t("api.conocimiento_inexistente", _lang(u)))
    return {"ok": True, "pieza": pieza}


@app.delete("/api/conocimiento/{pid}")
def conocimiento_borrar(pid: str, u: dict = Depends(require_admin)):
    if not conocimiento.borrar(pid):
        raise HTTPException(status_code=404, detail=i18n.t("api.conocimiento_inexistente", _lang(u)))
    return {"ok": True}


def _revisor_o_404(pid: str, u: dict) -> dict:
    """Only someone who'd already see this as active knowledge can review
    (approve/reject) a proposal — same node/feature scope as visibles_para,
    not a separate "reviewer" permission. Returns the piece or raises 404
    (whether it doesn't exist or it just isn't this user's: we don't
    distinguish, same criterion as conocimiento_detalle)."""
    p = conocimiento.detalle(pid)
    if not p or p not in conocimiento.visibles_para(u, [p]):
        raise HTTPException(status_code=404, detail=i18n.t("api.conocimiento_inexistente", _lang(u)))
    return p


def _editor_o_403(pid: str, u: dict) -> dict:
    p = conocimiento.detalle(pid)
    if not p or p not in conocimiento.visibles_para(u, [p]):
        raise HTTPException(status_code=404, detail=i18n.t("api.conocimiento_inexistente", _lang(u)))
    if not (u.get("es_admin") or (p.get("origen") or {}).get("quien") == u["username"]):
        raise HTTPException(status_code=403, detail=i18n.t("api.conocimiento_sin_permiso", _lang(u)))
    return p


class ConocimientoEditar(BaseModel):
    texto: str | None = None
    texto_en: str | None = None
    tipo: str | None = None
    ambito: str | None = None
    efecto: str | None = None
    entidad: str | None = None
    params: dict | None = None


@app.post("/api/conocimiento/{pid}/editar")
def conocimiento_editar(pid: str, req: ConocimientoEditar, u: dict = Depends(usuario_actual)):
    _editor_o_403(pid, u)
    try:
        pieza = conocimiento.edit_piece(
            pid, actor=u["username"], is_admin=bool(u.get("es_admin")),
            texto=req.texto, texto_en=req.texto_en, tipo=req.tipo, ambito=req.ambito,
            efecto=req.efecto, entidad=req.entidad, params=req.params)
    except conocimiento.ConocimientoInvalido as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "pieza": pieza}


@app.post("/api/conocimiento/{pid}/aprobar")
def conocimiento_aprobar(pid: str, u: dict = Depends(usuario_actual)):
    p = _revisor_o_404(pid, u)
    if p["estado"] != "pendiente":
        raise HTTPException(status_code=400, detail=i18n.t("api.conocimiento_no_pendiente", _lang(u)))
    pieza = conocimiento.aprobar(pid, u["username"])
    return {"ok": True, "pieza": pieza}


@app.post("/api/conocimiento/{pid}/rechazar")
def conocimiento_rechazar(pid: str, u: dict = Depends(usuario_actual)):
    p = _revisor_o_404(pid, u)
    if p["estado"] != "pendiente":
        raise HTTPException(status_code=400, detail=i18n.t("api.conocimiento_no_pendiente", _lang(u)))
    conocimiento.rechazar(pid, u["username"])
    return {"ok": True}


# --- Importador asistido (Plan 4) ---

class ImportPreviewRequest(BaseModel):
    csv: str
    destino: str = "venta_historica"
    usuario: str | None = None


@app.post("/api/import/preview")
def import_preview(req: ImportPreviewRequest, _u: dict = Depends(require_feature("cargar"))):
    if not req.csv.strip():
        raise HTTPException(status_code=400,
                            detail=i18n.t("api.archivo_vacio", _lang(_u)))
    info = importer.previsualizar_csv(req.csv, req.destino)
    if req.usuario:
        memoria.marcar_dato_cargado(req.usuario, req.destino)
    return info


class OtroArchivoRequest(BaseModel):
    nombre: str
    descripcion: str = ""
    usuario: str | None = None


@app.post("/api/cargar/otro")
def cargar_otro(req: OtroArchivoRequest, _u: dict = Depends(require_feature("cargar"))):
    memoria.agregar_archivo_libre(req.usuario or "dueño", req.nombre, req.descripcion)
    desc = f" Entendí que es: {req.descripcion}." if req.descripcion.strip() else ""
    return {"ok": True, "mensaje": f"Recibí «{req.nombre}».{desc} Lo guardé en la memoria de tu negocio."}


# --- Staging Area (zona de revisión): los datos nuevos pasan por acá ---

class StagingCrearRequest(BaseModel):
    nombre: str
    csv: str


class ResolverRequest(BaseModel):
    obs_id: str
    accion: str
    params: dict = {}


@app.post("/api/staging")
def staging_crear(req: StagingCrearRequest, u: dict = Depends(require_feature("cargar"))):
    if not req.csv.strip():
        raise HTTPException(status_code=400,
                            detail=i18n.t("api.archivo_vacio", _lang(u)))
    return staging.crear_batch(req.nombre, req.csv, _lang(u))


@app.get("/api/staging")
def staging_listar(u: dict = Depends(require_feature("cargar"))):
    # P24·G4 — la revisión habla el idioma de QUIEN MIRA, no del que creó el batch
    lang = _lang(u)
    return {"batches": [staging.localizar_batch(b, lang) for b in staging.listar()]}


@app.post("/api/staging/{batch_id}/resolver")
def staging_resolver(batch_id: str, req: ResolverRequest,
                     _u: dict = Depends(require_feature("cargar"))):
    try:
        return staging.resolver(batch_id, req.obs_id, req.accion, req.params)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/staging/{batch_id}/preview")
def staging_preview(batch_id: str, _u: dict = Depends(require_feature("cargar"))):
    try:
        return staging.preview(batch_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/staging/{batch_id}/integrar")
def staging_integrar(batch_id: str, u: dict = Depends(require_feature("cargar"))):
    try:
        return staging.integrar(batch_id, lang=_lang(u))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/staging/{batch_id}/descartar")
def staging_descartar(batch_id: str, _u: dict = Depends(require_feature("cargar"))):
    return staging.descartar(batch_id)


@app.post("/api/staging/{batch_id}/normalizacion/revertir")
def staging_revertir_normalizacion(batch_id: str,
                                   u: dict = Depends(require_feature("cargar"))):
    """Deshace el Nivel 1 (normalización automática) de un batch: vuelve al crudo."""
    try:
        return staging.revertir_normalizacion(batch_id, lang=_lang(u))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/contexto")
def contexto_listar(_u: dict = Depends(require_feature("admin_contexto"))):
    return {"items": ds.contexto_listar()}


class ContextoRequest(BaseModel):
    nombre: str
    tipo: str = "general"
    texto: str


@app.post("/api/contexto")
def contexto_agregar(req: ContextoRequest,
                     _u: dict = Depends(require_feature("admin_contexto"))):
    if not req.texto.strip():
        raise HTTPException(status_code=400,
                            detail=i18n.t("api.contenido_vacio", _lang(_u)))
    return ds.contexto_agregar(req.nombre, req.tipo, req.texto)


@app.get("/api/calidad")
def calidad(u: dict = Depends(require_feature("saneamiento"))):
    """Libro triado de calidad de dato (reemplaza las 'alertas')."""
    return store.libro_triado(_lang(u))


@app.get("/api/anomalias")
def anomalias_listar(_u: dict = Depends(require_feature("saneamiento"))):
    """Anomalías de negocio sobre los datos existentes (precio a pérdida, etc.)."""
    return {"anomalias": anomalias.analizar_existentes()}


class AnomaliaAplicarRequest(BaseModel):
    tipo: str
    accion: str
    params: dict = {}


@app.post("/api/anomalias/aplicar")
def anomalias_aplicar(req: AnomaliaAplicarRequest,
                      _u: dict = Depends(require_feature("saneamiento"))):
    try:
        return anomalias.aplicar(req.tipo, req.accion, req.params)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/versiones")
def versiones(_u: dict = Depends(require_feature("saneamiento"))):
    return {"versiones": store.versiones.list()}


@app.post("/api/versiones/{version_id}/restaurar")
def restaurar(version_id: int, u: dict = Depends(require_feature("saneamiento"))):
    try:
        snapshot = store.versiones.restore(version_id)
    except KeyError:
        raise HTTPException(status_code=404,
                            detail=i18n.t("api.version_inexistente", _lang(u),
                                          version_id=version_id))
    store.audit.record(actor=u["username"], accion="restaurar_version",
                       despues={"version_id": version_id})
    return {"version_id": version_id, "snapshot": snapshot}


@app.get("/api/audit")
def audit(_u: dict = Depends(require_admin)):
    return {"eventos": store.audit.list()}


# --- Bloque F · el registro de auditoría, LEGIBLE -----------------------------
# /api/audit sigue devolviendo el JSON crudo (depuración). Esto es la lectura
# para humanos: la misma fuente, clasificada, traducida y filtrable. No calcula
# nada nuevo — ver core/auditoria.py.

@app.get("/api/auditoria")
def auditoria_registro(clase: str | None = None, actor: str | None = None,
                       desde: str | None = None, hasta: str | None = None,
                       q: str | None = None, limite: int = 300,
                       u: dict = Depends(require_feature("auditoria"))):
    from core import auditoria
    return auditoria.registro(_lang(u), clase=clase, actor=actor,
                              desde=desde, hasta=hasta, q=q,
                              limite=max(1, min(limite, 2000)))


@app.get("/api/auditoria/hilo")
def auditoria_hilo(sujeto: str, u: dict = Depends(require_feature("auditoria"))):
    """La historia completa de UN cliente/archivo/persona: el «y después qué pasó»."""
    from core import auditoria
    return {"sujeto": sujeto, "eventos": auditoria.hilo(sujeto, _lang(u))}


# --- Bloque F · autonomía graduada -------------------------------------------

@app.get("/api/autonomia")
def autonomia_get(u: dict = Depends(require_feature("auditoria"))):
    from core import autonomia
    return autonomia.estado(_lang(u))


class AutonomiaRequest(BaseModel):
    clase: str
    nivel: str


@app.post("/api/autonomia")
def autonomia_set(req: AutonomiaRequest, u: dict = Depends(require_admin)):
    """Sólo el dueño mueve la perilla, y queda auditado como cualquier decisión.
    Las clases con candado (plata/stock/permisos) devuelven 422: no es un
    setting con default conservador, es una regla del producto."""
    from core import autonomia
    try:
        return autonomia.set_nivel(req.clase, req.nivel, actor=u["nombre"])
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# --- Saneamiento conversacional (Ángela ejecuta, con backup y reversión) ---

class SaneamientoRequest(BaseModel):
    # 'actor' del body ya NO se usa para identidad: el actor sale del token.
    actor: str = "dueño"


@app.get("/api/saneamiento/proponer/{categoria}")
def saneamiento_proponer(categoria: str, u: dict = Depends(require_feature("saneamiento"))):
    return saneamiento.proponer(categoria, _lang(u))


@app.post("/api/saneamiento/aplicar/{categoria}")
def saneamiento_aplicar(categoria: str, req: SaneamientoRequest | None = None,
                        u: dict = Depends(require_feature("saneamiento"))):
    try:
        return saneamiento.aplicar(categoria, actor=u["username"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/saneamiento/revertir/{version_id}")
def saneamiento_revertir(version_id: int, req: SaneamientoRequest | None = None,
                         u: dict = Depends(require_feature("saneamiento"))):
    try:
        return saneamiento.revertir(version_id, actor=u["username"])
    except KeyError:
        raise HTTPException(status_code=404,
                            detail=i18n.t("api.version_inexistente", _lang(u),
                                          version_id=version_id))


@app.post("/api/saneamiento/resetear")
def saneamiento_resetear(_u: dict = Depends(require_feature("saneamiento"))):
    store.resetear_actual()
    return {"ok": True, "mensaje": "Datos restaurados al original."}


# ---------------------------------------------------------------------------
# P22·C — Deploy de un solo servicio: reset admin + el frontend compilado.
# El catch-all del SPA va AL FINAL (los /api/* ya están registrados y ganan).
# ---------------------------------------------------------------------------

@app.post("/api/admin/reset-demo")
def admin_reset_demo(token: str):
    """Vuelve el demo público al estado canónico SIN reiniciar el contenedor.
    Protegido por POLPILOT_RESET_TOKEN (secret de Render, no es una credencial
    de usuario): sin el token exacto, 404 — el endpoint ni se revela. Además,
    el filesystem de Render es efímero: cada restart/redeploy resetea solo.

    Dos mitades, porque el estado vivo del demo vive en dos lugares:
      1. Archivos (fotos de perfil, adjuntos de piso, documentos generados,
         audios de muestra) — se restauran copiando de POLPILOT_CANONICAL_DIR,
         como siempre.
      2. Postgres (TODO lo demás — inventario, cuentas, caja, auditoría,
         staging, perfiles, etc., ver core/db/MIGRATING_A_MODULE.md) — se
         vacía para este tenant y se re-siembra desde el dataset real en
         disco (seed_db.seed_domains(), el mismo camino que un tenant recién
         montado).

    DEMO ONLY. On any other tenant it 404s before doing anything, even with
    the right token: POLPILOT_CANONICAL_DIR is image-wide and boot.py always
    makes the canonical copy, so a productive service that set
    POLPILOT_RESET_TOKEN (render.yaml declares it for every copy of the
    service block) would otherwise expose an endpoint that truncates a paying
    client's data. A productive tenant simply omits the token — this gate is
    what makes that not merely a convention."""
    import shutil
    if not _es_demo():
        raise HTTPException(status_code=404, detail="Not Found")
    esperado = os.environ.get("POLPILOT_RESET_TOKEN")
    canonical = os.environ.get("POLPILOT_CANONICAL_DIR")
    if not esperado or token != esperado or not canonical or not os.path.isdir(canonical):
        raise HTTPException(status_code=404, detail="Not Found")
    data_dir = paths.DATA_DIR
    for nombre in os.listdir(canonical):
        origen = os.path.join(canonical, nombre)
        destino = os.path.join(data_dir, nombre)
        if os.path.isdir(origen):
            if os.path.isdir(destino):
                shutil.rmtree(destino)
            shutil.copytree(origen, destino)
        else:
            shutil.copy2(origen, destino)
    # lo que el runtime creó y el canónico no tiene, se borra (sesiones ajenas)
    for nombre in os.listdir(data_dir):
        if not os.path.exists(os.path.join(canonical, nombre)):
            ruta = os.path.join(data_dir, nombre)
            (shutil.rmtree if os.path.isdir(ruta) else os.remove)(ruta)

    from core.db import reset as db_reset
    from core.db import tenant as db_tenant
    tid = db_tenant.current_tenant_id()
    db_reset.truncate_business_data(tid)

    if data_dir not in sys.path:
        sys.path.insert(0, data_dir)
    import seed_db
    seed_db.seed_domains()

    from core import analisis_cache
    store.reload()
    ds.reload_data()
    analisis_cache.datos_cambiaron()
    analisis_cache.precalentar()
    store.audit.record(actor="admin", accion="reset_demo_publico")
    return {"ok": True, "mensaje": "demo restaurado al estado canónico"}


_STATIC_DIR = os.environ.get("POLPILOT_STATIC_DIR", "")
if _STATIC_DIR and os.path.isdir(_STATIC_DIR):
    @app.get("/{spa_path:path}", include_in_schema=False)
    def spa(spa_path: str):
        """El frontend compilado (Vite) servido por FastAPI: un servicio, un
        puerto. Cualquier ruta que no sea un archivo real cae al index (SPA)."""
        candidato = os.path.normpath(os.path.join(_STATIC_DIR, spa_path))
        if not candidato.startswith(os.path.normpath(_STATIC_DIR)):
            raise HTTPException(status_code=404, detail="Not Found")  # path traversal
        if spa_path and os.path.isfile(candidato):
            return FileResponse(candidato)
        return FileResponse(os.path.join(_STATIC_DIR, "index.html"))

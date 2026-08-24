"""
Recordatorios — el sistema transversal de "avisame cuando".

Tres clases de recordatorio:
  - simple:    "anotá que tengo que llamar al contador" → queda activo hasta hacerse.
  - condición: "avisame si algo del depósito vence en menos de 15 días" → queda
               latente y se DISPARA cuando los datos cumplen la condición.
  - evento:    "cuando llegue un remito de La Serenísima, avisame" → se dispara
               cuando el evento ocurre (staging avisa al recibir un archivo).

La evaluación es perezosa: cada vez que alguien lista sus recordatorios se
re-evalúan las condiciones contra los datos vivos. No hay scheduler: el panel y
Ángela consultan seguido, y cuando el canal WhatsApp esté conectado, el envío
se engancha en marcar_disparado() (hook documentado abajo).

Respeta roles: cada recordatorio tiene `para` (username destino) y `creado_por`.
Uno puede anotarse cosas a sí mismo o asignarle a otro (eso ya lo permite la
lógica de equipo existente).

Condiciones soportadas (extensibles):
  {"tipo": "vencimiento_deposito", "dias": 15}
  {"tipo": "entrega_pendiente", "cliente": "garcía", "hora": "17"}   # hora informativa
  {"tipo": "llegada_batch", "origen": "la serenisima"}               # evento
"""
from __future__ import annotations

import datetime
import json
import os
import secrets
import unicodedata

from . import paths
from . import deposito, logistica

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = paths.DATA_DIR  # por-tenant: env POLPILOT_DATA_DIR o data/ (ver core/paths.py)
RECORDATORIOS_JSON = os.path.join(DATA_DIR, "recordatorios.json")


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def _ahora() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _load() -> list[dict]:
    try:
        return json.load(open(RECORDATORIOS_JSON, encoding="utf-8"))
    except Exception:
        return []


def _save(items: list[dict]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    json.dump(items, open(RECORDATORIOS_JSON, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


def crear(texto: str, para: str | None = None, creado_por: str | None = None,
          condicion: dict | None = None) -> dict:
    r = {
        "id": "r" + secrets.token_hex(3),
        "texto": (texto or "").strip(),
        "para": para or creado_por or "dueño",
        "creado_por": creado_por or "dueño",
        "condicion": condicion,
        # simple → activo (visible ya); con condición → latente hasta que se cumpla.
        "estado": "latente" if condicion else "activo",
        "creado": _ahora(),
        "disparado_en": None,
        "detalle_disparo": None,
        "canales": ["panel"],  # + "whatsapp" cuando el canal esté conectado
    }
    items = _load()
    items.append(r)
    _save(items)
    return r


def _marcar_disparado(r: dict, detalle: str) -> None:
    r["estado"] = "disparado"
    r["disparado_en"] = _ahora()
    r["detalle_disparo"] = detalle
    # P24·D6 — la ENTREGA es real: al dispararse, la notificación sale por la
    # campanita del destinatario (el canal interno que ya existe). Sin push al
    # teléfono: eso es post-submit y no se finge.
    try:
        import i18n
        from . import notificaciones
        lang = _lang_de(r.get("para"))
        notificaciones.emitir(
            para=r.get("para") or "",
            titulo=i18n.t("core.rec.notif_titulo", lang),
            cuerpo=(detalle or r.get("texto") or ""),
            tipo="recordatorio_disparado", ref=r.get("id"),
        )
    except Exception:  # noqa: BLE001 — el disparo nunca rompe la evaluación
        pass
    # HOOK WhatsApp: cuando la Business API esté conectada, acá se manda el
    # mensaje al número de r["para"] (auth.usuario_por_numero a la inversa).


def _lang_de(username: str | None) -> str | None:
    """El idioma del DESTINATARIO del recordatorio (el detalle del disparo lo
    lee él, no quien evaluó). Best-effort: sin perfil → default del tenant."""
    try:
        from . import perfiles
        return perfiles.idioma_de(username or "")
    except Exception:
        return None


def _cumple(cond: dict, lang: str | None = None) -> tuple[bool, str]:
    """Evalúa una condición contra los datos vivos. Devuelve (se_cumple, detalle)."""
    import i18n
    tipo = (cond or {}).get("tipo")
    if tipo == "vencimiento_deposito":
        dias = int(cond.get("dias", deposito.VENCIMIENTO_ALERTA_DIAS))
        v = deposito.vencimientos(dias)
        if v:
            peor = v[0]
            return True, i18n.t("core.rec.venc_deposito", lang, n=len(v), dias=dias,
                                producto=peor.get("producto"), lote=peor.get("lote"),
                                restantes=peor["dias_restantes"])
        return False, ""
    if tipo == "entrega_pendiente":
        cli = _norm(cond.get("cliente"))
        from .fechas import parse_fecha, hoy
        pendientes = [
            e for e in logistica.envios()
            if cli and cli in _norm(e.get("cliente")) and e["estado_norm"] != "entregado"
            and (parse_fecha(e.get("fecha_prevista")) or hoy()) <= hoy()
        ]
        if pendientes:
            e = pendientes[0]
            return True, i18n.t("core.rec.entrega_pendiente", lang,
                                cliente=e.get("cliente"), pedido=e.get("pedido"),
                                estado=e.get("estado"))
        return False, ""
    # P24·D6 — alertas personales por UMBRAL, evaluadas contra los datos vivos
    if tipo == "dormido_supera":
        umbral = float(cond.get("monto", 0))
        try:
            from . import analisis
            k = analisis.kpis(lang)
            monto = (k.get("dormido") or {}).get("monto")
        except Exception:  # noqa: BLE001
            monto = None
        if monto is not None and umbral > 0 and monto > umbral:
            return True, i18n.t("core.rec.dormido_supera", lang,
                                monto=i18n.pesos(monto, lang),
                                umbral=i18n.pesos(umbral, lang))
        return False, ""
    if tipo == "cliente_atraso_dias":
        dias = int(cond.get("dias", 45))
        try:
            from . import cuentas
            tarde = [c for c in cuentas.listar() if (c.get("dias_sin_pagar") or 0) > dias]
        except Exception:  # noqa: BLE001
            tarde = []
        if tarde:
            peor = max(tarde, key=lambda c: c["dias_sin_pagar"])
            return True, i18n.t("core.rec.cliente_atraso", lang, n=len(tarde), dias=dias,
                                cliente=peor["nombre"], peor=peor["dias_sin_pagar"])
        return False, ""
    if tipo == "programado":
        # "recordame los lunes X": dispara cuando LLEGA ese día de la semana
        # (0=lunes … 6=domingo). Entrega por campanita; sin push real.
        from .fechas import hoy as _hoy
        if _hoy().weekday() == int(cond.get("dia_semana", 0)):
            return True, ""
        return False, ""
    # "llegada_batch" es por evento (evento_batch), no por estado de datos.
    return False, ""


def evaluar() -> list[dict]:
    """Re-evalúa los latentes contra los datos y dispara los que se cumplen."""
    items = _load()
    disparados = []
    cambio = False
    for r in items:
        if r["estado"] != "latente" or not r.get("condicion"):
            continue
        ok, detalle = _cumple(r["condicion"], _lang_de(r.get("para")))
        if ok:
            _marcar_disparado(r, detalle)
            disparados.append(r)
            cambio = True
    if cambio:
        _save(items)
    return disparados


def evento_batch(tipo_dato: str, nombre_archivo: str) -> list[dict]:
    """Hook para staging: llegó un archivo. Dispara los 'llegada_batch' que matcheen
    por origen (substring del nombre) o por tipo de dato detectado."""
    items = _load()
    disparados = []
    cambio = False
    for r in items:
        if r["estado"] != "latente":
            continue
        cond = r.get("condicion") or {}
        if cond.get("tipo") != "llegada_batch":
            continue
        origen = _norm(cond.get("origen"))
        matchea = (origen and origen in _norm(nombre_archivo)) or \
                  (cond.get("tipo_dato") and cond["tipo_dato"] == tipo_dato)
        if matchea:
            import i18n
            _marcar_disparado(r, i18n.t("core.rec.llego_batch", _lang_de(r.get("para")),
                                        nombre=nombre_archivo, tipo=tipo_dato))
            disparados.append(r)
            cambio = True
    if cambio:
        _save(items)
    return disparados


_ORDEN = {"disparado": 0, "activo": 1, "latente": 2, "hecho": 3}


def listar(para: str | None = None, incluir_hechos: bool = False) -> list[dict]:
    """Los recordatorios de un usuario (los suyos + los que creó), evaluando
    las condiciones antes para que el panel siempre muestre el estado real."""
    evaluar()
    items = _load()
    if para:
        p = _norm(para)
        items = [r for r in items if _norm(r["para"]) == p or _norm(r["creado_por"]) == p]
    if not incluir_hechos:
        items = [r for r in items if r["estado"] != "hecho"]
    return sorted(items, key=lambda r: (_ORDEN.get(r["estado"], 9), r["creado"]))


def completar(rid: str) -> dict:
    items = _load()
    r = next((x for x in items if x["id"] == rid), None)
    if not r:
        raise KeyError("recordatorio inexistente")
    r["estado"] = "hecho"
    _save(items)
    return r

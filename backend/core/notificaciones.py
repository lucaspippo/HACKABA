"""
Notificaciones internas — un EVENTO, múltiples destinos.

PolPilot emite eventos en nombre del sistema ("Paula actualizó su descripción…")
y cada destino decide cómo entregarlos. Hoy el único destino activo es el PANEL
(la campanita); WhatsApp queda REGISTRADO pero inactivo — mismo patrón que el
slot MCP de conectores: cuando la Business API esté, activar WhatsApp es agregar
un destino, no reescribir el flujo.

Un evento: {id, para (username), titulo, cuerpo, tipo, ref (id relacionado),
leida, fecha}. El panel las persiste por destinatario.
"""
from __future__ import annotations

import datetime
import json
import os
import secrets

from . import paths

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = paths.DATA_DIR  # por-tenant: env POLPILOT_DATA_DIR o data/ (ver core/paths.py)
NOTIFICACIONES_JSON = os.path.join(DATA_DIR, "notificaciones.json")


def _ahora() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _load() -> list[dict]:
    try:
        return json.load(open(NOTIFICACIONES_JSON, encoding="utf-8"))
    except Exception:
        return []


def _save(items: list[dict]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    json.dump(items, open(NOTIFICACIONES_JSON, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


# --- Destinos -----------------------------------------------------------------

def _destino_panel(evento: dict) -> None:
    items = _load()
    items.append(evento)
    _save(items)


def _destino_whatsapp(evento: dict) -> None:
    # Slot inactivo (Fase WhatsApp Business API): el flujo ya trata a WhatsApp
    # como un destino más; activarlo = implementar esto y prenderlo en DESTINOS.
    raise NotImplementedError("WhatsApp todavía no está conectado (Business API pendiente).")


# (nombre, handler, activo). WhatsApp registrado pero APAGADO a propósito.
DESTINOS: list[tuple[str, object, bool]] = [
    ("panel", _destino_panel, True),
    ("whatsapp", _destino_whatsapp, False),
]


def destinos_registrados() -> list[dict]:
    return [{"nombre": n, "activo": a} for n, _, a in DESTINOS]


def emitir(para: str, titulo: str, cuerpo: str = "", tipo: str = "general",
           ref: str | None = None) -> dict:
    """Emite el evento por todos los destinos ACTIVOS. Devuelve el evento."""
    evento = {
        "id": "n" + secrets.token_hex(3),
        "para": (para or "").strip().lower(),
        "titulo": titulo,
        "cuerpo": cuerpo,
        "tipo": tipo,
        "ref": ref,
        "leida": False,
        "fecha": _ahora(),
    }
    for _, handler, activo in DESTINOS:
        if activo:
            handler(evento)
    return evento


def total_emitidas(hasta_iso: str | None = None) -> int:
    """Cuántas notificaciones emitió el sistema en este tenant (para el feed
    de actividad de Inicio — un conteo real, no un número inventado).
    P36·E1 — `hasta_iso` (YYYY-MM-DD): cuenta SOLO avisos con fecha ≤ ese día
    (la fecha congelada del demo), mismo filtro que el feed. Sin arg, todas."""
    items = _load()
    if hasta_iso:
        items = [n for n in items if (n.get("fecha") or "")[:10] <= hasta_iso]
    return len(items)


def listar(para: str, solo_no_leidas: bool = False) -> list[dict]:
    p = (para or "").strip().lower()
    items = [n for n in _load() if n["para"] == p]
    if solo_no_leidas:
        items = [n for n in items if not n["leida"]]
    return sorted(items, key=lambda n: n["fecha"], reverse=True)


def marcar_leida(nid: str) -> dict:
    items = _load()
    n = next((x for x in items if x["id"] == nid), None)
    if not n:
        raise KeyError("notificación inexistente")
    n["leida"] = True
    _save(items)
    return n

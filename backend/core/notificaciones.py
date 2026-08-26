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
import secrets


def _ahora() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


# --- Destinos -----------------------------------------------------------------

def _destino_panel(evento: dict) -> None:
    from core.db import notifications_repo, tenant as _tenant
    notifications_repo.create(_tenant.current_tenant_id(), evento)


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
    from core.db import notifications_repo, tenant as _tenant
    return notifications_repo.total_emitidas(_tenant.current_tenant_id(), hasta_iso)


def listar(para: str, solo_no_leidas: bool = False) -> list[dict]:
    from core.db import notifications_repo, tenant as _tenant
    p = (para or "").strip().lower()
    return notifications_repo.list_for(_tenant.current_tenant_id(), p, solo_no_leidas)


def marcar_leida(nid: str) -> dict:
    from core.db import notifications_repo, tenant as _tenant
    return notifications_repo.mark_read(_tenant.current_tenant_id(), nid)

"""
angela_transcripts.py · el registro CRUDO de lo que se dijo con Ángela.

Gemelo de core/whatsapp_channel.py (mismas tablas, mismo shape), pero para el
chat interno: `/api/angela` y `/api/angela/stream` en main.py, y — desde que
la voz se volvió conversacional — también core/voz.py cuando una nota de voz
termina en una pregunta libre en vez de un reporte de piso.

POR QUÉ ES DISTINTO de store.audit: el audit log (core/audit.py) ya registra
CADA consulta a Ángela, a propósito LIVIANO — actor, tools usadas, latencia,
sin texto — para alimentar el feed de actividad sin inflarlo. Este módulo es
lo opuesto a propósito: el texto completo, para volver a mirarlo crudo ante
una disputa, una auditoría o un "¿qué le dijo exactamente a esta persona?".
Las dos cosas conviven porque sirven preguntas distintas.

CÓMO SE AGRUPAN LOS TURNOS EN UNA CONVERSACIÓN: no hay hoy un id de hilo que
mande el frontend — assistant-ui maneja sus threads en localStorage del
browser, el backend nunca los vio. Así que la agrupación es por recencia:
mientras seguidos turnos del mismo actor/canal lleguen dentro de la ventana
de core/db/angela_conversations_repo.STALE_AFTER_MINUTES, caen en la misma
conversación; una pausa más larga abre una nueva. Es un best-effort, no una
correlación exacta con "qué pestaña de assistant-ui era" — alcanza para el
propósito de auditoría (reconstruir una sesión de trabajo), y si el producto
necesita más precisión más adelante, se resuelve pasando un thread_id real
desde el frontend sin tocar este módulo.

Registrar NUNCA rompe el chat: cada llamador la envuelve en try/except, igual
que ya hace store.audit.record. Un fallo de Postgres no debe convertirse en
que Ángela no responda.
"""
from __future__ import annotations


def registrar_turno(actor: str, mensaje_usuario: str, respuesta: str,
                     tools_used: list[str] | None = None, channel: str = "chat") -> dict:
    """Un turno completo: lo que la persona dijo + lo que Ángela contestó.
    Devuelve la conversación (para que un llamador que quiera el id, lo
    tenga), pero el retorno es best-effort — nadie debería depender de él
    para seguir funcionando."""
    from core.db import angela_conversations_repo as repo, tenant as _tenant
    tid = _tenant.current_tenant_id()
    conv = repo.get_or_create_open_conversation(tid, actor, channel=channel)
    if (mensaje_usuario or "").strip():
        repo.add_message(tid, conv["id"], "user", mensaje_usuario)
    if (respuesta or "").strip():
        repo.add_message(tid, conv["id"], "assistant", respuesta, tools_used=tools_used)
    return conv


def listar_conversaciones(actor: str | None = None, channel: str | None = None,
                          limit: int = 100) -> list[dict]:
    from core.db import angela_conversations_repo as repo, tenant as _tenant
    tid = _tenant.current_tenant_id()
    return repo.list_conversations(tid, actor=actor, channel=channel, limit=limit)


def obtener_transcripcion(conversation_id: str) -> dict | None:
    """La conversación + sus mensajes en orden, crudos — sin resumir ni
    traducir: es exactamente lo que se dijo."""
    from core.db import angela_conversations_repo as repo, tenant as _tenant
    tid = _tenant.current_tenant_id()
    conv = repo.get_conversation(tid, conversation_id)
    if not conv:
        return None
    conv["mensajes"] = repo.list_messages(tid, conversation_id)
    return conv

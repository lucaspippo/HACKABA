"""
whatsapp_channel.py — el canal de WhatsApp de cara al CLIENTE, configurable
por tenant (distinto del WhatsApp interno de empleados en main.py's
`/api/whatsapp`, que resuelve número → cuenta de empleado).

Qué resuelve: hoy un pedido por WhatsApp lo levanta un vendedor a mano en un
chat que se pierde. Acá el tenant conecta su propio número de WhatsApp
Business (Meta Cloud API) y el mensaje del cliente ENTRA al sistema: Ángela
(en su propia sesión acotada, ver backend/whatsapp_bot.py) contesta consultas
de catálogo y levanta el pedido o presupuesto — y eso queda igual que
cualquier otro reporte de piso (core/piso.py): un hecho registrado que el
dueño ve y aprueba, nunca una venta ejecutada sola.

Misma disciplina que core/conectores.py con Odoo: probar credenciales de
verdad antes de guardarlas, tokens encriptados en reposo (Fernet, ver
core/db/whatsapp_repo.py), y esto es la única puerta hacia la API de Meta —
nada más en el repo le pega directo.
"""
from __future__ import annotations

import hashlib
import hmac

import httpx

GRAPH_API_VERSION = "v20.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def probar_credenciales(phone_number_id: str, access_token: str) -> dict:
    """Confirma que el phone_number_id + token son válidos contra la Graph API
    de Meta, sin guardar nada — mismo criterio que conectores.probar_conexion_odoo:
    nunca persistir credenciales que no sirven."""
    if not phone_number_id or not access_token:
        raise ValueError("Falta el phone_number_id o el access token.")
    try:
        resp = httpx.get(
            f"{GRAPH_API_BASE}/{phone_number_id}",
            params={"fields": "display_phone_number,verified_name"},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10.0,
        )
    except httpx.HTTPError as e:
        raise ValueError(f"No se pudo conectar con la API de WhatsApp: {e}") from e
    if resp.status_code != 200:
        raise ValueError(
            "Meta rechazó esas credenciales de WhatsApp Business "
            f"(status {resp.status_code}): {resp.text[:200]}"
        )
    data = resp.json()
    return {
        "display_phone_number": data.get("display_phone_number"),
        "business_name": data.get("verified_name"),
    }


# --- config del tenant --------------------------------------------------------

def obtener_config(tenant_id: str) -> dict | None:
    """Config para el frontend: el token/secret NUNCA vuelven, mismo criterio
    que Odoo. Para código de servidor que sí necesita el secret (verificar la
    firma del webhook, enviar_mensaje) usar config_con_secretos()."""
    c = config_con_secretos(tenant_id)
    if not c:
        return None
    return {k: v for k, v in c.items() if k not in ("access_token", "app_secret")}


def config_con_secretos(tenant_id: str) -> dict | None:
    """SOLO para uso interno del servidor (verificar firma del webhook,
    enviar_mensaje) — nunca devolver esto en una respuesta de API."""
    from core.db import whatsapp_repo
    return whatsapp_repo.get_channel(tenant_id)


def guardar_config(tenant_id: str, *, phone_number_id: str, access_token: str,
                    app_secret: str, greeting_message: str = "",
                    enabled: bool = True, verify_token: str | None = None) -> dict:
    if not app_secret:
        raise ValueError("Falta el app secret (para validar la firma del webhook).")
    info = probar_credenciales(phone_number_id, access_token)
    from core.db import whatsapp_repo
    whatsapp_repo.save_channel(
        tenant_id, phone_number_id=phone_number_id,
        display_phone_number=info.get("display_phone_number"),
        business_name=info.get("business_name"),
        access_token=access_token, app_secret=app_secret,
        verify_token=verify_token, greeting_message=greeting_message,
        enabled=enabled,
    )
    return obtener_config(tenant_id)


def borrar_config(tenant_id: str) -> None:
    from core.db import whatsapp_repo
    whatsapp_repo.delete_channel(tenant_id)


# --- webhook: verificación de firma y handshake -------------------------------

def verificar_firma(app_secret: str, payload_bytes: bytes, signature_header: str | None) -> bool:
    """Valida X-Hub-Signature-256 (HMAC-SHA256 del body crudo con el app
    secret) — así el webhook sabe que el POST viene de Meta y no de cualquiera
    que le pegue a la URL adivinando el phone_number_id."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    esperado = hmac.new(app_secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    recibido = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(esperado, recibido)


def verificar_handshake(tenant_id: str, modo: str, token: str) -> bool:
    """GET de verificación que Meta manda una vez al configurar el webhook
    (hub.mode=subscribe, hub.verify_token=<lo que el tenant puso en Meta>)."""
    if modo != "subscribe":
        return False
    from core.db import whatsapp_repo
    c = whatsapp_repo.get_channel(tenant_id)
    return bool(c) and hmac.compare_digest(c["verify_token"], token or "")


# --- enviar / recibir mensajes -------------------------------------------------

def enviar_mensaje(tenant_id: str, telefono: str, texto: str) -> None:
    from core.db import whatsapp_repo
    c = whatsapp_repo.get_channel(tenant_id)
    if not c or not c["enabled"]:
        raise ValueError("No hay canal de WhatsApp activo para este tenant.")
    resp = httpx.post(
        f"{GRAPH_API_BASE}/{c['phone_number_id']}/messages",
        headers={"Authorization": f"Bearer {c['access_token']}"},
        json={
            "messaging_product": "whatsapp",
            "to": telefono,
            "type": "text",
            "text": {"body": texto},
        },
        timeout=10.0,
    )
    if resp.status_code >= 300:
        raise ValueError(f"Meta rechazó el envío del mensaje (status {resp.status_code}): "
                          f"{resp.text[:200]}")


def registrar_entrante(tenant_id: str, telefono: str, texto: str,
                        wa_message_id: str | None = None,
                        customer_name: str | None = None) -> dict:
    """Persiste el mensaje entrante y devuelve la conversación + el historial
    reciente ya en el shape que necesita el tool-use loop (role/content)."""
    from core.db import whatsapp_repo
    conv = whatsapp_repo.get_or_create_conversation(tenant_id, telefono, customer_name)
    whatsapp_repo.add_message(tenant_id, conv["id"], "in", texto, wa_message_id)
    mensajes = whatsapp_repo.list_messages(tenant_id, conv["id"], limit=20)
    historial = [
        {"role": "user" if m["direction"] == "in" else "assistant", "content": m["body"]}
        for m in mensajes[:-1]  # el último es el mensaje actual, lo manda responder() aparte
    ]
    return {"conversacion": conv, "historial": historial}


def registrar_saliente(tenant_id: str, conversation_id: str, texto: str) -> None:
    from core.db import whatsapp_repo
    whatsapp_repo.add_message(tenant_id, conversation_id, "out", texto)


def listar_conversaciones(tenant_id: str) -> list[dict]:
    from core.db import whatsapp_repo
    return whatsapp_repo.list_conversations(tenant_id)


def historial_conversacion(tenant_id: str, conversation_id: str) -> list[dict]:
    from core.db import whatsapp_repo
    return whatsapp_repo.list_messages(tenant_id, conversation_id, limit=200)


def marcar_necesita_atencion(tenant_id: str, conversation_id: str) -> None:
    from core.db import whatsapp_repo
    whatsapp_repo.set_conversation_status(tenant_id, conversation_id, "necesita_atencion")


# --- lo que el bot puede hacer: catálogo + capturar pedido/presupuesto -------

def buscar_catalogo(texto: str, limit: int = 8) -> list[dict]:
    """Búsqueda de catálogo SEGURA para un cliente: sólo lo que un mostrador le
    diría (nombre, precio de venta, si hay stock) — nunca costo, margen ni el
    inmovilizado que devuelve la búsqueda interna (ds.buscar_productos)."""
    import data_store as ds
    hits = ds.buscar_productos(texto, limit=limit)
    return [
        {
            "codigo": h.get("codigo"),
            "nombre": h.get("descripcion"),
            "precio": h.get("pvp"),
            "disponible": bool((h.get("stock") or 0) > 0),
        }
        for h in hits
        if h.get("pvp")  # sin precio de venta cargado, no se lo mostramos a un cliente
    ]


def registrar_pedido(*, telefono: str, cliente_nombre: str,
                      items: list[dict], nota: str = "") -> dict:
    """Deja el pedido como reporte de piso (core/piso.py), origen 'whatsapp':
    NO es una venta ejecutada — el dueño lo ve y lo cruza como cualquier otro
    pedido levantado por el equipo (ver el docstring de piso.py)."""
    from core import piso
    return piso.reportar("pedido", actor="Ángela (WhatsApp)", datos={
        "cliente": cliente_nombre or telefono, "telefono": telefono,
        "items": items, "nota": nota, "canal": "whatsapp",
    })


def registrar_presupuesto(*, telefono: str, cliente_nombre: str,
                           items: list[dict], nota: str = "") -> dict:
    from core import piso
    return piso.reportar("presupuesto", actor="Ángela (WhatsApp)", datos={
        "cliente": cliente_nombre or telefono, "telefono": telefono,
        "items": items, "nota": nota, "canal": "whatsapp",
    })

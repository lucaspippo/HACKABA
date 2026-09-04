"""
whatsapp_bot.py · La Ángela que atiende al CLIENTE por WhatsApp
================================================================
Deliberadamente NO es angela.py: angela.py es la socia del dueño y su
equipo, con ~50 herramientas internas (inventario, cuentas corrientes,
caja...) gateadas por rol. Un cliente que le escribe al número de ventas del
tenant no puede llegar ni cerca de esas herramientas — así que esta es una
sesión de tool-use CHICA Y APARTE, con su propio prompt y sus 4 tools, que
sólo sabe: buscar en el catálogo, levantar un pedido, levantar un
presupuesto, o avisar que la conversación necesita a una persona.

Igual que angela.py: el proveedor y el modelo los resuelve config.py (directo
contra Anthropic o por el AI Gateway), y sin ninguno configurado degrada con
elegancia (un mensaje fijo, nunca inventa nada ni se cuelga).

Todo lo que estas tools EJECUTAN vive en core/whatsapp_channel.py (el canal:
credenciales, envío, y el registro de pedidos como reportes de piso que el
dueño aprueba) — acá sólo vive la conversación.
"""
from __future__ import annotations

import json
import os

import config
from core import paths, whatsapp_channel

MAX_TOKENS = int(os.environ.get("POLPILOT_MAX_TOKENS", "512"))
MAX_TOOL_TURNS = 5

TOOLS = [
    {
        "name": "buscar_producto",
        "description": "Busca productos del catálogo por nombre para mostrárselos al "
        "cliente (nombre, precio, si hay stock). Usala apenas el cliente nombre un "
        "producto o categoría, aunque sea de forma imprecisa.",
        "input_schema": {
            "type": "object",
            "properties": {"texto": {"type": "string", "description": "Qué buscar, ej. 'aceite de girasol'."}},
            "required": ["texto"],
        },
    },
    {
        "name": "registrar_pedido",
        "description": "Registra un pedido cuando el cliente CONFIRMÓ qué quiere "
        "comprar (ya eligió productos y cantidades). No es una venta cerrada: alguien "
        "del negocio lo revisa y se pone en contacto para coordinar pago/entrega. "
        "Confirmá el pedido en un mensaje ANTES de llamar esta herramienta.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cliente_nombre": {"type": "string", "description": "Nombre con el que se identificó el cliente, si lo dio."},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "producto": {"type": "string"},
                            "cantidad": {"type": "string", "description": "Cantidad tal como la dijo el cliente, ej. '3 unidades', '2 kg'."},
                        },
                        "required": ["producto"],
                    },
                },
                "nota": {"type": "string", "description": "Cualquier aclaración (dirección, horario, forma de pago)."},
            },
            "required": ["items"],
        },
    },
    {
        "name": "registrar_presupuesto",
        "description": "Registra un pedido de PRESUPUESTO/cotización cuando el "
        "cliente todavía está averiguando precio y no confirmó compra.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cliente_nombre": {"type": "string"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "producto": {"type": "string"},
                            "cantidad": {"type": "string"},
                        },
                        "required": ["producto"],
                    },
                },
                "nota": {"type": "string"},
            },
            "required": ["items"],
        },
    },
    {
        "name": "derivar_a_persona",
        "description": "Marcá la conversación para que la atienda una persona del "
        "negocio: el cliente pide algo fuera de catálogo/pedidos (un reclamo, una "
        "pregunta que no sabés responder, quiere hablar con alguien). Decile al "
        "cliente que en breve lo contactan.",
        "input_schema": {
            "type": "object",
            "properties": {"motivo": {"type": "string"}},
            "required": ["motivo"],
        },
    },
]

SYSTEM_PROMPT = """Sos la asistente de ventas por WhatsApp de {empresa}. Hablás con \
CLIENTES, no con el equipo interno — nunca dijiste esto último en voz alta, simplemente \
actuás en consecuencia.

CÓMO HABLÁS:
- Como alguien del mostrador: cordial, directo, castellano rioplatense natural. Sin \
tono de bot ni "estimado cliente". Mensajes cortos (WhatsApp, no un mail).
- Nunca inventes precio, stock ni disponibilidad: siempre usá 'buscar_producto'. Si no \
está en el catálogo, decilo con honestidad y ofrecé anotarlo como consulta para que un \
vendedor confirme.
- Antes de 'registrar_pedido' o 'registrar_presupuesto', repetile al cliente qué \
entendiste (productos y cantidades) y esperá su confirmación en el mismo intercambio o \
el anterior — no registrés algo que el cliente no terminó de confirmar.
- Si preguntan por algo que no es catálogo/pedidos/presupuestos (reclamos, facturación, \
cuenta corriente, o simplemente piden hablar con una persona), usá 'derivar_a_persona' \
y avisales que alguien del equipo los contacta.
- Nunca dices que sos una IA a menos que te lo pregunten directamente.
{saludo}"""


def _fallback(mensaje: str) -> dict:
    return {
        "respuesta": "¡Gracias por escribirnos! En breve te responde alguien de nuestro "
        "equipo. Mientras tanto, contanos qué producto te interesa y la cantidad.",
        "modo": "simulado", "tools_usadas": [], "acciones": [],
    }


def _run_tool(name: str, args: dict, telefono: str) -> tuple[dict, dict | None]:
    accion = None
    if name == "buscar_producto":
        resultados = whatsapp_channel.buscar_catalogo(args.get("texto", ""))
        return {"resultados": resultados, "total": len(resultados)}, accion
    if name == "registrar_pedido":
        r = whatsapp_channel.registrar_pedido(
            telefono=telefono, cliente_nombre=args.get("cliente_nombre") or "",
            items=args.get("items") or [], nota=args.get("nota") or "")
        return {"ok": True, "id": r["id"]}, {"tipo": "pedido_registrado", "id": r["id"]}
    if name == "registrar_presupuesto":
        r = whatsapp_channel.registrar_presupuesto(
            telefono=telefono, cliente_nombre=args.get("cliente_nombre") or "",
            items=args.get("items") or [], nota=args.get("nota") or "")
        return {"ok": True, "id": r["id"]}, {"tipo": "presupuesto_registrado", "id": r["id"]}
    if name == "derivar_a_persona":
        return {"ok": True}, {"tipo": "necesita_persona", "motivo": args.get("motivo", "")}
    return {"error": f"herramienta desconocida: {name}"}, accion


def responder_cliente(mensaje: str, historial: list[dict], telefono: str,
                       saludo: str = "") -> dict:
    """El equivalente de angela.responder() pero para esta sesión chica y
    aparte. Nunca toca los contextvars de angela.py ni su TOOLS: aislamiento
    completo entre el chat interno y el bot de cara al cliente."""
    # config is the single provider switch (direct Anthropic or the AI
    # Gateway); reading a key here would disagree with it.
    try:
        client = config.get_client()
    except ImportError:                  # sin el paquete `anthropic`
        client = None
    if client is None:
        return _fallback(mensaje)

    system = SYSTEM_PROMPT.format(
        empresa=paths.EMPRESA,
        saludo=(f"\nSi es el primer mensaje de la conversación, empezá con algo como: "
                f"\"{saludo}\"" if saludo else ""),
    )
    messages: list[dict] = list(historial[-10:])
    messages.append({"role": "user", "content": mensaje})

    tools_usadas: list[str] = []
    acciones: list[dict] = []
    try:
        for _ in range(MAX_TOOL_TURNS):
            resp = client.messages.create(
                model=config.modelo_para(),
                max_tokens=MAX_TOKENS, system=system, tools=TOOLS, messages=messages,
            )
            if resp.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": resp.content})
                tool_results = []
                for block in resp.content:
                    if block.type == "tool_use":
                        tools_usadas.append(block.name)
                        result, accion = _run_tool(block.name, block.input or {}, telefono)
                        if accion:
                            acciones.append(accion)
                        tool_results.append({
                            "type": "tool_result", "tool_use_id": block.id,
                            "content": json.dumps(result, ensure_ascii=False),
                        })
                messages.append({"role": "user", "content": tool_results})
                continue

            texto = "".join(b.text for b in resp.content if b.type == "text").strip()
            return {"respuesta": texto, "modo": "claude",
                    "tools_usadas": tools_usadas, "acciones": acciones}

        return {"respuesta": "Perdón, ¿me lo repetís más simple? Me hice un lío.",
                "modo": "claude", "tools_usadas": tools_usadas, "acciones": acciones}
    except Exception as e:  # noqa: BLE001 — degradar nunca tira el webhook abajo
        fb = _fallback(mensaje)
        fb["error_tecnico"] = str(e)
        return fb


def _extraer_mensajes_texto(payload: dict) -> list[dict]:
    """Meta manda un `entry[].changes[].value` por evento; `messages` sólo
    está presente en un mensaje ENTRANTE de texto (no en el eco de status)."""
    out = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            contactos = {c.get("wa_id"): c.get("profile", {}).get("name")
                         for c in value.get("contacts", [])}
            for m in value.get("messages", []):
                if m.get("type") != "text":
                    continue
                out.append({
                    "telefono": m.get("from"),
                    "texto": (m.get("text") or {}).get("body", ""),
                    "wa_message_id": m.get("id"),
                    "nombre": contactos.get(m.get("from")),
                })
    return out


def procesar_webhook(tenant_id: str, payload: dict) -> None:
    """Procesa un POST de webhook de Meta ya autenticado (firma verificada
    por el caller). Por cada mensaje de texto entrante: lo persiste, arma el
    historial, le pide la respuesta a esta sesión de Ángela, y la manda de
    vuelta por WhatsApp."""
    config = whatsapp_channel.obtener_config(tenant_id)
    if not config or not config.get("enabled"):
        return
    for msg in _extraer_mensajes_texto(payload):
        if not msg["telefono"] or not msg["texto"]:
            continue
        estado = whatsapp_channel.registrar_entrante(
            tenant_id, msg["telefono"], msg["texto"], msg["wa_message_id"], msg["nombre"])
        conv = estado["conversacion"]
        es_primer_mensaje = not estado["historial"]
        r = responder_cliente(
            msg["texto"], estado["historial"], msg["telefono"],
            saludo=config.get("greeting_message", "") if es_primer_mensaje else "",
        )
        if any(a.get("tipo") == "necesita_persona" for a in r.get("acciones", [])):
            whatsapp_channel.marcar_necesita_atencion(tenant_id, conv["id"])
        if r.get("respuesta"):
            whatsapp_channel.registrar_saliente(tenant_id, conv["id"], r["respuesta"])
            whatsapp_channel.enviar_mensaje(tenant_id, msg["telefono"], r["respuesta"])

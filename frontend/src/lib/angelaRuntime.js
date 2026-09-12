// Adaptador de assistant-ui para el chat de Ángela: un ChatModelAdapter que
// habla NDJSON con /api/angela/stream (ver backend/angela.py::stream_responder)
// en vez del protocolo del Vercel AI SDK — no lo necesitamos porque el backend
// es Python puro. Cada línea es un evento {type: "text"|"tool_call"|"tool_result"|"done"};
// acá se traducen a los content parts que assistant-ui espera (append-only
// ChatModelRunResult), como layer arriba de useLocalRuntime.
import { api } from "./api";
import { authStore } from "./auth";

function textoDePartes(content = []) {
  return content
    .filter((p) => p.type === "text")
    .map((p) => p.text)
    .join("");
}

// El historial que el backend espera es {role, content:string}[]; el mensaje
// más nuevo (el que el usuario acaba de mandar) va aparte como `mensaje`.
function historialYMensaje(messages) {
  const ultimo = messages[messages.length - 1];
  const mensaje = textoDePartes(ultimo?.content);
  const historial = messages
    .slice(0, -1)
    .filter((m) => m.role === "user" || m.role === "assistant")
    .map((m) => ({ role: m.role, content: textoDePartes(m.content) }))
    .filter((m) => m.content);
  return { mensaje, historial };
}

/**
 * @param {{ vista?: () => string | null }} opciones — getter perezoso de en
 * qué pantalla está parado el usuario (para que Ángela sepa el contexto).
 */
export function crearAngelaModelAdapter({ vista } = {}) {
  return {
    async *run({ messages, abortSignal }) {
      const { mensaje, historial } = historialYMensaje(messages);
      if (!mensaje) {
        yield { content: [{ type: "text", text: "" }] };
        return;
      }

      const token = authStore.getSnapshot()?.token;
      let res;
      try {
        res = await api.angelaStream(mensaje, historial, {
          token,
          vista: vista?.() ?? null,
        }, { signal: abortSignal });
      } catch (e) {
        if (abortSignal.aborted) return;
        yield {
          content: [{
            type: "text",
            text: "Se me cortó la consulta al modelo. Probá de nuevo en un momento.",
          }],
        };
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      const parts = [];
      const toolIndexPorId = new Map();
      let textoActualIdx = null;
      // El evento "done" trae el mismo shape que siempre devolvió el chat NO
      // streaming (respuesta/modo/tools_usadas/acciones/opciones): viaja como
      // metadata.custom del mensaje para que quien orqueste el chat (efectos:
      // navegar, crear widget, entregar documento, chips de "opciones") lo lea
      // sin tener que parsear el contenido visible del mensaje.
      let resultadoFinal = null;

      const snapshot = () => ({
        content: parts.map((p) => ({ ...p })),
        ...(resultadoFinal ? { metadata: { custom: resultadoFinal } } : {}),
      });

      const procesarEvento = (ev) => {
        if (ev.type === "text") {
          if (textoActualIdx == null) {
            parts.push({ type: "text", text: ev.text });
            textoActualIdx = parts.length - 1;
          } else {
            parts[textoActualIdx] = { type: "text", text: ev.text };
          }
        } else if (ev.type === "tool_call") {
          textoActualIdx = null; // el próximo texto es de un turno nuevo
          parts.push({
            type: "tool-call",
            toolCallId: ev.id,
            toolName: ev.name,
            args: ev.input || {},
            argsText: JSON.stringify(ev.input || {}),
          });
          toolIndexPorId.set(ev.id, parts.length - 1);
        } else if (ev.type === "tool_result") {
          const i = toolIndexPorId.get(ev.id);
          if (i != null) parts[i] = { ...parts[i], result: ev.result };
        } else if (ev.type === "done") {
          resultadoFinal = ev.result || {};
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lineas = buffer.split("\n");
        buffer = lineas.pop() ?? "";
        for (const linea of lineas) {
          if (!linea.trim()) continue;
          let ev;
          try {
            ev = JSON.parse(linea);
          } catch {
            continue;
          }
          procesarEvento(ev);
        }
        yield snapshot();
      }
      if (buffer.trim()) {
        try {
          procesarEvento(JSON.parse(buffer));
        } catch {
          /* última línea incompleta — se ignora */
        }
      }
      yield snapshot();
    },
  };
}

// assistant-ui adapter for the chat: a ChatModelAdapter that speaks NDJSON
// with /api/angela/stream (see backend/angela.py::stream_response) instead of
// the Vercel AI SDK protocol — we don't need it since the backend is plain
// Python. Each line is an event {type: "text"|"tool_call"|"tool_result"|"done"};
// these get translated here into the content parts assistant-ui expects
// (append-only ChatModelRunResult), as a layer on top of useLocalRuntime.
import { api } from "./api";
import { authStore } from "./auth";

function textFromParts(content = []) {
  return content
    .filter((p) => p.type === "text")
    .map((p) => p.text)
    .join("");
}

// The backend expects history as {role, content:string}[]; the newest
// message (what the user just sent) goes separately as `mensaje`.
function historyAndMessage(messages) {
  const last = messages[messages.length - 1];
  const message = textFromParts(last?.content);
  const history = messages
    .slice(0, -1)
    .filter((m) => m.role === "user" || m.role === "assistant")
    .map((m) => ({ role: m.role, content: textFromParts(m.content) }))
    .filter((m) => m.content);
  return { message, history };
}

/**
 * @param {{ getCurrentView?: () => string | null }} options — lazy getter for
 * which screen the user is on (so the assistant knows the context).
 */
export function createChatModelAdapter({ getCurrentView } = {}) {
  return {
    async *run({ messages, abortSignal }) {
      const { message, history } = historyAndMessage(messages);
      if (!message) {
        yield { content: [{ type: "text", text: "" }] };
        return;
      }

      const token = authStore.getSnapshot()?.token;
      let res;
      try {
        res = await api.chatStream(message, history, {
          token,
          vista: getCurrentView?.() ?? null,
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
      const toolIndexById = new Map();
      let currentTextIndex = null;
      // The "done" event carries the same shape the non-streaming chat has
      // always returned (respuesta/modo/tools_usadas/acciones/opciones): it
      // travels as the message's metadata.custom so whatever orchestrates the
      // chat (side effects: navigate, create widget, deliver a document,
      // "opciones" chips) can read it without parsing the visible content.
      let finalResult = null;

      const snapshot = () => ({
        content: parts.map((p) => ({ ...p })),
        ...(finalResult ? { metadata: { custom: finalResult } } : {}),
      });

      const processEvent = (ev) => {
        if (ev.type === "text") {
          if (currentTextIndex == null) {
            parts.push({ type: "text", text: ev.text });
            currentTextIndex = parts.length - 1;
          } else {
            parts[currentTextIndex] = { type: "text", text: ev.text };
          }
        } else if (ev.type === "tool_call") {
          currentTextIndex = null; // the next text belongs to a new turn
          parts.push({
            type: "tool-call",
            toolCallId: ev.id,
            toolName: ev.name,
            args: ev.input || {},
            argsText: JSON.stringify(ev.input || {}),
          });
          toolIndexById.set(ev.id, parts.length - 1);
        } else if (ev.type === "tool_result") {
          const i = toolIndexById.get(ev.id);
          if (i != null) parts[i] = { ...parts[i], result: ev.result };
        } else if (ev.type === "done") {
          finalResult = ev.result || {};
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.trim()) continue;
          let ev;
          try {
            ev = JSON.parse(line);
          } catch {
            continue;
          }
          processEvent(ev);
        }
        yield snapshot();
      }
      if (buffer.trim()) {
        try {
          processEvent(JSON.parse(buffer));
        } catch {
          /* incomplete last line — ignored */
        }
      }
      yield snapshot();
    },
  };
}

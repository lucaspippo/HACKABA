/**
 * assistant-ui ChatModelAdapter over the NDJSON stream at
 * /api/angela/stream (see backend/angela.py::stream_response).
 *
 * The Vercel AI SDK protocol is not used: the backend is plain Python and
 * owns the tool loop. This translates wire events into the append-only
 * ChatModelRunResult assistant-ui expects, on top of useLocalRuntime.
 *
 * It never yields a fake assistant message for a failure — it THROWS, so
 * MessagePrimitive.Error owns the error state and a retry is possible.
 */
import type {
  ChatModelAdapter,
  ChatModelRunOptions,
  ChatModelRunResult,
  ThreadAssistantMessagePart,
  ThreadMessage,
} from "@assistant-ui/react";
import { api } from "../api";
import { cerebroBus } from "../cerebroBus";
import { authStore } from "../auth";
import { ChatStreamError, type ChatErrorCode } from "./errors";
import { parseStreamLine, type DoneResult, type Notice } from "./protocol";

export type ChatTurn = { role: "user" | "assistant"; content: string };

export type FetchStream = (
  message: string,
  history: ChatTurn[],
  extra: Record<string, unknown>,
  init: { signal: AbortSignal },
) => Promise<Response>;

export type ChatAdapterOptions = {
  /** Injectable for tests; defaults to api.chatStream. */
  fetchStream?: FetchStream;
};

function textOf(content: readonly { type: string; text?: string }[] = []): string {
  return content
    .filter((p) => p.type === "text")
    .map((p) => p.text ?? "")
    .join("");
}

/**
 * The backend takes history as {role, content:string}[] with the newest
 * message separate.
 */
function splitMessages(messages: readonly ThreadMessage[]) {
  const last = messages[messages.length - 1];
  const message = textOf(last?.content as never);
  const history = messages
    .slice(0, -1)
    .filter((m) => m.role === "user" || m.role === "assistant")
    .map((m) => ({ role: m.role as "user" | "assistant", content: textOf(m.content as never) }))
    .filter((m) => m.content);
  return { message, history };
}

const KNOWN_CODES: ReadonlySet<string> = new Set([
  "session_expired", "rate_limit", "server", "network", "stream", "aborted",
]);

/** Server codes are richer than the client's closed set; map the rest to `server`. */
function toClientCode(code: string): ChatErrorCode {
  return (KNOWN_CODES.has(code) ? code : "server") as ChatErrorCode;
}

export function createChatModelAdapter(
  { fetchStream }: ChatAdapterOptions = {},
) {
  const doFetch: FetchStream = fetchStream ?? ((m, h, extra, init) =>
    api.chatStream(m, h, extra, init));

  return {
    async *run({ messages, abortSignal }: ChatModelRunOptions) {
      const { message, history } = splitMessages(messages);
      if (!message) return;

      // La pantalla del cerebro arranca el viaje de cámara con esto, apenas
      // se manda la pregunta y antes de que vuelva nada.
      cerebroBus.empieza(message);

      const token = authStore.getSnapshot()?.token;

      let res: Response;
      try {
        res = await doFetch(message, history, { token }, { signal: abortSignal });
      } catch (e) {
        if (abortSignal.aborted) return;
        throw e instanceof ChatStreamError
          ? e
          : new ChatStreamError("network", String((e as Error)?.message ?? e));
      }

      const parts: ThreadAssistantMessagePart[] = [];
      const notices: Notice[] = [];
      const toolIndexById = new Map<string, number>();
      // toolCallId -> `status` line. Metadata, not `args`: those must keep
      // matching toolArgs.generated.ts.
      const toolLabels: Record<string, string> = {};
      let textIndex: number | null = null;
      let done: DoneResult | null = null;

      const snapshot = (): ChatModelRunResult => ({
        content: parts.map((p) => ({ ...p })),
        metadata: {
          custom: {
            ...(done ?? {}),
            ...(notices.length ? { notices: [...notices] } : {}),
            ...(Object.keys(toolLabels).length ? { toolLabels: { ...toolLabels } } : {}),
          },
        },
      });

      /** Returns a ChatStreamError to throw, or null to keep going. */
      const apply = (line: string): ChatStreamError | null => {
        const ev = parseStreamLine(line);
        if (!ev) return null;

        if (ev.type === "text") {
          if (textIndex == null) {
            parts.push({ type: "text", text: ev.delta });
            textIndex = parts.length - 1;
          } else {
            const current = parts[textIndex] as { type: "text"; text: string };
            parts[textIndex] = { type: "text", text: current.text + ev.delta };
          }
        } else if (ev.type === "tool_call") {
          textIndex = null; // later text belongs to a new turn
          if (ev.label) toolLabels[ev.id] = ev.label;
          // La pantalla del cerebro enciende el camino con esto. Fuera de esa
          // pantalla no hay listeners y no cuesta nada.
          cerebroBus.herramienta(ev.name, ev.label);
          parts.push({
            type: "tool-call",
            toolCallId: ev.id,
            toolName: ev.name,
            args: ev.input ?? {},
            argsText: JSON.stringify(ev.input ?? {}),
          } as ThreadAssistantMessagePart);
          toolIndexById.set(ev.id, parts.length - 1);
        } else if (ev.type === "tool_result") {
          const i = toolIndexById.get(ev.id);
          if (i != null) parts[i] = { ...parts[i], result: ev.result } as ThreadAssistantMessagePart;
        } else if (ev.type === "notice") {
          textIndex = null; // a notice closes the current text part
          notices.push({ kind: ev.kind });
        } else if (ev.type === "error") {
          return new ChatStreamError(toClientCode(ev.code));
        } else if (ev.type === "done") {
          done = ev.result ?? {};
          cerebroBus.termina((done as DoneResult)?.tools_used as string[] | undefined);
        }
        return null;
      };

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        let chunk: ReadableStreamReadResult<Uint8Array>;
        try {
          chunk = await reader.read();
        } catch (e) {
          if (abortSignal.aborted) return;
          throw new ChatStreamError("stream", String((e as Error)?.message ?? e));
        }
        if (chunk.done) break;

        buffer += decoder.decode(chunk.value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? ""; // the tail may be half a line
        for (const line of lines) {
          const err = apply(line);
          if (err) throw err;
        }
        yield snapshot();
      }

      if (buffer.trim()) {
        const err = apply(buffer);
        if (err) throw err;
      }

      // Defensive: a `done` with neither text nor notices used to render an
      // empty bubble (the v1 cap bug). Never let that happen silently again.
      const readDone = () => done;
      const finalAnswer = readDone()?.answer;
      if (parts.length === 0 && notices.length === 0 && finalAnswer) {
        parts.push({ type: "text", text: finalAnswer });
      }

      yield snapshot();
    },
  } satisfies ChatModelAdapter;
}

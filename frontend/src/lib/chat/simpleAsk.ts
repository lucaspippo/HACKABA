/**
 * A minimal one-shot client for /api/angela/stream: send one message, get
 * back the full assistant text once the stream ends (plus a running partial
 * via `onDelta`, for showing the answer as it arrives).
 *
 * For UIs that don't run inside assistant-ui's ThreadRuntime — today, only
 * VozAngela's conversational mode — and just need "ask, then show/speak the
 * answer", not the richer tool-call bookkeeping createChatModelAdapter (see
 * ./adapter.ts) does for the real chat thread. If a second caller shows up
 * wanting the same thing, that bookkeeping is the one to reuse/extract from,
 * not this — this stays deliberately thin.
 */
import { api } from "../api";
import { ChatStreamError, type ChatErrorCode } from "./errors";
import { parseStreamLine } from "./protocol";
import type { ChatTurn, FetchStream } from "./adapter";

export type SimpleAskOptions = {
  token?: string | null;
  channel?: string;
  history?: ChatTurn[];
  signal?: AbortSignal;
  onDelta?: (soFar: string) => void;
  /** A tool call started — its `label` is the same status line the visual
   * ToolCallCard shows while the call runs. Callers that want to stay
   * responsive during a slow tool (e.g. narrating it out loud) hook this
   * instead of waiting on the final answer. */
  onToolCall?: (label: string) => void;
  /** Injectable for tests; defaults to api.chatStream. */
  fetchStream?: FetchStream;
};

const KNOWN_CODES: ReadonlySet<string> = new Set([
  "session_expired", "rate_limit", "server", "network", "stream", "aborted",
]);

function toClientCode(code: string): ChatErrorCode {
  return (KNOWN_CODES.has(code) ? code : "server") as ChatErrorCode;
}

export async function askAngela(message: string, options: SimpleAskOptions = {}): Promise<string> {
  const { token, channel, history = [], signal, onDelta, onToolCall, fetchStream } = options;
  const doFetch = fetchStream ?? ((m, h, extra, init) => api.chatStream(m, h, extra, init));
  const res = await doFetch(message, history, { token, channel }, { signal: signal ?? new AbortController().signal });

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let text = "";

  const apply = (line: string) => {
    const ev = parseStreamLine(line);
    if (!ev) return;
    if (ev.type === "text") {
      text += ev.delta;
      onDelta?.(text);
    } else if (ev.type === "tool_call" && ev.label) {
      onToolCall?.(ev.label);
    } else if (ev.type === "error") {
      throw new ChatStreamError(toClientCode(ev.code));
    }
  };

  while (true) {
    let chunk: ReadableStreamReadResult<Uint8Array>;
    try {
      chunk = await reader.read();
    } catch (e) {
      if (signal?.aborted) throw new ChatStreamError("aborted");
      throw new ChatStreamError("stream", String((e as Error)?.message ?? e));
    }
    if (chunk.done) break;
    buffer += decoder.decode(chunk.value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const l of lines) apply(l);
  }
  if (buffer.trim()) apply(buffer);
  return text;
}

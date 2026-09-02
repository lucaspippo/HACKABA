/**
 * The `/api/angela/stream` wire protocol (v2), one JSON object per NDJSON line.
 * Mirrors backend/angela.py::stream_response — change both together.
 */
export type NoticeKind = "cap" | "tool_loop_exhausted" | "fake_model";

export type StreamEvent =
  | { type: "text"; delta: string }
  | { type: "tool_call"; id: string; name: string; input?: Record<string, unknown> }
  | { type: "tool_result"; id: string; result?: unknown }
  | { type: "notice"; kind: NoticeKind }
  | { type: "error"; code: string; retryable?: boolean }
  | { type: "done"; result?: DoneResult };

export type Notice = { kind: NoticeKind };

/** The final envelope. `answer` is legacy-defensive only: v2 sends text as deltas. */
export type DoneResult = {
  mode?: string;
  tools_used?: string[];
  actions?: Array<{ type: string } & Record<string, unknown>>;
  options?: Array<{ label: string; enviar: string }>;
  answer?: string;
};

/** Parse one NDJSON line. Returns null for blank or malformed lines. */
export function parseStreamLine(line: string): StreamEvent | null {
  const trimmed = line.trim();
  if (!trimmed) return null;
  try {
    const parsed = JSON.parse(trimmed) as StreamEvent;
    return parsed && typeof parsed.type === "string" ? parsed : null;
  } catch {
    // A truncated or corrupt line must not kill the stream.
    return null;
  }
}

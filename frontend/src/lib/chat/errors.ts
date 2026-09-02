/**
 * Chat stream failure codes. These drive both the copy the user sees and
 * whether a retry button is offered, so they are a closed set rather than
 * free-form strings.
 */
export type ChatErrorCode =
  | "session_expired"
  | "rate_limit"
  | "server"
  | "network"
  | "stream"
  | "aborted";

/** Codes worth offering a retry for. `session_expired` needs a new session, not a retry. */
const RETRYABLE: ReadonlySet<ChatErrorCode> = new Set<ChatErrorCode>([
  "rate_limit",
  "server",
  "network",
  "stream",
]);

export class ChatStreamError extends Error {
  readonly code: ChatErrorCode;
  readonly status?: number;

  constructor(code: ChatErrorCode, message?: string, status?: number) {
    super(message ?? code);
    this.name = "ChatStreamError";
    this.code = code;
    this.status = status;
  }

  get retryable(): boolean {
    return RETRYABLE.has(this.code);
  }
}

/** HTTP status -> error code. Anything unrecognised is treated as a server fault. */
export function chatErrorCodeFromStatus(status: number): ChatErrorCode {
  if (status === 401 || status === 403) return "session_expired";
  if (status === 429) return "rate_limit";
  return "server";
}

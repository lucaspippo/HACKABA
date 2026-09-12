import { describe, expect, it } from "vitest";
import { ChatStreamError, chatErrorCodeFromStatus } from "./errors";

describe("chatErrorCodeFromStatus", () => {
  it("maps 401 to session_expired", () => {
    expect(chatErrorCodeFromStatus(401)).toBe("session_expired");
  });

  it("maps 429 to rate_limit", () => {
    expect(chatErrorCodeFromStatus(429)).toBe("rate_limit");
  });

  it("maps any 5xx to server", () => {
    expect(chatErrorCodeFromStatus(500)).toBe("server");
    expect(chatErrorCodeFromStatus(503)).toBe("server");
  });

  it("falls back to server for unexpected statuses", () => {
    expect(chatErrorCodeFromStatus(418)).toBe("server");
  });
});

describe("ChatStreamError", () => {
  it("keeps its code and is instanceof Error", () => {
    const err = new ChatStreamError("rate_limit", "too many");
    expect(err).toBeInstanceOf(Error);
    expect(err.code).toBe("rate_limit");
    expect(err.message).toBe("too many");
  });

  it("marks rate_limit and server and network as retryable", () => {
    expect(new ChatStreamError("rate_limit").retryable).toBe(true);
    expect(new ChatStreamError("server").retryable).toBe(true);
    expect(new ChatStreamError("network").retryable).toBe(true);
  });

  it("marks session_expired as not retryable", () => {
    expect(new ChatStreamError("session_expired").retryable).toBe(false);
  });
});

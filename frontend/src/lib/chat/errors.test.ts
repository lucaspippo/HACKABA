import { describe, expect, it } from "vitest";
import { toAssistantError } from "@assistant-ui/core";
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

// ErrorState reads its code off `message.status.error.code`, which only
// works because assistant-ui's `toAssistantError` duck-types on `.code` and
// `.message` being strings and returns the original object unchanged when
// they are (see @assistant-ui/core's isAssistantError). That is a structural
// coincidence with an external package, not a stated contract, so it is
// pinned here directly against the real function rather than reasoned about
// from source: if a future assistant-ui version stops doing this, this test
// fails instead of ErrorState silently showing generic copy for everything.
describe("ChatStreamError through assistant-ui's toAssistantError", () => {
  it("survives with its code intact", () => {
    expect(toAssistantError(new ChatStreamError("network")).code).toBe("network");
    expect(toAssistantError(new ChatStreamError("rate_limit")).code).toBe("rate_limit");
  });

  it("survives even with no message argument, since message defaults to code", () => {
    expect(toAssistantError(new ChatStreamError("session_expired")).code).toBe("session_expired");
  });
});

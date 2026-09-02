import { describe, expect, it, vi, afterEach, beforeEach } from "vitest";
import { elapsedLabel } from "./useElapsedSince";

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe("elapsedLabel", () => {
  it("hides anything under two seconds as noise", () => {
    expect(elapsedLabel(0)).toBe("");
    expect(elapsedLabel(1900)).toBe("");
  });

  it("shows whole seconds", () => {
    expect(elapsedLabel(2000)).toBe("2s");
    expect(elapsedLabel(7400)).toBe("7s");
  });

  it("switches to minutes past sixty seconds", () => {
    expect(elapsedLabel(60000)).toBe("1m 0s");
    expect(elapsedLabel(95000)).toBe("1m 35s");
  });
});

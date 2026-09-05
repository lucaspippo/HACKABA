import { describe, expect, it } from "vitest";
import { hasVisibleBody } from "./messageBody";

describe("hasVisibleBody", () => {
  it("keeps the bubble while the run is in flight", () => {
    expect(hasVisibleBody({ partCount: 0, noticeCount: 0, isRunning: true })).toBe(true);
  });

  it("keeps the bubble once there is content", () => {
    expect(hasVisibleBody({ partCount: 1, noticeCount: 0, isRunning: false })).toBe(true);
  });

  it("keeps the bubble for a notice with no content", () => {
    expect(hasVisibleBody({ partCount: 0, noticeCount: 1, isRunning: false })).toBe(true);
  });

  it("drops the bubble for a finished run that produced nothing", () => {
    expect(hasVisibleBody({ partCount: 0, noticeCount: 0, isRunning: false })).toBe(false);
  });
});

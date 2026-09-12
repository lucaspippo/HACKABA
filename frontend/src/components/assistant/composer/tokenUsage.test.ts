import { describe, expect, it } from "vitest";
import { latestUsage } from "./tokenUsage";
import type { WireUsage } from "./tokenUsage";

const withUsage = (usage: WireUsage) => ({ metadata: { custom: { usage } } });

describe("latestUsage", () => {
  it("reports nothing when no message carries usage", () => {
    expect(latestUsage([{}, { metadata: {} }])).toBeNull();
  });

  it("reports nothing when the backend omits the context window", () => {
    expect(latestUsage([withUsage({ system: 1000, tools: 2000 })])).toBeNull();
  });

  it("converts tokens to the thousands the meter renders", () => {
    const usage = latestUsage([
      withUsage({ system: 2500, tools: 12000, messages: 8000, context_window: 200000 }),
    ]);
    expect(usage).toEqual({ system: 2.5, tools: 12, messages: 8, total: 200 });
  });

  it("takes the newest turn rather than summing, since each turn resends the history", () => {
    const usage = latestUsage([
      withUsage({ system: 2000, tools: 10000, messages: 1000, context_window: 200000 }),
      withUsage({ system: 2000, tools: 10000, messages: 5000, context_window: 200000 }),
    ]);
    expect(usage?.messages).toBe(5);
  });

  it("skips trailing messages that carry no usage", () => {
    const usage = latestUsage([
      withUsage({ system: 2000, tools: 10000, messages: 5000, context_window: 200000 }),
      {},
    ]);
    expect(usage?.messages).toBe(5);
  });

  it("treats missing segments as zero", () => {
    expect(latestUsage([withUsage({ context_window: 200000 })])).toEqual({
      system: 0, tools: 0, messages: 0, total: 200,
    });
  });

  it("never reports a negative segment", () => {
    const usage = latestUsage([withUsage({ system: -5, context_window: 200000 })]);
    expect(usage?.system).toBe(0);
  });
});

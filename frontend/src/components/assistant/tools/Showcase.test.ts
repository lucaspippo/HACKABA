import { describe, expect, it } from "vitest";
import { TOOL_PRESENTERS } from "./registry";
import fixtures from "./fixtures.generated.json";

type Fixture = { toolName: string; args: Record<string, unknown>; result: unknown };
const FIXTURES = fixtures as Record<string, Fixture>;

/**
 * The showcase is only a regression surface while every presenter has a
 * fixture. A presenter added without one renders nowhere but a paid chat turn,
 * which is the problem the route exists to solve.
 */
describe("the showcase fixtures", () => {
  it("covers every registered presenter", () => {
    const covered = new Set(Object.values(FIXTURES).map((f) => f.toolName));
    const missing = Object.keys(TOOL_PRESENTERS).filter((n) => !covered.has(n));
    expect(missing, `no fixture for: ${missing.join(", ")}`).toEqual([]);
  });

  it("carries a tool name, args and a result on every entry", () => {
    for (const [id, fixture] of Object.entries(FIXTURES)) {
      expect(fixture.toolName, `${id} has no toolName`).toBeTruthy();
      expect(fixture.args, `${id} has no args`).toBeTypeOf("object");
      expect(fixture.result, `${id} has no result`).not.toBeUndefined();
    }
  });

  it("includes the failure states a chat turn cannot be made to produce", () => {
    const failures = Object.values(FIXTURES).filter(
      (f) => (f.result as { ok?: boolean } | null)?.ok === false,
    );
    expect(failures.length).toBeGreaterThan(0);
  });
});

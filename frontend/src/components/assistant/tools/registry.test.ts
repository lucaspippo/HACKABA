import { describe, expect, it } from "vitest";
import { TOOL_PRESENTERS, presenterFor, toolComponentsByName } from "./registry";

describe("the registry", () => {
  it("returns undefined for a tool with no presenter", () => {
    expect(presenterFor("a_tool_that_does_not_exist")).toBeUndefined();
  });

  it("exposes every presenter as a by_name component", () => {
    const byName = toolComponentsByName();
    expect(Object.keys(byName).sort()).toEqual(Object.keys(TOOL_PRESENTERS).sort());
  });

  it("only registers presenters that declare labels", () => {
    for (const [name, presenter] of Object.entries(TOOL_PRESENTERS)) {
      expect(presenter.labels, `${name} has no labels`).toBeTruthy();
    }
  });

  it("keys every presenter by a snake_case tool name", () => {
    // Exact matching against angela.py's tool names is enforced at COMPILE
    // time by typing the registry as Partial<Record<ToolName, ...>> — a typo
    // fails `npm run typecheck`, which beats any runtime assertion. This is
    // the cheap shape guard on top of it.
    for (const name of Object.keys(TOOL_PRESENTERS)) {
      expect(name).toMatch(/^[a-z][a-z0-9_]*$/);
    }
  });
});

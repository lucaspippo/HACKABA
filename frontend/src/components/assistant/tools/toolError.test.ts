import { describe, expect, it } from "vitest";
import { toolErrorMessage } from "./toolError";

describe("toolErrorMessage", () => {
  it("prefers motivo over error when both are present", () => {
    expect(toolErrorMessage({ error: "sin_acceso", motivo: "tu rol no tiene ese módulo" })).toBe(
      "tu rol no tiene ese módulo",
    );
  });

  it("falls back to error when there is no motivo", () => {
    expect(toolErrorMessage({ error: "sin_acceso" })).toBe("sin_acceso");
  });

  it("returns undefined for a result with neither field", () => {
    expect(toolErrorMessage({ ok: true, series: [] })).toBeUndefined();
  });

  it("returns undefined for non-object results", () => {
    expect(toolErrorMessage(null)).toBeUndefined();
    expect(toolErrorMessage(undefined)).toBeUndefined();
    expect(toolErrorMessage("plain string")).toBeUndefined();
    expect(toolErrorMessage(42)).toBeUndefined();
  });
});

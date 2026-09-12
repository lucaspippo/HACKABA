import { describe, expect, it } from "vitest";
import { formatValue } from "./series";

describe("formatValue", () => {
  it("formats $ as pesos", () => {
    expect(formatValue(1234, "$")).toMatch(/\$/);
  });

  it("formats % with a trailing percent sign", () => {
    expect(formatValue(42, "%")).toBe("42%");
  });

  it("formats any other unit as a plain number", () => {
    expect(formatValue(1234, "unidades")).not.toMatch(/[$%]/);
  });
});

import { describe, expect, it } from "vitest";
import { fmtValor } from "./series";

describe("fmtValor", () => {
  it("formats $ as pesos", () => {
    expect(fmtValor(1234, "$")).toMatch(/\$/);
  });

  it("formats % with a trailing percent sign", () => {
    expect(fmtValor(42, "%")).toBe("42%");
  });

  it("formats any other unidad as a plain number", () => {
    expect(fmtValor(1234, "unidades")).not.toMatch(/[$%]/);
  });
});

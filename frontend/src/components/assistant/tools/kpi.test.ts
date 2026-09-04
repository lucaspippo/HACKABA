import { describe, expect, it } from "vitest";
import { saludTono } from "./kpi";

describe("saludTono", () => {
  it("maps en_orden to the salvia (in-order) tone", () => {
    expect(saludTono("en_orden")).toContain("salvia");
  });

  it("maps atencion to the oro (attention) tone", () => {
    expect(saludTono("atencion")).toContain("oro");
  });

  it("treats any other level as a real problem (rojo), never a silent default", () => {
    expect(saludTono("critico")).toContain("rojo");
    expect(saludTono(undefined)).toContain("rojo");
  });
});

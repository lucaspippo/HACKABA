import { describe, expect, it } from "vitest";
import { healthTone } from "./kpi";

describe("healthTone", () => {
  it("maps en_orden to the salvia (in-order) tone", () => {
    expect(healthTone("en_orden")).toContain("salvia");
  });

  it("maps atencion to the oro (attention) tone", () => {
    expect(healthTone("atencion")).toContain("oro");
  });

  it("treats any other level as a real problem (rojo), never a silent default", () => {
    expect(healthTone("critico")).toContain("rojo");
    expect(healthTone(undefined)).toContain("rojo");
  });
});

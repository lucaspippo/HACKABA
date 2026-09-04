import { describe, expect, it } from "vitest";
import { toneChipClass } from "./priorities";

describe("toneChipClass", () => {
  it("maps the three known tones to their chip classes", () => {
    expect(toneChipClass("rojo")).toContain("rojo");
    expect(toneChipClass("oro")).toContain("oro");
    expect(toneChipClass("salvia")).toContain("salvia");
  });

  it("falls back to a neutral chip for an unknown or missing tone", () => {
    expect(toneChipClass("nada_conocido")).toContain("papel-hondo");
    expect(toneChipClass(undefined)).toContain("papel-hondo");
  });
});

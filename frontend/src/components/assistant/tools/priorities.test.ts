import { describe, expect, it } from "vitest";
import { tonoChip } from "./priorities";

describe("tonoChip", () => {
  it("maps the three known tones to their chip classes", () => {
    expect(tonoChip("rojo")).toContain("rojo");
    expect(tonoChip("oro")).toContain("oro");
    expect(tonoChip("salvia")).toContain("salvia");
  });

  it("falls back to a neutral chip for an unknown or missing tone", () => {
    expect(tonoChip("nada_conocido")).toContain("papel-hondo");
    expect(tonoChip(undefined)).toContain("papel-hondo");
  });
});

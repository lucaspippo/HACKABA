import { describe, expect, it } from "vitest";
import { toolLabelKeys, humanizeToolName } from "./labels";

describe("humanizeToolName", () => {
  it("turns a snake_case tool name into readable words", () => {
    expect(humanizeToolName("top_inmovilizado")).toBe("top inmovilizado");
    expect(humanizeToolName("plata_en")).toBe("plata en");
  });

  it("leaves a single word alone", () => {
    expect(humanizeToolName("recordar")).toBe("recordar");
  });
});

describe("toolLabelKeys", () => {
  it("derives i18n keys from the tool name", () => {
    expect(toolLabelKeys("consultar_serie")).toEqual({
      running: "tool.consultar_serie.running",
      done: "tool.consultar_serie.done",
    });
  });
});

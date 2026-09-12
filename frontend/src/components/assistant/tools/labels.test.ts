import { describe, expect, it } from "vitest";
import { toolLabelKeys, humanizeToolName, toolStatusText } from "./labels";

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

describe("toolStatusText", () => {
  it("keeps the model's status line after the call finishes", () => {
    expect(
      toolStatusText("propose_rule", {
        running: false,
        modelLabel: "proponiendo recargo por mercadería fallada",
      }),
    ).toBe("proponiendo recargo por mercadería fallada");
  });

  it("falls back to the i18n (or humanized) label when there is no status", () => {
    expect(toolStatusText("propose_rule", { running: false })).not.toBe("");
    expect(toolStatusText("propose_rule", { running: true })).toMatch(/…$/);
  });
});

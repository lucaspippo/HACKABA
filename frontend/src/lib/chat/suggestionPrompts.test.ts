import { describe, expect, it } from "vitest";
import {
  MAX_SUGGESTIONS,
  SUGGESTION_CATALOG,
  suggestionPromptsFor,
} from "./suggestionPrompts";

describe("suggestionPromptsFor", () => {
  it("always offers priorities, even with no other features", () => {
    const ids = suggestionPromptsFor(() => false).map((p) => p.id);
    expect(ids).toEqual(["priorities"]);
  });

  it("picks the four richest demos when the user has everything", () => {
    const ids = suggestionPromptsFor(() => true).map((p) => p.id);
    expect(ids).toEqual(["priorities", "capital", "cash", "sales"]);
    expect(ids).toHaveLength(MAX_SUGGESTIONS);
  });

  it("falls through to collections when cash and sales are out of reach", () => {
    const has = (f: string) => f === "cuentas" || f === "cobranzas";
    const ids = suggestionPromptsFor(has).map((p) => p.id);
    expect(ids).toEqual(["priorities", "capital", "collect"]);
  });

  it("gives warehouse roles stock, warehouse and data cleanup", () => {
    const has = (f: string) =>
      f === "deposito" || f === "inventario" || f === "saneamiento";
    const ids = suggestionPromptsFor(has).map((p) => p.id);
    expect(ids).toEqual(["priorities", "capital", "data", "stock"]);
  });

  it("gives every catalog entry a unique id and a Spanish prompt", () => {
    const ids = SUGGESTION_CATALOG.map((p) => p.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const item of SUGGESTION_CATALOG) {
      expect(item.prompt.length).toBeGreaterThan(10);
      expect(item.labelKey.startsWith("angela.suggest.")).toBe(true);
    }
  });
});

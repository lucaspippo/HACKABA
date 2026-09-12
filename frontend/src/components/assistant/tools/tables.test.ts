import { describe, expect, it } from "vitest";
import { sortRows } from "./tables";

describe("sortRows", () => {
  const rows = [
    { name: "Beta", balance: 100 },
    { name: "Alpha", balance: 300 },
    { name: "Gamma", balance: 200 },
  ];

  it("sorts numerically descending by default direction", () => {
    expect(sortRows(rows, "balance", -1).map((r) => r.balance)).toEqual([300, 200, 100]);
  });

  it("sorts numerically ascending", () => {
    expect(sortRows(rows, "balance", 1).map((r) => r.balance)).toEqual([100, 200, 300]);
  });

  it("sorts strings alphabetically, honoring direction", () => {
    expect(sortRows(rows, "name", 1).map((r) => r.name)).toEqual(["Alpha", "Beta", "Gamma"]);
    expect(sortRows(rows, "name", -1).map((r) => r.name)).toEqual(["Gamma", "Beta", "Alpha"]);
  });

  it("does not mutate the input array", () => {
    const copy = [...rows];
    sortRows(rows, "balance", 1);
    expect(rows).toEqual(copy);
  });
});

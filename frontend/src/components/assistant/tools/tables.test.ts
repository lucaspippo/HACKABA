import { describe, expect, it } from "vitest";
import { sortRows } from "./tables";

describe("sortRows", () => {
  const rows = [
    { nombre: "Beta", saldo: 100 },
    { nombre: "Alfa", saldo: 300 },
    { nombre: "Gama", saldo: 200 },
  ];

  it("sorts numerically descending by default direction", () => {
    expect(sortRows(rows, "saldo", -1).map((r) => r.saldo)).toEqual([300, 200, 100]);
  });

  it("sorts numerically ascending", () => {
    expect(sortRows(rows, "saldo", 1).map((r) => r.saldo)).toEqual([100, 200, 300]);
  });

  it("sorts strings alphabetically, honoring direction", () => {
    expect(sortRows(rows, "nombre", 1).map((r) => r.nombre)).toEqual(["Alfa", "Beta", "Gama"]);
    expect(sortRows(rows, "nombre", -1).map((r) => r.nombre)).toEqual(["Gama", "Beta", "Alfa"]);
  });

  it("does not mutate the input array", () => {
    const copy = [...rows];
    sortRows(rows, "saldo", 1);
    expect(rows).toEqual(copy);
  });
});

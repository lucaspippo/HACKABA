import { describe, expect, it } from "vitest";
import { keys } from "./keys";

describe("query keys", () => {
  it("prefixes every key with polpilot so invalidate-all is one prefix", () => {
    expect(keys.all()).toEqual(["polpilot"]);
    expect(keys.inventario()[0]).toBe("polpilot");
    expect(keys.caja()[0]).toBe("polpilot");
  });

  it("nests inventario children under the inventario prefix", () => {
    expect(keys.inventarioViz().slice(0, 2)).toEqual(keys.inventario());
    expect(keys.inventarioTop(10).slice(0, 2)).toEqual(keys.inventario());
    expect(keys.inventarioBurn("ABC").slice(0, 2)).toEqual(keys.inventario());
  });

  it("puts request params in the key so filters do not share a cache entry", () => {
    expect(keys.productos({ q: "cafe" })).toEqual(["polpilot", "productos", { q: "cafe" }]);
    expect(keys.fichaProducto("X1")).toEqual(["polpilot", "ficha", "producto", "X1"]);
    expect(keys.deposito(15)).toEqual(["polpilot", "deposito", 15]);
  });

  it("nests piso reads under a piso prefix", () => {
    expect(keys.piso.mios()).toEqual(["polpilot", "piso", "mios"]);
    expect(keys.piso.mios().slice(0, 2)).toEqual(keys.piso.all());
  });
});

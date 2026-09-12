import { describe, expect, it } from "vitest";
import { keys } from "./keys";
import { MUTATIONS, invalidationKeys } from "./mutations";

function includesPrefix(list: unknown[][], prefix: unknown[]) {
  return list.some((key) => prefix.every((part, i) => key[i] === part));
}

describe("mutation invalidation map", () => {
  it("lists every write that the api client exposes", () => {
    const required = [
      "objetivoCrear",
      "objetivoEstado",
      "cajaCerrar",
      "cajaMovimiento",
      "cobranzaRegistrar",
      "conocimientoAprobar",
      "articuloCrear",
      "saleCrear",
      "receiptCrear",
      "preferenciaSet",
      "pisoReportar",
      "perfilIdioma",
    ] as const;
    for (const name of required) {
      expect(MUTATIONS[name], name).toBeTruthy();
    }
  });

  it("invalidates caja, local closes and inicio after closing cash", () => {
    const inv = invalidationKeys("cajaCerrar");
    expect(includesPrefix(inv, keys.caja())).toBe(true);
    expect(includesPrefix(inv, keys.cierresLocales().slice(0, 2))).toBe(true);
    expect(includesPrefix(inv, keys.inicio())).toBe(true);
  });

  it("invalidates cobranza and cuentas after registering a collection", () => {
    const inv = invalidationKeys("cobranzaRegistrar");
    expect(includesPrefix(inv, keys.cobranza())).toBe(true);
    expect(includesPrefix(inv, keys.cuentas())).toBe(true);
  });

  it("invalidates knowledge lists after an approval", () => {
    const inv = invalidationKeys("conocimientoAprobar");
    expect(includesPrefix(inv, keys.conocimiento().slice(0, 2))).toBe(true);
  });

  it("invalidates inventory after article or stock writes", () => {
    expect(includesPrefix(invalidationKeys("articuloCrear"), keys.inventario())).toBe(true);
    expect(includesPrefix(invalidationKeys("saleCrear"), keys.inventario())).toBe(true);
    expect(includesPrefix(invalidationKeys("receiptCrear"), keys.inventario())).toBe(true);
  });

  it("throws on an unknown mutation name", () => {
    expect(() => invalidationKeys("doesNotExist")).toThrow(/unknown mutation/i);
  });
});

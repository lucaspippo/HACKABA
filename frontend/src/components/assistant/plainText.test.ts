import { describe, expect, it } from "vitest";
import { plainText } from "./plainText";

describe("plainText", () => {
  it("drops bold and italic markers", () => {
    expect(plainText("Tenés **$85.700.000** en *mora*.")).toBe("Tenés $85.700.000 en mora.");
  });

  it("drops underscore emphasis", () => {
    expect(plainText("__importante__ y _leve_")).toBe("importante y leve");
  });

  it("keeps a link's text and drops its target", () => {
    expect(plainText("Mirá [Cuentas](https://example.com) ahora")).toBe("Mirá Cuentas ahora");
  });

  it("drops inline code backticks", () => {
    expect(plainText("El campo `saldo` está vacío")).toBe("El campo saldo está vacío");
  });

  it("drops heading hashes and list bullets", () => {
    expect(plainText("## Resumen\n- Uno\n- Dos")).toBe("Resumen\nUno\nDos");
  });

  it("keeps ordered list numbers, which carry meaning when read aloud", () => {
    expect(plainText("1. Uno\n2. Dos")).toBe("1. Uno\n2. Dos");
  });

  it("leaves plain prose untouched", () => {
    expect(plainText("Sin formato.")).toBe("Sin formato.");
  });

  it("does not mangle a lone asterisk between words", () => {
    expect(plainText("3 * 4")).toBe("3 * 4");
  });
});

describe("knowledge citations", () => {
  it("drops the marker so a screen reader does not read it", () => {
    expect(plainText("Le tolerás 45 días [·](#memoria-k01) porque es vieja.")).toBe(
      "Le tolerás 45 días porque es vieja.",
    );
  });

  it("still keeps the text of an ordinary link", () => {
    expect(plainText("Mirá [el informe](https://x.com).")).toBe("Mirá el informe.");
  });
});

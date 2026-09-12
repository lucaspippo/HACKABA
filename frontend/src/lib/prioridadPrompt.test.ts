import { describe, expect, it } from "vitest";
import { t } from "./i18n";
import { buildPrioridadPrompt } from "./prioridadPrompt";

const ITEM = {
  titulo: "Cobrar a los 3 clientes atrasados",
  resumen: "3 clientes tienen saldo vencido sin pagar.",
  monto: 85_700_000,
  fuentes: ["cuentas corrientes", "movimientos históricos por cliente"],
  insight: {
    pattern: { label: "3 clientes tienen saldo vencido sin pagar." },
    hypothesis: { label: "Ese dinero está trabajando en el negocio de otro." },
    recommendation: { detail: "Llamar hoy a los tres, empezando por el más atrasado." },
    risk: { label: "Capital inmovilizado en la calle." },
    owner: { suggested: "Aldo" },
    deadline: { date: "2026-09-12", basis: "curva de mora" },
    evidence: [
      {
        weight: "primary",
        label: "Saldo vencido total",
        value: 85_700_000,
        unit: "ars",
        records: [
          { name: "Autoservicio 9 de Julio", amount: 42_000_000 },
          { name: "Almacén San Martín", amount: 24_500_000 },
        ],
      },
      {
        weight: "primary",
        label: "Días sin pagar vs. su promedio",
        value: 66,
        unit: "days",
      },
    ],
  },
};

describe("buildPrioridadPrompt", () => {
  it("asks for a thorough natural-language reading and grounds it in the card", () => {
    const prompt = buildPrioridadPrompt(ITEM, t, "es");
    expect(prompt).toContain("lenguaje claro");
    expect(prompt).toContain("Cobrar a los 3 clientes atrasados");
    expect(prompt).toContain("Ese dinero está trabajando en el negocio de otro.");
    expect(prompt).toContain("Capital inmovilizado en la calle.");
    expect(prompt).toContain("Saldo vencido total");
    expect(prompt).toContain("Autoservicio 9 de Julio");
    expect(prompt).toContain("cuentas corrientes");
    expect(prompt).toContain("Aldo");
    expect(prompt).toMatch(/1\./);
    expect(prompt.length).toBeGreaterThan(400);
  });

  it("falls back to the title when the recommendation has no label of its own", () => {
    const prompt = buildPrioridadPrompt(ITEM, t, "es");
    expect(prompt).toContain("Qué conviene hacer: Cobrar a los 3 clientes atrasados");
    expect(prompt).toContain("Llamar hoy a los tres");
  });

  it("returns empty when there is no card", () => {
    expect(buildPrioridadPrompt(null, t)).toBe("");
  });
});

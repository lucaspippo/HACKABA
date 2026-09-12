/**
 * Empty-state prompts for Ángela. Each one is meant to exercise a real,
 * multi-tool capability (priorities, recoverable capital, cash patterns,
 * deflated sales, data cleanup, credit) rather than a one-number lookup.
 * The label is what the user sees; `prompt` is what the engine receives
 * and stays in Spanish.
 */

export type SuggestionPrompt = {
  id: string;
  labelKey: string;
  prompt: string;
  /** Shown when the user has any of these features. Omit to show to everyone. */
  anyOf?: readonly string[];
};

export const MAX_SUGGESTIONS = 4;

export const SUGGESTION_CATALOG: readonly SuggestionPrompt[] = [
  {
    id: "priorities",
    labelKey: "angela.suggest.priorities",
    prompt: "¿Cuáles son mis prioridades de hoy y por dónde me conviene empezar?",
  },
  {
    id: "capital",
    labelKey: "angela.suggest.capital",
    prompt: "¿Cuánto capital tengo trabado, de dónde sale y cómo lo destrabo?",
    anyOf: ["inventario", "cuentas", "oportunidades", "finanzas"],
  },
  {
    id: "cash",
    labelKey: "angela.suggest.cash",
    prompt: "¿Hay un patrón raro en los cierres de caja de los sábados?",
    anyOf: ["caja"],
  },
  {
    id: "sales",
    labelKey: "angela.suggest.sales",
    prompt:
      "Mostrame la evolución de ventas de los últimos 12 meses en pesos constantes y decime qué cambió de verdad.",
    anyOf: ["evolucion"],
  },
  {
    id: "data",
    labelKey: "angela.suggest.data",
    prompt: "¿Qué datos sucios tengo y proponé un plan para corregirlos?",
    anyOf: ["saneamiento"],
  },
  {
    id: "collect",
    labelKey: "angela.suggest.collect",
    prompt: "¿Quiénes me deben, hace cuánto, y a quién le puedo dar más crédito?",
    anyOf: ["cuentas", "cobranzas"],
  },
  {
    id: "stock",
    labelKey: "angela.suggest.stock",
    prompt: "¿Dónde está el mayor riesgo de mi inventario y qué plata está en juego?",
    anyOf: ["inventario"],
  },
  {
    id: "warehouse",
    labelKey: "angela.suggest.warehouse",
    prompt: "¿Qué stock está en negativo o por vencer, y qué plata representa?",
    anyOf: ["deposito"],
  },
];

export function suggestionPromptsFor(
  hasFeature: (feature: string) => boolean,
  catalog: readonly SuggestionPrompt[] = SUGGESTION_CATALOG,
  limit: number = MAX_SUGGESTIONS,
): SuggestionPrompt[] {
  return catalog
    .filter((item) => !item.anyOf || item.anyOf.some((feature) => hasFeature(feature)))
    .slice(0, limit);
}

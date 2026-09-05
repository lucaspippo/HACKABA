/** Every tool result that failed (feature gate, bad input, empty window) carries
 * `motivo` (the human explanation) and/or `error` (a short code) — shared by
 * Fallback's GenericResult and every presenter, so a gated/failed call never
 * renders as a silent blank card. */
export function toolErrorMessage(result: unknown): string | undefined {
  if (!result || typeof result !== "object") return undefined;
  const r = result as { error?: unknown; motivo?: unknown };
  const msg = r.motivo ?? r.error;
  return typeof msg === "string" ? msg : undefined;
}

export function ToolErrorText({ message }: { message: string }) {
  return <p className="mt-1 text-sm text-rojo-hondo">{message}</p>;
}

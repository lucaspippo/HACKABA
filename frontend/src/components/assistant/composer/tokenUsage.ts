export type WireUsage = {
  system?: number;
  tools?: number;
  messages?: number;
  context_window?: number;
};

export type ComposerUsageValues = {
  system: number;
  tools: number;
  messages: number;
  total: number;
};

type UsageCarrier = { metadata?: { custom?: { usage?: WireUsage } } };

const toK = (tokens: number) => Math.max(0, Math.round(tokens / 100) / 10);

/**
 * The newest reported usage, not the sum: every turn re-sends the whole
 * conversation, so its input count already IS the current context size.
 * Summing across turns would count the same history once per turn.
 */
export function latestUsage(
  messages: readonly UsageCarrier[],
): ComposerUsageValues | null {
  for (let i = messages.length - 1; i >= 0; i--) {
    const usage = messages[i]?.metadata?.custom?.usage;
    if (!usage || !usage.context_window) continue;
    return {
      system: toK(usage.system ?? 0),
      tools: toK(usage.tools ?? 0),
      messages: toK(usage.messages ?? 0),
      total: toK(usage.context_window),
    };
  }
  return null;
}

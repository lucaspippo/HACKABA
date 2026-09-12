export const RATES = [1, 1.25, 1.5, 0.75] as const;

export function splitWords(text: string): string[] {
  return text.split(/\s+/).filter(Boolean);
}

/**
 * The word the synthesiser is on, from the character offset its `boundary`
 * event reports. Measured, not interpolated from elapsed time: speech rate
 * varies within an utterance, so a time-based guess drifts off the word
 * actually being spoken.
 */
export function wordIndexAt(text: string, charIndex: number): number {
  if (charIndex <= 0) return 0;
  const upTo = text.slice(0, charIndex);
  const spoken = splitWords(upTo).length;
  return Math.max(0, /\s$/.test(upTo) ? spoken : spoken - 1);
}

export function nextRate(rate: number): number {
  const i = RATES.indexOf(rate as (typeof RATES)[number]);
  return RATES[(i + 1) % RATES.length]!;
}

export function formatElapsed(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

/**
 * Two short generated tones marking a voice call's start and end — the
 * "connected" / "hung up" cues, the way Claude's voice mode plays one on
 * each transition. Synthesized with the Web Audio API rather than shipped
 * as audio assets: no files to source, and identical across locales.
 */
let sharedContext: AudioContext | null = null;

function audioContext(): AudioContext | null {
  if (typeof window === "undefined") return null;
  const Ctor = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!Ctor) return null;
  if (!sharedContext) sharedContext = new Ctor();
  if (sharedContext.state === "suspended") sharedContext.resume().catch(() => {});
  return sharedContext;
}

function tone(freq: number, startOffset: number, duration: number, peak = 0.08) {
  const ctx = audioContext();
  if (!ctx) return;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = "sine";
  osc.frequency.value = freq;
  const t0 = ctx.currentTime + startOffset;
  gain.gain.setValueAtTime(0, t0);
  gain.gain.linearRampToValueAtTime(peak, t0 + 0.015);
  gain.gain.exponentialRampToValueAtTime(0.0001, t0 + duration);
  osc.connect(gain).connect(ctx.destination);
  osc.start(t0);
  osc.stop(t0 + duration + 0.02);
}

/** Rising two-note chime — the mic just started listening. */
export function playCallStartSound(): void {
  tone(660, 0, 0.14);
  tone(880, 0.09, 0.16);
}

/** Falling two-note chime — the call just ended. */
export function playCallEndSound(): void {
  tone(660, 0, 0.14);
  tone(440, 0.09, 0.18);
}

import { useEffect, useState } from "react";

/**
 * Wall-clock ms since `startedAt`, ticking once a second. Returns 0 when
 * `startedAt` is null (nothing running).
 *
 * Not assistant-ui's `useToolCallElapsed`: that hook reads `part.timing` from
 * the current message-part scope and returns undefined outside one, but the
 * thinking row renders before any part exists.
 */
export function useElapsedSince(startedAt: number | null): number {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (startedAt == null) return;
    setNow(Date.now());
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [startedAt]);

  return startedAt == null ? 0 : Math.max(0, now - startedAt);
}

/**
 * Elapsed ms as display text. Under two seconds shows nothing: a timer that
 * flickers on every fast answer is noise, not information.
 */
export function elapsedLabel(ms: number): string {
  if (ms < 2000) return "";
  const total = Math.floor(ms / 1000);
  if (total < 60) return `${total}s`;
  return `${Math.floor(total / 60)}m ${total % 60}s`;
}

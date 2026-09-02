import { useCallback, useEffect, useRef, useState } from "react";

const FRACTION_KEY = "polpilot.angelaPanelFraction";
const DEFAULT_FRACTION = 1 / 3;
const MAX_FRACTION = 0.5;
const MIN_WIDTH_PX = 320;
// Buffer past the 1/2 cap before the panel auto-maximizes, so brushing past
// the cap while aiming for it doesn't accidentally trigger fullscreen.
const OVERDRAG_PX = 48;

function clamp(n, min, max) {
  return Math.min(max, Math.max(min, n));
}

export function useAngelaPanelWidth(containerRef, onMaximize) {
  const [fraction, setFraction] = useState(DEFAULT_FRACTION);
  const fractionRef = useRef(fraction);
  fractionRef.current = fraction;
  const drag = useRef(null);
  const [, bump] = useState(0);

  useEffect(() => {
    let raw = null;
    try { raw = window.localStorage.getItem(FRACTION_KEY); } catch { /* empty */ }
    const n = raw ? Number(raw) : NaN;
    if (Number.isFinite(n) && n > 0 && n <= MAX_FRACTION) setFraction(n);
  }, []);

  useEffect(() => {
    const onResize = () => bump((n) => n + 1);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const persist = useCallback((next) => {
    try { window.localStorage.setItem(FRACTION_KEY, String(next)); } catch { /* empty */ }
  }, []);

  const total = containerRef.current?.clientWidth || 0;
  const minFraction = total > 0 ? Math.min(MIN_WIDTH_PX / total, MAX_FRACTION) : 0;
  const width = Math.round(clamp(fraction, minFraction, MAX_FRACTION) * total) || undefined;

  const onPointerDown = useCallback((e) => {
    const t = containerRef.current?.clientWidth || 0;
    if (!t) return;
    e.preventDefault();
    drag.current = { startX: e.clientX, startFraction: fractionRef.current, total: t };
    e.currentTarget.setPointerCapture?.(e.pointerId);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onPointerMove = useCallback((e) => {
    if (!drag.current) return;
    const { startX, startFraction, total: t } = drag.current;
    // The panel sits on the right edge, so dragging left grows it.
    const next = startFraction + (startX - e.clientX) / t;
    if (next > MAX_FRACTION + OVERDRAG_PX / t) {
      drag.current = null;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      onMaximize?.();
      return;
    }
    const minF = Math.min(MIN_WIDTH_PX / t, MAX_FRACTION);
    setFraction(clamp(next, minF, MAX_FRACTION));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onMaximize]);

  const endDrag = useCallback((e) => {
    if (!drag.current) return;
    drag.current = null;
    e.currentTarget.releasePointerCapture?.(e.pointerId);
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
    persist(fractionRef.current);
  }, [persist]);

  return { width, onPointerDown, onPointerMove, onPointerUp: endDrag };
}

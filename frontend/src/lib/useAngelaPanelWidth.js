import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

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

function clearDragCursor() {
  document.body.style.cursor = "";
  document.body.style.userSelect = "";
}

export function useAngelaPanelWidth(containerRef, onMaximize) {
  const [fraction, setFraction] = useState(DEFAULT_FRACTION);
  const [dragging, setDragging] = useState(false);
  const [, bump] = useState(0);

  const fractionRef = useRef(fraction);
  fractionRef.current = fraction;
  const dragRef = useRef(null);
  const onMaximizeRef = useRef(onMaximize);
  onMaximizeRef.current = onMaximize;
  const containerRefHeld = useRef(containerRef);
  containerRefHeld.current = containerRef;

  const persist = useCallback((next) => {
    try { window.localStorage.setItem(FRACTION_KEY, String(next)); } catch { /* empty */ }
  }, []);

  // Stable window listeners: identities never change, body always reads refs.
  const listeners = useRef({ move: null, up: null });
  const detach = () => {
    window.removeEventListener("pointermove", listeners.current.move);
    window.removeEventListener("mousemove", listeners.current.move);
    window.removeEventListener("pointerup", listeners.current.up);
    window.removeEventListener("mouseup", listeners.current.up);
    window.removeEventListener("pointercancel", listeners.current.up);
  };
  if (!listeners.current.move) {
    listeners.current.move = (e) => {
      const drag = dragRef.current;
      if (!drag) return;
      const next = drag.startFraction + (drag.startX - e.clientX) / drag.total;
      if (next > MAX_FRACTION + OVERDRAG_PX / drag.total) {
        dragRef.current = null;
        setDragging(false);
        clearDragCursor();
        detach();
        onMaximizeRef.current?.();
        return;
      }
      const minF = Math.min(MIN_WIDTH_PX / drag.total, MAX_FRACTION);
      setFraction(clamp(next, minF, MAX_FRACTION));
    };
    listeners.current.up = () => {
      if (!dragRef.current) return;
      dragRef.current = null;
      setDragging(false);
      clearDragCursor();
      detach();
      persist(fractionRef.current);
    };
  }

  useEffect(() => {
    let raw = null;
    try { raw = window.localStorage.getItem(FRACTION_KEY); } catch { /* empty */ }
    const n = raw ? Number(raw) : NaN;
    if (Number.isFinite(n) && n > 0 && n <= MAX_FRACTION) setFraction(n);
  }, []);

  useEffect(() => {
    const onResize = () => bump((n) => n + 1);
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      detach();
      clearDragCursor();
    };
  }, []);

  // Ref is empty on the first render; reread after layout so open isn't
  // stuck at width 0 (which the motion dock treats as "closed").
  useLayoutEffect(() => {
    bump((n) => n + 1);
  }, []);

  const total = containerRef.current?.clientWidth || 0;
  const minFraction = total > 0 ? Math.min(MIN_WIDTH_PX / total, MAX_FRACTION) : 0;
  const width = Math.round(clamp(fraction, minFraction, MAX_FRACTION) * total) || undefined;

  const onPointerDown = useCallback((e) => {
    const dock = e.currentTarget.closest("#angela-dock");
    const t = dock?.parentElement?.clientWidth || containerRefHeld.current.current?.clientWidth || 0;
    if (!t) return;
    e.preventDefault();
    const dockWidth = dock?.getBoundingClientRect().width || fractionRef.current * t;
    dragRef.current = {
      startX: e.clientX,
      startFraction: dockWidth / t,
      total: t,
    };
    setDragging(true);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    window.addEventListener("pointermove", listeners.current.move);
    window.addEventListener("mousemove", listeners.current.move);
    window.addEventListener("pointerup", listeners.current.up);
    window.addEventListener("mouseup", listeners.current.up);
    window.addEventListener("pointercancel", listeners.current.up);
  }, []);

  const remeasure = useCallback(() => bump((n) => n + 1), []);

  return {
    width,
    dragging,
    onPointerDown,
    remeasure,
  };
}

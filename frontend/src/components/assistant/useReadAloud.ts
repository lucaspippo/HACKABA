import { useCallback, useEffect, useRef, useState } from "react";
import { RATES, formatElapsed, splitWords, wordIndexAt } from "./readAloud";

export function isReadAloudSupported(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

export function useReadAloud(text: string) {
  const words = splitWords(text);
  const [playing, setPlaying] = useState(false);
  const [charIndex, setCharIndex] = useState(0);
  const [rate, setRate] = useState<number>(RATES[0]);
  const [elapsedMs, setElapsedMs] = useState(0);
  const startedAt = useRef(0);

  const stop = useCallback(() => {
    if (isReadAloudSupported()) window.speechSynthesis.cancel();
    setPlaying(false);
    setCharIndex(0);
    setElapsedMs(0);
  }, []);

  const speak = useCallback(
    (from: number, atRate: number) => {
      if (!isReadAloudSupported()) return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text.slice(from));
      utterance.rate = atRate;
      utterance.lang = document.documentElement.lang || "es-AR";
      utterance.onboundary = (event) => setCharIndex(from + event.charIndex);
      utterance.onend = () => {
        setPlaying(false);
        setCharIndex(0);
        setElapsedMs(0);
      };
      startedAt.current = Date.now() - elapsedMs;
      setPlaying(true);
      window.speechSynthesis.speak(utterance);
    },
    [text, elapsedMs],
  );

  const toggle = useCallback(() => {
    if (playing) stop();
    else {
      setElapsedMs(0);
      speak(0, rate);
    }
  }, [playing, rate, speak, stop]);

  // Rate changes restart from the word being spoken: the Web Speech API
  // cannot retune an utterance already in flight.
  const cycleRate = useCallback(() => {
    const next = RATES[(RATES.indexOf(rate as (typeof RATES)[number]) + 1) % RATES.length]!;
    setRate(next);
    if (playing) speak(charIndex, next);
  }, [rate, playing, charIndex, speak]);

  useEffect(() => {
    if (!playing) return;
    const id = setInterval(() => setElapsedMs(Date.now() - startedAt.current), 250);
    return () => clearInterval(id);
  }, [playing]);

  useEffect(() => stop, [stop]);

  return {
    words,
    spokenIndex: wordIndexAt(text, charIndex),
    playing,
    rate,
    elapsed: formatElapsed(elapsedMs),
    toggle,
    cycleRate,
  };
}

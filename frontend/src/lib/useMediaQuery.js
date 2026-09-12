import { useSyncExternalStore } from "react";

const cache = new Map();

function entry(query) {
  let found = cache.get(query);
  if (found) return found;
  const list = window.matchMedia(query);
  found = {
    subscribe(onChange) {
      list.addEventListener("change", onChange);
      return () => list.removeEventListener("change", onChange);
    },
    get: () => list.matches,
  };
  cache.set(query, found);
  return found;
}

export function useMediaQuery(query) {
  const supported = typeof window !== "undefined" && "matchMedia" in window;
  const { subscribe, get } = supported
    ? entry(query)
    : { subscribe: () => () => {}, get: () => false };
  return useSyncExternalStore(subscribe, get, () => false);
}

/** A device that takes photos: a touch screen with a camera behind it. */
export function useHasCamera() {
  const coarse = useMediaQuery("(pointer: coarse)");
  return coarse && typeof navigator !== "undefined" && !!navigator.mediaDevices;
}

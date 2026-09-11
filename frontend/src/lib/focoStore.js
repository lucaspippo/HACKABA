import { useSyncExternalStore } from "react";

// Productos puntuales que Ángela señala: al ir al inventario, se muestra SOLO
// esa selección, resaltada — no toda la lista.
let foco = null; // { titulo, codigos: [..] }
const listeners = new Set();

export const focoStore = {
  subscribe(l) { listeners.add(l); return () => listeners.delete(l); },
  getSnapshot() { return foco; },
  set(f) { foco = f; listeners.forEach((l) => l()); },
  clear() { foco = null; listeners.forEach((l) => l()); },
};

export function useFoco() {
  return useSyncExternalStore(focoStore.subscribe, focoStore.getSnapshot);
}

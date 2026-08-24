import { useSyncExternalStore } from "react";

// Documento que Ángela propuso y el usuario está editando antes de generar el PDF.
// `nuevo` marca que hay un documento que el usuario todavía no abrió — alimenta
// el micro-indicador (punto, no número) del sidebar (P17·E2a).
let snap = { doc: null, nuevo: false };
const listeners = new Set();
const emit = (doc, nuevo) => {
  snap = { doc, nuevo };
  listeners.forEach((l) => l());
};

export const docStore = {
  subscribe(l) { listeners.add(l); return () => listeners.delete(l); },
  getSnapshot() { return snap; },
  set(doc) { emit(doc, true); },
  patch(cambios) { emit({ ...snap.doc, ...cambios }, snap.nuevo); },
  visto() { if (snap.nuevo) emit(snap.doc, false); },
};

export function useDoc() {
  return useSyncExternalStore(docStore.subscribe, docStore.getSnapshot).doc;
}

export function useDocNuevo() {
  return useSyncExternalStore(docStore.subscribe, docStore.getSnapshot).nuevo;
}

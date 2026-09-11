import { useSyncExternalStore } from "react";

// Feedback unificado de acciones: UN toast estilo papel, en un solo lugar.
// Uso: toast("Listo, aprobada la solicitud."); toast(msg, "error").
let items = [];
const listeners = new Set();
let seq = 0;

function emit() {
  listeners.forEach((l) => l());
}

export function toast(texto, tipo = "ok") {
  const id = ++seq;
  items = [...items, { id, texto, tipo }];
  emit();
  setTimeout(() => {
    items = items.filter((t) => t.id !== id);
    emit();
  }, 3800);
}

export function useToasts() {
  return useSyncExternalStore(
    (l) => (listeners.add(l), () => listeners.delete(l)),
    () => items
  );
}

import { useSyncExternalStore } from "react";

// Sesión del usuario logueado. Persiste en localStorage. Reactiva.
const KEY = "polpilot.session.v1";
let session = load();
const listeners = new Set();

function load() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) || null;
  } catch {
    return null;
  }
}
function emit() {
  listeners.forEach((l) => l());
}

export const authStore = {
  subscribe(l) {
    listeners.add(l);
    return () => listeners.delete(l);
  },
  getSnapshot() {
    return session;
  },
  async login(username, password) {
    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const e = await res.json().catch(() => ({}));
      throw new Error(e.detail || "No pudimos iniciar sesión.");
    }
    session = await res.json(); // { token, usuario }
    localStorage.setItem(KEY, JSON.stringify(session));
    sessionStorage.removeItem("polpilot.logout.manual");
    emit();
    return session;
  },
  // `manual: true` = el usuario ELIGIÓ salir (botón): el autologin del demo
  // (B8) no lo vuelve a meter — ve la pantalla de login, que sigue existiendo.
  // Sin `manual` (401 por server reiniciado) el autologin puede re-entrar solo.
  logout({ manual = false } = {}) {
    session = null;
    localStorage.removeItem(KEY);
    if (manual) sessionStorage.setItem("polpilot.logout.manual", "1");
    emit();
  },
  // "View as / Ver como" del demo (P9·E): adopta la sesión LEGÍTIMA que emitió
  // el server para el usuario destino — misma forma que login ({token, usuario}).
  adoptar(nueva) {
    if (!nueva?.token || !nueva?.usuario) return;
    session = nueva;
    localStorage.setItem(KEY, JSON.stringify(session));
    emit();
  },
  // Refresca el usuario desde el backend (features nuevas tras una aprobación).
  async refresh() {
    if (!session?.token) return;
    const res = await fetch(`/api/me?token=${encodeURIComponent(session.token)}`);
    if (!res.ok) return; // sesión caída: se resuelve en el próximo login
    session = { ...session, usuario: await res.json() };
    localStorage.setItem(KEY, JSON.stringify(session));
    emit();
  },
  tiene(feature) {
    return !!session?.usuario?.features?.includes(feature);
  },
};

export function useSession() {
  return useSyncExternalStore(authStore.subscribe, authStore.getSnapshot);
}

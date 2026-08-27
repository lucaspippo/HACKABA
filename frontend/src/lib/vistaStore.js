import { useSyncExternalStore } from "react";

// Preferencias de vista que el dueño le pide a Ángela ("el dueño moldea su software").
// Ángela devuelve action {type:"modify_view", cambios:{...}} y acá se aplican y persisten.
// Arrancamos con un set acotado de modificaciones bien implementadas (no genérico infinito).
//
// P19·A — el SERVIDOR es la fuente de verdad de lo que Ángela recuerda
// (memoria.json por usuario): sin_torta, margen_pin_umbral, orden_home y los
// widgets sobreviven recarga, logout y cambio de máquina. localStorage queda
// como cache para que el primer render no parpadee; `hidratarServer()` pisa
// con lo del server apenas llega, y los cambios locales que son preferencia
// (quitar un widget, deshacer un orden) se escriben de vuelta vía
// /api/preferencias (write-through, fire-and-forget con log honesto).
const KEY = "polpilot.vista.v1";
const DEFAULT = {
  inicioTopN: 6,          // cuántos productos en "Dónde está la plata" del inicio
  mostrarEficiencia: true, // mostrar/ocultar la franja "lo que te ahorró"
  invMostrarMargen: false, // columna margen en la tabla de inventario (cuando haya datos)
  invOcultarCosto: false,  // ocultar la columna de costo en la tabla de inventario
  widgets: {},            // { seccion: [ {id, tipo, datos_fuente, titulo} ] } — creados por Ángela
  pestanas: [],           // [ {id, nombre, filtro} ] — pestañas del inventario creadas por Ángela
  balanzaEsquemaOk: false, // el dueño aceptó gestionar las balanzas como categoría aparte
  sidebarColapsado: false, // sidebar desktop en modo riel de íconos (solo local, no cruza dispositivo)
  // P19 — espejo local de las preferencias del server (fuente: memoria.json)
  sinTorta: false,         // no quiere gráficos de torta/donut
  margenPinUmbral: null,   // margen teórico < N% fijado arriba donde se listan márgenes
  ordenHome: null,         // orden de los bloques del Inicio (null = default)
};

let estado = load();
const listeners = new Set();

function load() {
  try {
    return { ...DEFAULT, ...(JSON.parse(localStorage.getItem(KEY)) || {}) };
  } catch {
    return { ...DEFAULT };
  }
}

// Write-through al server SOLO de las claves que viven en la memoria del
// usuario. Import perezoso de api para no crear ciclos (api importa auth).
async function _alServer(clave, valor) {
  try {
    const { api } = await import("./api");
    await api.preferenciaSet(clave, valor);
  } catch (e) {
    // Honesto en consola; la UI ya aplicó el cambio local y el server
    // se reconcilia en la próxima hidratación.
    console.warn("preferencia no persistida en el server:", clave, e);
  }
}

export const vistaStore = {
  subscribe(l) { listeners.add(l); return () => listeners.delete(l); },
  getSnapshot() { return estado; },
  aplicar(cambios = {}) {
    estado = { ...estado, ...cambios };
    localStorage.setItem(KEY, JSON.stringify(estado));
    listeners.forEach((l) => l());
  },
  // P19·A — lo que el server recuerda pisa el cache local (server = verdad).
  hidratarServer({ vista = {} } = {}) {
    this.aplicar({
      sinTorta: !!vista.sin_torta,
      margenPinUmbral: vista.margen_pin_umbral ?? null,
      ordenHome: vista.orden_home ?? null,
      widgets: vista.widgets ?? {},
    });
  },
  agregarWidget(seccion, widget) {
    if (!seccion || !widget) return;
    const widgets = { ...(estado.widgets || {}) };
    widgets[seccion] = [...(widgets[seccion] || []).filter((w) => w.id !== widget.id), widget];
    this.aplicar({ widgets });
    // El alta por chat YA la persistió el backend (crear_widget); no se re-escribe.
  },
  quitarWidget(seccion, id) {
    const widgets = { ...(estado.widgets || {}) };
    widgets[seccion] = (widgets[seccion] || []).filter((w) => w.id !== id);
    this.aplicar({ widgets });
    _alServer("widgets", widgets);
  },
  cambiarTipoWidget(id, tipo) {
    const widgets = { ...(estado.widgets || {}) };
    for (const sec of Object.keys(widgets)) {
      widgets[sec] = widgets[sec].map((w) => (w.id === id ? { ...w, tipo } : w));
    }
    this.aplicar({ widgets });
    _alServer("widgets", widgets);
  },
  setOrdenHome(orden) {
    this.aplicar({ ordenHome: orden });
    if (orden) _alServer("orden_home", orden);
  },
  agregarPestana(pestana) {
    if (!pestana?.id) return;
    const pestanas = [...(estado.pestanas || []).filter((p) => p.id !== pestana.id), pestana];
    this.aplicar({ pestanas });
  },
  quitarPestana(id) {
    this.aplicar({ pestanas: (estado.pestanas || []).filter((p) => p.id !== id) });
  },
  reset() {
    estado = { ...DEFAULT };
    localStorage.setItem(KEY, JSON.stringify(estado));
    listeners.forEach((l) => l());
  },
};

export function useVista() {
  return useSyncExternalStore(vistaStore.subscribe, vistaStore.getSnapshot);
}

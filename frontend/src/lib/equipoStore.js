import { useSyncExternalStore } from "react";
import { t } from "./i18n";

// Store compartido de objetivos y recordatorios del equipo (mobile + desktop).
// Persiste en localStorage. Ángela puede crear items desde el chat.
// Arquitectura pensada para que en el futuro se alimente de WhatsApp.

// P9·C1 (M2): el tablero es POR TENANT — el seed de Horizonte jamás aparece
// en el demo del Litoral (ni al revés). El tenant llega de /api/health (config
// del backend) vía equipoStore.setTenant(); se cachea para cargar sin parpadeo.
const KEY_BASE = "polpilot.equipo.v2";
const KEY_LEGACY = "polpilot.equipo.v1"; // piloto pre-P9: se migra tal cual
const TENANT_KEY = "polpilot.tenant";

// P37 — INCIDENTE DE PRIVACIDAD: el tenant NO tiene default (era "piloto"): así
// nunca se usa una semilla del piloto antes de que /api/health confirme el
// tenant real (equipoStore.setTenant). Con tenant desconocido, el tablero
// arranca VACÍO.
let tenant = localStorage.getItem(TENANT_KEY) || "";
const KEY = () => `${KEY_BASE}.${tenant || "sin_tenant"}`;

// P37 — La semilla del PILOTO tenía nombres de empleados y datos de negocio
// REALES de Horizonte hardcodeados: viajaba en el bundle público de la demo.
// SE ELIMINÓ del frontend. El tablero del piloto (cuando corre bajo SU tenant)
// arranca vacío y se llena por gestión manual / futuro backend — jamás con
// datos reales embebidos en el JS que sirve la demo.
const SEED_VACIO = { objetivos: [], recordatorios: [] };

// Semilla del DEMO, coherente con el dataset del Litoral (sus "puntitos": sin
// PVP, anulados con resto, negativos chicos) y con SU equipo (usuarios_demo).
// Los textos son KEYS del diccionario: se traducen al renderizar (demo bilingüe).
const SEED_DEMO = {
  objetivos: [
    {
      id: "o1",
      nombre: "seed_demo.obj_pvp",
      responsable: "Celeste",
      estado: "en_proceso",
      fecha: "seed_demo.fecha_semana",
    },
    {
      id: "o2",
      nombre: "seed_demo.obj_anulados",
      responsable: "Ramón",
      estado: "pendiente",
      fecha: "seed_demo.fecha_mes",
    },
  ],
  recordatorios: [
    { id: "r1", texto: "seed_demo.rec_conteo", responsable: "Tomás", hecho: false },
    { id: "r2", texto: "seed_demo.rec_listas", responsable: "Celeste", hecho: false },
  ],
};

let state = load();
const listeners = new Set();

function load() {
  try {
    const raw = localStorage.getItem(KEY());
    if (raw) return JSON.parse(raw);
  } catch {
    /* noop */
  }
  // Solo el DEMO tiene semilla (claves i18n, empresa ficticia). Cualquier otro
  // tenant (incluido "sin_tenant" antes de que health resuelva) arranca vacío.
  return structuredClone(tenant === "demo" ? SEED_DEMO : SEED_VACIO);
}

function save() {
  localStorage.setItem(KEY(), JSON.stringify(state));
  listeners.forEach((l) => l());
}

function emitSet(next) {
  state = next;
  save();
}

const uid = (p) => `${p}${Date.now().toString(36)}`;

export const equipoStore = {
  subscribe(listener) {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
  getSnapshot() {
    return state;
  },

  /** El tenant llega de /api/health. Si cambió, se recarga el tablero de ESE tenant. */
  setTenant(nuevo) {
    const valido = nuevo === "demo" ? "demo" : "piloto";
    if (valido === tenant) return;
    tenant = valido;
    localStorage.setItem(TENANT_KEY, tenant);
    state = load();
    listeners.forEach((l) => l());
    // P29·B2 — en una sesión FRESCA (localStorage vacío) el sincronizar() del
    // arranque puede correr ANTES de que health resuelva el tenant: el merge
    // del server caía en el tablero equivocado y el objetivo asignado no
    // aparecía hasta la próxima sesión. Al cambiar de tenant se re-mezcla.
    this.sincronizar();
  },

  addRecordatorio(texto, responsable = t("equipo.sin_asignar")) {
    emitSet({
      ...state,
      recordatorios: [{ id: uid("r"), texto, responsable, hecho: false }, ...state.recordatorios],
    });
  },
  toggleRecordatorio(id) {
    emitSet({
      ...state,
      recordatorios: state.recordatorios.map((r) =>
        r.id === id ? { ...r, hecho: !r.hecho } : r
      ),
    });
  },
  addObjetivo(nombre, responsable = t("equipo.sin_asignar"), fecha = t("equipo.sin_fecha"), id = null) {
    // Idempotente: si el objetivo ya llegó del server (Ángela lo persistió,
    // P9·C5/M9), no se duplica en el tablero local.
    if (id && state.objetivos.some((o) => o.id === id)) return;
    const oid = id || uid("o");
    emitSet({
      ...state,
      objetivos: [
        { id: oid, nombre, responsable, fecha, estado: "pendiente" },
        ...state.objetivos,
      ],
    });
    // Persistencia server-side de lo creado A MANO acá (adoptar/tablero): el
    // resto del equipo lo ve. Si vino con id, el server ya lo tiene.
    if (!id) {
      import("./api").then(({ api }) =>
        api.objetivoCrear(nombre, responsable, fecha, oid).catch(() => {})
      );
    }
  },
  cicloEstado(id) {
    const orden = ["pendiente", "en_proceso", "listo"];
    let nuevoEstado = null;
    emitSet({
      ...state,
      objetivos: state.objetivos.map((o) => {
        if (o.id !== id) return o;
        nuevoEstado = orden[(orden.indexOf(o.estado) + 1) % orden.length];
        return { ...o, estado: nuevoEstado };
      }),
    });
    // El estado también se persiste server-side (404 si es un seed local: ok).
    if (nuevoEstado) {
      import("./api").then(({ api }) =>
        api.objetivoEstado(id, nuevoEstado).catch(() => {})
      );
    }
  },

  /** Mezcla los objetivos del SERVER en el tablero. P24·A2: además de sumar
   *  los ids nuevos, ACTUALIZA estado/responsable de los conocidos (server
   *  gana) — el avance que marca el empleado le llega al dueño y viceversa. */
  async sincronizar() {
    try {
      const { api } = await import("./api");
      const r = await api.objetivos();
      const delServer = new Map((r.objetivos || []).map((o) => [o.id, o]));
      const locales = new Set(state.objetivos.map((o) => o.id));
      const nuevos = (r.objetivos || []).filter((o) => !locales.has(o.id));
      const actualizados = state.objetivos.map((o) => {
        const s = delServer.get(o.id);
        return s ? { ...o, estado: s.estado, responsable: s.responsable, fecha: s.fecha } : o;
      });
      emitSet({ ...state, objetivos: [...nuevos, ...actualizados] });
    } catch {
      /* sin red o sin sesión: el tablero local sigue andando */
    }
  },

  // Aplica las acciones que devuelve Ángela desde el chat.
  aplicarAcciones(acciones = []) {
    for (const a of acciones) {
      if (a.type === "crear_recordatorio") this.addRecordatorio(a.texto, a.responsable);
      if (a.type === "crear_objetivo") this.addObjetivo(a.nombre, a.responsable, a.fecha, a.id);
    }
  },
};

// Hook reactivo
export function useEquipo() {
  return useSyncExternalStore(equipoStore.subscribe, equipoStore.getSnapshot);
}

// Keys del diccionario (patrón lk): se traducen con t() al renderizar.
export const ESTADO_LABEL = {
  pendiente: "equipo.estado_pendiente",
  en_proceso: "equipo.estado_en_proceso",
  listo: "equipo.estado_listo",
};

import { useSyncExternalStore } from "react";
import { ES } from "./locales/es.js";
import { EN } from "./locales/en.js";
import { authStore } from "./auth.js";

// Idioma de la interfaz (Prompt 8). Reactivo, con la MISMA fuente de verdad que
// el backend: la preferencia vive POR USUARIO en su perfil (el servidor la manda
// en login/me como usuario.idioma); acá solo se cachea para pintar sin parpadeo.
// Resolución: elección del usuario > cache local > default del tenant (/api/health).
// Convención de la casa: TODO string nuevo nace bilingüe — entra a locales/es.js
// y locales/en.js el mismo día. Los keys internos (features, rutas, tools) no se
// traducen: son identificadores.

const KEY = "polpilot.lang.v1";
const TENANT_LANG_KEY = "polpilot.tenant_lang";  // default del tenant, cacheado
const DICTS = { es: ES, en: EN };
const VALIDOS = ["es", "en"];

let lang = load();
const listeners = new Set();

function load() {
  try {
    const s = JSON.parse(localStorage.getItem("polpilot.session.v1"));
    if (VALIDOS.includes(s?.usuario?.idioma)) return s.usuario.idioma;
  } catch { /* sin sesión */ }
  // 1) lo que el usuario ELIGIÓ explícitamente (perfil).
  let cache = null;
  try { cache = localStorage.getItem(KEY); } catch { /* localStorage no disponible */ }
  if (VALIDOS.includes(cache)) return cache;
  // 2) P37·AJUSTE 1 — el default del TENANT (POLPILOT_DEFAULT_LANG, "en" en la
  //    demo), cacheado tras el primer health: así el path mobile ARRANCA en
  //    inglés como desktop, sin flash de español. El cambio manual (arriba)
  //    siempre gana.
  let tenantLang = null;
  try { tenantLang = localStorage.getItem(TENANT_LANG_KEY); } catch { /* localStorage no disponible */ }
  if (VALIDOS.includes(tenantLang)) return tenantLang;
  // 3) último recurso, solo antes de conocer el tenant en el primerísimo load.
  return "es";
}

function emit() {
  listeners.forEach((l) => l());
}

export const langStore = {
  subscribe(l) {
    listeners.add(l);
    return () => listeners.delete(l);
  },
  getSnapshot() {
    return lang;
  },
  /** Cambia el idioma: pinta ya, persiste en el perfil del usuario (servidor). */
  async set(nuevo) {
    if (!VALIDOS.includes(nuevo) || nuevo === lang) return;
    lang = nuevo;
    localStorage.setItem(KEY, nuevo);
    emit();
    const s = authStore.getSnapshot();
    if (s?.token && s?.usuario?.username) {
      try {
        const { runMutation } = await import("./query");
        await runMutation("perfilIdioma", s.usuario.username, s.token, nuevo);
        await authStore.refresh(); // la sesión cacheada queda con el idioma nuevo
      } catch { /* sin red: queda el cache local; el servidor se sincroniza al próximo cambio */ }
    }
  },
  /** Al loguear / refrescar sesión: adoptar el idioma que dice el servidor. */
  syncDesdeUsuario(usuario) {
    if (VALIDOS.includes(usuario?.idioma) && usuario.idioma !== lang) {
      lang = usuario.idioma;
      localStorage.setItem(KEY, lang);
      emit();
    }
  },
  /** Pre-sesión (Login): adoptar el default del tenant si el visitante no eligió. */
  syncDefaultTenant(idiomaDefault) {
    if (!VALIDOS.includes(idiomaDefault)) return;
    // Cachear el default del tenant para que el PRÓXIMO load arranque ya en ese
    // idioma (sin el "es" de último recurso) — sin pisar la elección del usuario.
    localStorage.setItem(TENANT_LANG_KEY, idiomaDefault);
    if (!localStorage.getItem(KEY) && idiomaDefault !== lang) {
      lang = idiomaDefault;
      emit();
    }
  },
};

/** Traduce un key. Params con {nombre}. Key faltante → cae a ES → key visible. */
export function t(key, params) {
  const texto = DICTS[lang]?.[key] ?? DICTS.es[key] ?? key;
  if (!params) return texto;
  return texto.replace(/\{(\w+)\}/g, (m, k) => (params[k] ?? m));
}

/** Nombre de rol en pantalla. El rol interno (string del seed) no cambia:
 *  se traduce solo el display, con fallback al rol tal cual si no hay clave. */
export function tRol(rol) {
  if (!rol) return "";
  const key = "rol." + rol;
  const texto = DICTS[lang]?.[key] ?? DICTS.es[key];
  return texto ?? rol;
}

/** El texto de un DATO bilingüe: la descripción de un perfil, una nota del
 *  equipo, una pieza del conocimiento del negocio. Estos textos no son UI (no
 *  viven en el diccionario): nacen en los dos idiomas junto al dato, y acá se
 *  elige el del que mira. Sin versión en inglés cae al castellano — nunca queda
 *  vacío, y ese fallback es el caso REAL de lo que una persona reescribió de su
 *  propio perfil: son sus palabras y se muestran tal cual las escribió. */
export function tDato(es, en) {
  return (lang === "en" && en) ? en : (es || "");
}

/** Nombre de categoría del dataset en pantalla. El valor de dato (string del
 *  ERP, p.ej. "fiambres y quesos (balanza)") es la clave canónica para el
 *  round-trip a /api/consulta-serie; acá se traduce SOLO el display. Set
 *  finito (~8 rubros). Sin clave → cae al valor tal cual (ES = el dato). */
export function tCat(cat) {
  if (!cat) return "";
  const texto = DICTS[lang]?.["cat." + cat];
  return texto ?? cat;
}

export function useLang() {
  return useSyncExternalStore(langStore.subscribe, langStore.getSnapshot);
}

/** Hook de conveniencia: re-renderiza al cambiar el idioma y devuelve t. */
export function useT() {
  useLang();
  return t;
}

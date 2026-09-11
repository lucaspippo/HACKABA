// Formateo de plata, números y fechas — UN solo lugar, consciente del idioma.
// ES: $1.234.567 (formato argentino de siempre). EN: $1,234,567 (agrupación
// en-US) — un reviewer estadounidense lee "$1.234" como un dólar con centavos
// y ese malentendido es letal (mismo espíritu que el validador del factor
// ×1000). La moneda SIEMPRE es pesos argentinos: en EN, "ARS" discreto donde
// haga falta desambiguar (helper monedaSufijo), sin ensuciar las cards.
import { langStore, t } from "./i18n.js";

const LOCALE = { es: "es-AR", en: "en-US" };

const _pesoFmt = {};
const _numFmt = {};
function pesoFmtDe(lang) {
  if (!_pesoFmt[lang]) {
    _pesoFmt[lang] = new Intl.NumberFormat(LOCALE[lang] || LOCALE.es, {
      style: "currency", currency: "ARS", maximumFractionDigits: 0,
      currencyDisplay: "symbol",
    });
  }
  return _pesoFmt[lang];
}
function numFmtDe(lang) {
  if (!_numFmt[lang]) {
    _numFmt[lang] = new Intl.NumberFormat(LOCALE[lang] || LOCALE.es, { maximumFractionDigits: 0 });
  }
  return _numFmt[lang];
}

// UNA regla para toda la plata: sin espacio entre $ y el número, y sin el
// prefijo "ARS " que algunos locales le meten al peso argentino.
export const peso = (n) => {
  const lang = langStore.getSnapshot();
  return pesoFmtDe(lang)
    .format(Math.round(n || 0))
    .replace(/^(-?)(ARS\s?|\$\s?)/, "$1$$");
};

// Versión compacta para números grandes en espacios chicos: $18,4M (ES) / $18.4M (EN)
export function pesoCorto(n) {
  const lang = langStore.getSnapshot();
  const v = Math.abs(n || 0);
  const signo = n < 0 ? "-" : "";
  const dec = (x) => (lang === "en" ? x : x.replace(".", ","));
  if (v >= 1_000_000) return `${signo}$${dec((v / 1_000_000).toFixed(1))}M`;
  if (v >= 1_000) return `${signo}$${(v / 1_000).toFixed(0)}${lang === "en" ? "K" : " mil"}`;
  return `${signo}$${Math.round(v)}`;
}

export const num = (n) => numFmtDe(langStore.getSnapshot()).format(Math.round(n || 0));

// Fechas localizadas: "12 jul 2026" (ES) / "Jul 12, 2026" (EN).
// Acepta ISO ("2026-07-12" o con hora) y devuelve el string tal cual si no parsea.
export function fecha(iso) {
  if (!iso) return "";
  const d = new Date(String(iso).length === 10 ? `${iso}T00:00:00` : iso);
  if (isNaN(d)) return String(iso);
  const lang = langStore.getSnapshot();
  return new Intl.DateTimeFormat(LOCALE[lang] || LOCALE.es,
    { day: "numeric", month: "short", year: "numeric" }).format(d);
}

// "ARS" discreto para desambiguar la moneda en EN (en ES no hace falta).
export const monedaSufijo = () => (langStore.getSnapshot() === "en" ? " ARS" : "");

/**
 * Renderiza las PARTES que manda el backend ([{k, p}, ...]) en el idioma ACTIVO.
 *
 * El backend decide QUÉ decir y con qué números (determinista, en el core); el
 * idioma lo pone quien dibuja. Antes el servidor mandaba el párrafo ya armado y
 * salía en español sobre una UI en inglés, porque el idioma del perfil y el del
 * navegador se desincronizan.
 *
 * Convención de params, para no tener que conocer clave por clave:
 *   `*_pesos` → plata      `*_fecha` → fecha ISO      el resto va tal cual
 * Y `d` (cantidad de diferencias) elige la variante `_dif` cuando es > 0.
 *
 * Vive acá y no en i18n.js a propósito: format.js ya importa de i18n, así que
 * no abre un ciclo de imports nuevo.
 */
export function renderPartes(partes, prefijo = "angela.pro_") {
  return (partes || []).map(({ k, p }) => {
    const params = {};
    for (const [nombre, valor] of Object.entries(p || {})) {
      params[nombre] = nombre.endsWith("_pesos") ? peso(valor)
        : nombre.endsWith("_fecha") ? fecha(valor)
          : valor;
    }
    return t(prefijo + k + (Number(p?.d) > 0 ? "_dif" : ""), params);
  }).filter(Boolean);
}

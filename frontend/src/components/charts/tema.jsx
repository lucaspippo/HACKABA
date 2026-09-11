import { GRAFICO } from "../../lib/paleta";

// Theme compartido de charts (P17·E3) — se define UNA vez, todos lo consumen:
//  · grid SOLO horizontal, 1px, ~6% de opacidad
//  · half-frame: sin línea de eje Y, eje X hairline (nada arriba ni a la derecha)
//  · tabular-nums en todos los números
//  · tooltip blanco con sombra suave (jamás negro)
//  · línea de datos 2.5px (más gruesa que ejes/grid)

export const STROKE_DATA = 2.5;
export const GRIS_TENUE = "#c9c5bd"; // serie secundaria/tenue (sin carga semántica)

// OJO recharts v2: NO envolver sus hijos (CartesianGrid/XAxis/…) en componentes
// propios — el chart los ignora. Por eso el theme son PROPS, no wrappers:
//   <CartesianGrid {...gridProps} />
export const gridProps = {
  horizontal: true,
  vertical: false,
  stroke: "rgba(33,32,29,0.06)",
  strokeWidth: 1,
};

const tickBase = { fontSize: 11, fill: GRAFICO.tintaSuave, fontVariantNumeric: "tabular-nums" };

export const ejeX = (extra = {}) => ({
  axisLine: { stroke: GRAFICO.linea, strokeWidth: 1 },
  tickLine: false,
  tick: tickBase,
  ...extra,
});

export const ejeY = (extra = {}) => ({
  axisLine: false,
  tickLine: false,
  tick: tickBase,
  ...extra,
});

// Props para el <Tooltip> default de recharts: card blanca, sombra suave.
export const tooltipProps = {
  contentStyle: {
    background: GRAFICO.superficie,
    border: `1px solid ${GRAFICO.linea}`,
    borderRadius: 12,
    boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
    fontSize: 12,
    color: GRAFICO.tinta,
    fontVariantNumeric: "tabular-nums",
  },
  labelStyle: { fontWeight: 600, color: GRAFICO.tinta },
  itemStyle: { color: GRAFICO.tinta },
  cursor: { fill: "rgba(33,32,29,0.04)" },
};

// Escala secuencial de UN hue (teal) para el treemap: más oscuro = más plata.
// t en [0,1] → color entre teal claro y teal profundo.
export function tealSecuencial(t) {
  const claro = [215, 231, 235];   // #d7e7eb
  const oscuro = [24, 77, 89];     // #184d59
  const c = claro.map((v, i) => Math.round(v + (oscuro[i] - v) * Math.min(1, Math.max(0, t))));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

// ¿El texto sobre este fill va claro u oscuro? (luminancia aproximada)
export function textoSobre(fillRgb) {
  const m = /rgb\((\d+),(\d+),(\d+)\)/.exec(fillRgb);
  if (!m) return GRAFICO.superficie;
  const [r, g, b] = [+m[1], +m[2], +m[3]];
  const lum = 0.299 * r + 0.587 * g + 0.114 * b;
  return lum > 150 ? GRAFICO.tinta : GRAFICO.superficie;
}

// Paleta para gráficos (Recharts recibe hex, no clases Tailwind).
// Espeja los tokens de src/index.css — si el @theme cambia, cambiar acá también.
// El violeta NO participa: es exclusivo de Ángela/IA, nunca una serie de datos.
export const GRAFICO = {
  tinta: "#21201d",
  tintaSuave: "#6e6a63",
  linea: "#e9e7e2",
  fondo: "#fbfbfa",
  superficie: "#ffffff",
  hielo: "#2b7a8c", // capital congelado / plata
  oro: "#de7c1a", // atención / nominal
  salvia: "#2f7d5b", // en orden / positivo
  rojo: "#d2372b", // problema real
  rojoHondo: "#a82a20",
};

// Series categóricas (datos sin carga semántica): variaciones de hielo/oro/salvia.
export const SERIES = [
  GRAFICO.hielo,
  GRAFICO.oro,
  GRAFICO.salvia,
  "#4f9aa8",
  "#c06e15",
  "#55917a",
];

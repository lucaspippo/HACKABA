// Metadata de cada grupo de problemas: copy en lenguaje humano (no técnico),
// tono, y la acción que Ángela sugiere. Una sola fuente para Inicio/Alertas/Inventario.
// i18n: titulo/resumen/detalle/accion son KEYS del diccionario (patrón lk:) —
// el consumidor los pasa por t() al renderizar. El texto vive en locales/es.js y en.js.

export const ALERTA_DEFS = {
  fantasmas: {
    grupo: "fantasmas",
    titulo: "alertadefs.fantasmas.titulo",
    resumen: "alertadefs.fantasmas.resumen",
    detalle: "alertadefs.fantasmas.detalle",
    accion: "alertadefs.fantasmas.accion",
    tono: "atencion",
    metrica: "unidades",
  },
  negativos: {
    grupo: "negativos",
    titulo: "alertadefs.negativos.titulo",
    resumen: "alertadefs.negativos.resumen",
    detalle: "alertadefs.negativos.detalle",
    accion: "alertadefs.negativos.accion",
    tono: "urgente",
    metrica: "unidades",
  },
  sin_pvp: {
    grupo: "sin_pvp",
    titulo: "alertadefs.sin_pvp.titulo",
    resumen: "alertadefs.sin_pvp.resumen",
    detalle: "alertadefs.sin_pvp.detalle",
    accion: "alertadefs.sin_pvp.accion",
    tono: "atencion",
    metrica: "cantidad",
  },
  balanza: {
    grupo: "balanza",
    titulo: "alertadefs.balanza.titulo",
    resumen: "alertadefs.balanza.resumen",
    detalle: "alertadefs.balanza.detalle",
    accion: "alertadefs.balanza.accion",
    tono: "urgente",
    metrica: "cantidad",
  },
  costo_viejo: {
    grupo: "costo_viejo",
    titulo: "alertadefs.costo_viejo.titulo",
    resumen: "alertadefs.costo_viejo.resumen",
    detalle: "alertadefs.costo_viejo.detalle",
    accion: "alertadefs.costo_viejo.accion",
    tono: "atencion",
    metrica: "cantidad",
  },
};

export const ORDEN_ALERTAS = ["balanza", "negativos", "fantasmas", "sin_pvp", "costo_viejo"];

// P38·A — QUÉ cuenta como "Datos a corregir", en UN solo lugar.
//
// Antes cada pantalla lo sumaba a mano y el costo viejo quedaba afuera del
// badge pero adentro de la sección: el sidebar decía 15 y el libro listaba 5
// grupos. Un costo sin actualizar hace más de un año ES un registro a
// corregir —la propia app avisa que "el margen que ves ahí no es real"—, así
// que entra. Ahora el badge del sidebar, el filtro de la tabla de stock y la
// sección Saneamiento cuentan exactamente lo mismo.
export const GRUPOS_A_CORREGIR = ["fantasmas", "negativos", "sin_pvp", "balanza", "costo_viejo"];

// El número lo calcula el núcleo (resumen.a_corregir): cuenta REGISTROS, no
// incidencias — un producto con dos problemas es un producto a corregir, no
// dos. El fallback suma los grupos sólo si el backend es viejo.
export function contarACorregir(data) {
  if (!data) return 0;
  const resumen = data.resumen || (data.total_articulos != null ? data : null);
  if (resumen && resumen.a_corregir != null) return resumen.a_corregir;
  const alertas = data.alertas || data;
  return GRUPOS_A_CORREGIR.reduce((n, g) => n + (alertas?.[g]?.cantidad || 0), 0);
}

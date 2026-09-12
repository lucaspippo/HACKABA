import { num } from "./format";

// Categorías del libro de calidad con corrección automática propuesta
// (espejo de CATEGORIAS_AUTO del backend): las únicas que esperan un OK.
export const CATEGORIAS_CON_PROPUESTA = ["fantasma", "balanza"];

// Arma la cola de decisión del dueño desde /api/inicio (P13). Devuelve datos
// puros — cada superficie decide el CTA (desktop navega con highlight, mobile
// lo abre con Ángela). Sin dato real no hay card: nada se inventa.
export function armarDecisiones(ini, t) {
  if (!ini) return [];
  const d = [];
  // UNA DECISIÓN POR ARCHIVO, no por lote.
  //
  // El bug: cuatro lotes del mismo CSV producían cuatro filas idénticas —
  // mismo título, mismo nombre de archivo, mismas 12 filas— una debajo de la
  // otra. Nadie puede decidir entre cuatro cosas que se leen igual, y el que
  // abre esto a las siete de la mañana asume que la pantalla está rota.
  //
  // La unidad de esta cola es el ARCHIVO que espera un OK, no la fila de la
  // tabla de lotes (PRODUCT.md, The Counting Rule). Sumar las filas de varios
  // lotes del mismo archivo sí es legítimo: son renglones del mismo import, y
  // el número que el dueño necesita es cuántos va a integrar en total.
  //
  // Los ids de los lotes viajan en `batches` para que la acción siga pudiendo
  // abrirlos: se agrupa lo que se MUESTRA, no lo que se hace.
  const porArchivo = new Map();
  for (const b of ini.staging?.batches || []) {
    const clave = b.nombre || b.id;
    const g = porArchivo.get(clave)
      || { nombre: b.nombre, batches: [], filas: 0 };
    g.batches.push(b.id);
    g.filas += b.total_filas || 0;
    porArchivo.set(clave, g);
  }
  for (const g of porArchivo.values()) {
    d.push({
      id: `staging-${g.batches.join("-")}`,
      tipo: "staging",
      batches: g.batches,
      titulo: t("inicio.dec_staging_titulo"),
      // Con un solo lote, la frase de siempre. Con varios, se dice cuántos:
      // esconder que son cuatro sería cambiar un bug visible por uno callado.
      detalle: g.batches.length > 1
        ? t("inicio.dec_staging_detalle_lotes",
            { nombre: g.nombre, lotes: num(g.batches.length), n: num(g.filas) })
        : t("inicio.dec_staging_detalle", { nombre: g.nombre, n: num(g.filas) }),
      monto: null,
    });
  }
  const grupos = (ini.calidad?.grupos || [])
    .filter((g) => CATEGORIAS_CON_PROPUESTA.includes(g.categoria) && g.cantidad > 0)
    .sort((a, b) => (b.impacto_pesos || 0) - (a.impacto_pesos || 0));
  // BLOQUE F·3 — CONTRA LA FATIGA DE APROBACIÓN. Si el dueño puso la limpieza
  // de datos en "todo junto" (core/autonomia.py), las categorías reversibles
  // viajan como UNA card en vez de una por categoría. Sigue habiendo un sí
  // humano: cambia cuántas veces se lo interrumpe, no quién decide. El default
  // es "de a una" — nadie agrupa nada sin que el dueño lo elija.
  if (ini.autonomia_datos === "agrupa" && grupos.length > 1) {
    d.push({
      id: "calidad-agrupada",
      tipo: "calidad_agrupada",
      categorias: grupos.map((g) => g.categoria),
      titulo: t("inicio.dec_calidad_junta_titulo", { n: num(grupos.length) }),
      detalle: t("inicio.dec_calidad_junta_detalle", {
        n: num(grupos.reduce((a, g) => a + g.cantidad, 0)),
        labels: grupos.map((g) => g.label).join(", "),
      }),
      monto: grupos.reduce((a, g) => a + (g.impacto_pesos || 0), 0) || null,
    });
  } else {
    for (const g of grupos) {
      d.push({
        id: `calidad-${g.categoria}`,
        tipo: "calidad",
        categoria: g.categoria,
        titulo: g.label,
        detalle: t("inicio.dec_calidad_detalle", { n: num(g.cantidad) }),
        monto: g.impacto_pesos > 0 ? g.impacto_pesos : null,
      });
    }
  }
  if ((ini.solicitudes || []).length > 0) {
    d.push({
      id: "solicitudes",
      tipo: "solicitudes",
      titulo: t("inicio.dec_solicitudes_titulo"),
      detalle: t("inicio.dec_solicitudes_detalle", { n: num(ini.solicitudes.length) }),
      monto: null,
    });
  }
  return d;
}

// EL PUENTE ENTRE EL CHAT Y EL GRAFO.
//
// La pantalla del cerebro usa el chat REAL del producto (ChatPanel, con las
// tarjetas de herramienta de ToolCallCard): no hay un chat propio ni una copia
// del tratamiento visual. Pero el grafo necesita saber qué herramientas se
// están llamando para encender el camino, y esa información vive adentro del
// runtime de assistant-ui.
//
// En vez de duplicar el parseo del stream, el adapter —que ya ve pasar cada
// evento— avisa por acá. Un bus de tres eventos y nada más:
//
//     empieza()            una pregunta arrancó
//     herramienta(nombre)  esa herramienta se está ejecutando
//     termina(tools)       la respuesta cerró
//
// Sin listeners no pasa nada: fuera de la pantalla del cerebro esto es un
// no-op, así que el chat normal no paga ni un render por existir.
const listeners = new Set();

function emitir(evento) {
  for (const l of listeners) {
    try { l(evento); } catch { /* un listener roto no corta el stream */ }
  }
}

export const cerebroBus = {
  empieza(pregunta) { emitir({ tipo: "empieza", pregunta }); },
  herramienta(nombre, etiqueta) { emitir({ tipo: "herramienta", nombre, etiqueta }); },
  termina(tools) { emitir({ tipo: "termina", tools: tools || [] }); },
  subscribe(l) {
    listeners.add(l);
    return () => listeners.delete(l);
  },
  get activo() { return listeners.size > 0; },
};

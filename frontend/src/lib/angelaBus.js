// Mensajes PROACTIVOS de Ángela (B1): el backend los compone al confirmarse
// una carga y el flujo que confirmó los empuja acá; el chat (AngelaView) los
// muestra como mensajes de Ángela sin que nadie pregunte.
//
// Cada mensaje tiene un id incremental y sale de la cola UNA sola vez
// (drain o entrega en vivo): el doble-mount de StrictMode no duplica nada.
let seq = 0;
let cola = [];
const listeners = new Set();

export const angelaBus = {
  push(content) {
    const msg = { id: ++seq, content };
    if (listeners.size > 0) {
      listeners.forEach((l) => l(msg));
    } else {
      cola.push(msg);
    }
  },
  subscribe(l) {
    listeners.add(l);
    return () => listeners.delete(l);
  },
  drain() {
    const pendientes = cola;
    cola = [];
    return pendientes;
  },
};

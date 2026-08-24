// Capa del empleado (frontline). Una VISTA para roles que YA existen — no un
// permiso nuevo. El acceso lo dan los features del rol; esto sólo decide qué
// TAREAS se le derivan del día. Quién aterriza en su vista de trabajo y con qué
// acciones/chips lo decide el catálogo de roles (lib/roles.js, P39·2).

// Las tareas del día NO son un store nuevo: se DERIVAN de señales que el sistema
// ya tiene (mismos endpoints que ve el dueño), filtradas a lo que el rol puede
// leer. Si un rol no tiene el feature (p.ej. mostrador sin saneamiento), esa
// señal simplemente no llega y su tarea no aparece — sin inventar nada.
//
// `cerrable` = la tarea se CIERRA desde el piso (saneamiento aplica la
// corrección real → auditoría atribuida a la persona → el dueño la ve en Equipo,
// y el cerebro registra la decisión). Las no-cerrables abren Ángela (lectura):
// contar negativos y verificar entradas necesitan un ajuste de stock que llega
// en un pase posterior — acá se muestran, no se fingen.
//   - fantasma : productos anulados que siguen con stock (cerrable · saneamiento)
//   - balanza  : balanzas descalibradas (cerrable · saneamiento)
//   - negativo : stock negativo por contar (lectura → Ángela; cierre = pase E3)
//   - entrada  : lote en el área de revisión por verificar (lectura → Ángela)
const CATS_CERRABLES = ["fantasma", "balanza"];
export function derivarTareas(ini) {
  const tareas = [];
  const grupos = ini?.calidad?.grupos || [];
  for (const cat of CATS_CERRABLES) {
    const g = grupos.find((x) => x.categoria === cat);
    if (g && g.cantidad > 0) tareas.push({ id: cat, tipo: cat, categoria: cat, cerrable: true, n: g.cantidad });
  }
  const neg = grupos.find((g) => g.categoria === "negativo");
  if (neg && neg.cantidad > 0) tareas.push({ id: "neg", tipo: "negativo", cerrable: false, n: neg.cantidad });
  for (const b of (ini?.staging?.batches || [])) {
    tareas.push({
      id: "ent-" + b.id, tipo: "entrada", cerrable: false, batchId: b.id,
      nombre: b.nombre, filas: b.total_filas ?? (b.filas ? b.filas.length : null),
    });
  }
  return tareas;
}

// P39·2 — las preguntas por oficio se mudaron a lib/roles.js (el catálogo cubre
// los SIETE roles, no sólo depósito y mostrador). Acá quedan las que además de
// preguntar son TAREAS de lectura del piso: MobileApp las usa para abrir Ángela
// cuando se toca una tarea derivada.
export const PREGUNTA_TAREA = {
  negativo: "piso.chip_negativo",
  entrada: "piso.chip_remito",
};

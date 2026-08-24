// Centro de alertas (P16/P17): UNA fuente para las señales y su conteo.
// La pantalla Alertas renderiza cada señal con su copy/CTA; el badge del
// sidebar solo las CUENTA — mismas condiciones, imposible que diverjan.
import { api } from "./api";
import { authStore } from "./auth";

export async function cargarSenales() {
  const pedir = (cond, fn) => (cond ? fn().catch(() => null) : Promise.resolve(null));
  const sesion = authStore.getSnapshot();
  const [evolucion, ventas, cuentas, analisis, deposito, pagos, inventario, caja, solicitudes,
         traslados, vencimientos] = await Promise.all([
    api.evolucion().catch(() => null),
    pedir(authStore.tiene("inventario"), api.ventas),
    pedir(authStore.tiene("cuentas"), api.cuentas),
    pedir(authStore.tiene("oportunidades"), api.analisis),
    pedir(authStore.tiene("deposito"), () => api.deposito()),
    pedir(authStore.tiene("finanzas"), api.pagos),
    // P25·B2 — las señales nuevas piden sus datos (mismo patrón, mismo gate)
    pedir(authStore.tiene("inventario"), api.inventario),
    pedir(authStore.tiene("caja"), api.cajaEstado),
    pedir(!!sesion?.usuario?.es_admin,
          () => api.solicitudes(sesion.token, "pendiente")),
    // P38·F/H — los dos cruces nuevos, con el mismo gate por módulo
    pedir(authStore.tiene("inventario"), api.traslados),
    pedir(authStore.tiene("deposito"), () => api.vencimientos(30)),
  ]);
  return { evolucion, ventas, cuentas, analisis, deposito, pagos, inventario, caja,
           solicitudes, traslados, vencimientos };
}

// Las señales vivas, como ids con su tono y sus datos crudos. El orden es el
// de gravedad (rojo primero) que la pantalla ya usa.
// P27·B — severidad SEMÁNTICA real: rojo = pérdida activa o riesgo serio;
// oro = atención/decisión pendiente; azul = informativa (te aviso, no te
// apuro). No todo es rojo: una alerta que grita siempre no dice nada.
export function alertasVivas(s) {
  const v = [];
  const quiebre = s.ventas?.quiebre;
  if (quiebre?.cantidad > 0) v.push({ id: "quiebre", tono: "rojo", datos: quiebre });
  const mora = s.cuentas?.alertas;
  if (mora?.cantidad > 0) v.push({ id: "morosos", tono: "rojo", datos: mora });
  const pv = s.pagos?.resumen;
  if (pv?.pagos_vencidos > 0) v.push({ id: "pago_vencido", tono: "rojo", datos: pv });
  const dep = s.deposito?.resumen;
  if (dep?.vencidos > 0) v.push({ id: "dep_vencidos", tono: "rojo", datos: dep });
  if (dep?.por_vencer > 0) v.push({ id: "dep_porvencer", tono: "oro", datos: dep });
  if (dep?.discrepancias > 0) v.push({ id: "dep_discrep", tono: "oro", datos: dep });
  if (pv?.por_pagar_semana > 0) v.push({ id: "pago_semana", tono: "azul", datos: pv });
  if (pv?.cheques_cartera > 0) v.push({ id: "cheques", tono: "azul", datos: pv });
  const pico = s.analisis?.estacionalidad?.proximos_picos?.[0];
  if (pico) v.push({ id: "pico", tono: "azul", datos: pico });
  // P25·B2 — las señales de negocio que los datos YA sostienen:
  // 1 · el moroso pagando MUY por encima de su propio promedio histórico
  const atrasado = (s.cuentas?.clientes || []).filter((c) => c.en_mora && c.atraso_vs_promedio >= 80)
    .sort((a, b) => b.atraso_vs_promedio - a.atraso_vs_promedio)[0];
  if (atrasado) v.push({ id: "moroso_atraso", tono: "rojo", datos: atrasado });
  // 2 · costo sin actualizar hace más de un año (la detección ya existe)
  const cv = s.inventario?.alertas?.costo_viejo;
  if (cv?.cantidad > 0) v.push({ id: "costo_viejo", tono: "oro", datos: cv });
  // 3 · caja del día inusual vs el promedio del historial (detección existente)
  const cj = s.caja;
  if (cj?.abierta && cj?.totales?.total > 0 && (cj.historial || []).length >= 5) {
    const proms = cj.historial.map((h) => h.total).filter((x) => x > 0);
    const prom = proms.reduce((a, b) => a + b, 0) / proms.length;
    const desvio = prom ? Math.abs(cj.totales.total - prom) / prom : 0;
    if (desvio > 0.4) v.push({ id: "caja_inusual", tono: "oro",
                               datos: { total: cj.totales.total, promedio: prom,
                                        historial: cj.historial } });
  }
  // P38·H — lo que vence Y no llegás a vender al ritmo actual. Distinto de
  // dep_porvencer (que sólo mira la fecha): acá hay plata que se va a tirar.
  const venc = s.vencimientos;
  if (venc?.disponible && venc.lotes_en_riesgo > 0) {
    v.push({ id: "venc_riesgo", tono: "rojo", datos: venc });
  }
  // P41·2.1 — la separación de locales propios YA NO es un hallazgo. Que Ángela
  // le "descubra" al dueño que Sucursal Norte es su propio local es decirle algo
  // que obviamente ya sabe: suena tonto y gasta un lugar en Insights.
  // Es una acción de ESTRUCTURA que Ángela ya hizo (los rankings del producto
  // salen limpios desde el bloque F), y como tal se cuenta en "lo que Ángela ya
  // hizo" (ver ActividadFeed) y se VE en el mapa. Los datos siguen en
  // s.traslados para quien los quiera: lo que se fue es la tarjeta de alerta.
  // 4 · solicitud de módulo esperando al dueño (con su porqué, P24·C3)
  const sols = s.solicitudes?.solicitudes;
  if (sols?.length > 0) v.push({ id: "solicitud_pendiente", tono: "oro",
                                 datos: { n: sols.length, primera: sols[0] } });
  return v;
}

export function contarAlertas(s) {
  const caidas = s.evolucion?.hay_datos ? (s.evolucion.alertas || []).length : 0;
  return caidas + alertasVivas(s).length;
}

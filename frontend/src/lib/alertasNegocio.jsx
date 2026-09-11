// P35·E3 — Fuente ÚNICA de la presentación de las alertas de negocio, extraída
// de sections/AlertasNegocio.jsx SIN cambiar su salida (refactor que preserva
// comportamiento). La usan: el desktop (AlertasNegocio, grilla de cards) y el
// mobile (InsightsMobile, filas compactas). Cero datos nuevos: solo re-empaqueta
// lo que ya compone lib/centroAlertas + el copy i18n existente (alertasneg.*).
import { PackageX, HandCoins, TrendingUp, Clock, Scale, Banknote, FileText,
         Store, CalendarX } from "lucide-react";
import { alertasVivas } from "./centroAlertas";
import { pesoCorto, num } from "./format";

// Serie P21 armada en el cliente con los MISMOS datos crudos de la señal.
export const serie = (nombre, puntos, unidad, temporal, ventana = "") => ({
  ok: true, series: [{ nombre, puntos }],
  meta: { unidad, temporal, ventana },
});

const mesesEntre = (desde, hasta) => {
  const out = [];
  let a = +desde.slice(0, 4), m = +desde.slice(5, 7);
  while (`${String(a).padStart(4, "0")}-${String(m).padStart(2, "0")}` <= hasta) {
    out.push(`${String(a).padStart(4, "0")}-${String(m).padStart(2, "0")}`);
    m += 1;
    if (m > 12) { a += 1; m = 1; }
  }
  return out.slice(-24);
};

// La curva de pagos de un cliente moroso (fecha congelada, no "hoy" del navegador).
export const curvaPagos = (cliente, nombre) => {
  const movs = cliente.movimientos || [];
  const pagos = movs.filter((m) => m.tipo === "pago" || m.tipo === "cobro");
  if (pagos.length < 4) return null;
  const porMes = {};
  for (const p of pagos) {
    const k = (p.fecha || "").slice(0, 7);
    if (k) porMes[k] = (porMes[k] || 0) + (p.monto || 0);
  }
  const hasta = movs.map((m) => (m.fecha || "").slice(0, 7)).sort().pop();
  const meses = mesesEntre(Object.keys(porMes).sort()[0], hasta);
  return serie(nombre, meses.map((k) => ({ x: k, y: porMes[k] || 0 })), "$", true,
               `${meses[0]} → ${meses[meses.length - 1]}`);
};

// Copy/ícono/cifra/fuentes/porqué por señal — condiciones y severidad vienen del
// lib compartido (centroAlertas). Cada entrada trae el dato, el porqué al
// expandir, y una acción. `onNavegar` es opcional (el mobile lo puede omitir).
export function presentacionAlertas(t, onNavegar) {
  return {
    quiebre: (d) => ({ icon: PackageX, titulo: t("alertasneg.fut_stock_t"),
      detalle: t("alertasneg.quiebre_d", { n: num(d.cantidad) }),
      cifraTexto: num(d.cantidad),
      fuentes: [t("alertasneg.f_stock"), t("alertasneg.f_ventas")],
      porque: [t("alertasneg.q_quiebre", { n: num(d.cantidad) })],
      chat: t("alertasneg.ac_quiebre"),
      cta: t("alertasneg.ver_inventario"), ir: () => onNavegar?.("inventario", "rotacion") }),
    morosos: (d) => ({ icon: HandCoins, titulo: t("alertasneg.fut_clientes_t"),
      detalle: t("alertasneg.morosos_d", { n: num(d.cantidad), monto: pesoCorto(d.impacto_pesos) }),
      monto: d.impacto_pesos,
      fuentes: [t("alertasneg.f_cuentas"), t("alertasneg.f_hist_pagos")],
      porque: [t("alertasneg.q_morosos", { n: num(d.cantidad), monto: pesoCorto(d.impacto_pesos) })],
      chat: t("alertasneg.ac_morosos"),
      cta: t("alertasneg.ver_cuentas"), ir: () => onNavegar?.("cuentas", "morosos") }),
    pago_vencido: (d) => ({ icon: Banknote, titulo: t("alertasneg.pago_vencido_t"),
      detalle: t("alertasneg.pago_vencido_d", { n: num(d.pagos_vencidos), monto: pesoCorto(d.vencidos_total) }),
      monto: d.vencidos_total,
      fuentes: [t("alertasneg.f_finanzas")],
      porque: [t("alertasneg.q_pago_vencido", { n: num(d.pagos_vencidos) })],
      chat: t("alertasneg.ac_pago_vencido"),
      cta: t("alertasneg.ver_finanzas"), ir: () => onNavegar?.("finanzas") }),
    dep_vencidos: (d) => ({ icon: Clock, titulo: t("alertasneg.dep_vencidos_t"),
      detalle: t("alertasneg.dep_vencidos_d", { n: num(d.vencidos) }),
      cifraTexto: num(d.vencidos),
      fuentes: [t("alertasneg.f_deposito")],
      porque: [t("alertasneg.q_dep_vencidos", { n: num(d.vencidos) })],
      chat: t("alertasneg.ac_dep_vencidos"),
      cta: t("alertasneg.ver_deposito"), ir: () => onNavegar?.("deposito") }),
    dep_porvencer: (d) => ({ icon: Clock, titulo: t("alertasneg.dep_porvencer_t"),
      detalle: t("alertasneg.dep_porvencer_d", { n: num(d.por_vencer) }),
      cifraTexto: num(d.por_vencer),
      fuentes: [t("alertasneg.f_deposito")],
      porque: [t("alertasneg.q_dep_porvencer", { n: num(d.por_vencer) })],
      chat: t("alertasneg.ac_dep_porvencer"),
      cta: t("alertasneg.ver_deposito"), ir: () => onNavegar?.("deposito") }),
    dep_discrep: (d) => ({ icon: Scale, titulo: t("alertasneg.dep_discrep_t"),
      detalle: t("alertasneg.dep_discrep_d", { n: num(d.discrepancias) }),
      cifraTexto: num(d.discrepancias),
      fuentes: [t("alertasneg.f_deposito")],
      porque: [t("alertasneg.q_dep_discrep", { n: num(d.discrepancias) })],
      chat: t("alertasneg.ac_dep_discrep"),
      cta: t("alertasneg.ver_deposito"), ir: () => onNavegar?.("deposito") }),
    pago_semana: (d) => ({ icon: Banknote, titulo: t("alertasneg.pago_semana_t"),
      detalle: t("alertasneg.pago_semana_d", { monto: pesoCorto(d.por_pagar_semana) }),
      monto: d.por_pagar_semana,
      fuentes: [t("alertasneg.f_finanzas")],
      porque: [t("alertasneg.q_pago_semana")],
      chat: t("alertasneg.ac_pago_semana"),
      cta: t("alertasneg.ver_finanzas"), ir: () => onNavegar?.("finanzas") }),
    cheques: (d) => ({ icon: FileText, titulo: t("alertasneg.cheques_t"),
      detalle: t("alertasneg.cheques_d", { n: num(d.cheques_cartera), monto: pesoCorto(d.cheques_total) }),
      monto: d.cheques_total,
      fuentes: [t("alertasneg.f_finanzas")],
      porque: [t("alertasneg.q_cheques", { n: num(d.cheques_cartera) })],
      chat: t("alertasneg.ac_cheques"),
      cta: t("alertasneg.ver_finanzas"), ir: () => onNavegar?.("finanzas") }),
    pico: (d) => ({ icon: TrendingUp, titulo: t("alertasneg.fut_compra_t"),
      detalle: d.aviso,
      cifraTexto: `×${d.indice}`,
      fuentes: [t("alertasneg.f_ventas10"), t("alertasneg.f_estacion")],
      porque: [t("alertasneg.q_pico", { mes: d.mes, cat: d.categoria })],
      chat: t("alertasneg.ac_pico", { cat: d.categoria }),
      cta: t("alertasneg.ver_evolucion"), ir: () => onNavegar?.("evolucion") }),
    moroso_atraso: (d) => ({ icon: HandCoins, titulo: t("alertasneg.moroso_atraso_t", { nombre: d.nombre }),
      detalle: t("alertasneg.moroso_atraso_d", { dias: num(d.dias_sin_pagar), atraso: num(d.atraso_vs_promedio), prom: num(d.promedio_pago_dias) }),
      monto: d.saldo,
      fuentes: [t("alertasneg.f_cuentas"), t("alertasneg.f_hist_pagos")],
      porque: [t("alertasneg.q_moroso_atraso_1", { nombre: d.nombre, dias: num(d.dias_sin_pagar), prom: num(d.promedio_pago_dias) }),
               t("alertasneg.q_moroso_atraso_2", { atraso: num(d.atraso_vs_promedio) })],
      grafico: curvaPagos(d, t("alertasneg.g_pagos", { nombre: d.nombre })),
      chat: t("alertasneg.ac_moroso_atraso", { nombre: d.nombre }),
      cta: t("alertasneg.ver_cuentas"), ir: () => onNavegar?.("cuentas", `cliente-${d.id}`) }),
    costo_viejo: (d) => ({ icon: Clock, titulo: t("alertasneg.costo_viejo_t"),
      detalle: t("alertasneg.costo_viejo_d", { n: num(d.cantidad) }),
      cifraTexto: num(d.cantidad),
      fuentes: [t("alertasneg.f_costos")],
      porque: [t("alertasneg.q_costo_viejo", { n: num(d.cantidad) })],
      chat: t("alertasneg.ac_costo_viejo"),
      cta: t("alertasneg.ver_inventario"), ir: () => onNavegar?.("inventario", "costo_viejo") }),
    caja_inusual: (d) => ({ icon: Banknote, titulo: t("alertasneg.caja_inusual_t"),
      detalle: t("alertasneg.caja_inusual_d", { total: pesoCorto(d.total), prom: pesoCorto(d.promedio) }),
      monto: d.total,
      fuentes: [t("alertasneg.f_caja"), t("alertasneg.f_hist_caja")],
      porque: [t("alertasneg.q_caja_inusual", { total: pesoCorto(d.total), prom: pesoCorto(d.promedio) })],
      grafico: (d.historial || []).length >= 5
        ? serie(t("alertasneg.g_caja"),
                d.historial.filter((h) => h.total > 0).map((h) => ({ x: h.fecha, y: h.total })),
                "$", true)
        : null,
      chat: t("alertasneg.ac_caja_inusual"),
      cta: t("alertasneg.ver_caja"), ir: () => onNavegar?.("caja") }),
    // P38·H — vencimiento × ritmo real de venta: lo que NO llegás a vender.
    venc_riesgo: (d) => ({ icon: CalendarX, titulo: t("alertasneg.venc_riesgo_t", { n: num(d.lotes_en_riesgo) }),
      detalle: t("alertasneg.venc_riesgo_d", { producto: d.items[0]?.producto, dias: num(d.items[0]?.dias_restantes), monto: pesoCorto(d.total_en_riesgo) }),
      monto: d.total_en_riesgo,
      fuentes: [t("alertasneg.f_deposito"), t("alertasneg.f_ventas")],
      porque: [t("alertasneg.q_venc_riesgo_1", { producto: d.items[0]?.producto, cant: num(Math.round(d.items[0]?.cantidad || 0)), dias: num(d.items[0]?.dias_restantes), ritmo: num(Math.round(d.items[0]?.ritmo_mes || 0)) }),
               t("alertasneg.q_venc_riesgo_2", { n: num(d.lotes_en_riesgo), monto: pesoCorto(d.total_en_riesgo) })],
      chat: t("alertasneg.ac_venc_riesgo"),
      cta: t("alertasneg.ver_deposito"), ir: () => onNavegar?.("deposito", "vencimientos") }),
    // P38·F — el ERP cuenta como venta lo que es reposición a un local propio.
    local_propio: (d) => ({ icon: Store, titulo: t("alertasneg.local_propio_t", { local: d.top_local?.local }),
      detalle: t("alertasneg.local_propio_d", { monto: pesoCorto(d.total_12m), puesto: d.top_local?.puesto_como_cliente }),
      monto: d.total_12m,
      montoLabel: t("alertasneg.local_propio_label"),
      fuentes: [t("alertasneg.f_traslados"), t("alertasneg.f_ventas"), t("alertasneg.f_cuentas")],
      porque: [d.top_local?.desplaza
                 ? t("alertasneg.q_local_propio_1", { local: d.top_local.local, monto: pesoCorto(d.top_local.monto), puesto: d.top_local.puesto_como_cliente, cliente: d.top_local.desplaza })
                 : t("alertasneg.q_local_propio_1b", { local: d.top_local?.local, monto: pesoCorto(d.top_local?.monto), puesto: d.top_local?.puesto_como_cliente }),
               t("alertasneg.q_local_propio_2", { producto: d.distorsionado?.producto, crudo: d.distorsionado?.pos_crudo, real: d.distorsionado?.pos_real }),
               t("alertasneg.q_local_propio_3")],
      grafico: serie(t("alertasneg.g_local_propio"),
                     (d.locales || []).map((l) => ({ x: l.local, y: l.monto })), "$", false),
      chat: t("alertasneg.ac_local_propio"),
      cta: t("alertasneg.ver_inventario"), ir: () => onNavegar?.("inventario", "margenes") }),
    solicitud_pendiente: (d) => ({ icon: FileText, titulo: t("alertasneg.solicitud_t", { n: num(d.n) }),
      detalle: t("alertasneg.solicitud_d", { nombre: d.primera?.nombre, modulo: d.primera?.label }),
      cifraTexto: num(d.n),
      fuentes: [t("alertasneg.f_equipo")],
      porque: [t("alertasneg.q_solicitud", { nombre: d.primera?.nombre, modulo: d.primera?.label })],
      chat: t("alertasneg.ac_solicitud"),
      cta: t("alertasneg.ver_equipo"), ir: () => onNavegar?.("equipo", "solicitudes") }),
  };
}

// Cada señal cae en UN grupo de urgencia (curaduría P32·2, no recorte).
export const GRUPO_DE = {
  quiebre: "hoy", morosos: "hoy", moroso_atraso: "hoy", dep_vencidos: "hoy", pago_vencido: "hoy",
  venc_riesgo: "hoy",
  dep_porvencer: "semana", pago_semana: "semana", cheques: "semana", dep_discrep: "semana",
  costo_viejo: "cuenta", solicitud_pendiente: "cuenta", pico: "cuenta", caja_inusual: "cuenta",
  local_propio: "cuenta",
};

// Las alertas VIVAS ya presentadas (id, tono, icon, titulo, detalle, monto/cifra,
// fuentes, porque, chat, cta, ir). `senales` = salida de cargarSenales().
export function construirAlertas(senales, t, onNavegar) {
  if (!senales) return [];
  const P = presentacionAlertas(t, onNavegar);
  return alertasVivas(senales)
    .filter((s) => P[s.id])
    .map((s) => ({ id: s.id, tono: s.tono, grupo: GRUPO_DE[s.id] || "cuenta", ...P[s.id](s.datos) }));
}

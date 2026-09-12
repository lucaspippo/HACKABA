import { useEffect, useMemo, useRef, useState } from "react";
import {
  ReactFlow, ReactFlowProvider, Handle, Position, useReactFlow,
  useNodesState, useEdgesState, MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  TrendingUp, Boxes, Warehouse, Truck, Users, Landmark, Banknote, Globe,
  ZoomIn, ZoomOut, Maximize, X, ArrowRight, Bell, Sparkles, GitMerge, Lightbulb,
  ChevronRight, Plus, Minus, Shield, Info, GraduationCap, BookOpen, ChevronDown, Check,
  Brain, FileText, Expand, Waypoints, Store,
} from "lucide-react";
import AngelaMark from "../../components/AngelaMark";
import { CuerpoConsulta } from "../../components/Widget";
import ErrorBoundary from "../../components/ErrorBoundary";
import { api } from "../../lib/api";
import { cargarSenales, alertasVivas, contarAlertas } from "../../lib/centroAlertas";
import { armarDecisiones } from "../../lib/decisiones";
import { GRAFICO } from "../../lib/paleta";
import { useIsDesktop } from "../../lib/useViewport";
import { useSession } from "../../lib/auth";
import { pesoCorto, num } from "../../lib/format";
import { useT, useLang, tRol, tCat } from "../../lib/i18n";

// P28 → P29·C — "El mapa que produce": de diagrama a CEREBRO. El mapa no vale
// por mostrar conexiones: vale porque del cruce nacen conclusiones. Reglas:
//   · cada dato sale de la MISMA fuente cacheada que su sección (cero números
//     nuevos; el mapa compone, no calcula);
//   · cada hallazgo activo tiene su CAMINO (la secuencia de nodos que lo
//     produjo) y se ilumina en secuencia al tocarlo — el cerebro pensando;
//   · los nodos devuelven CONCLUSIONES con número, jamás definiciones;
//   · expansión en profundidad: UNA rama a la vez, breadcrumb, y solo los
//     niveles que el dataset sostiene (sin datos no hay nodo).

// --- catálogo de dominios --------------------------------------------------------
const DOMINIOS = {
  ventas: { lk: "mapa.d_ventas", icon: TrendingUp, seccion: "evolucion",
            prompt: "contame cómo vienen mis ventas contra el año pasado" },
  inventario: { lk: "mapa.d_inventario", icon: Boxes, seccion: "inventario",
                prompt: "contame el estado de mi inventario: plata parada y riesgos" },
  deposito: { lk: "mapa.d_deposito", icon: Warehouse, seccion: "deposito",
              prompt: "contame qué pasa en el depósito: vencimientos y diferencias" },
  proveedores: { lk: "mapa.d_proveedores", icon: Truck, seccion: "finanzas",
                 prompt: "contame de mis proveedores: qué debo y qué conviene adelantar" },
  clientes: { lk: "mapa.d_clientes", icon: Users, seccion: "cuentas",
              prompt: "contame de mis clientes: quién debe y quién se está enfriando" },
  caja: { lk: "mapa.d_caja", icon: Banknote, seccion: "caja",
          prompt: "contame cómo viene la caja de hoy y la semana" },
  equipo: { lk: "mapa.d_equipo", icon: Landmark, seccion: "equipo",
            prompt: "contame qué está haciendo mi equipo y qué espera mi decisión" },
  contexto: { lk: "mapa.d_contexto", icon: Globe, seccion: "evolucion",
              prompt: "contame cómo pega la inflación y el dólar en mi negocio" },
};

// P40·3 — LOS CORTES de cada fuente: qué tipos de dato contiene. Es el mapa
// completo — el nivel que faltaba entre "la fuente" y "las entidades".
//
// Son ESTÁTICOS a propósito: un corte no trae datos, dice qué hay y a dónde ir.
// Por eso las 8 fuentes se pueden desplegar juntas sin trabar nada (la carga
// pesada sigue siendo bajo demanda: recién al tocar un corte se abre la vista
// que sí consulta). El `a` es una sección REAL del producto y el `hl` su
// subtab/highlight: ningún corte lleva a un callejón sin salida.
const CORTES = {
  ventas: [
    { id: "v_local", lk: "mapa.corte_v_local", a: "caja" },
    { id: "v_rubro", lk: "mapa.corte_v_rubro", a: "evolucion" },
    { id: "v_canal", lk: "mapa.corte_v_canal", a: "oportunidades" },
    { id: "v_cliente", lk: "mapa.corte_v_cliente", a: "cuentas" },
    { id: "v_evol", lk: "mapa.corte_v_evol", a: "evolucion" },
  ],
  inventario: [
    { id: "i_stock", lk: "mapa.corte_i_stock", a: "inventario" },
    { id: "i_rot", lk: "mapa.corte_i_rot", a: "inventario" },
    { id: "i_quiebres", lk: "mapa.corte_i_quiebres", a: "oportunidades" },
    { id: "i_vto", lk: "mapa.corte_i_vto", a: "deposito" },
    { id: "i_parada", lk: "mapa.corte_i_parada", a: "inventario" },
    { id: "i_pesables", lk: "mapa.corte_i_pesables", a: "inventario", hl: "balanzas" },
  ],
  clientes: [
    { id: "c_cc", lk: "mapa.corte_c_cc", a: "cuentas" },
    { id: "c_morosos", lk: "mapa.corte_c_morosos", a: "cuentas" },
    { id: "c_conc", lk: "mapa.corte_c_conc", a: "oportunidades" },
    { id: "c_scoring", lk: "mapa.corte_c_scoring", a: "cuentas" },
  ],
  proveedores: [
    { id: "p_oc", lk: "mapa.corte_p_oc", a: "documentos" },
    { id: "p_repo", lk: "mapa.corte_p_repo", a: "oportunidades" },
    { id: "p_ofertas", lk: "mapa.corte_p_ofertas", a: "oportunidades" },
    { id: "p_costos", lk: "mapa.corte_p_costos", a: "finanzas" },
  ],
  caja: [
    { id: "k_cierres", lk: "mapa.corte_k_cierres", a: "caja" },
    { id: "k_flujo", lk: "mapa.corte_k_flujo", a: "finanzas" },
    { id: "k_margenes", lk: "mapa.corte_k_margenes", a: "inventario", hl: "margenes" },
  ],
  deposito: [
    { id: "d_ubic", lk: "mapa.corte_d_ubic", a: "deposito" },
    { id: "d_lotes", lk: "mapa.corte_d_lotes", a: "deposito" },
    { id: "d_remitos", lk: "mapa.corte_d_remitos", a: "cargar" },
  ],
  equipo: [
    { id: "e_hizo", lk: "mapa.corte_e_hizo", a: "equipo", hl: "actividad" },
    { id: "e_piso", lk: "mapa.corte_e_piso", a: "oportunidades" },
    { id: "e_act", lk: "mapa.corte_e_act", a: "equipo" },
  ],
  contexto: [
    { id: "x_ipc", lk: "mapa.corte_x_ipc", a: "evolucion" },
    { id: "x_dolar", lk: "mapa.corte_x_dolar", a: "evolucion" },
  ],
};

const ALERTA_DOMINIO = {
  quiebre: "inventario", costo_viejo: "inventario",
  morosos: "clientes", moroso_atraso: "clientes",
  pago_vencido: "proveedores", pago_semana: "proveedores",
  cheques: "caja", caja_inusual: "caja",
  dep_vencidos: "deposito", dep_porvencer: "deposito", dep_discrep: "deposito",
  pico: "ventas", solicitud_pendiente: "equipo",
};
const OPORTUNIDAD_DOMINIO = {
  cobrar_morosos: "clientes", cliente_frio: "clientes", concentracion: "clientes",
  despertar_dormido: "inventario", quiebre_inminente: "inventario", margen_bajo: "inventario",
  ventana_compra: "proveedores", estrella_caida: "ventas", pre_pico: "ventas",
  // P38·D — la oferta que hay que medir contra la rotación nace en el proveedor
  sobrecompra: "proveedores",
};

// P29·C1 — EL CAMINO de cada hallazgo: la secuencia de nodos que lo produjo.
// Conocimiento del cruce (determinista), no un dato inventado: es literalmente
// qué fuentes se cruzaron, en el orden del razonamiento.
const CAMINOS = {
  ventana_compra: ["proveedores", "contexto", "inventario"],
  cliente_frio: ["clientes", "ventas"],
  quiebre_inminente: ["inventario", "ventas"],
  estrella_caida: ["ventas", "contexto"],
  pre_pico: ["ventas", "inventario"],
  concentracion: ["clientes", "ventas"],
  cobrar_morosos: ["clientes", "caja"],
  despertar_dormido: ["inventario", "ventas"],
  margen_bajo: ["proveedores", "inventario"],
  // oferta del proveedor × rotación real × vencimiento del lote (depósito)
  sobrecompra: ["proveedores", "ventas", "deposito"],
  a_morosos: ["clientes", "caja"],
  a_moroso_atraso: ["clientes", "caja"],
  a_pago_vencido: ["proveedores", "caja"],
  a_dep_vencidos: ["deposito", "inventario"],
  a_quiebre: ["inventario", "ventas"],
  x_capital_skus: ["inventario", "caja"],
  x_proyeccion_moroso: ["clientes", "caja"],
};

const POS = {
  centro: { x: -70, y: -74 },
  // S1 — el cerebro, en su propio lugar. P41·1.2 — se mudó de (-78,400): ahí lo
  // pisaba el abanico de sub-nodos de Inventario (radio 205 desde y≈315). Bajarlo
  // en el mismo eje resolvía el choque pero estiraba el grafo y el fitView lo
  // dejaba fuera de cuadro. Va al hueco angular libre entre Equipo (~47°) y Caja
  // (~6°), donde no llega el abanico de ninguna fuente y el encuadre no cambia.
  memory: { x: 500, y: 430 },
  proveedores: { x: -515, y: -65 },
  contexto: { x: -420, y: -330 },
  ventas: { x: -62, y: -350 },
  clientes: { x: 300, y: -280 },
  caja: { x: 395, y: -20 },
  equipo: { x: 195, y: 215 },
  inventario: { x: -105, y: 250 },
  deposito: { x: -405, y: 180 },
};

const RELACIONES = [
  { s: "proveedores", t: "deposito", tipo: "producto" },
  { s: "deposito", t: "inventario", tipo: "producto" },
  { s: "inventario", t: "ventas", tipo: "producto" },
  { s: "ventas", t: "clientes", tipo: "plata" },
  { s: "clientes", t: "caja", tipo: "plata" },
  { s: "caja", t: "proveedores", tipo: "plata" },
  { s: "contexto", t: "inventario", tipo: "senal" },
  { s: "contexto", t: "ventas", tipo: "senal" },
  { s: "equipo", t: "deposito", tipo: "senal" },
  { s: "equipo", t: "ventas", tipo: "senal" },
];
const COLOR_RELACION = { producto: GRAFICO.hielo, plata: GRAFICO.salvia, senal: "#a39e96" };
const AZUL_IA = "#2a5cdf"; // el camino del cerebro pensando: EXCLUSIVO de Ángela/IA
// El conocimiento del dueño ("lo que Aldo me enseñó") tiene identidad propia:
// ocre cálido + birrete, distinto del azul-IA (dato) y del violeta (hallazgo).
const K_COLOR = "#a86b1e";

const ANILLO = { rojo: "border-rojo", oro: "border-oro", verde: "border-salvia/70" };
const PULSO_COLOR = { rojo: "rgba(210,55,43,.5)", oro: "rgba(222,124,26,.5)" };

// --- carga: los MISMOS endpoints cacheados de las secciones ----------------------
// P31·4 — re-fetch cuando cambia el idioma CONFIRMADO por el servidor: los
// títulos de las cards y las conclusiones vienen del backend (lang del perfil).
// Al togglear EN/ES, LangSwitch persiste y refresca la sesión → cambia
// `langKey` → el mapa vuelve a pedir todo en el idioma nuevo (sin desfasajes).
// P32·1 — cache de sesión (por idioma): al VOLVER al mapa se ve al instante,
// sin skeleton; se refresca en background.
let _cacheMapa = { lang: null, datos: null };
function useMapaDatos(langKey) {
  const [d, setD] = useState(_cacheMapa.lang === langKey ? _cacheMapa.datos : null);
  // El idioma VIGENTE en un ref: aplicamos el resultado del fetch solo si sigue
  // siendo el idioma actual. Antes se usaba un flag `vivo` de cleanup, pero en
  // dev (StrictMode doble-invoca el efecto) y durante el settle inicial es→en,
  // ese flag dejaba el setD FINAL en false y el mapa quedaba clavado en
  // "Cruzando tus fuentes…". Con el ref, el último idioma siempre gana y siempre
  // pinta — sin carreras. (P-E3·fix)
  const langVigente = useRef(langKey);
  langVigente.current = langKey;
  useEffect(() => {
    const miLang = langKey;
    (async () => {
      const senales = await cargarSenales().catch(() => null);
      const [ops, calidad, macro, ini, equipoAct, anomalias, conocimiento] = await Promise.all([
        api.oportunidades().catch(() => null),
        api.calidad().catch(() => null),
        api.macro().catch(() => null),
        api.inicio().catch(() => null),
        api.equipoActividad().catch(() => null),
        api.anomalias().catch(() => null),
        api.conocimiento().catch(() => null),
      ]);
      if (langVigente.current !== miLang) return;  // llegó tarde: otro idioma ya manda
      const datos = { senales: senales || {}, ops, calidad, macro, ini, equipoAct, anomalias, conocimiento };
      _cacheMapa = { lang: miLang, datos };
      setD(datos);
    })();
  }, [langKey]);
  return d;
}

// --- el modelo: dato clave + semáforo + CONCLUSIONES + HALLAZGOS por dominio -----
function armarModelo(d, t) {
  const s = d.senales;
  const vivas = s ? alertasVivas(s) : [];
  const evo = s?.evolucion;
  const caidas = evo?.hay_datos ? (evo.alertas || []) : [];
  const inter = evo?.interanual?.variacion_real_pct;
  const inv = s?.inventario?.resumen;
  const topInmov = s?.inventario?.top_inmovilizado || [];
  const dep = s?.deposito?.resumen;
  const pag = s?.pagos?.resumen;
  const proy = s?.pagos?.proyeccion;
  const cue = s?.cuentas;
  const caja = s?.caja;
  const sols = s?.solicitudes?.solicitudes || [];
  const ipc = d.macro?.inflacion;
  const dolar = d.macro?.dolar;
  const cards = d.ops?.cards || [];
  const porCard = Object.fromEntries(cards.map((c) => [c.id, c]));
  const decisiones = d.ini ? armarDecisiones(d.ini, t) : [];
  const act = d.ini?.actividad;
  const personas = d.equipoAct?.actividad || [];
  const fmtPct = (v) => (v == null ? "—" : `${v > 0 ? "+" : ""}${v}%`);
  const dato = (viva) => vivas.find((x) => x.id === viva)?.datos;

  // ---- HALLAZGOS (P29·C1/3.b): oportunidades + alertas serias + cruces extra ----
  // P30·A1 — cada hallazgo lleva su NATURALEZA (del backend para las cards):
  // recuperable (homogéneo, sumable) · accionable (tiene $ pero otra magnitud) ·
  // riesgo (exposición, jamás en una suma de plata). Solo lo recuperable se suma.
  const hallazgos = [];
  for (const c of cards) {
    hallazgos.push({
      id: c.id, tipo: c.naturaleza === "riesgo" ? "riesgo" : "oportunidad",
      titulo: c.titulo, monto: c.monto, montoLabel: c.monto_label || null,
      naturaleza: c.naturaleza || "accionable",
      camino: CAMINOS[c.id] || [OPORTUNIDAD_DOMINIO[c.id]].filter(Boolean),
      fuentes: c.fuentes || [], porque: c.drill?.porque || [],
      supuestos: c.drill?.supuestos || [], grafico: c.drill?.grafico || null,
      chat: c.accion_chat, seccion: "oportunidades", dominio: OPORTUNIDAD_DOMINIO[c.id],
      conocimiento: c.conocimiento_aplicado || [], chipConocimiento: c.chip_conocimiento || null,
    });
  }
  const mkAlerta = (id, viva, titulo, monto, cifraTexto, porque, fuentes, seccion, chat) =>
    hallazgos.push({ id, tipo: "alerta", titulo, monto, cifraTexto, naturaleza: "accionable",
      camino: CAMINOS[id] || [], porque, supuestos: [], fuentes, chat,
      seccion, dominio: CAMINOS[id]?.[0] });
  // P30·C1 — "Cobrar a los morosos" (card) y "Clientes que no pagaron" (alerta
  // a_morosos) eran EL MISMO hallazgo ($85,7M) con dos nombres → se cae la
  // alerta, queda la card (trae drill + gráfico). El desvío histórico
  // (moroso_atraso, Doña Elsa) SÍ es distinto y se mantiene.
  const da = dato("moroso_atraso");
  if (da) mkAlerta("a_moroso_atraso", "moroso_atraso",
    t("alertasneg.moroso_atraso_t", { nombre: da.nombre }), da.saldo, null,
    [t("alertasneg.q_moroso_atraso_1", { nombre: da.nombre, dias: num(da.dias_sin_pagar), prom: num(da.promedio_pago_dias) }),
     t("alertasneg.q_moroso_atraso_2", { atraso: num(da.atraso_vs_promedio) })],
    [t("alertasneg.f_cuentas"), t("alertasneg.f_hist_pagos")], "alertas",
    t("alertasneg.ac_moroso_atraso", { nombre: da.nombre }));
  const dp = dato("pago_vencido");
  if (dp) mkAlerta("a_pago_vencido", "pago_vencido", t("alertasneg.pago_vencido_t"),
    dp.vencidos_total, null,
    [t("alertasneg.q_pago_vencido", { n: num(dp.pagos_vencidos) })],
    [t("alertasneg.f_finanzas")], "alertas", t("alertasneg.ac_pago_vencido"));
  const dv = dato("dep_vencidos");
  if (dv) mkAlerta("a_dep_vencidos", "dep_vencidos", t("alertasneg.dep_vencidos_t"),
    null, num(dv.vencidos),
    [t("alertasneg.q_dep_vencidos", { n: num(dv.vencidos) })],
    [t("alertasneg.f_deposito")], "alertas", t("alertasneg.ac_dep_vencidos"));

  // Cruces P29 (3.b): composiciones aritméticas de fuentes reales ya cargadas.
  const sumaTop10 = topInmov.reduce((a, x) => a + (x.inmovilizado || 0), 0);
  if (inv?.inmovilizado_total && sumaTop10 > 0) {
    const pct10 = Math.round((sumaTop10 / inv.inmovilizado_total) * 100);
    hallazgos.push({
      id: "x_capital_skus", tipo: "cruce", naturaleza: "accionable",
      titulo: t("mapa.h_capital_t", { pct: pct10 }), monto: sumaTop10,
      montoLabel: t("mapa.lbl_inmovilizado"),
      camino: CAMINOS.x_capital_skus,
      fuentes: [t("alertasneg.f_stock"), t("alertasneg.f_costos")],
      porque: [t("mapa.h_capital_q", { pct: pct10, monto: pesoCorto(sumaTop10),
                                       total: pesoCorto(inv.inmovilizado_total) })],
      supuestos: [], seccion: "inventario", dominio: "inventario",
      chat: "mostrame los 10 productos con más plata inmovilizada",
    });
  }
  const v30 = proy?.disponible && (proy.ventanas || []).find((v) => v.dias === 30);
  const peorMoroso = (cue?.clientes || []).filter((c) => c.en_mora)
    .sort((a, b) => b.saldo - a.saldo)[0];
  if (v30 && peorMoroso) {
    const sinPeor = v30.neto - peorMoroso.saldo;
    hallazgos.push({
      id: "x_proyeccion_moroso", tipo: "cruce", naturaleza: "accionable",
      titulo: t("mapa.h_proy_t", { nombre: peorMoroso.nombre }), monto: peorMoroso.saldo,
      montoLabel: t("mapa.lbl_saldo_moroso"),
      camino: CAMINOS.x_proyeccion_moroso,
      fuentes: [t("alertasneg.f_cuentas"), t("alertasneg.f_finanzas")],
      porque: [t("mapa.h_proy_q1", { neto: pesoCorto(v30.neto), cobros: pesoCorto(v30.cobros), pagos: pesoCorto(v30.pagos) }),
               t("mapa.h_proy_q2", { nombre: peorMoroso.nombre, saldo: pesoCorto(peorMoroso.saldo), sin: pesoCorto(sinPeor) })],
      supuestos: proy.supuestos ? [proy.supuestos] : [], seccion: "finanzas",
      dominio: "clientes", chat: `qué pasa con mi caja si ${peorMoroso.nombre} no paga`,
    });
  }
  hallazgos.sort((a, b) => (b.monto || 0) - (a.monto || 0));
  const nacenEn = {};
  for (const h of hallazgos) {
    const n = h.camino?.[0];
    if (n) nacenEn[n] = (nacenEn[n] || 0) + 1;
  }

  // ---- semáforos (mismas condiciones que el badge de Alertas) -------------------
  const tonoDe = (dom) => {
    const propias = vivas.filter((v) => ALERTA_DOMINIO[v.id] === dom);
    if (propias.some((v) => v.tono === "rojo") || (dom === "ventas" && caidas.length)) return "rojo";
    if (propias.some((v) => v.tono === "oro")) return "oro";
    return "verde";
  };
  const alertaDe = (dom) => {
    const propias = vivas.filter((x) => ALERTA_DOMINIO[x.id] === dom);
    if (dom === "ventas" && caidas.length) return { tono: "rojo", n: caidas.length + propias.length, seccion: "evolucion" };
    if (!propias.length) return null;
    const tono = propias.some((x) => x.tono === "rojo") ? "rojo"
      : propias.some((x) => x.tono === "oro") ? "oro" : "azul";
    return { tono, n: propias.length, seccion: "alertas" };
  };

  // ---- el dato del nodo ----------------------------------------------------------
  const datoNodo = {
    ventas: inter != null ? t("mapa.n_interanual", { pct: fmtPct(inter) }) : t("mapa.n_sin_dato"),
    inventario: inv ? pesoCorto(inv.inmovilizado_total) : "—",
    deposito: dep ? t("mapa.n_por_vencer", { n: num(dep.por_vencer || 0) }) : "—",
    proveedores: pag ? (pag.vencidos_total > 0
      ? t("mapa.n_vencido", { monto: pesoCorto(pag.vencidos_total) })
      : t("mapa.n_semana", { monto: pesoCorto(pag.por_pagar_semana || 0) })) : "—",
    clientes: cue?.alertas ? t("mapa.n_mora", { monto: pesoCorto(cue.alertas.impacto_pesos || 0) }) : "—",
    caja: caja?.abierta ? t("mapa.n_hoy", { monto: pesoCorto(caja.totales?.total || 0) }) : t("mapa.n_caja_cerrada"),
    equipo: sols.length ? t("mapa.n_solicitudes", { n: num(sols.length) }) : t("mapa.n_al_dia"),
    contexto: ipc?.disponible ? t("mapa.n_ipc", { pct: `${ipc.valor}` }) : t("mapa.n_sin_dato"),
  };

  // ---- P29·C2: CONCLUSIONES con número, jamás definiciones -----------------------
  const cardDatos = (id) => porCard[id]?.datos;
  const confiable = (cue?.clientes || []).filter((c) => c.score === "confiable" && c.promedio_pago_dias)
    .sort((a, b) => a.promedio_pago_dias - b.promedio_pago_dias)[0];
  const promCaja = (caja?.historial || []).map((h) => h.total).filter((x) => x > 0);
  const cajaProm = promCaja.length ? promCaja.reduce((a, b) => a + b, 0) / promCaja.length : null;
  const masActivo = [...personas].sort((a, b) => (b.correcciones || 0) - (a.correcciones || 0))[0];
  const anomAnulados = (d.anomalias?.anomalias || []).find((a) => (a.tipo || "").includes("anulado"));
  const conclusiones = {
    ventas: [
      inter != null && t("mapa.c_v_interanual", { pct: fmtPct(inter), base: evo?.mes_base || "" }),
      cardDatos("estrella_caida") && t("mapa.c_v_estrella", {
        producto: cardDatos("estrella_caida").producto, pos: cardDatos("estrella_caida").rank_facturacion,
        n: cardDatos("estrella_caida").racha_meses }),
      cardDatos("pre_pico") && t("mapa.c_v_pico", {
        idx: cardDatos("pre_pico").indice, cat: cardDatos("pre_pico").categoria,
        dias: cardDatos("pre_pico").cobertura_pico_dias }),
    ].filter(Boolean),
    inventario: [
      inv && sumaTop10 > 0 && t("mapa.c_i_capital", {
        pct: Math.round((sumaTop10 / inv.inmovilizado_total) * 100), monto: pesoCorto(sumaTop10) }),
      porCard.despertar_dormido && t("mapa.c_i_dormido", { monto: pesoCorto(porCard.despertar_dormido.monto) }),
      cardDatos("quiebre_inminente") && t("mapa.c_i_quiebre", {
        producto: cardDatos("quiebre_inminente").producto, dias: cardDatos("quiebre_inminente").dias_cobertura,
        pos: cardDatos("quiebre_inminente").rank_facturacion }),
      anomAnulados && t("mapa.c_i_anulados", { n: num(anomAnulados.items) }),
    ].filter(Boolean).slice(0, 3),
    deposito: [
      dep?.vencidos > 0 && t("mapa.c_d_vencidos", { n: num(dep.vencidos) }),
      dep?.por_vencer > 0 && t("mapa.c_d_porvencer", { n: num(dep.por_vencer) }),
      dep?.discrepancias > 0 && t("mapa.c_d_discrep", { n: num(dep.discrepancias) }),
    ].filter(Boolean),
    proveedores: [
      pag && t("mapa.c_p_debes", { total: pesoCorto(pag.por_pagar_total || 0), semana: pesoCorto(pag.por_pagar_semana || 0) }),
      cardDatos("ventana_compra") && t("mapa.c_p_ventana", {
        ahorro: pesoCorto(porCard.ventana_compra.monto), compra: pesoCorto(cardDatos("ventana_compra").compra) }),
      pag?.vencidos_total > 0 && t("mapa.c_p_vencido", { monto: pesoCorto(pag.vencidos_total) }),
    ].filter(Boolean),
    clientes: [
      cardDatos("concentracion") && t("mapa.c_c_conc", { pct: cardDatos("concentracion").pct_top3 }),
      da && t("mapa.c_c_atraso", { nombre: da.nombre, atraso: num(da.atraso_vs_promedio) }),
      confiable && t("mapa.c_c_confiable", { nombre: confiable.nombre, dias: num(confiable.promedio_pago_dias) }),
    ].filter(Boolean),
    caja: [
      caja?.abierta && cajaProm && t("mapa.c_j_hoy", {
        total: pesoCorto(caja.totales?.total || 0),
        pct: Math.round(((caja.totales?.total || 0) / cajaProm - 1) * 100) }),
      v30 && t("mapa.c_j_proy", { cobros: pesoCorto(v30.cobros), pagos: pesoCorto(v30.pagos), neto: pesoCorto(v30.neto) }),
      pag?.cheques_cartera > 0 && t("mapa.c_j_cheques", { n: num(pag.cheques_cartera), monto: pesoCorto(pag.cheques_total) }),
    ].filter(Boolean),
    equipo: [
      sols.length > 0 && t("mapa.c_e_solicitud", { n: num(sols.length), nombre: sols[0]?.nombre || "" }),
      masActivo?.correcciones > 0 && t("mapa.c_e_correcciones", { nombre: masActivo.nombre, n: num(masActivo.correcciones) }),
      decisiones.length > 0 && t("mapa.c_e_decisiones", { n: num(decisiones.length) }),
    ].filter(Boolean),
    contexto: [
      ipc?.disponible && t("mapa.c_x_ipc", { pct: ipc.valor, fuente: ipc.fuente || "" }),
      dolar?.disponible && t("mapa.c_x_dolar", { valor: num(dolar.valor) }),
      evo?.hay_indice && t("mapa.c_x_deflacta", { mes: evo.mes_base || "" }),
    ].filter(Boolean),
  };

  const issues = d.calidad?.total_issues || 0;
  const totalReg = inv?.total_articulos || 0;
  const pulso = {
    senales: s ? contarAlertas(s) : 0,
    decisiones: decisiones.length,
    // P30·A3 — cuenta lo MISMO que la sección/badge: capturables (sin riesgo)
    oportunidades: cards.filter((c) => c.naturaleza !== "riesgo").length,
    salud: totalReg ? Math.round((1 - issues / totalReg) * 1000) / 10 : null,
    saludFormula: t("mapa.salud_formula", { issues: num(issues), total: num(totalReg) }),
  };
  // P30·A4 — las FUENTES REALES contadas (no un número fijo, no respuestas de
  // API derivadas): las 8 fuentes de datos distintas del negocio. Mismo listado
  // que los chips del pulso: el conteo de la frase y los chips nunca divergen.
  const FUENTES_REALES = [
    { on: !!s?.ventas, lk: "alertasneg.f_ventas" },        // ventas (10 años)
    { on: !!s?.inventario, lk: "alertasneg.f_stock" },     // inventario / stock
    { on: !!s?.cuentas, lk: "alertasneg.f_cuentas" },      // cuentas corrientes
    { on: !!s?.caja, lk: "alertasneg.f_caja" },            // caja diaria
    { on: !!s?.pagos, lk: "mapa.f_finanzas" },             // pagos / cheques
    { on: !!s?.deposito, lk: "mapa.f_deposito" },          // depósito / lotes
    { on: !!porCard.ventana_compra, lk: "mapa.f_lista" },  // lista del proveedor
    { on: !!d.macro, lk: "mapa.f_macro" },                 // IPC + dólar
  ];
  const fuentesActivas = FUENTES_REALES.filter((f) => f.on);
  // P30·A4 — años REALES: la serie de ventas es mensual; su largo/12 es el span
  // verdadero (10), no los años con 12 meses completos que usa estacionalidad (9).
  const mesesSerie = (evo?.serie || []).length;
  const conteos = {
    anios: mesesSerie ? Math.round(mesesSerie / 12)
                      : (s?.analisis?.estacionalidad?.anios_analizados || 0),
    productos: totalReg, clientes: cue?.clientes?.length || 0,
    fuentes: fuentesActivas.length,
  };

  // ---- CONOCIMIENTO ("lo que Aldo me enseñó") por nodo -------------------------
  // Una pieza es PROFUNDA (modifica un hallazgo → link + "aplicada N veces") o de
  // CONTEXTO (Ángela la tiene en cuenta, sin mover un número). "Aplicada hoy" es
  // derivado: la pieza aparece en el conocimiento_aplicado de un hallazgo vivo.
  const kPiezas = d.conocimiento?.piezas || [];
  const aplicadasHoy = new Set();
  const linkPieza = {};
  const _reg = (id, link) => { if (!id) return; aplicadasHoy.add(id); if (link && !linkPieza[id]) linkPieza[id] = link; };
  for (const c of cards) for (const p of (c.conocimiento_aplicado || []))
    _reg(p.id, { seccion: "oportunidades", titulo: c.titulo, hallazgo: c.id });
  for (const p of (proy?.conocimiento_aplicado || []))
    _reg(p.id, { seccion: "finanzas", titulo: t("mapa.k_link_caja") });
  for (const sp of (s?.deposito?.discrepancias_suprimidas || [])) _reg(sp.regla?.id,
    { seccion: "deposito", titulo: t("mapa.k_link_deposito") });
  for (const cl of (cue?.clientes || [])) for (const p of (cl.conocimiento || []))
    _reg(p.id, { seccion: "cuentas", titulo: cl.nombre });
  const conocimientoPorNodo = {};
  for (const p of kPiezas) {
    (conocimientoPorNodo[p.nodo] ||= []).push({
      ...p, profunda: !!p.efecto_profundo,
      aplicadaHoy: aplicadasHoy.has(p.id), link: linkPieza[p.id] || null,
    });
  }
  // más aplicadas primero dentro de cada nodo (para el "por defecto 2-3")
  for (const arr of Object.values(conocimientoPorNodo))
    arr.sort((a, b) => (b.profunda - a.profunda) || (b.veces_aplicada - a.veces_aplicada));
  const conocimiento = {
    porNodo: conocimientoPorNodo, piezas: kPiezas,
    total: kPiezas.length, aplicadasHoy: aplicadasHoy.size,
  };

  // Doña Elsa (k01): el 113% es la ALERTA a_moroso_atraso, que YA tiene camino
  // (clientes→caja) pero no cargaba conocimiento. La enganchamos acá para que la
  // regla ilumine su camino desde el panel Memory, igual que Gaseosa/ventana.
  const _hMoroso = hallazgos.find((h) => h.id === "a_moroso_atraso");
  const _pElsa = Object.values(conocimientoPorNodo).flat().find((p) => p.id === "k01");
  if (_hMoroso && _pElsa) {
    _hMoroso.conocimiento = [_pElsa];
    _pElsa.profunda = true;
    _pElsa.link = { seccion: "alertas", titulo: _hMoroso.titulo, hallazgo: "a_moroso_atraso" };
  }

  const dominios = {};
  for (const id of Object.keys(DOMINIOS)) {
    dominios[id] = {
      id, tono: tonoDe(id), dato: datoNodo[id], conclusiones: conclusiones[id] || [],
      alerta: alertaDe(id), nHallazgos: nacenEn[id] || 0,
      hallazgos: hallazgos.filter((h) => h.camino?.[0] === id || h.dominio === id),
      conocimiento: conocimientoPorNodo[id] || [],
    };
  }
  const hayActividad = (d.ini?.actividad?.feed || []).length > 0;
  const erpSimulado = (s?.inventario?.meta?.fuente || "").includes("DEMO");

  // Tarea 2 · S1 — la MEMORIA del negocio: reglas (las 22 piezas) + documentos
  // que Ángela leyó/cargó + decisiones que aplicó. TODO de fuentes que ya existen
  // (conocimiento + audit trail/feed). Guarda de fecha ≤ 2026-07-07: no se cuelan
  // los eventos basura de pruebas en vivo (reloj real). Un ítem es DECISIÓN solo
  // si tiene antes Y después reales; si no, no entra como decisión.
  const _feedMem = (d.ini?.actividad?.feed || []).filter((f) => (f.cuando || "") <= "2026-07-07T23:59:59");
  const _esDoc = (a) => /^(cargar_|integrar_)/.test(a || "");
  const _conAntesYdespues = (f) => {
    const a = f.detalle?.antes, b = f.detalle?.despues;
    return !!(a && Object.keys(a).length && b && Object.keys(b).length);
  };
  const _docsMem = _feedMem.filter((f) => _esDoc(f.accion));
  const _decisionesMem = _feedMem.filter((f) => !_esDoc(f.accion) && _conAntesYdespues(f));
  // Dominios PROFUNDOS: los que tienen un hallazgo modificado por una pieza (los
  // que "mueven un número"). Son a los que el nodo Memory tira aristas al hover.
  const _domProfundos = [...new Set(
    hallazgos.filter((h) => (h.conocimiento || []).length > 0)
      .map((h) => h.dominio || h.camino?.[0]).filter(Boolean))];
  const memoria = {
    total: conocimiento.total, docs: _docsMem.length, decisiones: _decisionesMem.length,
    dominios: Object.keys(conocimientoPorNodo), dominiosProfundos: _domProfundos,
    conocimiento, docsItems: _docsMem, decisionesItems: _decisionesMem,
  };

  // Sub-niveles con datos locales (los que no necesitan fetch)
  const segmentos = { confiable: [], atencion: [], riesgoso: [] };
  for (const c of cue?.clientes || []) (segmentos[c.score] || segmentos.atencion).push(c);

  return {
    dominios, pulso, conteos, hayActividad, hallazgos, erpSimulado, conocimiento, memoria,
    fuentesActivas, actividad: act, personas, proy,
    clientes: cue?.clientes || [], segmentos,
    proveedoresReales: _proveedoresDe(s?.pagos),
    pagosLists: { por_vencer: s?.pagos?.pagos_por_vencer || [], vencidos: s?.pagos?.pagos_vencidos || [],
                  cheques: s?.pagos?.cheques || [] },
    depositoLists: { vencidos: s?.deposito?.vencidos || [], por_vencer: s?.deposito?.vencimientos || [],
                     discrepancias: s?.deposito?.discrepancias || [] },
    caja, pag, macro: d.macro, evo,
  };
}

function _proveedoresDe(pagos) {
  const filas = [...(pagos?.pagos_por_vencer || []), ...(pagos?.pagos_vencidos || [])];
  const por = {};
  for (const f of filas) {
    if (!f?.proveedor) continue;
    por[f.proveedor] = (por[f.proveedor] || 0) + (f.monto || 0);
  }
  return Object.entries(por).map(([nombre, monto]) => ({ nombre, monto }))
    .sort((a, b) => b.monto - a.monto).slice(0, 6);
}

// --- nodos custom -----------------------------------------------------------------
const HANDLES = ["t", "r", "b", "l"];
const POS_HANDLE = { t: Position.Top, r: Position.Right, b: Position.Bottom, l: Position.Left };
function HandlesOcultos() {
  return HANDLES.map((h) => (
    <span key={h}>
      <Handle id={`s-${h}`} type="source" position={POS_HANDLE[h]} style={{ opacity: 0, pointerEvents: "none" }} />
      <Handle id={`t-${h}`} type="target" position={POS_HANDLE[h]} style={{ opacity: 0, pointerEvents: "none" }} />
    </span>
  ));
}

function NodoCentro({ data }) {
  return (
    <div className={`rf-suave grid h-[148px] w-[140px] place-items-center ${data.apagado ? "rf-apagado" : ""}`}>
      <div className="anillo-respira grid h-[124px] w-[124px] place-items-center rounded-full border border-linea bg-crema sombra-alta">
        <img src="/logos/litoral.png" alt="" className="h-12 w-auto" draggable="false" />
        {/* La presencia de Ángela, cerca del centro (la esfera acompaña) */}
        <span className="esfera-orbita"><AngelaMark size={22} /></span>
      </div>
    </div>
  );
}

function NodoDominio({ data }) {
  const Icon = data.icon;
  const conPulso = (data.tono === "rojo" || data.tono === "oro") && !data.enCamino;
  return (
    <div className={`rf-suave flex w-[124px] flex-col items-center text-center ${data.apagado ? "rf-apagado" : ""}`}>
      <HandlesOcultos />
      <div className="relative">
        <div
          className={`grid h-[76px] w-[76px] place-items-center rounded-full border-[3px] bg-crema sombra-papel transition-transform ${ANILLO[data.tono]} ${data.hover || data.enCamino ? "scale-110 sombra-alta" : ""} ${conPulso ? "nodo-pulso" : ""}`}
          style={{
            ...(conPulso ? { "--pulso-color": PULSO_COLOR[data.tono] } : {}),
            ...(data.enCamino ? { boxShadow: `0 0 0 3px ${AZUL_IA}55, 0 8px 22px rgba(42,92,223,.25)` } : {}),
          }}
        >
          <Icon size={26} className="text-tinta" />
        </div>
        {data.nHallazgos > 0 && (
          <span className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-violeta px-1 text-[0.66rem] font-bold text-crema"
            title={`${data.nHallazgos}`}>
            {data.nHallazgos}
          </span>
        )}
        {data.nConocimiento > 0 && (
          <span className="absolute -left-1 -top-1 flex h-5 min-w-5 items-center gap-0.5 rounded-full px-1 text-[0.66rem] font-bold text-crema sombra-papel"
            style={{ background: K_COLOR }} title={`${data.nConocimiento}`}>
            <GraduationCap size={11} /> {data.nConocimiento}
          </span>
        )}
        {data.bombilla && (
          <span className="absolute -bottom-2 left-1/2 flex -translate-x-1/2 items-center gap-1 whitespace-nowrap rounded-full bg-violeta px-2 py-0.5 text-[0.68rem] font-bold text-crema sombra-alta">
            <Lightbulb size={11} /> {data.bombilla}
          </span>
        )}
        {/* P30·B/P31·3 — botón EXPANDIR explícito y SIEMPRE visible (no hover):
            afordancia clara con acento IA. data-expand lo detecta el handler;
            el doble clic sigue de atajo. Pulso-pista en el primer abrir. */}
        {data.expandible && !data.bombilla && (
          <button data-expand="1"
            className={`absolute -bottom-2.5 left-1/2 grid h-[24px] w-[24px] -translate-x-1/2 place-items-center rounded-full border border-violeta/35 bg-violeta-suave text-violeta sombra-papel transition-transform hover:scale-110 ${data.pista ? "pista-pulso" : ""}`}>
            {data.expandida ? <Minus size={14} data-expand="1" /> : <Plus size={14} data-expand="1" />}
          </button>
        )}
      </div>
      <p className="mt-2 font-display text-[0.86rem] font-bold leading-tight">{data.label}</p>
      <p className="plata text-[0.74rem] leading-tight text-tinta-suave">{data.dato}</p>
    </div>
  );
}

function NodoSub({ data }) {
  // E3·1 — un bucket vacío informativo se muestra ATENUADO, con un check (buena
  // noticia) en vez de un "0" neutro, y la lectura explícita como dato.
  const vacio = data.vacio;
  return (
    <div className={`rf-suave flex w-[110px] flex-col items-center text-center ${data.apagado ? "rf-apagado" : ""}`}
      style={vacio ? { opacity: 0.5 } : undefined}>
      <HandlesOcultos />
      {/* P41·1.4 — un LOCAL PROPIO no es un cliente: cuadrado (no círculo),
          ícono de tienda y trazo punteado. Se distingue sin leer la etiqueta. */}
      <div className={`grid h-[46px] w-[46px] place-items-center border-2 bg-crema sombra-papel ${
        data.esLocalPropio ? "rounded-xl border-dashed border-hielo/70"
        : `rounded-full ${vacio ? "border-dashed border-linea" : (data.anillo || "border-linea")}`}`}>
        {data.esLocalPropio
          ? <Store size={18} className="text-hielo" />
          : vacio && data.vacioBueno
          ? <Check size={18} className="text-salvia" />
          : <span className={`font-display text-[0.72rem] font-bold ${vacio ? "text-tinta-suave" : ""}`}>{data.inicial}</span>}
      </div>
      <p className={`mt-1 text-[0.68rem] font-semibold leading-tight ${vacio ? "text-tinta-suave" : ""}`}>{data.label}</p>
      {data.esLocalPropio && (
        <span className="mt-0.5 rounded-full bg-hielo/12 px-1.5 py-px text-[0.56rem] font-bold uppercase tracking-wide text-hielo">
          {data.badge}
        </span>
      )}
      {data.dato && <p className="plata text-[0.66rem] leading-tight text-tinta-suave">{data.dato}</p>}
    </div>
  );
}

// E3·5 — el nodo de CONOCIMIENTO en el camino: visualmente distinto de las
// fuentes de datos (ocre + birrete, no azul), etiquetado para que se entienda
// sin leyenda que la conclusión = datos + algo que el dueño enseñó.
function NodoConocimiento({ data }) {
  return (
    <div className="rf-suave flex w-[128px] flex-col items-center text-center" style={{ opacity: data.apagado ? 0.25 : 1 }}>
      <HandlesOcultos />
      <div className="grid h-[52px] w-[52px] place-items-center rounded-2xl border-2 sombra-papel"
        style={{ background: "#fbf3e4", borderColor: K_COLOR,
          boxShadow: data.enCamino ? `0 0 0 3px ${K_COLOR}55, 0 8px 22px ${K_COLOR}33` : undefined,
          transform: data.enCamino ? "scale(1.08)" : "none", transition: "transform .2s ease" }}>
        <GraduationCap size={24} style={{ color: K_COLOR }} />
      </div>
      <p className="mt-1 text-[0.66rem] font-bold leading-tight" style={{ color: K_COLOR }}>{data.etiqueta}</p>
      {data.texto && <p className="mt-0.5 max-w-[128px] text-[0.6rem] leading-tight text-tinta-suave line-clamp-2">{data.texto}</p>}
    </div>
  );
}

// Tarea 2 · S1 — el nodo BUSINESS MEMORY: el cerebro del negocio hecho nodo,
// pegado al logo. Ocre (mismo lenguaje del conocimiento), badge con el total.
// Al tocarlo (S2) abre el panel de 4 capas. Alimenta a los dominios (aristas ocre).
function NodoMemory({ data }) {
  return (
    <div className={`rf-suave flex w-[156px] flex-col items-center text-center ${data.apagado ? "rf-apagado" : ""}`}>
      <HandlesOcultos />
      <div className="relative">
        <div className="grid h-[92px] w-[92px] place-items-center rounded-2xl border-2 sombra-alta transition-transform hover:scale-105"
          style={{ background: "#fbf3e4", borderColor: K_COLOR,
            boxShadow: data.enCamino ? `0 0 0 3px ${K_COLOR}55, 0 8px 22px ${K_COLOR}33` : undefined }}>
          <Brain size={40} style={{ color: K_COLOR }} />
        </div>
        {data.total > 0 && (
          <span className="absolute -right-2 -top-2 grid h-7 min-w-[28px] place-items-center rounded-full px-1.5 text-[0.8rem] font-bold text-crema sombra-papel"
            style={{ background: K_COLOR }} title={`${data.total}`}>
            {data.total}
          </span>
        )}
      </div>
      <p className="mt-2 font-display text-[0.9rem] font-bold leading-tight" style={{ color: K_COLOR }}>{data.label}</p>
      <p className="plata text-[0.68rem] leading-tight text-tinta-suave">{data.dato}</p>
    </div>
  );
}

// P40·3 — el nodo de CORTE del mapa completo: dice qué tipo de dato hay en esa
// fuente y lleva ahí. Chato y chico a propósito — no compite con las fuentes ni
// con los sub-nodos (que sí muestran números).
function NodoCorte({ data }) {
  return (
    <div className={`rf-suave w-[126px] ${data.apagado ? "rf-apagado" : ""}`}>
      <HandlesOcultos />
      <div className="rounded-full border border-linea bg-crema px-2.5 py-1.5 text-center sombra-papel transition-colors hover:border-hielo/60">
        <p className="text-[0.66rem] font-semibold leading-tight text-tinta">{data.label}</p>
      </div>
    </div>
  );
}

const NODE_TYPES = { centro: NodoCentro, dominio: NodoDominio, sub: NodoSub, conocimiento: NodoConocimiento, memory: NodoMemory, corte: NodoCorte };

function ladoHacia(a, b) {
  const dx = b.x - a.x, dy = b.y - a.y;
  if (Math.abs(dx) > Math.abs(dy)) return dx > 0 ? "r" : "l";
  return dy > 0 ? "b" : "t";
}

// --- construcción del grafo (UNA rama expandida a la vez, P29·C3) -----------------
function armarGrafo(modelo, rama, nivel2, t, extras = {}, pistaNodo = null, completo = false) {
  // P40·3 — en el mapa completo las fuentes se separan (×1.55) para que los
  // cortes de las 8 entren sin amontonarse. Mismo grafo, más aire: no hay una
  // segunda versión del mapa que después se desincronice.
  const ESC = completo ? 1.55 : 1;
  const P = completo
    ? Object.fromEntries(Object.entries(POS).map(([k, v]) => [k, { x: v.x * ESC, y: v.y * ESC }]))
    : POS;
  const nodes = [{
    id: "centro", type: "centro", position: P.centro, draggable: false,
    selectable: false, data: { apagado: false },
  }];
  for (const [id, def] of Object.entries(DOMINIOS)) {
    const m = modelo.dominios[id];
    nodes.push({
      id, type: "dominio", position: P[id], draggable: false,
      // los 8 dominios se pueden abrir (todos tienen sub-entidades reales)
      data: { icon: def.icon, label: t(def.lk), dato: m.dato, tono: m.tono,
              nHallazgos: m.nHallazgos, nConocimiento: (m.conocimiento || []).length,
              hover: false, apagado: false,
              expandible: true, expandida: rama === id,
              pista: pistaNodo === id && !rama },
    });
  }
  const edges = RELACIONES.map((r, i) => ({
    id: `e${i}`, source: r.s, target: r.t, tipo: r.tipo,
    sourceHandle: `s-${ladoHacia(P[r.s], P[r.t])}`,
    targetHandle: `t-${ladoHacia(P[r.t], P[r.s])}`,
    animated: modelo.hayActividad && r.tipo === "producto",
    markerEnd: { type: MarkerType.ArrowClosed, color: COLOR_RELACION[r.tipo], width: 16, height: 16 },
    style: { stroke: COLOR_RELACION[r.tipo], strokeWidth: 1.6, opacity: 0.55,
             transition: "opacity .18s ease" },
  }));

  // Tarea 2 · S1 — el nodo MEMORY y sus aristas ocre a los dominios que nutre.
  // Aditivo: no toca centro, dominios ni relaciones. Trazo ocre punteado, sutil
  // (distinto del azul-dato y del gris-relación): "el cerebro alimenta a todos".
  if (modelo.memoria) {
    nodes.push({
      id: "memory", type: "memory", position: P.memory, draggable: false,
      data: { label: t("mapa.memoria_label"),
              dato: t("mapa.memoria_dato", { reglas: modelo.memoria.total,
                     docs: modelo.memoria.docs, dec: modelo.memoria.decisiones }),
              total: modelo.memoria.total, apagado: false },
    });
    // Solo a los dominios PROFUNDOS (los que tienen un hallazgo modificado). Las
    // aristas nacen OCULTAS (opacity 0): el efecto de hover/selección las enciende
    // (ver Lienzo). En reposo el nodo va limpio.
    for (const dom of (modelo.memoria.dominiosProfundos || [])) {
      if (!P[dom]) continue;
      edges.push({
        id: `mem-${dom}`, source: "memory", target: dom, tipo: "memoria",
        sourceHandle: `s-${ladoHacia(P.memory, P[dom])}`,
        targetHandle: `t-${ladoHacia(P[dom], P.memory)}`,
        style: { stroke: K_COLOR, strokeWidth: 1, opacity: 0,
                 strokeDasharray: "5 4", transition: "opacity .25s ease" },
      });
    }
  }

  const centroDe = (id) => ({ x: P[id].x + 62, y: P[id].y + 65 });
  const armarSubs = (padre, subs, radio = 205) => {
    const pc = centroDe(padre);
    const base = Math.atan2(pc.y, pc.x);
    const n = subs.length;
    subs.forEach((sb, i) => {
      const ang = base + (n === 1 ? 0 : (-1.05 + (2.1 * i) / (n - 1)));
      const x = pc.x + Math.cos(ang) * radio - 55;
      const y = pc.y + Math.sin(ang) * radio - 40;
      const sid = sb.sid || `${padre}:${i}`;
      nodes.push({ id: sid, type: "sub", position: { x, y }, draggable: false,
                   data: { ...sb, padre, apagado: false } });
      edges.push({
        id: `se-${sid}`, source: sb.origen || padre, target: sid, tipo: "sub",
        sourceHandle: `s-${ladoHacia(P[padre] || { x, y }, { x, y })}`,
        targetHandle: `t-${ladoHacia({ x, y }, P[padre] || { x, y })}`,
        style: { stroke: "#c9c5be", strokeWidth: 1.1, opacity: 0.5 },
      });
      sb._pos = { x, y };
    });
  };

  // P40·3 — MAPA COMPLETO: cada fuente abre sus CORTES (qué tipos de dato
  // contiene) en abanico hacia afuera del centro. Sin fetch: son etiquetas con
  // destino, así que las 8 pueden estar desplegadas a la vez sin costo.
  if (completo) {
    for (const [dom, cortes] of Object.entries(CORTES)) {
      if (!P[dom] || !cortes.length) continue;
      const pc = centroDe(dom);
      const base = Math.atan2(pc.y, pc.x);   // hacia afuera del centro
      const n = cortes.length;
      const abanico = Math.min(1.9, 0.42 * (n - 1));
      cortes.forEach((c, i) => {
        const ang = base + (n === 1 ? 0 : -abanico / 2 + (abanico * i) / (n - 1));
        const x = pc.x + Math.cos(ang) * 232 - 63;
        const y = pc.y + Math.sin(ang) * 232 - 14;
        const cid = `corte:${c.id}`;
        nodes.push({ id: cid, type: "corte", position: { x, y }, draggable: false,
                     data: { label: t(c.lk), corte: c, padre: dom, apagado: false } });
        edges.push({
          id: `ce-${cid}`, source: dom, target: cid, tipo: "corte",
          sourceHandle: `s-${ladoHacia(P[dom], { x, y })}`,
          targetHandle: `t-${ladoHacia({ x, y }, P[dom])}`,
          style: { stroke: "#c9c5be", strokeWidth: 1, opacity: 0.45 },
        });
      });
    }
  }

  if (rama) {
    const subs = subsDe(rama, modelo, t, extras);
    armarSubs(rama, subs);
    // Nivel 2: los hijos del sub elegido, alrededor DE ese sub.
    if (nivel2?.sub && nivel2.items?.length) {
      const padreSub = subs.find((sb) => (sb.sid || `${rama}:${subs.indexOf(sb)}`) === nivel2.sub);
      if (padreSub?._pos) {
        const pc = { x: padreSub._pos.x + 55, y: padreSub._pos.y + 40 };
        const base = Math.atan2(pc.y, pc.x);
        nivel2.items.forEach((sb, i) => {
          const n = nivel2.items.length;
          const ang = base + (n === 1 ? 0 : (-0.8 + (1.6 * i) / (n - 1)));
          const x = pc.x + Math.cos(ang) * 165 - 55;
          const y = pc.y + Math.sin(ang) * 165 - 40;
          const sid = `${nivel2.sub}>${i}`;
          nodes.push({ id: sid, type: "sub", position: { x, y }, draggable: false,
                       data: { ...sb, padre: nivel2.sub, apagado: false } });
          edges.push({ id: `se2-${sid}`, source: nivel2.sub, target: sid, tipo: "sub",
            style: { stroke: "#c9c5be", strokeWidth: 1, opacity: 0.45 } });
        });
      }
    }
  }
  return { nodes, edges };
}

// P41·1.3 — mientras el fetch de una rama viaja, el sub-nodo dice "cargando" en
// vez de dejar la rama abierta y VACÍA (se veía como una rama suelta/rota).
function subCargando(sid, t) {
  return { sid, label: t("mapa.s_cargando"), inicial: "", dato: "",
           anillo: "border-linea", kind: "cargando", vacio: true, cargando: true };
}

// Los sub-nodos de NIVEL 1 de cada dominio — solo entidades REALES del dataset.
function subsDe(dominio, modelo, t, extras = {}) {
  const anilloScore = (s) => (s === "riesgoso" ? "border-rojo" : s === "atencion" ? "border-oro" : "border-salvia/70");
  switch (dominio) {
    case "clientes": {
      const seg = modelo.segmentos;
      // E3·1 — un segmento vacío es informativo (0 en riesgo = buena noticia): se
      // muestra atenuado con la lectura explícita, nunca un círculo con "0".
      const segSub = (key, label, anillo, bueno) => {
        const arr = seg[key] || [];
        return { sid: `clientes:${key}`, label, inicial: num(arr.length),
          dato: arr.length ? pesoCorto(arr.reduce((a, c) => a + c.saldo, 0))
                           : t(bueno ? "mapa.s_vacio_bueno" : "mapa.s_vacio"),
          anillo: arr.length ? anillo : "border-linea", kind: "segmento", seg: key,
          vacio: arr.length === 0, vacioBueno: bueno };
      };
      // Los 3 segmentos son CLIENTES externos; los locales propios van aparte,
      // marcados como lo que son (P41·1.4).
      const propios = (extras.locales || []).map((l, i) => ({
        sid: `clientes:local:${i}`, label: l.local, inicial: "", dato: pesoCorto(l.monto),
        anillo: "border-hielo/60", kind: "local_propio", nombre: l.local,
        esLocalPropio: true, badge: t("mapa.s_local_propio"),
      }));
      return [
        segSub("confiable", t("mapa.s_confiables"), "border-salvia/70", false),
        segSub("atencion", t("mapa.s_atencion"), "border-oro", true),
        segSub("riesgoso", t("mapa.s_riesgo"), "border-rojo", true),
        ...propios,
      ];
    }
    case "proveedores":
      return modelo.proveedoresReales.map((p, i) => ({
        sid: `proveedores:${i}`, label: p.nombre, inicial: p.nombre[0], dato: pesoCorto(p.monto),
        anillo: "border-linea", kind: "proveedor", nombre: p.nombre,
      }));
    case "inventario":
      if (!extras.categorias) return [subCargando("inventario:cargando", t)];
      // label = display traducido; nombre = valor crudo del ERP (la clave del
      // round-trip a consulta-serie al expandir la categoría — NO se traduce).
      return (extras.categorias || []).map((c, i) => {
        const lab = tCat(c.x);
        return {
          sid: `inventario:${i}`, label: lab, inicial: String(lab)[0].toUpperCase(),
          dato: pesoCorto(c.y), anillo: "border-hielo/50", kind: "categoria_inv", nombre: c.x,
        };
      });
    case "ventas": {
      if (!extras.ventasCats) return [subCargando("ventas:cargando", t)];
      // P41·1.3 — el corte que faltaba: los DOS CANALES del negocio. Sale de
      // /api/margenes (bloque C), que ya separa mayorista de mostrador.
      const can = extras.canales;
      const canales = [];
      if (can?.mayorista?.disponible) {
        const v = (can.mayorista.grupos || []).reduce((a, g) => a + (g.ventas_12m || 0), 0);
        if (v > 0) canales.push({ sid: "ventas:canal_may", label: t("mapa.s_mayorista"),
          inicial: "", dato: pesoCorto(v), anillo: "border-hielo/60", kind: "canal", canal: "mayorista" });
      }
      // OJO: minorista.total es el RESUMEN del canal (un objeto con ventas,
      // costo, ganancia y margen), no un número — el monto sale de ventas_12m.
      const vMos = can?.minorista?.total?.ventas_12m || 0;
      if (can?.minorista?.disponible && vMos > 0) {
        canales.push({ sid: "ventas:canal_mos", label: t("mapa.s_mostrador"),
          inicial: "", dato: pesoCorto(vMos), anillo: "border-oro",
          kind: "canal", canal: "mostrador" });
      }
      const cats = (extras.ventasCats || []).map((c, i) => {
        const lab = tCat(c.x);
        return {
          sid: `ventas:${i}`, label: lab, inicial: String(lab)[0].toUpperCase(),
          dato: pesoCorto(c.y), anillo: "border-salvia/60", kind: "categoria_venta", nombre: c.x,
        };
      });
      return [...canales, ...cats];
    }
    case "caja": {
      const cobrar = modelo.clientes.reduce((a, c) => a + (c.saldo || 0), 0);
      const pagar = modelo.pag?.por_pagar_total || 0;
      return [
        { sid: "caja:cobrar", label: t("mapa.s_por_cobrar"), inicial: "+",
          dato: cobrar ? pesoCorto(cobrar) : t("mapa.s_vacio_bueno"),
          anillo: cobrar ? "border-salvia/70" : "border-linea", kind: "caja_cobrar", vacio: !cobrar, vacioBueno: true },
        { sid: "caja:pagar", label: t("mapa.s_por_pagar"), inicial: "−",
          dato: pagar ? pesoCorto(pagar) : t("mapa.s_vacio_bueno"),
          anillo: pagar ? "border-oro" : "border-linea", kind: "caja_pagar", vacio: !pagar, vacioBueno: true },
        { sid: "caja:proy", label: t("mapa.s_proyeccion"), inicial: "30",
          dato: modelo.proy?.disponible ? pesoCorto((modelo.proy.ventanas || []).find((v) => v.dias === 30)?.neto || 0) : "—",
          anillo: "border-hielo/50", kind: "caja_proy" },
        // P41·1.3 — la caja del MOSTRADOR, local por local: el corte que el
        // reporte de cierres (bloque E) ya calcula y que acá faltaba colgado.
        ...((extras.cierres?.locales || []).map((l, i) => ({
          sid: `caja:local:${i}`, label: l.local, inicial: "",
          dato: pesoCorto(l.total), anillo: l.variacion_pct == null ? "border-linea"
            : l.variacion_pct < 0 ? "border-oro" : "border-salvia/70",
          kind: "cierre_local", nombre: l.local, esLocalPropio: true,
          badge: l.variacion_pct == null ? t("mapa.s_local_propio")
            : `${l.variacion_pct > 0 ? "+" : ""}${l.variacion_pct}%`,
        }))),
      ];
    }
    case "deposito": {
      const dl = modelo.depositoLists;
      const depSub = (key, label, unidad, anillo) => {
        const arr = dl[key] || [];
        return { sid: `deposito:${key}`, label, inicial: num(arr.length),
          dato: arr.length ? t(unidad) : t("mapa.s_vacio_bueno"),
          anillo: arr.length ? anillo : "border-linea", kind: "dep", lista: key,
          vacio: arr.length === 0, vacioBueno: true };
      };
      // P41·1.3 — "en riesgo" es distinto de "por vencer": cruza la fecha con el
      // ritmo real de venta (bloque H). Es plata que se va a tirar, no una fecha.
      const venc = extras.vencimientos;
      const riesgo = venc?.disponible && venc.lotes_en_riesgo > 0
        ? [{ sid: "deposito:riesgo", label: t("mapa.s_venc_riesgo"),
             inicial: num(venc.lotes_en_riesgo), dato: pesoCorto(venc.total_en_riesgo),
             anillo: "border-rojo", kind: "dep_riesgo" }]
        : [];
      return [
        depSub("vencidos", t("mapa.s_vencidos"), "mapa.s_lotes", "border-rojo"),
        depSub("por_vencer", t("mapa.s_porvencer"), "mapa.s_lotes", "border-oro"),
        depSub("discrepancias", t("mapa.s_discrep"), "mapa.s_items", "border-oro"),
        ...riesgo,
      ];
    }
    case "equipo":
      return modelo.personas.slice(0, 7).map((p, i) => ({
        sid: `equipo:${i}`, label: p.nombre, inicial: p.nombre[0], dato: tRol(p.rol),
        anillo: (p.consultas + p.cargas + p.correcciones) > 0 ? "border-salvia/70" : "border-linea",
        kind: "persona", persona: p,
      }));
    case "contexto":
      return [
        { sid: "contexto:ipc", label: t("mapa.m_ipc"), inicial: "%",
          dato: modelo.macro?.inflacion?.disponible ? `${modelo.macro.inflacion.valor}%` : "—",
          anillo: "border-hielo/50", kind: "macro", cual: "inflacion" },
        { sid: "contexto:dolar", label: t("mapa.m_dolar"), inicial: "$",
          dato: modelo.macro?.dolar?.disponible ? `$${num(modelo.macro.dolar.valor)}` : "—",
          anillo: "border-hielo/50", kind: "macro", cual: "dolar" },
      ];
    default:
      return [];
  }
}

// --- insights ----------------------------------------------------------------------
function armarInsight(domId, modelo, t, alCamino) {
  const def = DOMINIOS[domId];
  const m = modelo.dominios[domId];
  return {
    id: domId, icon: def.icon, titulo: t(def.lk), tono: m.tono,
    conclusiones: m.conclusiones, alerta: m.alerta,
    hallazgos: m.hallazgos.slice(0, 3), conocimiento: m.conocimiento || [],
    seccion: def.seccion, prompt: def.prompt, alCamino,
  };
}

// Texto de una pieza en el idioma actual (el frontend recibe ambos del backend).
function textoPieza(p, lang) {
  return lang === "en" && p.texto_en ? p.texto_en : p.texto;
}

const K_TIPO_LABEL = { regla: "mapa.k_regla", excepcion: "mapa.k_excepcion",
  protocolo: "mapa.k_protocolo", contexto: "mapa.k_contexto" };

// Una pieza de conocimiento. PROFUNDA (mueve un número): borde ocre, birrete,
// "aplicada N veces" + link a dónde la aplicó. CONTEXTO: más tenue, libro, dice
// cómo influye — sin link a un número que no cambió (honesto, defendible).
function PiezaK({ p, lang, t, nodoLabel, onNavegar, onVer }) {
  const prof = p.profunda;
  const Icon = prof ? GraduationCap : BookOpen;
  return (
    <div className={`rounded-lg border px-2.5 py-1.5 ${prof ? "border-l-[3px] bg-papel" : "border-dashed bg-transparent"}`}
      style={prof ? { borderColor: "var(--color-linea)", borderLeftColor: K_COLOR } : { borderColor: "var(--color-linea)" }}>
      <div className="flex items-start gap-1.5">
        <Icon size={13} className="mt-0.5 shrink-0" style={{ color: prof ? K_COLOR : "var(--color-tinta-suave)" }} />
        <p className={`text-[0.78rem] leading-snug ${prof ? "text-tinta" : "text-tinta-suave"}`}>{textoPieza(p, lang)}</p>
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 pl-[19px] text-[0.66rem]">
        {prof ? (
          <>
            <span className="font-semibold" style={{ color: K_COLOR }}>{t("mapa.k_aplicada", { n: p.veces_aplicada })}</span>
            {p.link && (
              // En el panel Memory (onVer presente) y con hallazgo: ILUMINA el camino
              // (verHallazgo directo). Si no hay hallazgo o es otro panel: navega.
              <button onClick={() => (onVer && p.link.hallazgo ? onVer(p) : onNavegar?.(p.link.seccion))}
                className="inline-flex items-center gap-0.5 text-hielo hover:underline">
                {onVer && p.link.hallazgo ? t("mapa.k_ver_camino") : t("mapa.k_ver_donde")} <ArrowRight size={10} />
              </button>
            )}
          </>
        ) : (
          <span className="italic text-tinta-suave">{t("mapa.k_influye", { nodo: nodoLabel })}</span>
        )}
      </div>
    </div>
  );
}

// El bloque "Lo que Aldo me enseñó" de un nodo: agrupado por tipo, las 2-3 más
// aplicadas por defecto, el resto tras "ver las N restantes".
function ConocimientoNodo({ piezas, nodoLabel, t, onNavegar }) {
  const lang = useLang();
  const [verTodo, setVerTodo] = useState(false);
  if (!piezas.length) return <p className="text-[0.78rem] text-tinta-suave">{t("mapa.k_vacio")}</p>;
  const mostradas = verTodo ? piezas : piezas.slice(0, 3);
  const restantes = piezas.length - mostradas.length;
  // agrupar las mostradas por tipo, respetando el orden (profundas primero)
  const grupos = {};
  for (const p of mostradas) (grupos[p.tipo] ||= []).push(p);
  return (
    <div className="space-y-2">
      {["regla", "excepcion", "protocolo", "contexto"].filter((tp) => grupos[tp]).map((tp) => (
        <div key={tp} className="space-y-1">
          <p className="text-[0.64rem] font-semibold uppercase tracking-wide text-tinta-suave">{t(K_TIPO_LABEL[tp])}</p>
          {grupos[tp].map((p) => (
            <PiezaK key={p.id} p={p} lang={lang} t={t} nodoLabel={nodoLabel} onNavegar={onNavegar} />
          ))}
        </div>
      ))}
      {(restantes > 0 || verTodo) && (
        <button onClick={() => setVerTodo((v) => !v)} className="text-[0.72rem] font-semibold text-hielo hover:underline">
          {verTodo ? t("mapa.k_ver_menos") : t("mapa.k_ver_restantes", { n: restantes })}
        </button>
      )}
    </div>
  );
}

// E3·6 — el panel COMPLETO de conocimiento (lo abre la franja "Lo que me
// enseñaste"): todas las piezas, filtrables por tipo (mueven un número / dan
// contexto) y por nodo.
function PanelConocimientoFull({ conocimiento, t, onNavegar, onCerrar }) {
  const lang = useLang();
  const [fTipo, setFTipo] = useState("todos");
  const [fNodo, setFNodo] = useState(null);
  const todas = Object.values(conocimiento.porNodo || {}).flat();
  const nodos = [...new Set(todas.map((p) => p.nodo))];
  let vis = todas;
  if (fTipo === "prof") vis = vis.filter((p) => p.profunda);
  if (fTipo === "ctx") vis = vis.filter((p) => !p.profunda);
  if (fNodo) vis = vis.filter((p) => p.nodo === fNodo);
  const Chip = ({ activo, onClick, children }) => (
    <button onClick={onClick} className={`rounded-full border px-2.5 py-1 text-[0.72rem] font-semibold ${activo ? "border-tinta bg-tinta text-crema" : "border-linea text-tinta-suave hover:border-tinta/40"}`}>{children}</button>
  );
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-tinta/40 p-4 backdrop-blur-sm" onClick={onCerrar}>
      <div className="flex max-h-[85dvh] w-full max-w-2xl flex-col rounded-2xl border border-linea bg-crema sombra-alta" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-2 border-b border-linea p-5 pb-3">
          <div>
            <h3 className="flex items-center gap-2 font-display text-[1.1rem] font-bold" style={{ color: K_COLOR }}>
              <GraduationCap size={18} /> {t("mapa.kpanel_titulo")}
            </h3>
            <p className="mt-0.5 text-[0.8rem] text-tinta-suave">{t("mapa.kpanel_sub", { total: conocimiento.total, hoy: conocimiento.aplicadasHoy })}</p>
          </div>
          <button onClick={onCerrar} className="text-tinta-suave hover:text-tinta"><X size={18} /></button>
        </div>
        <div className="flex flex-wrap gap-1.5 px-5 py-3">
          <Chip activo={fTipo === "todos"} onClick={() => setFTipo("todos")}>{t("mapa.kpanel_todos")}</Chip>
          <Chip activo={fTipo === "prof"} onClick={() => setFTipo("prof")}>{t("mapa.kpanel_profundas")}</Chip>
          <Chip activo={fTipo === "ctx"} onClick={() => setFTipo("ctx")}>{t("mapa.kpanel_contexto")}</Chip>
          <span className="mx-1 w-px bg-linea" />
          {nodos.map((nd) => (
            <Chip key={nd} activo={fNodo === nd} onClick={() => setFNodo((x) => (x === nd ? null : nd))}>{t(DOMINIOS[nd]?.lk || nd)}</Chip>
          ))}
        </div>
        <div className="min-h-0 flex-1 space-y-2 overflow-y-auto px-5 pb-5">
          {vis.length === 0 && <p className="text-[0.82rem] text-tinta-suave">{t("mapa.kpanel_vacio")}</p>}
          {vis.map((p) => (
            <PiezaK key={p.id} p={p} lang={lang} t={t} nodoLabel={t(DOMINIOS[p.nodo]?.lk || p.nodo)} onNavegar={(sec) => { onCerrar(); onNavegar?.(sec); }} />
          ))}
        </div>
      </div>
    </div>
  );
}

// Sección colapsable del panel derecho (le da aire: cada bloque se pliega).
function SeccionPanel({ titulo, n, abierta, onToggle, accent, children }) {
  return (
    <div className="mt-3 border-t border-linea pt-2.5 first:mt-0 first:border-0 first:pt-0">
      <button onClick={onToggle} className="flex w-full items-center justify-between gap-2 text-left">
        <span className="flex items-center gap-1.5 text-[0.7rem] font-semibold uppercase tracking-wide"
          style={{ color: accent || "var(--color-tinta-suave)" }}>
          {titulo}{n != null && <span className="text-tinta-suave">· {n}</span>}
        </span>
        <ChevronDown size={14} className={`text-tinta-suave transition-transform ${abierta ? "" : "-rotate-90"}`} />
      </button>
      {abierta && <div className="mt-2">{children}</div>}
    </div>
  );
}

// Tarea 2 · S2 — la sección del audit trail a la que apunta cada ítem del cerebro
// (trazabilidad): el documento al movimiento que generó, la decisión al hallazgo.
const MEM_SECCION = {
  cargar_remito: "deposito", integrar_staging: "inventario", cargar_recibo: "cuentas",
  sanear_costo_viejo: "inventario", corregir_precio_perdida: "inventario",
};
// Las 3 reglas que se GRABAN (tienen camino): Doña Elsa, Gaseosa, ventana/viernes.
// Van primero en la vista compacta — nunca escondidas detrás de "ver todas".
const MEM_VIDEO_IDS = ["k01", "k11", "k07"];
// La lectura HUMANA de un evento del audit trail — interpreta el dato real (no lo
// inventa): interpola proveedor/archivo/cliente y el antes→después que ya existen.
function _memDocTexto(f, t) {
  const d = f.detalle?.despues || {};
  if (f.accion === "cargar_remito") return t("mapa.mem_doc_remito", { ref: d.proveedor || "" });
  if (f.accion === "integrar_staging") return t("mapa.mem_doc_lista", { ref: d.archivo || "", filas: d.filas || 0 });
  if (f.accion === "cargar_recibo") return t("mapa.mem_doc_recibo", { ref: d.cliente || "" });
  return t("mapa.mem_doc_generico");
}
function _memDecLabel(f, t) {
  if (f.accion === "sanear_costo_viejo") return t("mapa.mem_dec_costo");
  if (f.accion === "corregir_precio_perdida") return t("mapa.mem_dec_precio");
  return t("mapa.mem_dec_generico");
}
const _primerValor = (o) => (o && Object.keys(o).length ? Object.values(o)[0] : null);

function MemDocItem({ f, t, onNavegar }) {
  const sec = MEM_SECCION[f.accion];
  return (
    <div className="rounded-lg border border-linea bg-papel px-2.5 py-1.5">
      <div className="flex items-start gap-1.5">
        <FileText size={13} className="mt-0.5 shrink-0 text-hielo" />
        <p className="text-[0.78rem] leading-snug text-tinta">{_memDocTexto(f, t)}</p>
      </div>
      {sec && (
        <div className="mt-1 pl-[19px]">
          <button onClick={() => onNavegar?.(sec)} className="inline-flex items-center gap-0.5 text-[0.66rem] text-hielo hover:underline">
            {t("mapa.mem_ver_origen")} <ArrowRight size={10} />
          </button>
        </div>
      )}
    </div>
  );
}

function MemDecItem({ f, t, onNavegar }) {
  const sec = MEM_SECCION[f.accion];
  // Se lee como APRENDIZAJE (cómo Ángela opera ahora), con la evidencia real
  // debajo: fixed = antes − después (lo que corrigió), left = después (lo que
  // queda). Mismo dato del audit trail. Si no es numérico, cae a factual antes→después.
  const antes = Number(_primerValor(f.detalle?.antes)), despues = Number(_primerValor(f.detalle?.despues));
  const numerico = Number.isFinite(antes) && Number.isFinite(despues);
  const fixed = numerico ? Math.max(0, antes - despues) : null;
  return (
    <div className="rounded-lg border border-l-[3px] border-linea bg-papel px-2.5 py-1.5" style={{ borderLeftColor: K_COLOR }}>
      <div className="flex items-start gap-1.5">
        <Check size={13} className="mt-0.5 shrink-0" style={{ color: K_COLOR }} />
        <p className="text-[0.78rem] leading-snug text-tinta">{_memDecLabel(f, t)}</p>
      </div>
      <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 pl-[19px] text-[0.66rem]">
        {numerico
          ? <span className="font-semibold" style={{ color: K_COLOR }}>{t("mapa.mem_dec_stats", { fixed, left: despues })}</span>
          : <span className="font-semibold text-tinta-suave">{String(_primerValor(f.detalle?.antes))} → {String(_primerValor(f.detalle?.despues))}</span>}
        {sec && (
          <button onClick={() => onNavegar?.(sec)} className="inline-flex items-center gap-0.5 text-hielo hover:underline">
            {t("mapa.mem_ver_origen")} <ArrowRight size={10} />
          </button>
        )}
      </div>
    </div>
  );
}

// Tarea 2 · S2 — el panel del nodo BUSINESS MEMORY: las 4 capas de un company
// brain, todas con datos que YA existen. Reglas (las 22 piezas por tipo), docs
// (audit trail: archivos que Ángela leyó/cargó), lo aprendido (correcciones con
// antes→después real) y trazabilidad (cada ítem linkea a su origen + resumen).
function MemoriaPanel({ memoria, t, onNavegar, onPreguntar, onCerrar, onVerRegla, flotante }) {
  const lang = useLang();
  const [ab, setAb] = useState({ reglas: true, docs: true, dec: true, traza: true });
  const [verTodas, setVerTodas] = useState(false);
  const tog = (k) => setAb((a) => ({ ...a, [k]: !a[k] }));
  // piezas ENRIQUECIDas (con profunda/link/veces_aplicada) — vienen de porNodo,
  // no del array crudo. Sin esto todas se ven como "contexto".
  const piezas = Object.values(memoria.conocimiento.porNodo || {}).flat();
  const grupos = {};
  for (const p of piezas) (grupos[p.tipo] ||= []).push(p);
  const reglasConLink = piezas.filter((p) => p.link).length;
  // Vista compacta (5): las 3 del video primero, después el resto de profundas por
  // veces aplicadas, después contexto. "Ver todas" muestra las 22 por tipo.
  const rankVideo = (p) => { const i = MEM_VIDEO_IDS.indexOf(p.id); return i === -1 ? 99 : i; };
  const compactas = [...piezas].sort((a, x) =>
    (rankVideo(a) - rankVideo(x)) || ((x.profunda ? 1 : 0) - (a.profunda ? 1 : 0)) ||
    ((x.veces_aplicada || 0) - (a.veces_aplicada || 0))).slice(0, 5);
  return (
    <div className={`border border-linea ${chasisPanel(flotante, "max-h-[68dvh]")}`}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="grid h-8 w-8 place-items-center rounded-xl border-2" style={{ background: "#fbf3e4", borderColor: K_COLOR }}>
            <Brain size={17} style={{ color: K_COLOR }} />
          </span>
          <h3 className="font-display text-[1rem] font-bold leading-tight" style={{ color: K_COLOR }}>{t("mapa.memoria_label")}</h3>
        </div>
        <button onClick={onCerrar} className="text-tinta-suave hover:text-tinta"><X size={16} /></button>
      </div>
      <p className="mt-1 text-[0.78rem] leading-snug text-tinta-suave">{t("mapa.mem_intro")}</p>

      <SeccionPanel titulo={t("mapa.mem_cap_reglas")} n={memoria.total} accent={K_COLOR} abierta={ab.reglas} onToggle={() => tog("reglas")}>
        {!verTodas ? (
          <div className="space-y-1">
            {compactas.map((p) => (
              <PiezaK key={p.id} p={p} lang={lang} t={t} nodoLabel={t(DOMINIOS[p.nodo]?.lk || p.nodo)}
                onNavegar={onNavegar} onVer={onVerRegla} />
            ))}
            <button onClick={() => setVerTodas(true)} className="text-[0.72rem] font-semibold text-hielo hover:underline">
              {t("mapa.mem_ver_todas", { n: memoria.total })}
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {["regla", "excepcion", "protocolo", "contexto"].filter((tp) => grupos[tp]).map((tp) => (
              <div key={tp} className="space-y-1">
                <p className="text-[0.62rem] font-semibold uppercase tracking-wide text-tinta-suave">{t(K_TIPO_LABEL[tp])} · {grupos[tp].length}</p>
                {grupos[tp].map((p) => (
                  <PiezaK key={p.id} p={p} lang={lang} t={t} nodoLabel={t(DOMINIOS[p.nodo]?.lk || p.nodo)}
                    onNavegar={onNavegar} onVer={onVerRegla} />
                ))}
              </div>
            ))}
            <button onClick={() => setVerTodas(false)} className="text-[0.72rem] font-semibold text-hielo hover:underline">
              {t("mapa.k_ver_menos")}
            </button>
          </div>
        )}
      </SeccionPanel>

      <SeccionPanel titulo={t("mapa.mem_cap_docs")} n={memoria.docs} accent={K_COLOR} abierta={ab.docs} onToggle={() => tog("docs")}>
        <div className="space-y-1.5">
          {memoria.docsItems.map((f, i) => <MemDocItem key={i} f={f} t={t} onNavegar={onNavegar} />)}
          {!memoria.docsItems.length && <p className="text-[0.76rem] text-tinta-suave">{t("mapa.mem_vacio")}</p>}
        </div>
      </SeccionPanel>

      <SeccionPanel titulo={t("mapa.mem_cap_dec")} n={memoria.decisiones} accent={K_COLOR} abierta={ab.dec} onToggle={() => tog("dec")}>
        <div className="space-y-1.5">
          {memoria.decisionesItems.map((f, i) => <MemDecItem key={i} f={f} t={t} onNavegar={onNavegar} />)}
          {!memoria.decisionesItems.length && <p className="text-[0.76rem] text-tinta-suave">{t("mapa.mem_vacio")}</p>}
        </div>
      </SeccionPanel>

      <SeccionPanel titulo={t("mapa.mem_cap_traza")} accent={K_COLOR} abierta={ab.traza} onToggle={() => tog("traza")}>
        <p className="text-[0.76rem] leading-snug text-tinta-suave">
          {t("mapa.mem_traza", { reglas: reglasConLink, docs: memoria.docs, dec: memoria.decisiones })}
        </p>
      </SeccionPanel>

      {/* P41·1.2 — consultar la memoria del negocio ahí mismo */}
      <PreguntarAqui prompt={t("mapa.mem_prompt")} onPreguntar={onPreguntar} t={t} />
    </div>
  );
}

// P42·fix — EL CHASIS de los tres paneles del mapa (nodo / hallazgo / memoria).
//
// `flotante` = el panel vive DENTRO del lienzo, anclado arriba y abajo por su
// contenedor absoluto: toma el alto que le dan (h-full) y scrollea adentro.
// Suelto (mobile, mapa apilado, aside) sigue siendo una tarjeta del flujo con su
// tope en dvh. La diferencia es sólo de caja: el contenido no cambia.
//
// Por qué existe: el panel era un hijo más de la columna izquierda, que es un
// flex column. Con `overflow-y-auto` su min-height automático es 0 — el único de
// los cuatro que puede encogerse — así que todo lo que le sobraba a la columna se
// lo comía él y quedaba en 28px (una línea). Anclado ya no depende de lo que
// midan El Pulso, Últimos cruces y Fuentes.
const chasisPanel = (flotante, maxH) =>
  `${flotante ? "h-full" : `mb-3 ${maxH}`} overflow-y-auto rounded-[var(--radius-card)] bg-crema p-4 sombra-papel`;

const CHIP_HALLAZGO = {
  oportunidad: { icon: Sparkles, cls: "text-salvia" },
  alerta: { icon: Bell, cls: "text-rojo" },
  cruce: { icon: GitMerge, cls: "text-hielo" },
  riesgo: { icon: Shield, cls: "text-oro-tinta" },
};

// La tarjeta compacta de un hallazgo (vive en paneles y fila inferior; al
// tocarla el mapa dibuja su camino — el mecanismo que ata todo, P29·3.c).
// P31·1 — layout APILADO (título arriba, monto abajo): en columnas angostas
// (el pulso mide ~178px) el layout horizontal colapsaba el título a 0 y el
// texto se encimaba. Cuando el $ es riesgo/exposición se rotula corto
// ("exposición"); el detalle completo ("no es deuda") vive en el drill.
export function HallazgoChip({ h, onVer }) {
  const t = useT();
  const c = CHIP_HALLAZGO[h.tipo] || CHIP_HALLAZGO.cruce;
  const Icon = c.icon;
  return (
    <button onClick={() => onVer?.(h)}
      className="flex w-full items-start gap-2 rounded-xl border border-linea bg-papel px-3 py-2 text-left transition-colors hover:border-violeta/40">
      <Icon size={14} className={`mt-0.5 shrink-0 ${c.cls}`} />
      <span className="min-w-0 flex-1">
        <span className="block text-[0.78rem] font-semibold leading-tight">{h.titulo}</span>
        {h.conocimiento?.length > 0 && (
          <span className="mt-0.5 inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[0.58rem] font-bold"
            style={{ background: `${K_COLOR}1a`, color: K_COLOR }}>
            <GraduationCap size={9} /> {t("mapa.chip_mas_regla")}
          </span>
        )}
        {h.monto != null && (
          <span className="mt-0.5 flex items-baseline gap-1.5">
            <span className="plata text-[0.78rem] font-semibold text-tinta">{pesoCorto(h.monto)}</span>
            {h.tipo === "riesgo" && <span className="text-[0.6rem] font-semibold uppercase tracking-wide text-oro-tinta">{t("mapa.chip_exposicion")}</span>}
          </span>
        )}
      </span>
    </button>
  );
}

// Panel derecho, modo NODO: conclusiones con número + hallazgos + acciones.
// Panel derecho, modo HALLAZGO: la explicación completa (qué se cruzó, con qué
// datos, en qué ventana, qué concluye, qué acción propone) + "ver cómo lo pensé".
export function InsightNodo({ insight, onNavegar, onPreguntar, onCerrar, flotante = false }) {
  const t = useT();
  if (insight.esHallazgo) return <HallazgoDetalle h={insight.h} alCamino={insight.alCamino}
    onNavegar={onNavegar} onPreguntar={onPreguntar} onCerrar={onCerrar} t={t} flotante={flotante} />;
  if (insight.esMemory) return <MemoriaPanel memoria={insight.memoria} t={t}
    onNavegar={onNavegar} onPreguntar={onPreguntar} onCerrar={onCerrar} onVerRegla={insight.verRegla}
    flotante={flotante} />;
  // La rama NODO vive en su PROPIO componente. Antes el useState de abajo estaba
  // DESPUÉS de estos early-return: para un panel memoria/hallazgo corría 1 hook
  // (useT) y para uno de nodo 2 (useT + useState). Como es el MISMO InsightNodo
  // montado (sólo cambia la prop insight), pasar de memoria/hallazgo → nodo hacía
  // que React viera distinto número de hooks y tirara "Rendered more hooks than
  // during the previous render" → pantalla en blanco. Aislado, cada componente
  // tiene sus hooks incondicionales y la transición entre paneles es segura.
  return <NodoDetalle insight={insight} onNavegar={onNavegar}
    onPreguntar={onPreguntar} onCerrar={onCerrar} t={t} flotante={flotante} />;
}

function NodoDetalle({ insight, onNavegar, onPreguntar, onCerrar, t, flotante }) {
  const Icon = insight.icon;
  const punto = { rojo: "bg-rojo", oro: "bg-oro", verde: "bg-salvia" }[insight.tono];
  // Blindaje: un panel presentacional NUNCA revienta por un insight incompleto.
  // La causa raíz (sub-nodos sin conocimiento) se arregla en seleccionarSub; esto
  // garantiza que cualquier forma de insight (hoy o mañana) se pinte sin caerse.
  const conclusiones = insight.conclusiones || [];
  const hallazgos = insight.hallazgos || [];
  const nK = (insight.conocimiento || []).length;
  // Secciones colapsables (E3·3): por defecto abro Lo que veo y Hallazgos;
  // Conocimiento abierto si hay pocas cosas arriba, para que respire.
  const [abierto, setAbierto] = useState({ ver: true, hall: true, cono: true });
  const tog = (k) => setAbierto((a) => ({ ...a, [k]: !a[k] }));
  return (
    <div className={`border border-linea ${chasisPanel(flotante, "max-h-[62dvh]")}`}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="grid h-8 w-8 place-items-center rounded-full border border-linea bg-papel">
            <Icon size={16} />
          </span>
          <h3 className="font-display text-[1rem] font-bold leading-tight">{insight.titulo}</h3>
          <span className={`h-2 w-2 rounded-full ${punto}`} />
        </div>
        <button onClick={onCerrar} className="text-tinta-suave hover:text-tinta"><X size={16} /></button>
      </div>

      <SeccionPanel titulo={t("mapa.sec_conclusiones")} abierta={abierto.ver} onToggle={() => tog("ver")}>
        <div className="space-y-1.5">
          {conclusiones.map((c, i) => (
            <p key={i} className="text-[0.84rem] leading-snug text-tinta">· {c}</p>
          ))}
          {conclusiones.length === 0 && (
            <p className="text-[0.82rem] text-tinta-suave">{t("mapa.sin_conclusiones")}</p>
          )}
        </div>
      </SeccionPanel>

      {hallazgos.length > 0 && (
        <SeccionPanel titulo={t("mapa.sec_hallazgos")} n={hallazgos.length}
          abierta={abierto.hall} onToggle={() => tog("hall")}>
          <div className="space-y-1.5">
            {hallazgos.map((h) => (
              <HallazgoChip key={h.id} h={h} onVer={(x) => insight.alCamino?.(x)} />
            ))}
          </div>
        </SeccionPanel>
      )}

      {nK > 0 && (
        <SeccionPanel titulo={<span className="inline-flex items-center gap-1"><GraduationCap size={12} />{t("mapa.k_titulo")}</span>}
          n={nK} accent={K_COLOR} abierta={abierto.cono} onToggle={() => tog("cono")}>
          <ConocimientoNodo piezas={insight.conocimiento} nodoLabel={insight.titulo} t={t} onNavegar={onNavegar} />
        </SeccionPanel>
      )}

      {/* P41·1.1 — Ángela vive DENTRO del panel: se le pregunta por ESTE nodo
          sin salir del mapa. La sugerencia del dominio queda a un toque. */}
      <PreguntarAqui prompt={insight.prompt} onPreguntar={onPreguntar} t={t} />

      {/* El detalle completo es opcional y va ÚLTIMO: el nodo primero informa. */}
      <div className="mt-3 border-t border-linea pt-3">
        <button onClick={() => onNavegar?.(insight.seccion, insight.hl)}
          className="inline-flex items-center gap-1.5 rounded-full border border-linea px-3.5 py-1.5 text-[0.8rem] font-semibold text-tinta hover:border-tinta/30">
          {t("mapa.ir_a", { seccion: t(`nav.${insight.seccion}`) })} <ArrowRight size={13} />
        </button>
      </div>
    </div>
  );
}

// La caja de Ángela dentro de un panel del mapa: la pregunta sugerida del nodo
// + texto libre. No abre otra pantalla — usa el mismo canal de siempre.
function PreguntarAqui({ prompt, onPreguntar, t }) {
  const [q, setQ] = useState("");
  const mandar = () => { const x = q.trim(); if (x) { onPreguntar?.(x); setQ(""); } };
  return (
    <div className="mt-3 rounded-xl border border-violeta/20 bg-violeta/[0.04] p-2.5">
      <div className="flex items-center gap-1.5">
        <AngelaMark size={16} />
        <p className="text-[0.72rem] font-semibold uppercase tracking-wide text-violeta">{t("mapa.preguntar_aqui")}</p>
      </div>
      {prompt && (
        <button onClick={() => onPreguntar?.(prompt)}
          className="mt-1.5 w-full rounded-lg border border-linea bg-crema px-2.5 py-1.5 text-left text-[0.76rem] leading-snug text-tinta hover:border-violeta/40">
          {prompt}
        </button>
      )}
      <div className="mt-1.5 flex items-center gap-1.5">
        <input value={q} onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && mandar()}
          placeholder={t("mapa.preguntar_ph")}
          className="min-w-0 flex-1 rounded-full border border-linea bg-crema px-3 py-1.5 text-[0.76rem] outline-none focus:border-violeta/40" />
        <button onClick={mandar} disabled={!q.trim()}
          className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-violeta text-crema disabled:opacity-40">
          <ArrowRight size={13} />
        </button>
      </div>
    </div>
  );
}

function HallazgoDetalle({ h, alCamino, onNavegar, onPreguntar, onCerrar, t, flotante }) {
  const c = CHIP_HALLAZGO[h.tipo] || CHIP_HALLAZGO.cruce;
  const Icon = c.icon;
  return (
    <div className={`border border-violeta/25 ${chasisPanel(flotante, "max-h-[52dvh]")}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <Icon size={16} className={c.cls} />
          <h3 className="font-display text-[0.98rem] font-bold leading-tight">{h.titulo}</h3>
        </div>
        <button onClick={onCerrar} className="text-tinta-suave hover:text-tinta"><X size={16} /></button>
      </div>
      {h.monto != null && (
        <p className="plata mt-1 text-2xl font-medium text-tinta">
          {pesoCorto(h.monto)}
          {/* P30·A2 — la etiqueta del $ cuando NO es plata a cobrar (ej.
              concentración: facturación 12m, no deuda) */}
          {h.montoLabel && <span className="ml-2 align-middle text-[0.7rem] font-normal text-tinta-suave">{h.montoLabel}</span>}
        </p>
      )}

      {/* Qué se cruzó */}
      <p className="mt-2 text-[0.72rem] text-tinta-suave">{t("cardneg.cruce")} {h.fuentes.join(" · ")}</p>
      {/* El porqué con los datos */}
      <div className="mt-2 space-y-1.5">
        {h.porque.map((p, i) => (
          <p key={i} className="text-[0.86rem] leading-snug text-tinta">{p}</p>
        ))}
      </div>
      {h.grafico && (
        <div className="mt-2.5 rounded-xl border border-linea bg-papel p-2.5">
          <CuerpoConsulta resultado={h.grafico} t={t} />
        </div>
      )}
      {/* La ventana / supuestos declarados */}
      {h.supuestos.length > 0 && (
        <p className="mt-2 rounded-lg bg-papel-hondo/50 px-2.5 py-1.5 text-[0.74rem] leading-snug text-tinta-suave">
          {h.supuestos.join(" · ")}
        </p>
      )}

      <div className="mt-3 flex flex-wrap gap-2">
        <button onClick={() => alCamino?.(h)}
          className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-3.5 py-1.5 text-[0.8rem] font-semibold text-crema">
          <Lightbulb size={13} /> {t("mapa.como_lo_pense")}
        </button>
        {h.chat && (
          <button onClick={() => onPreguntar?.(h.chat)}
            className="inline-flex items-center gap-1.5 rounded-full border border-violeta/40 px-3.5 py-1.5 text-[0.8rem] font-semibold text-violeta">
            <AngelaMark size={13} /> {t("mapa.preguntar")}
          </button>
        )}
        <button onClick={() => onNavegar?.(h.seccion)}
          className="inline-flex items-center gap-1.5 rounded-full border border-linea px-3.5 py-1.5 text-[0.8rem] font-semibold text-tinta-suave hover:text-tinta">
          {t("mapa.ver_seccion")} <ArrowRight size={13} />
        </button>
      </div>
    </div>
  );
}

// --- controles ----------------------------------------------------------------------
function Controles() {
  const t = useT();
  const rf = useReactFlow();
  const B = ({ onClick, title, children }) => (
    <button onClick={onClick} title={title}
      className="grid h-9 w-9 place-items-center rounded-full border border-linea bg-crema text-tinta-suave sombra-papel hover:text-tinta">
      {children}
    </button>
  );
  return (
    <div className="absolute bottom-4 right-4 z-10 flex flex-col gap-1.5">
      <B onClick={() => rf.zoomIn({ duration: 200 })} title={t("mapa.acercar")}><ZoomIn size={16} /></B>
      <B onClick={() => rf.zoomOut({ duration: 200 })} title={t("mapa.alejar")}><ZoomOut size={16} /></B>
      <B onClick={() => rf.fitView({ padding: 0.15, duration: 300 })} title={t("mapa.recentrar")}><Maximize size={15} /></B>
    </div>
  );
}

// --- el lienzo ------------------------------------------------------------------------
function Lienzo({ modelo, rama, nivel2, extras, pistaNodo, onExpandir, onExpandirSub, onSeleccion,
                  onSeleccionSub, onSeleccionMemoria, onCorte, camino, completo = false, t }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [hover, setHover] = useState(null);
  const rf = useReactFlow();

  useEffect(() => {
    const g = armarGrafo(modelo, rama, nivel2, t, extras, pistaNodo, completo);
    setNodes(g.nodes);
    setEdges(g.edges);
    requestAnimationFrame(() => rf.fitView({ padding: 0.15, duration: 250 }));
  }, [modelo, rama, nivel2, extras, pistaNodo, completo, t, setNodes, setEdges, rf]);

  // Hover-focus + CAMINO iluminado en secuencia (el camino manda sobre el hover)
  useEffect(() => {
    const nodosCamino = camino ? camino.nodos.slice(0, camino.paso + 1) : null;
    const setCam = new Set(nodosCamino || []);
    // El hover del nodo MEMORY NO atenúa el resto (queda limpio): solo enciende
    // sus aristas ocre (más abajo). Por eso se excluye del set de vecinos.
    const vecinos = !camino && hover && hover !== "memory" ? new Set([hover]) : null;
    if (vecinos) {
      for (const r of RELACIONES) {
        if (r.s === hover) vecinos.add(r.t);
        if (r.t === hover) vecinos.add(r.s);
      }
    }
    // P40·1 — FOCO AL EXPANDIR: mientras una rama está abierta, el resto del mapa
    // se atenúa. Antes la atenuación existía sólo en hover, así que abrir Ventas
    // dejaba sus sub-ramas compitiendo con las otras 7 fuentes — justo el ruido
    // que la expansión venía a resolver. El camino y el hover siguen mandando
    // por encima (son gestos más específicos y momentáneos).
    const focoRama = !camino && !hover && rama ? rama : null;

    const kNode = camino?.kNode || null;
    const esK = (id) => typeof id === "string" && id.startsWith("k:");
    const posDe = (id) => (esK(id) && kNode ? kNode.pos : POS[id]);
    setNodes((nds) => {
      // quitar cualquier nodo de conocimiento viejo antes de recolocar el actual
      const base = nds.filter((n) => n.type !== "conocimiento");
      const mapped = base.map((n) => {
        const esSub = n.type === "sub";
        let apagado = false, enCamino = false, bombilla = null;
        if (camino) {
          enCamino = setCam.has(n.id);
          apagado = !enCamino;
          const ultimo = camino.nodos[camino.nodos.length - 1];
          if (n.id === ultimo && camino.paso >= camino.nodos.length - 1 && camino.monto != null) {
            bombilla = pesoCorto(camino.monto);
          }
        } else if (vecinos) {
          apagado = !(esSub ? n.data.padre === hover : vecinos.has(n.id));
        } else if (focoRama) {
          // Los sub-nodos son SIEMPRE los de la rama abierta: quedan encendidos.
          // El centro queda encendido (es el ancla del cerebro); las otras
          // fuentes y la memoria se atenúan, sin desaparecer.
          apagado = !esSub && n.id !== focoRama && n.id !== "centro";
        }
        return { ...n, data: { ...n.data, hover: !camino && hover === n.id, apagado, enCamino, bombilla } };
      });
      if (kNode) {
        mapped.push({ id: kNode.id, type: "conocimiento", position: kNode.pos,
          draggable: false, selectable: false,
          data: { etiqueta: kNode.etiqueta, texto: kNode.texto,
                  enCamino: setCam.has(kNode.id), apagado: !setCam.has(kNode.id) } });
      }
      return mapped;
    });
    setEdges((eds) => {
      const base = eds.filter((e) => !e.id.startsWith("cam-"));
      const conEstilo = base.map((e) => {
        if (e.tipo === "memoria") {
          // aristas del cerebro: ocre punteado sutil, visibles SOLO con hover del
          // memory. `animated` (el mismo flujo de dashes que ya usa el mapa) hace
          // que el trazo VIAJE del cerebro al dominio — "lo alimenta", no un cable.
          const on = !camino && hover === "memory";
          return { ...e, animated: on, style: { ...e.style, opacity: on ? 0.35 : 0 } };
        }
        const activo = vecinos && (hover === e.source || hover === e.target);
        // Con foco de rama, sólo se ven los trazos que la tocan (y los que
        // cuelgan de ella): el resto baja, no se apaga del todo.
        const enFoco = focoRama && (e.tipo === "sub" || e.source === focoRama || e.target === focoRama);
        const opacidadBase = e.tipo === "sub" ? 0.5 : 0.55;
        return { ...e, style: { ...e.style,
          strokeWidth: activo ? 2.6 : e.tipo === "sub" ? 1.1 : 1.6,
          opacity: camino ? 0.08
                 : vecinos ? (activo ? 0.95 : 0.12)
                 : focoRama ? (enFoco ? opacidadBase : 0.1)
                 : opacidadBase } };
      });
      if (!camino) return conEstilo;
      const overlay = [];
      for (let i = 0; i < camino.nodos.length - 1; i++) {
        const a = camino.nodos[i], b = camino.nodos[i + 1];
        const pa = posDe(a), pb = posDe(b);
        if (!pa || !pb) continue;
        const visible = camino.paso > i;
        // el trazo que TOCA el nodo de conocimiento es ocre y punteado (distinto
        // del azul-IA de las fuentes de datos) — se lee sin leyenda.
        const esTrazoK = esK(a) || esK(b);
        const color = esTrazoK ? K_COLOR : AZUL_IA;
        overlay.push({
          id: `cam-${i}`, source: a, target: b,
          sourceHandle: `s-${ladoHacia(pa, pb)}`, targetHandle: `t-${ladoHacia(pb, pa)}`,
          animated: visible,
          markerEnd: { type: MarkerType.ArrowClosed, color, width: 18, height: 18 },
          style: { stroke: color, strokeWidth: 3, opacity: visible ? 0.95 : 0,
                   strokeDasharray: esTrazoK ? "6 4" : undefined,
                   transition: "opacity .25s ease" },
        });
      }
      return [...conEstilo, ...overlay];
    });
    // Deps ESTRUCTURALES incluidas a propósito: el efecto de arriba (armarGrafo
    // base) puede re-correr durante un camino activo (p.ej. cuando se apaga la
    // pista de descubrimiento) y PISA el nodo ocre de conocimiento. Como este
    // efecto está definido DESPUÉS, compartir sus deps garantiza que corra justo
    // después y RE-APLIQUE el camino + el nodo k:* (antes aparecía y desaparecía).
  }, [hover, camino, modelo, rama, nivel2, extras, pistaNodo, completo, setNodes, setEdges]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      nodeTypes={NODE_TYPES}
      fitView
      fitViewOptions={{ padding: 0.15 }}
      minZoom={0.35}
      maxZoom={1.8}
      nodesConnectable={false}
      edgesFocusable={false}
      zoomOnDoubleClick={false}
      onNodeMouseEnter={(_e, n) => (n.type === "dominio" || n.type === "memory") && setHover(n.id)}
      onNodeMouseLeave={() => setHover(null)}
      onNodeClick={(_e, n) => {
        // P30·B — el botón [+/−] del nodo expande/colapsa (data-expand); el
        // resto del nodo abre su panel. Bulletproof: no depende del doble clic.
        if (n.type === "dominio") {
          if (_e.target?.closest?.("[data-expand]")) onExpandir(n.id);
          else onSeleccion(n.id);
        }
        if (n.type === "sub") onSeleccionSub(n.id, n.data);
        if (n.type === "memory") onSeleccionMemoria?.();
        // P40·4 — un corte LLEVA al dato: abre su sección real (con el subtab
        // que corresponde) y cierra la vista completa.
        if (n.type === "corte") onCorte?.(n.data.corte);
      }}
      onNodeDoubleClick={(_e, n) => {
        if (n.type === "dominio") onExpandir(n.id);
        if (n.type === "sub") onExpandirSub(n.id, n.data);
      }}
      onPaneClick={() => onSeleccion(null)}
      proOptions={{ hideAttribution: false }}
    >
      <Controles />
    </ReactFlow>
  );
}

// --- versión apilada (mobile / fallback honesto) --------------------------------------
function MapaApilado({ modelo, onSeleccion, seleccion, onNavegar, onPreguntar, onVerHallazgo, t }) {
  const orden = ["proveedores", "deposito", "inventario", "ventas", "clientes", "caja", "equipo", "contexto"];
  return (
    <div className="space-y-2.5">
      {/* Los hallazgos primero: lo que el cerebro produjo (tap → explicación) */}
      <div className="rounded-[var(--radius-card)] border border-violeta/20 bg-violeta/[0.04] p-3.5">
        <p className="mb-2 text-[0.72rem] font-semibold uppercase tracking-wide text-violeta">
          {t("mapa.fila_hallazgos", { n: num(modelo.hallazgos.length) })}
        </p>
        <div className="space-y-1.5">
          {modelo.hallazgos.slice(0, 4).map((h) => (
            <HallazgoChip key={h.id} h={h} onVer={onVerHallazgo} />
          ))}
        </div>
      </div>
      {orden.map((id) => {
        const def = DOMINIOS[id];
        const m = modelo.dominios[id];
        const Icon = def.icon;
        const punto = { rojo: "bg-rojo", oro: "bg-oro", verde: "bg-salvia" }[m.tono];
        const abierto = seleccion?.id === id && !seleccion?.esHallazgo;
        return (
          <div key={id} className="rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
            <button onClick={() => onSeleccion(abierto ? null : id)}
              className="flex w-full items-center gap-3 p-4 text-left">
              <span className={`grid h-11 w-11 shrink-0 place-items-center rounded-full border-2 bg-papel ${ANILLO[m.tono]}`}>
                <Icon size={19} />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block font-display text-[0.98rem] font-bold leading-tight">{t(def.lk)}</span>
                <span className="plata block text-[0.8rem] text-tinta-suave">{m.dato}</span>
              </span>
              {m.nHallazgos > 0 && (
                <span className="grid h-5 min-w-5 shrink-0 place-items-center rounded-full bg-violeta px-1 text-[0.66rem] font-bold text-crema">{m.nHallazgos}</span>
              )}
              <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${punto}`} />
            </button>
            {abierto && (
              <div className="border-t border-linea px-4 pb-4 pt-3">
                <InsightNodo insight={seleccion} onNavegar={onNavegar}
                  onPreguntar={onPreguntar} onCerrar={() => onSeleccion(null)} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// --- la sección --------------------------------------------------------------------------
export default function MapaNegocio({ onNavegar, onPreguntar, onInsight }) {
  const t = useT();
  const lang = useLang();
  const esDesktop = useIsDesktop();
  // Idioma para pedir/cachear el mapa: el del perfil si está seteado, si no el de
  // la UI (langStore = default del tenant o el toggle). El `|| "es"` viejo hacía
  // que un usuario con idioma NULL (el default de casi todos) cacheara/reintentara
  // como "es" aunque el chrome estuviera en EN — y no re-fetcheaba al togglear.
  const langKey = useSession()?.usuario?.idioma || lang;
  const datos = useMapaDatos(langKey);
  const [rama, setRama] = useState(null);           // dominio expandido (UNA a la vez)
  const [nivel2, setNivel2] = useState(null);       // {sub, etiqueta, items}
  const [extras, setExtras] = useState({});         // fetch lazy: categorias inv/ventas
  const [camino, setCamino] = useState(null);       // {id, nodos, paso, monto}
  const [seleccionMobile, setSeleccionMobile] = useState(null);
  const [insightMobileH, setInsightMobileH] = useState(null);
  const [pista, setPista] = useState(false);        // P31·3 — pulso-pista 1ª vez
  const [completo, setCompleto] = useState(false);  // P40·3 — el mapa completo (overlay)
  // P41·1.1 — el panel del nodo/hallazgo/memoria vive a la IZQUIERDA del
  // lienzo (antes iba al aside derecho, encima del chat). El mapa NO se cierra.
  const [panelIzq, setPanelIzq] = useState(null);
  const [panelK, setPanelK] = useState(false);      // E3·6 — panel completo "Lo que me enseñaste"

  const modelo = useMemo(() => (datos ? armarModelo(datos, t) : null), [datos, t]);

  // P31·3 — descubribilidad: la PRIMERA vez que se abre el mapa en la sesión,
  // el nodo con más hallazgos late suave unas veces para invitar a expandir.
  useEffect(() => {
    if (!modelo) return;
    try {
      if (sessionStorage.getItem("polpilot.mapa.pista")) return;
      sessionStorage.setItem("polpilot.mapa.pista", "1");
    } catch { /* sin storage: igual mostramos la pista una vez */ }
    setPista(true);
    const tmr = setTimeout(() => setPista(false), 4200);
    return () => clearTimeout(tmr);
  }, [!!modelo]);

  // El nodo objetivo de la pista: el dominio con más hallazgos activos.
  const pistaNodo = useMemo(() => {
    if (!pista || !modelo) return null;
    return Object.entries(modelo.dominios)
      .sort((a, b) => (b[1].nHallazgos || 0) - (a[1].nHallazgos || 0))[0]?.[0] || null;
  }, [pista, modelo]);

  // El camino avanza solo (1-1.5s total). Con motion-reduce: directo al final.
  useEffect(() => {
    if (!camino || camino.paso >= camino.nodos.length) return;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
      setCamino((c) => c && { ...c, paso: c.nodos.length });
      return;
    }
    const timer = setTimeout(() => setCamino((c) => c && { ...c, paso: c.paso + 1 }), 420);
    return () => clearTimeout(timer);
  }, [camino]);

  // Ver un hallazgo = camino iluminado + explicación completa en el panel (3.c)
  const verHallazgo = (h) => {
    setRama(null); setNivel2(null);
    const orig = h.camino?.length ? h.camino : [h.dominio].filter(Boolean);
    // E3·5 — si el hallazgo lo modificó una pieza de conocimiento, ésta entra al
    // camino como punto PROPIO, entre las fuentes de datos y la conclusión.
    const kp = (h.conocimiento || [])[0];
    let nodos = orig, kNode = null;
    if (kp && orig.length) {
      const kNodeId = "k:" + kp.id;
      const last = orig[orig.length - 1];
      const prev = orig[orig.length - 2] || orig[0];
      const pa = POS[prev] || POS[last] || { x: 0, y: 0 };
      const pc = POS[last] || pa;
      const posK = { x: (pa.x + pc.x) / 2 + 60, y: (pa.y + pc.y) / 2 - 90 };
      nodos = [...orig.slice(0, -1), kNodeId, last];
      kNode = { id: kNodeId, pos: posK, etiqueta: t("mapa.leyenda_conocimiento"),
                texto: textoPieza(kp, lang) };
    }
    setCamino({ id: h.id, nodos, paso: 0, monto: h.monto ?? null, kNode });
    const ins = { esHallazgo: true, h, alCamino: verHallazgo };
    if (esDesktop) setPanelIzq(ins);
    else setInsightMobileH(ins);
  };

  const expandir = (id) => {
    setCamino(null); setNivel2(null);
    setRama((r) => (r === id ? null : id));
    if (id === "inventario" && !extras.categorias) {
      api.consultaSerie({ fuente: "inventario", metrica: "inmovilizado", agrupar: "categoria", top_n: 6 })
        .then((r) => r?.ok && setExtras((e) => ({ ...e, categorias: r.series[0].puntos.slice(0, 6) })))
        .catch(() => {});
    }
    // P41·1.4 — los LOCALES PROPIOS cuelgan de Clientes pero NO son clientes:
    // se piden al abrir la rama (bajo demanda, como el resto) y se pintan
    // distinto para que la estructura del negocio se lea de un vistazo.
    if (id === "clientes" && !extras.locales) {
      api.traslados()
        .then((r) => r?.disponible && setExtras((e) => ({ ...e, locales: r.locales || [] })))
        .catch(() => {});
    }
    if (id === "ventas" && !extras.ventasCats) {
      api.consultaSerie({ fuente: "ventas", metrica: "pesos", agrupar: "categoria", top_n: 6 })
        .then((r) => r?.ok && setExtras((e) => ({ ...e, ventasCats: r.series[0].puntos.slice(0, 6) })))
        .catch(() => {});
    }
    // P41·1.3 — cortes que la fuente REALMENTE contiene y no estaban colgados:
    // los dos canales de venta, los cierres por local y lo que vence sin llegar
    // a venderse. Todos bajo demanda, como el resto.
    if (id === "ventas" && !extras.canales) {
      api.margenes()
        .then((r) => r?.disponible && setExtras((e) => ({ ...e, canales: r })))
        .catch(() => setExtras((e) => ({ ...e, canales: null })));
    }
    if (id === "caja" && !extras.cierres) {
      api.cierresLocales(7)
        .then((r) => r?.disponible && setExtras((e) => ({ ...e, cierres: r })))
        .catch(() => setExtras((e) => ({ ...e, cierres: null })));
    }
    if (id === "deposito" && !extras.vencimientos) {
      api.vencimientos(30)
        .then((r) => r?.disponible && setExtras((e) => ({ ...e, vencimientos: r })))
        .catch(() => setExtras((e) => ({ ...e, vencimientos: null })));
    }
  };

  // Nivel 2: los hijos REALES del sub tocado (donde el dataset los sostiene).
  const expandirSub = async (sid, data) => {
    if (nivel2?.sub === sid) { setNivel2(null); return; }
    const items = [];
    if (data.kind === "segmento") {
      for (const c of (modelo.segmentos[data.seg] || []).slice(0, 5)) {
        items.push({ label: c.nombre, inicial: c.nombre[0], dato: pesoCorto(c.saldo),
          anillo: data.anillo, kind: "cliente", cliente: c });
      }
    } else if (data.kind === "dep") {
      for (const it of (modelo.depositoLists[data.lista] || []).slice(0, 5)) {
        const nombre = it.producto || it.descripcion || it.nombre || "?";
        items.push({ label: nombre, inicial: String(nombre)[0],
          dato: it.cantidad != null ? num(it.cantidad) : (it.vence || it.dias != null ? String(it.dias ?? "") : ""),
          anillo: data.anillo, kind: "item" });
      }
    } else if (data.kind === "caja_pagar") {
      for (const f of modelo.pagosLists.por_vencer.slice(0, 4)) {
        items.push({ label: f.proveedor, inicial: f.proveedor[0], dato: pesoCorto(f.monto),
          anillo: "border-oro", kind: "item" });
      }
    } else if (data.kind === "caja_cobrar") {
      for (const c of modelo.clientes.filter((x) => x.saldo > 0).sort((a, b) => b.saldo - a.saldo).slice(0, 4)) {
        items.push({ label: c.nombre, inicial: c.nombre[0], dato: pesoCorto(c.saldo),
          anillo: "border-salvia/70", kind: "cliente", cliente: c });
      }
    } else if (data.kind === "categoria_inv") {
      const r = await api.consultaSerie({ fuente: "inventario", metrica: "inmovilizado",
        agrupar: "producto", categoria: data.nombre, top_n: 4 }).catch(() => null);
      for (const p of r?.ok ? r.series[0].puntos : []) {
        items.push({ label: p.x, inicial: String(p.x)[0], dato: pesoCorto(p.y),
          anillo: "border-hielo/50", kind: "item" });
      }
    } else if (data.kind === "proveedor") {
      // sus productos (por marca en la descripción) + su factura pendiente
      const marca = data.nombre.replace(/^(Distrib\.|Frigorífico|Golosinas|Alimentos|Lácteos|Limpieza)\s*/i, "")
        .replace(/\s*(SA|SRL|Mayorista)\s*$/i, "").trim();
      const r = await api.consultaSerie({ fuente: "inventario", metrica: "inmovilizado",
        agrupar: "producto", producto: marca, top_n: 3 }).catch(() => null);
      for (const p of r?.ok ? r.series[0].puntos : []) {
        items.push({ label: p.x, inicial: String(p.x)[0], dato: pesoCorto(p.y),
          anillo: "border-hielo/50", kind: "item" });
      }
      for (const f of [...modelo.pagosLists.por_vencer, ...modelo.pagosLists.vencidos]
        .filter((f) => f.proveedor === data.nombre).slice(0, 2)) {
        items.push({ label: f.numero || t("mapa.s_factura"), inicial: "F",
          dato: pesoCorto(f.monto), anillo: "border-oro", kind: "item" });
      }
    }
    if (items.length) setNivel2({ sub: sid, etiqueta: data.label, items });
  };

  // Click en un sub-nodo: sus conclusiones al panel (entidades reales).
  const seleccionarSub = (sid, data) => {
    // `hl` viaja hasta el botón "ver más" para que el drill-through abra la
    // entidad puntual (el modal de este cliente), no sólo la sección genérica.
    let conclusiones = [], titulo = data.label, prompt = null, seccion = null, hl = null;
    if (data.kind === "cliente" || (data.kind === "segmento" && false)) {
      const c = data.cliente;
      if (c) {
        conclusiones = [
          t("mapa.sc_saldo", { monto: pesoCorto(c.saldo), dias: num(c.dias_sin_pagar) }),
          t("mapa.sc_promedio", { dias: num(c.promedio_pago_dias || c.plazo_dias) }),
          c.atraso_vs_promedio > 0 && t("mapa.sc_desvio", { pct: num(c.atraso_vs_promedio) }),
        ].filter(Boolean);
        prompt = `contame de ${c.nombre}: su historial y su riesgo`;
        seccion = "cuentas";
        hl = c.id != null ? `cliente-${c.id}` : null;
      }
    } else if (data.kind === "persona") {
      const p = data.persona;
      conclusiones = [
        (p.consultas + p.cargas + p.correcciones) > 0
          ? t("mapa.sp_actividad", { consultas: num(p.consultas), cargas: num(p.cargas), correcciones: num(p.correcciones) })
          : t("equipo.ficha_sin_actividad"),
        p.temas_top?.length > 0 && t("equipo.act_temas", { temas: p.temas_top.map(([k]) => k.replaceAll("_", " ")).join(", ") }),
      ].filter(Boolean);
      prompt = `qué estuvo haciendo ${p.nombre} esta semana`;
      seccion = "equipo";
    } else if (data.kind === "macro") {
      const m = modelo.macro?.[data.cual];
      conclusiones = m?.disponible
        ? [`${m.indicador}: ${data.cual === "inflacion" ? m.valor + "%" : "$" + num(m.valor)} (${m.fuente || ""})`,
           modelo.evo?.hay_indice && t("mapa.c_x_deflacta", { mes: modelo.evo.mes_base || "" })].filter(Boolean)
        : [t("mapa.n_sin_dato")];
      seccion = "evolucion";
    } else {
      conclusiones = [data.dato ? `${data.label}: ${data.dato}` : data.label];
      seccion = DOMINIOS[rama]?.seccion || null;
    }
    // conocimiento: [] es OBLIGATORIO — NodoDetalle lee insight.conocimiento.length.
    // El insight de un sub-nodo (entidad real: cliente, ítem, persona) no cablea
    // conocimiento propio, pero el campo debe existir o el panel revienta.
    const ins = { id: sid, icon: DOMINIOS[rama]?.icon || Boxes, titulo, tono: "verde",
      conclusiones, alerta: null, hallazgos: [], conocimiento: [], seccion: seccion || "panel", hl,
      prompt: prompt || DOMINIOS[rama]?.prompt, alCamino: verHallazgo };
    if (esDesktop) setPanelIzq(ins);
    else setSeleccionMobile(ins);
  };

  // P40·4 — un corte del mapa completo LLEVA al dato: cierra el overlay y abre
  // la sección real con su subtab. Nunca deja al usuario mirando una etiqueta.
  const irACorte = (c) => {
    if (!c) return;
    setCompleto(false);
    onNavegar?.(c.a, c.hl || null);
  };

  const seleccionar = (id) => {
    if (!id) {
      // click afuera: colapsa un nivel por vez; después limpia camino/panel
      if (nivel2) { setNivel2(null); return; }
      if (rama) { setRama(null); return; }
      if (camino) { setCamino(null); }
      setPanelIzq(null); setSeleccionMobile(null);
      return;
    }
    setCamino(null);
    const ins = armarInsight(id, modelo, t, verHallazgo);
    if (esDesktop) setPanelIzq(ins);
    else setSeleccionMobile(ins);
  };

  // Tarea 2 · S3 — regla del panel Memory → verHallazgo DIRECTO (el flujo de Latest
  // crosses que anda tras adda81c): busca el hallazgo que la pieza modificó y lo
  // ilumina. Si la pieza no cuelga de un hallazgo con camino (p.ej. Doña Elsa, que
  // es anotación de cuentas), navega a su sección.
  const verReglaCamino = (p) => {
    const hid = p?.link?.hallazgo;
    const h = hid ? modelo.hallazgos.find((x) => x.id === hid) : null;
    if (h) verHallazgo(h);
    else if (p?.link?.seccion) onNavegar?.(p.link.seccion);
  };
  const seleccionarMemoria = () => {
    setRama(null); setNivel2(null); setCamino(null);
    const ins = { esMemory: true, memoria: modelo.memoria, verRegla: verReglaCamino };
    if (esDesktop) setPanelIzq(ins);
    else setSeleccionMobile(ins);
  };

  if (!modelo) {
    return (
      <div>
        <Cabecera t={t} modelo={null} />
        <div className="h-[420px] animate-pulse rounded-[var(--radius-card)] border border-linea/60 bg-papel-hondo/50" />
      </div>
    );
  }

  const H = modelo.hallazgos;
  const nAlertas = H.filter((h) => h.tipo === "alerta").length;
  const nOps = H.filter((h) => h.tipo === "oportunidad").length;
  // P30·A1 — NUNCA sumar magnitudes incompatibles. Lo único homogéneo y
  // capturable es lo RECUPERABLE (cobranza vencida + capital dormido + ahorro):
  // ese es el titular honesto. La concentración es EXPOSICIÓN, se muestra
  // aparte y jamás entra en la suma de plata.
  const recuperables = H.filter((h) => h.naturaleza === "recuperable");
  const recuperable = recuperables.reduce((a, h) => a + (h.monto || 0), 0);
  const exposicion = H.filter((h) => h.naturaleza === "riesgo").reduce((a, h) => a + (h.monto || 0), 0);
  const top = H.find((h) => h.naturaleza === "recuperable") || H[0];
  const act = modelo.actividad;
  const hechoN = act ? (act.correcciones || 0) + (act.staging_procesados || 0) + (act.alertas_emitidas || 0) : 0;

  return (
    <div>
      <Cabecera t={t} modelo={modelo} />

      {esDesktop ? (
        <>
        {/* P42·2 — EL LIENZO SOLO, a todo el ancho. La columna izquierda (El
            Pulso + Últimos cruces + Fuentes) se sacó: a 208px apretaba tres
            tarjetas en una tira ilegible y le comía un cuarto de pantalla al
            mapa, que es lo que esta vista viene a mostrar. Lo que daba sigue en
            pie por otros caminos: los números del pulso están en los badges del
            nav y en la fila de abajo, los cruces se encienden desde los chips de
            "Hallazgos" del panel de cada nodo y desde la fila inferior, y las
            fuentes se cuentan en la frase de la cabecera. */}
        <div className="h-[calc(100dvh-300px)] min-h-[440px]">
          {/* --panel-w: el ancho del panel del nodo, UNA sola vez. Lo usan el
              panel, el breadcrumb y la leyenda, así que corriendo este número se
              corre todo junto (antes de esto había tres constantes sueltas que
              se desincronizaban). Con clamp, 340px cuando el lienzo es ancho y
              hasta 268 cuando está apretado (1280 + el chat de Ángela abierto):
              el mapa nunca queda reducido a una franja. */}
          <div className="relative h-full w-full overflow-hidden rounded-[var(--radius-card)] border border-linea mapa-lienzo sombra-papel"
            style={{ "--panel-w": "clamp(268px, 30%, 380px)" }}>
            {/* Breadcrumb de la rama (P29·C3): dónde estás parado.
                Con el panel abierto se corre a su derecha — si no, queda tapado
                (mismo criterio que la cámara del cerebro). */}
            {rama && (
              <div className="absolute top-4 z-10 flex items-center gap-1 rounded-full border border-linea bg-crema/95 px-3 py-1.5 text-[0.76rem] font-semibold sombra-papel backdrop-blur"
                style={{ left: panelIzq ? "calc(var(--panel-w) + 2rem)" : "1rem" }}>
                <button onClick={() => { setRama(null); setNivel2(null); }} className="text-tinta-suave hover:text-tinta">{t("nav.mapa")}</button>
                <ChevronRight size={12} className="text-tinta-suave" />
                <button onClick={() => setNivel2(null)} className={nivel2 ? "text-tinta-suave hover:text-tinta" : "text-tinta"}>{t(DOMINIOS[rama].lk)}</button>
                {nivel2 && (<><ChevronRight size={12} className="text-tinta-suave" /><span className="text-tinta">{nivel2.etiqueta}</span></>)}
              </div>
            )}

            {/* la leyenda también se corre (y se acota) cuando el panel ocupa la
                izquierda: envuelve antes que meterse debajo */}
            <div className="absolute bottom-4 z-10 flex flex-wrap gap-3 rounded-full border border-linea bg-crema/95 px-3.5 py-1.5 sombra-papel backdrop-blur"
              style={panelIzq
                ? { left: "calc(var(--panel-w) + 2rem)", maxWidth: "calc(100% - var(--panel-w) - 3rem)" }
                : { left: "1rem", maxWidth: "calc(100% - 2rem)" }}>
              {[["producto", t("mapa.leyenda_producto")], ["plata", t("mapa.leyenda_plata")], ["senal", t("mapa.leyenda_senal")]].map(([k, l]) => (
                <span key={k} className="flex items-center gap-1.5 text-[0.7rem] font-semibold text-tinta-suave">
                  <span className="h-0.5 w-4 rounded-full" style={{ background: COLOR_RELACION[k] }} /> {l}
                </span>
              ))}
              <span className="flex items-center gap-1.5 text-[0.7rem] font-semibold text-violeta">
                <span className="h-0.5 w-4 rounded-full" style={{ background: AZUL_IA }} /> {t("mapa.leyenda_camino")}
              </span>
              <span className="flex items-center gap-1.5 text-[0.7rem] font-semibold" style={{ color: K_COLOR }}>
                <span className="h-0 w-4 border-t-2 border-dashed" style={{ borderColor: K_COLOR }} /> {t("mapa.leyenda_conocimiento")}
              </span>
              <span className="text-[0.7rem] text-tinta-suave/70">{t("mapa.pista_expandir")}</span>
            </div>

            {/* P40·3 — el acceso a la vista completa. Arriba a la derecha del
                lienzo, lejos de los controles de zoom (que son otra cosa). */}
            <button onClick={() => setCompleto(true)}
              className="absolute right-4 top-4 z-10 inline-flex items-center gap-1.5 rounded-full border border-linea bg-crema/95 px-3.5 py-1.5 text-[0.76rem] font-semibold text-tinta-suave sombra-papel backdrop-blur hover:text-tinta">
              <Expand size={14} /> {t("mapa.ver_completo")}
            </button>

            <ReactFlowProvider>
              <Lienzo modelo={modelo} rama={rama} nivel2={nivel2} extras={extras}
                pistaNodo={pistaNodo}
                onExpandir={expandir} onExpandirSub={expandirSub}
                onSeleccion={seleccionar} onSeleccionSub={seleccionarSub}
                onSeleccionMemoria={seleccionarMemoria}
                camino={camino} t={t} />
            </ReactFlowProvider>

            {/* P42·fix — EL PANEL DEL NODO, adentro del lienzo y sobre el lado
                izquierdo. Anclado top/bottom: usa el alto del mapa (no el sobrante
                de una columna) y scrollea adentro. z-20 = por encima del canvas y
                de las chapas del lienzo, y lejos del zoom (abajo a la derecha). */}
            {panelIzq && (
              <div className="absolute bottom-4 left-4 top-4 z-20" style={{ width: "var(--panel-w)" }}>
                <ErrorBoundary key={"panel:" + (panelIzq.esMemory ? "mem"
                  : panelIzq.esHallazgo ? "hall:" + (panelIzq.h?.id || "") : "nodo:" + (panelIzq.id || ""))}>
                  <InsightNodo insight={panelIzq} onNavegar={onNavegar} onPreguntar={onPreguntar}
                    onCerrar={() => setPanelIzq(null)} flotante />
                </ErrorBoundary>
              </div>
            )}
          </div>
        </div>

        {/* P40·3 — EL MAPA COMPLETO: el mismo grafo con más aire y los CORTES de
            las 8 fuentes desplegados. Overlay, no otra sección: se cierra y el
            mapa de siempre queda exactamente como estaba. */}
        {completo && (
          <div className="fixed inset-0 z-50 flex flex-col bg-papel">
            <div className="flex shrink-0 items-center gap-3 border-b border-linea px-5 py-3">
              <Waypoints size={18} className="text-hielo" />
              <div className="min-w-0 flex-1">
                <h2 className="font-display text-[1.05rem] font-bold leading-tight">{t("mapa.completo_titulo")}</h2>
                <p className="truncate text-[0.8rem] text-tinta-suave">{t("mapa.completo_sub")}</p>
              </div>
              <button onClick={() => setCompleto(false)}
                className="inline-flex items-center gap-1.5 rounded-full border border-linea px-3.5 py-1.5 text-[0.8rem] font-semibold text-tinta-suave hover:text-tinta">
                <X size={14} /> {t("mapa.completo_cerrar")}
              </button>
            </div>
            <div className="relative min-h-0 flex-1">
              <ReactFlowProvider>
                <Lienzo modelo={modelo} rama={rama} nivel2={nivel2} extras={extras}
                  pistaNodo={null} completo
                  onExpandir={expandir} onExpandirSub={expandirSub}
                  onSeleccion={seleccionar} onSeleccionSub={seleccionarSub}
                  onSeleccionMemoria={seleccionarMemoria}
                  onCorte={irACorte}
                  camino={camino} t={t} />
              </ReactFlowProvider>
            </div>
          </div>
        )}

        {/* LA FILA DE ABAJO (P29·C4 → P34·1): lo que el cerebro produjo. Cada
            tile APILA label / número / contexto; el contexto envuelve hasta 2
            líneas (line-clamp-2, break-words) — NUNCA se corta con "…". */}
        <div className="mt-3 grid grid-cols-2 items-stretch gap-2.5 xl:grid-cols-4">
          {/* E3·6 — "Lo que me enseñaste" reemplaza a "Conexiones" (que se mudó a
              El pulso). Abre el panel completo, filtrable por tipo y por nodo. */}
          <button onClick={() => setPanelK(true)}
            className="card-hover flex flex-col rounded-[var(--radius-card)] border bg-crema px-3.5 py-2.5 text-left sombra-papel"
            style={{ borderColor: `${K_COLOR}55` }}>
            <p className="flex items-center gap-1.5 text-[0.64rem] font-semibold uppercase tracking-wide" style={{ color: K_COLOR }}>
              <GraduationCap size={12} /> {t("mapa.fila_ensenaste")}
            </p>
            <p className="plata mt-0.5 text-xl font-medium leading-none">
              {num(modelo.conocimiento.total)} <span className="text-[0.7rem] font-normal text-tinta-suave">· {num(modelo.conocimiento.aplicadasHoy)} {t("mapa.k_aplicadas_hoy")}</span>
            </p>
            <p className="mt-1 line-clamp-3 break-words text-[0.66rem] leading-snug text-tinta-suave">{t("mapa.fila_ensenaste_sub", { total: modelo.conocimiento.total, hoy: modelo.conocimiento.aplicadasHoy })}</p>
          </button>
          <button onClick={() => top && verHallazgo(top)}
            className="card-hover flex flex-col rounded-[var(--radius-card)] border border-linea bg-crema px-3.5 py-2.5 text-left sombra-papel">
            <p className="flex items-center gap-1.5 text-[0.64rem] font-semibold uppercase tracking-wide text-violeta"><Lightbulb size={12} /> {t("mapa.fila_hallazgos_t")}</p>
            <p className="plata mt-0.5 text-xl font-medium leading-none">{num(nAlertas)} + {num(nOps)}</p>
            <p className="mt-1 line-clamp-3 break-words text-[0.66rem] leading-snug text-tinta-suave">{top ? t("mapa.fila_hallazgos_top", { titulo: top.titulo }) : t("mapa.fila_hallazgos_sub")}</p>
          </button>
          {/* Capital recuperable: número + desglose (2 líneas si hace falta); la
              nota de exposición se conserva como tooltip + ícono info. */}
          <button onClick={() => recuperables[0] && verHallazgo(recuperables[0])}
            title={exposicion > 0 ? t("mapa.fila_exposicion", { monto: pesoCorto(exposicion) }) : ""}
            className="card-hover flex flex-col rounded-[var(--radius-card)] border border-linea bg-crema px-3.5 py-2.5 text-left sombra-papel">
            <p className="flex items-center gap-1.5 text-[0.64rem] font-semibold uppercase tracking-wide text-salvia">
              <Sparkles size={12} /> {t("mapa.fila_recuperable")}
              {exposicion > 0 && <Info size={11} className="text-tinta-suave/70" />}
            </p>
            <p className="plata mt-0.5 text-xl font-medium leading-none text-salvia">{pesoCorto(recuperable)}</p>
            <p className="mt-1 line-clamp-3 break-words text-[0.66rem] leading-snug text-tinta-suave">
              {recuperables.map((h) => `${t(`mapa.recc_${h.id}`)} ${pesoCorto(h.monto)}`).join(" · ")}
            </p>
          </button>
          <button onClick={() => onNavegar?.("panel")}
            className="card-hover flex flex-col rounded-[var(--radius-card)] border border-linea bg-crema px-3.5 py-2.5 text-left sombra-papel">
            <p className="flex items-center gap-1.5 text-[0.64rem] font-semibold uppercase tracking-wide text-tinta-suave"><AngelaMark size={12} /> {t("mapa.fila_hizo")}</p>
            <p className="plata mt-0.5 text-xl font-medium leading-none">{num(hechoN)}</p>
            <p className="mt-1 line-clamp-3 break-words text-[0.66rem] leading-snug text-tinta-suave">{t("mapa.fila_hizo_sub")}</p>
          </button>
        </div>
        </>
      ) : (
        <>
          {insightMobileH && (
            <div className="mb-3">
              <InsightNodo insight={insightMobileH} onNavegar={onNavegar}
                onPreguntar={onPreguntar} onCerrar={() => setInsightMobileH(null)} />
              {/* el camino, contado (sin canvas): la secuencia que lo produjo */}
              <p className="mt-1 px-1 text-[0.74rem] text-tinta-suave">
                {t("mapa.camino_textual")}: {(insightMobileH.h.camino || []).map((n) => t(DOMINIOS[n]?.lk || n)).join(" → ")} → 💡
              </p>
            </div>
          )}
          <MapaApilado modelo={modelo} seleccion={seleccionMobile}
            onSeleccion={(id) => seleccionar(id)} onNavegar={onNavegar}
            onPreguntar={onPreguntar} onVerHallazgo={verHallazgo} t={t} />
        </>
      )}
      {panelK && (
        <PanelConocimientoFull conocimiento={modelo.conocimiento} t={t}
          onNavegar={onNavegar} onCerrar={() => setPanelK(false)} />
      )}
    </div>
  );
}

function Cabecera({ t, modelo }) {
  const c = modelo?.conteos;
  return (
    <div className="mb-4">
      <h1 className="font-display text-2xl font-bold leading-none">{t("nav.mapa")}</h1>
      <p className="mt-1 text-[0.92rem] text-tinta-suave">{t("mapa.subtitulo")}</p>
      <div className="mt-2.5 flex items-center gap-2.5">
        <AngelaMark size={30} estado={modelo ? "idle" : "pensando"} />
        <p className="min-w-0 text-[0.86rem] leading-snug text-tinta">
          {c ? `${t("mapa.frase", { anios: num(c.anios), productos: num(c.productos), clientes: num(c.clientes), fuentes: num(c.fuentes) })} ${t("mapa.angela_cruces", { n: num(modelo.hallazgos.length) })}`
             : t("mapa.cargando")}
        </p>
      </div>
    </div>
  );
}

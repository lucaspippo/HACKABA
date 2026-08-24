// P39·2 — LA VISTA-HERRAMIENTA DE CADA ROL.
//
// Cuando un empleado entra (o el dueño usa "Ver como"), aterriza en SU pantalla
// de trabajo, no en un dashboard de monitoreo ni en un chat vacío. Cada rol
// declara acá cuatro cosas:
//   (a) tareas   — qué tiene que hacer hoy (se DERIVAN de datos reales, ver piso.js)
//   (b) acciones — los botones con los que hace su trabajo
//   (c) chips    — las preguntas típicas de su oficio, pre-cargadas para Ángela
//   (d) lo que reporta hacia arriba — cada acción de tipo "reporte" entra al
//       sistema atribuida a la persona y el dueño la ve en su panel (ver Parte 3)
//
// COHERENCIA CON «QUIÉN VE QUÉ»: cada acción y cada chip declara los features
// que necesita. Si el rol no los tiene habilitados en la matriz, eso no se
// muestra — la vista nunca ofrece algo que la matriz no permite. Si el dueño le
// habilita un módulo, aparece solo.
//
// El rol se lee del TEXTO del rol (el del seed), no de una lista de usernames:
// una persona nueva con el mismo rol hereda su vista sin tocar código.

// El orden importa: "Encargado de depósito" es depósito, no sucursal.
const CATALOGO = [
  {
    id: "administracion",
    match: /administraci/i,
    acciones: [
      // Va por el flujo REAL de documentos (Ángela lo arma y deja la tarjeta de
      // descarga en el chat) — el mismo que la grilla de Documentos, no uno paralelo.
      { id: "reporte_cierres", icon: "FileText", need: ["documentos"], kind: "angela",
        pregunta: "documentos.card_cierres_enviar", destaca: true },
      { id: "aplicar_pago", icon: "HandCoins", need: ["cuentas"], kind: "navegar", a: "cuentas" },
    ],
    chips: [
      { k: "rol.chip_cierres_hoy", need: ["caja"] },
      { k: "rol.chip_entro_semana", need: ["caja"] },
      { k: "rol.chip_quien_debe", need: ["cuentas"] },
    ],
  },
  {
    id: "compras",
    match: /compras/i,
    acciones: [
      { id: "preparar_oc", icon: "ClipboardList", need: ["oportunidades"], kind: "navegar",
        a: "oportunidades", destaca: true },
      { id: "ver_ofertas", icon: "Tag", need: ["oportunidades"], kind: "navegar", a: "oportunidades" },
    ],
    chips: [
      { k: "rol.chip_por_quebrar", need: ["inventario"] },
      { k: "rol.chip_cuanto_vendemos", need: ["inventario"] },
      { k: "rol.chip_oferta_conviene", need: ["inventario"] },
    ],
  },
  {
    id: "deposito",
    match: /dep[oó]sito/i,
    voz: true,
    acciones: [
      { id: "cargar_remito", icon: "Camera", need: ["cargar"], kind: "navegar", a: "cargar",
        destaca: true },
      { id: "reportar_faltante", icon: "TriangleAlert", need: ["deposito"], kind: "reporte",
        tipo: "faltante" },
      { id: "marcar_conteo", icon: "ListChecks", need: ["deposito"], kind: "reporte",
        tipo: "conteo" },
    ],
    chips: [
      { k: "rol.chip_donde_esta", need: ["deposito"] },
      { k: "rol.chip_ultimo_remito", need: ["cargar"] },
      { k: "rol.chip_negativos", need: ["inventario"] },
    ],
  },
  {
    id: "reparto",
    match: /reparto|chofer|cami[oó]n/i,
    voz: true,
    acciones: [
      { id: "mi_ruta", icon: "Truck", need: ["logistica"], kind: "navegar", a: "logistica",
        destaca: true },
      { id: "confirmar_entrega", icon: "PackageCheck", need: ["logistica"], kind: "reporte",
        tipo: "entrega" },
      { id: "reportar_faltante", icon: "TriangleAlert", need: ["deposito"], kind: "reporte",
        tipo: "faltante" },
    ],
    chips: [
      { k: "rol.chip_unidades_bajo", need: ["logistica"] },
      { k: "rol.chip_falta_entregar", need: ["logistica"] },
    ],
  },
  {
    id: "preventa",
    match: /preventista|vendedor/i,
    acciones: [
      { id: "plazo_seguro", icon: "ShieldCheck", need: ["cuentas"], kind: "angela",
        pregunta: "rol.chip_plazo", destaca: true },
      { id: "registrar_pedido", icon: "ClipboardList", need: ["cuentas"], kind: "reporte",
        tipo: "pedido" },
    ],
    chips: [
      { k: "rol.chip_plazo", need: ["cuentas"] },
      { k: "rol.chip_al_dia", need: ["cuentas"] },
      { k: "rol.chip_precio_actual", need: ["inventario"] },
    ],
  },
  {
    id: "mostrador",
    match: /mostrador/i,
    voz: true,
    acciones: [
      { id: "precio_pesable", icon: "Scale", need: ["inventario"], kind: "angela",
        pregunta: "rol.chip_pesable_actualizado", destaca: true },
      { id: "stock_local", icon: "Boxes", need: ["inventario"], kind: "angela",
        pregunta: "rol.chip_tenemos_stock" },
    ],
    chips: [
      { k: "rol.chip_cambio_precio", need: ["inventario"] },
      { k: "rol.chip_tenemos_stock", need: ["inventario"] },
      { k: "rol.chip_pesable_actualizado", need: ["inventario"] },
    ],
  },
  {
    id: "sucursal",
    match: /sucursal/i,
    voz: true,
    acciones: [
      { id: "cierre_local", icon: "Wallet", need: ["caja"], kind: "navegar", a: "caja",
        destaca: true },
      { id: "pedir_reposicion", icon: "PackagePlus", need: ["inventario"], kind: "reporte",
        tipo: "reposicion" },
    ],
    chips: [
      { k: "rol.chip_venta_local", need: ["caja"] },
      { k: "rol.chip_falta_reponer", need: ["inventario"] },
      { k: "rol.chip_contra_mes", need: ["caja"] },
    ],
  },
];

/** El rol-herramienta de una persona (null = el dueño, que tiene su propio panel). */
export function rolDe(user) {
  if (!user || user.es_admin) return null;
  const texto = user.rol || "";
  return CATALOGO.find((r) => r.match.test(texto)) || null;
}

/** ¿Esta persona aterriza en su vista de trabajo? */
export function tieneVistaHerramienta(user) {
  return rolDe(user) != null;
}

const tieneFeats = (user, need) =>
  (need || []).every((f) => (user?.features || []).includes(f));

/** Las acciones que este rol puede USAR de verdad (según «Quién ve qué»). */
export function accionesDe(user) {
  const r = rolDe(user);
  if (!r) return [];
  return r.acciones.filter((a) => tieneFeats(user, a.need));
}

/** P44·A2 — ¿este rol REPORTA por voz desde el piso?
 *
 *  Hay dos usos distintos de la misma voz, y conviene no confundirlos:
 *
 *    · CONSULTAR — "¿cuánta plata tengo parada?". Eso lo quiere cualquiera, y
 *      por eso el micrófono del chat de Ángela no tiene gate: está para todos,
 *      del dueño para abajo. No hace falta preguntar nada acá.
 *
 *    · REPORTAR — "llegaron ocho cajas falladas". Eso es trabajo de piso: entra
 *      por `piso.reportar` y termina en una propuesta que alguien aprueba. Sólo
 *      tiene sentido para quien está parado frente a la mercadería, y por eso el
 *      botón de voz de la vista de trabajo sí se pregunta por el rol.
 *
 *  Sale del rol y no de una feature porque no es un permiso: es una forma de
 *  trabajar. El motor ya los contemplaba a todos (`core/voz.py` habla de
 *  "depósito, reparto y mostrador"; `entrega` y `reposicion` son sus intenciones). */
export function reportaPorVoz(user) {
  return !!rolDe(user)?.voz;
}

/** Las preguntas pre-cargadas de su oficio (sólo las que su rol puede responder). */
export function chipsDe(user) {
  const r = rolDe(user);
  if (!r) return [];
  return r.chips.filter((c) => tieneFeats(user, c.need));
}

/** Los campos de cada formulario de reporte: qué le pedimos al que está parado
 *  en el depósito o arriba del camión. Corto — se completa con una mano. */
export const CAMPOS_REPORTE = {
  faltante: [
    { id: "producto", lk: "rol.f_producto", tipo: "texto", requerido: true },
    { id: "cantidad", lk: "rol.f_cantidad", tipo: "numero", requerido: true },
    { id: "motivo", lk: "rol.f_motivo", tipo: "opciones",
      opciones: [
        { v: "roto", lk: "rol.motivo_roto" },
        { v: "faltante", lk: "rol.motivo_faltante" },
        { v: "vencido", lk: "rol.motivo_vencido" },
        { v: "no_pedido", lk: "rol.motivo_no_pedido" },
      ] },
    { id: "nota", lk: "rol.f_nota", tipo: "texto" },
  ],
  conteo: [
    { id: "producto", lk: "rol.f_producto", tipo: "texto", requerido: true },
    { id: "contado", lk: "rol.f_contado", tipo: "numero", requerido: true },
    { id: "nota", lk: "rol.f_nota", tipo: "texto" },
  ],
  entrega: [
    { id: "cliente", lk: "rol.f_cliente", tipo: "texto", requerido: true },
    // P41·4 — la PRUEBA: foto del remito firmado (o de la mercadería entregada).
    // No es decorativa — es el respaldo del repartidor si el cliente después
    // dice que no recibió. Opcional: una entrega sin foto igual se confirma.
    { id: "prueba", lk: "rol.f_prueba", tipo: "foto" },
    { id: "nota", lk: "rol.f_nota_entrega", tipo: "texto" },
  ],
  reposicion: [
    { id: "producto", lk: "rol.f_producto", tipo: "texto", requerido: true },
    { id: "cantidad", lk: "rol.f_cantidad", tipo: "numero" },
    { id: "nota", lk: "rol.f_nota", tipo: "texto" },
  ],
  pedido: [
    { id: "cliente", lk: "rol.f_cliente", tipo: "texto", requerido: true },
    { id: "nota", lk: "rol.f_nota_pedido", tipo: "texto" },
  ],
};

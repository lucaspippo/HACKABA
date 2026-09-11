import { useState } from "react";
import {
  FileCheck2, Truck, FileText, Receipt, ShoppingCart, Tag, CheckCircle2,
  Wrench, Undo2, Sparkles, Zap, Clock, UserMinus, ChevronDown, ShieldCheck, Check,
} from "lucide-react";
import { useT } from "../lib/i18n";
import { num, pesoCorto } from "../lib/format";

// El feed de "lo que Ángela ya hizo" (P13 → P36·E2): cada acción es una
// CAPACIDAD distinta del producto, así que se nota — ícono propio por tipo,
// color semántico, fecha relativa (a la fecha congelada del tenant), agrupada
// por día, y el detalle real del audit al tocar. Compartido desktop/mobile.
// Los eventos vienen de /api/actividad (auditoría real); acá solo se presentan.

// Del slug de auditoría al texto humano y bilingüe del feed.
export function textoFeed(e, t) {
  const MAPA = {
    sanear_fantasma_custom: "inicio.feed_acc_fantasma",
    restaurar_version: "inicio.feed_acc_revertir",
    revertir_version: "inicio.feed_acc_revertir",
    revertir_normalizacion_nivel1: "inicio.feed_acc_revertir_norm",
    validacion_montos_ventas: "inicio.feed_acc_validacion",
    integrar_staging: "inicio.feed_acc_staging",
    crear_apartado: "inicio.feed_acc_apartado",
    corregir_precio_perdida: "inicio.feed_acc_perdida",
    cargar_remito: "inicio.feed_acc_remito",
    cargar_factura: "inicio.feed_acc_factura",
    cargar_recibo: "inicio.feed_acc_recibo",
    cargar_orden_compra: "inicio.feed_acc_oc",
  };
  if (MAPA[e.accion]) return t(MAPA[e.accion]);
  if (e.accion?.startsWith("sanear_"))
    return t("inicio.feed_acc_sanear", { cat: e.accion.slice(7).replace(/_/g, " ") });
  return t("inicio.feed_acc_generico", { accion: (e.accion || "").replace(/_/g, " ") });
}

// Ícono + color + "familia" por tipo de acción (P36·E2). La familia decide con
// qué contador se filtra (correccion / procesado).
const ICONO = {
  integrar_staging: { Icon: FileCheck2, tono: "text-salvia", bg: "bg-salvia/12", fam: "procesado" },
  cargar_remito: { Icon: Truck, tono: "text-hielo", bg: "bg-hielo/12", fam: "correccion" },
  cargar_factura: { Icon: FileText, tono: "text-hielo", bg: "bg-hielo/12", fam: "correccion" },
  cargar_recibo: { Icon: Receipt, tono: "text-salvia", bg: "bg-salvia/12", fam: "correccion" },
  cargar_orden_compra: { Icon: ShoppingCart, tono: "text-hielo", bg: "bg-hielo/12", fam: "correccion" },
  corregir_precio_perdida: { Icon: Tag, tono: "text-oro-tinta", bg: "bg-oro/15", fam: "correccion" },
  aplicar_lista_precios: { Icon: Tag, tono: "text-oro-tinta", bg: "bg-oro/15", fam: "correccion" },
  validacion_montos_ventas: { Icon: CheckCircle2, tono: "text-salvia", bg: "bg-salvia/12", fam: "correccion" },
  revertir_version: { Icon: Undo2, tono: "text-tinta-suave", bg: "bg-papel-hondo", fam: "correccion" },
  restaurar_version: { Icon: Undo2, tono: "text-tinta-suave", bg: "bg-papel-hondo", fam: "correccion" },
};
export function iconoDe(accion) {
  if (ICONO[accion]) return ICONO[accion];
  if (accion?.startsWith("sanear_")) return { Icon: Wrench, tono: "text-oro-tinta", bg: "bg-oro/15", fam: "correccion" };
  return { Icon: Sparkles, tono: "text-violeta", bg: "bg-violeta/10", fam: "correccion" };
}

// Fecha RELATIVA corta, contra la fecha congelada del tenant (no la real).
export function fechaRelativa(cuando, hoyISO, t) {
  const dia = (cuando || "").slice(0, 10);
  if (!dia) return "";
  const ref = hoyISO || dia;
  const d = new Date(dia + "T00:00:00"), h = new Date(ref + "T00:00:00");
  const dias = Math.round((h - d) / 86400000);
  if (dias <= 0) return t("feed.hoy");
  if (dias === 1) return t("feed.ayer");
  if (dias < 7) return t("feed.hace_dias", { n: dias });
  return dia;
}

// El detalle REAL del audit (antes/despues) en una frase: qué tocó y cuántos.
export function detalleFeed(e, t) {
  const a = e.detalle?.antes || {}, d = e.detalle?.despues || {};
  const partes = [];
  for (const k of ["casos", "productos", "filas", "registros"]) {
    if (typeof a[k] === "number" && typeof d[k] === "number")
      return t("feed.det_de_a", { antes: num(a[k]), despues: num(d[k]), que: t(`feed.u_${k}`) });
    if (typeof d[k] === "number") partes.push(t("feed.det_n", { n: num(d[k]), que: t(`feed.u_${k}`) }));
  }
  if (d.archivo) partes.push(d.archivo);
  if (d.proveedor) partes.push(d.proveedor);
  if (d.cliente) partes.push(d.cliente);
  return partes.join(" · ");
}
// Las correcciones/saneos crean versión → tienen respaldo y son reversibles.
export function esReversible(accion) {
  return accion?.startsWith("sanear_") || accion === "corregir_precio_perdida"
      || accion === "aplicar_lista_precios" || accion?.startsWith("revertir_");
}

function Fila({ e, hoyISO, t }) {
  const [abierto, setAbierto] = useState(false);
  const { Icon, tono, bg } = iconoDe(e.accion);
  const det = detalleFeed(e, t);
  const rev = esReversible(e.accion);
  return (
    <div className="border-b border-linea last:border-0">
      <button onClick={() => setAbierto((v) => !v)} className="flex w-full items-center gap-3 py-2.5 text-left">
        <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-full ${bg}`}>
          <Icon size={15} className={tono} />
        </span>
        <span className="min-w-0 flex-1 text-[0.9rem] leading-snug text-tinta">
          {textoFeed(e, t)}
          {e.veces > 1 && <span className="ml-1.5 text-[0.74rem] font-semibold text-tinta-suave">×{e.veces}</span>}
        </span>
        <span className="shrink-0 text-[0.74rem] text-tinta-suave" title={(e.cuando || "").slice(0, 10)}>
          {fechaRelativa(e.cuando, hoyISO, t)}
        </span>
        <ChevronDown size={15} className={`shrink-0 text-tinta-suave transition-transform ${abierto ? "rotate-180" : ""}`} />
      </button>
      {abierto && (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 pb-3 pl-10 text-[0.8rem] text-tinta-suave">
          {det && <span>{det}</span>}
          {rev && (
            <span className="inline-flex items-center gap-1 text-salvia">
              <ShieldCheck size={13} /> {t("feed.reversible")}
            </span>
          )}
          <span className="text-tinta-suave/70">{(e.cuando || "").slice(0, 10)}</span>
        </div>
      )}
    </div>
  );
}

// Bloque completo: contadores (chips clickeables que filtran) + lista agrupada
// por día. `compact` reduce paddings para el mobile.
export function FeedActividad({ act, estructura }) {
  const t = useT();
  const [filtro, setFiltro] = useState(null); // null | correccion | procesado | aviso
  const hoyISO = act?.hoy;
  const feed = act?.feed || [];

  const CHIPS = [
    { id: "correccion", n: act?.correcciones || 0, Icon: Zap,
      lk1: "inicio.ahorro_correcciones_l_1", lk: "inicio.ahorro_correcciones_l" },
    { id: "procesado", n: act?.staging_procesados || 0, Icon: Clock,
      lk1: "inicio.ahorro_staging_l_1", lk: "inicio.ahorro_staging_l" },
    { id: "aviso", n: act?.alertas_emitidas || 0, Icon: UserMinus,
      lk1: "inicio.ahorro_alertas_l_1", lk: "inicio.ahorro_alertas_l" },
  ];
  const visibles = filtro
    ? feed.filter((e) => (filtro === "aviso" ? false : iconoDe(e.accion).fam === filtro))
    : feed;

  const grupos = [];
  for (const e of visibles) {
    const dia = (e.cuando || "").slice(0, 10);
    let g = grupos.find((x) => x.dia === dia);
    if (!g) { g = { dia, items: [] }; grupos.push(g); }
    g.items.push(e);
  }

  return (
    <div>
      {/* P41·2.1 — ESTRUCTURACIÓN SILENCIOSA. Que Ángela "descubra" que Sucursal
          Norte es un local propio no es un hallazgo: el dueño ya lo sabe. Lo que
          sí vale contar es el trabajo que hizo con eso — separar los traslados
          internos de la venta real para que los rankings no mientan. Va acá,
          como limpieza HECHA, no como novedad que se anuncia. */}
      {estructura?.disponible && estructura.locales?.length > 0 && (
        <div className="mb-2 flex items-start gap-2 rounded-xl border border-hielo/25 bg-hielo/[0.05] px-3 py-2">
          <Check size={14} className="mt-0.5 shrink-0 text-hielo" />
          <p className="text-[0.8rem] leading-snug text-tinta">
            {t("feed.estructura_locales", {
              n: num(estructura.locales.length),
              monto: pesoCorto(estructura.total_12m || 0),
            })}
          </p>
        </div>
      )}

      <div className="mb-1 flex flex-wrap gap-1.5">
        {CHIPS.map((c) => (
          <button
            key={c.id}
            onClick={() => setFiltro(filtro === c.id ? null : c.id)}
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[0.74rem] font-semibold transition-colors ${
              filtro === c.id ? "border-violeta bg-violeta/[0.06] text-violeta" : "border-linea text-tinta-suave hover:text-tinta"
            }`}
          >
            <c.Icon size={12} className={filtro === c.id ? "text-violeta" : "text-salvia"} />
            {num(c.n)} {t(c.n === 1 ? c.lk1 : c.lk)}
          </button>
        ))}
      </div>

      {filtro === "aviso" ? (
        <p className="px-1 py-4 text-center text-[0.85rem] text-tinta-suave">{t("feed.avisos_bandeja")}</p>
      ) : visibles.length === 0 ? (
        <p className="px-1 py-4 text-center text-[0.85rem] text-tinta-suave">{t("feed.sin_resultados")}</p>
      ) : (
        grupos.map((g) => (
          <div key={g.dia}>
            <p className="mt-2 pb-0.5 text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-tinta-suave/70">
              {fechaRelativa(g.dia, hoyISO, t)}
            </p>
            {g.items.map((e, i) => <Fila key={`${e.accion}-${e.cuando}-${i}`} e={e} hoyISO={hoyISO} t={t} />)}
          </div>
        ))
      )}
    </div>
  );
}

// Compat: la fila plana anterior (aún referenciada por MapaNegocio).
export function FeedItem({ color, texto, cuando }) {
  return (
    <li className="flex items-start gap-3">
      <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${color}`} />
      <span className="flex-1 text-tinta">{texto}</span>
      <span className="shrink-0 text-[0.74rem] text-tinta-suave">{cuando}</span>
    </li>
  );
}

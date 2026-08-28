import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  TrendingUp, Bell, Sparkles, ClipboardList, ArrowRight, Clock, Zap, UserMinus,
  AlertTriangle, Inbox, Lightbulb, ShieldCheck, Camera, FileText, MessageCircle,
} from "lucide-react";
import AngelaMark from "../../components/AngelaMark";
import StatusPill from "../../components/StatusPill";
import { FeedActividad } from "../../components/ActividadFeed";
import { armarDecisiones } from "../../lib/decisiones";
import { ALERTA_DEFS, ORDEN_ALERTAS, contarACorregir } from "../../lib/alertas";
import { useVista, vistaStore } from "../../lib/vistaStore";
import Widget from "../../components/Widget";
import { api } from "../../lib/api";
import { useSession, authStore } from "../../lib/auth";
import { useEmpresa } from "../../lib/useEmpresa";
import { fecha, pesoCorto, num } from "../../lib/format";
import { useT, useLang } from "../../lib/i18n";

// P13/P15: el Home es el resumen ejecutivo de la IA — en 5 segundos tiene que
// decir "Ángela ya trabajó por vos; esto es lo único importante de hoy".
// La fila de 4 tarjetas de arriba sigue la referencia de diseño; cada tarjeta
// sale de un dato real (alertas, cola de decisión, análisis cacheado, salud).
// Nada se inventa: sin dato real no hay tarjeta.

const MAX_DECISIONES = 4;

// P15·E3: en la fila de tarjetas los detalles largos se recortan a la PRIMERA
// frase (edición, no elipsis) — el texto completo vive en Oportunidades.
const primeraFrase = (s) => {
  if (!s) return s;
  const i = s.indexOf(". ");
  return i > 0 ? s.slice(0, i + 1) : s;
};

// Tonos de las tarjetas del resumen: un color, un significado.
const TONO = {
  rojo: { chip: "bg-rojo/10 text-rojo", monto: "text-rojo", icono: "bg-rojo/10 text-rojo", cta: "border-rojo/30 text-rojo hover:bg-rojo hover:text-crema" },
  oro: { chip: "bg-oro/15 text-oro-tinta", monto: "text-oro-tinta", icono: "bg-oro/15 text-oro-tinta", cta: "border-oro/40 text-oro-tinta hover:bg-oro hover:text-crema" },
  salvia: { chip: "bg-salvia/12 text-salvia", monto: "text-salvia", icono: "bg-salvia/12 text-salvia", cta: "border-salvia/30 text-salvia hover:bg-salvia hover:text-crema" },
};

function CartaResumen({ c, t }) {
  const tono = TONO[c.tono];
  const Icon = c.icon;
  return (
    <div data-nav-id={c.navId} className="card-hover flex flex-col rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
      <div className="flex items-center justify-between gap-2">
        <span className={`rounded-full px-2.5 py-1 text-[0.88rem] font-semibold ${tono.chip}`}>{c.chip}</span>
        {c.n != null && (
          <span className={`grid h-5 min-w-5 place-items-center rounded-full px-1 text-[0.88rem] font-bold ${tono.chip}`}>{num(c.n)}</span>
        )}
      </div>
      {/* P15·E3: el título envuelve completo (nada cortado en cámara); el
          clamp-3 del detalle es red de seguridad — el copy se acorta para
          no llegar nunca a él. */}
      <p className="mt-2.5 font-display text-[1.02rem] font-bold leading-tight">{c.titulo}</p>
      {c.detalle && <p className="mt-1 line-clamp-3 text-[0.86rem] leading-snug text-tinta-suave">{c.detalle}</p>}
      <div className="mt-auto flex items-end justify-between gap-2 pt-3">
        <div className="min-w-0">
          {c.monto != null && c.monto > 0 && (
            <>
              <p className="text-[0.88rem] text-tinta-suave">{t("inicio.card_impacto")}</p>
              <p className={`plata text-xl font-medium leading-tight ${tono.monto}`}>{pesoCorto(c.monto)}</p>
            </>
          )}
        </div>
        <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-2xl ${tono.icono}`}>
          <Icon size={19} />
        </span>
      </div>
      {c.ir && (
        <button onClick={c.ir} className={`mt-3 inline-flex items-center gap-1.5 self-start rounded-full border px-3.5 py-1.5 text-[0.88rem] font-semibold transition-colors ${tono.cta}`}>
          {c.cta} <ArrowRight size={13} />
        </button>
      )}
    </div>
  );
}

export default function Inicio({ data, oportunidades, onNavegar, onPreguntar }) {
  const t = useT();
  const session = useSession();
  const nombre = session?.usuario?.nombre || t("inicio.nombre_fallback");
  const { resumen, alertas, top_inmovilizado } = data;
  const vista = useVista();
  // P38·A — la MISMA cuenta que el badge del sidebar y el filtro del stock.
  const datosACorregir = contarACorregir(data);
  // Mora real solo si el rol tiene la feature (sin "0" mentiroso, P9·C2).
  // morosos=null significa "todavía no sé" (cargando o fetch caído): la
  // métrica muestra "—", jamás un 0 inventado (P15·E1).
  const tieneCuentas = authStore.tiene("cuentas");
  const [morosos, setMorosos] = useState(null);
  useEffect(() => {
    if (!tieneCuentas) return;
    api.cuentas().then((d) => setMorosos(d.alertas)).catch(() => {});
  }, [tieneCuentas]);
  // El resumen ejecutivo: una sola llamada al agregador. Atada al token (el
  // relogin silencioso tras un reinicio la reintenta, B8) y al idioma (los
  // labels del backend vienen ya localizados y hay que repedirlos).
  // Si falla, reintenta solo cada 4s y el Home LO DICE — un feed vacío por
  // fetch caído no es información, es mentira accidental (P15·E1).
  const lang = useLang();
  const [ini, setIni] = useState(null);
  const [iniError, setIniError] = useState(false);
  useEffect(() => {
    let vivo = true;
    let timer;
    const pedir = () =>
      api.inicio()
        .then((d) => { if (!vivo) return; setIni(d); setIniError(false); })
        .catch(() => { if (!vivo) return; setIniError(true); timer = setTimeout(pedir, 4000); });
    pedir();
    return () => { vivo = false; clearTimeout(timer); };
  }, [session?.token, lang]);
  const act = ini?.actividad;
  // P41·2.1 — la separación de locales propios ya no es alerta: es trabajo
  // hecho, y se cuenta en el feed. Endpoint chico, sin bloquear el render.
  const [estructura, setEstructura] = useState(null);
  useEffect(() => {
    if (!authStore.tiene("inventario")) return;
    api.traslados().then(setEstructura).catch(() => {});
  }, []);
  const iniCargando = !ini && !iniError;
  // 5ª KPI (P17·E3): rotación promedio — ya viaja calculada en el cache de
  // /api/analisis; solo se muestra si está disponible (ventas validadas).
  const [rotDias, setRotDias] = useState(null);
  useEffect(() => {
    if (!authStore.tiene("oportunidades")) return;
    api.analisis()
      .then((a) => { if (a?.rotacion?.disponible && a.rotacion.dias_promedio != null) setRotDias(Math.round(a.rotacion.dias_promedio)); })
      .catch(() => {});
  }, []);
  const [prio, setPrio] = useState(null);
  useEffect(() => {
    if (!authStore.tiene("alertas") && !authStore.tiene("oportunidades")) return;
    api.prioridades().then(setPrio).catch(() => {});
  }, [session?.token, lang]);

  // --- La cola de decisión: staging + propuestas del libro + solicitudes ---
  const decisiones = armarDecisiones(ini, t).map((d) => ({
    ...d,
    cta: d.tipo.startsWith("calidad") ? t("inicio.dec_ver_propuesta") : t("inicio.dec_revisar"),
    ir: d.tipo === "staging"
      ? () => onNavegar("pendientes")
      : d.tipo === "calidad"
      ? () => onNavegar("saneamiento", d.categoria)
      // agrupada (F·3): lleva a la sección entera, donde están las dos juntas
      : d.tipo === "calidad_agrupada"
      ? () => onNavegar("saneamiento")
      : () => onNavegar("equipo", "solicitudes"),
  }));

  const ops = (prio?.act || []).map((o) => ({
    id: o.id, titulo: o.titulo, detalle: o.resumen, monto: o.monto,
  }));

  // --- La fila de la referencia: hasta 4 tarjetas, cada una con dato real ---
  const cartas = [];
  const problemaTop = ORDEN_ALERTAS
    .map((g) => ({ g, def: ALERTA_DEFS[g], stat: alertas[g] }))
    .find((x) => x.def.tono === "urgente" && x.stat?.cantidad > 0);
  if (problemaTop) {
    cartas.push({
      id: "atencion", tono: "rojo", chip: t("inicio.card_atencion"), n: problemaTop.stat.cantidad,
      titulo: t(problemaTop.def.titulo), detalle: t(problemaTop.def.resumen),
      monto: problemaTop.stat.impacto_pesos, icon: AlertTriangle,
      cta: t("inicio.card_resolver"), ir: () => onNavegar("inventario", problemaTop.g),
    });
  }
  if (decisiones.length > 0) {
    const d = decisiones[0];
    cartas.push({
      id: "decision", tono: "oro", chip: t("decision.espera_ok"), n: decisiones.length,
      titulo: d.titulo, detalle: d.detalle, monto: d.monto, icon: Inbox, cta: d.cta, ir: d.ir,
      navId: "decisiones", // la esfera del sidebar navega ACÁ cuando espera tu OK
    });
  }
  for (const [i, o] of ops.entries()) {
    if (cartas.length >= 4) break;
    cartas.push({
      id: `op-${o.id}`, tono: "salvia",
      chip: i === 0 ? t("inicio.card_oportunidad") : t("inicio.card_seguimiento"),
      titulo: o.titulo, detalle: primeraFrase(o.detalle), monto: o.monto,
      icon: i === 0 ? Lightbulb : TrendingUp,
      cta: t("inicio.card_ver_analisis"), ir: () => onNavegar("prioridades"),
    });
  }
  const opsUsadas = cartas.filter((c) => c.id.startsWith("op-")).length;
  // La tarjeta de estado solo entra si sobra lugar: cuando el día está cargado,
  // los 4 slots son contenido real; cuando está tranquilo, cierra la fila con
  // el estado honesto ("Todo bajo control" solo si de verdad no hay pendientes).
  // P29·A — y SOLO si hay salud: un rol sin inventario recibe el esqueleto
  // dataSinInventario (resumen sin salud) — sin dato no hay tarjeta de estado.
  if (cartas.length < 4 && resumen.salud) {
    const todoEnOrden = resumen.salud.nivel === "en_orden" && cartas.every((c) => c.tono === "salvia");
    cartas.push({
      id: "estado",
      tono: resumen.salud.nivel === "en_orden" ? "salvia" : resumen.salud.nivel === "atencion" ? "oro" : "rojo",
      chip: t("inicio.card_estado"),
      titulo: todoEnOrden ? t("inicio.card_estado_ok") : resumen.salud.label,
      detalle: todoEnOrden ? t("inicio.card_estado_detalle") : t("inicio.card_estado_mirar"),
      icon: ShieldCheck,
      cta: (authStore.tiene("alertas") || authStore.tiene("oportunidades")) ? t("inicio.card_ver_alertas") : null,
      ir: (authStore.tiene("alertas") || authStore.tiene("oportunidades")) ? () => onNavegar("prioridades") : null,
    });
  }
  const fila = cartas.slice(0, 4);
  const decisionesRestantes = decisiones.slice(1);
  const opsRestantes = ops.slice(opsUsadas, opsUsadas + 3);

  const metricas = [
    { label: t("inicio.metrica_inmovilizado"), valor: pesoCorto(resumen.inmovilizado_total), icon: TrendingUp, color: "text-hielo", sec: "inventario", hl: "plata" },
    { label: t("inicio.metrica_corregir"), valor: num(datosACorregir), icon: ClipboardList, color: "text-oro-tinta", sec: "saneamiento" },
    tieneCuentas
      ? { label: t("inicio.metrica_mora"), valor: morosos ? num(morosos.cantidad) : "—", icon: Bell, color: morosos?.cantidad ? "text-rojo" : "text-tinta-suave", sec: "cuentas" }
      : { label: t("inicio.metrica_mora_bloqueada"), valor: "—", icon: Bell, color: "text-tinta-suave", sec: "cuentas" },
    { label: t("inicio.metrica_oportunidades"), valor: num(prio?.badge ?? ops.length), icon: Sparkles, color: "text-salvia", sec: "prioridades" },
    ...(rotDias != null
      ? [{ label: t("inicio.metrica_rotacion"), valor: num(rotDias), icon: Clock, color: "text-hielo", sec: "prioridades" }]
      : []),
  ];

  const accesos = [
    authStore.tiene("cargar") && { icon: Camera, lk: "inicio.acceso_foto", ir: () => onNavegar("cargar") },
    authStore.tiene("documentos") && { icon: FileText, lk: "inicio.acceso_doc", ir: () => onNavegar("documentos") },
    (ini?.staging?.batches?.length || 0) > 0 && { icon: Inbox, lk: "nav.pendientes", ir: () => onNavegar("pendientes") },
    { icon: MessageCircle, lk: "inicio.preguntar_angela", ir: () => onPreguntar(t("inicio.enviar_empezar")) },
  ].filter(Boolean).slice(0, 4);

  // P19·B — el Home en BLOQUES con orden por usuario: Ángela lo reordena por
  // chat ("las oportunidades arriba de las decisiones") y queda persistido en
  // su memoria del servidor. El catálogo es cerrado (estos 6 y nada más) y el
  // orden inválido cae al default sin romper nada.
  // P24·C1 — default del TENANT DEMO: "lo que Ángela ya hizo" ARRIBA de la cola
  // de decisión (decisión de producto). El reorden por chat sigue mandando.
  const { erpSimulado } = useEmpresa();
  const ORDEN_DEFAULT = erpSimulado
    ? ["cards", "feed", "decisiones", "oportunidades", "metricas", "plata"]
    : ["cards", "decisiones", "oportunidades", "feed", "metricas", "plata"];
  const orden = Array.isArray(vista.ordenHome) &&
    [...vista.ordenHome].sort().join() === [...ORDEN_DEFAULT].sort().join()
    ? vista.ordenHome : ORDEN_DEFAULT;

  const bloqueCards = (
    /* La fila de tarjetas: lo único importante de hoy, con su $. El corte a
       4 columnas es por viewport REAL (con el panel de Ángela abierto, 4
       columnas solo respiran de ~1700px para arriba). */
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 3xl:grid-cols-4">
      {fila.map((c) => <CartaResumen key={c.id} c={c} t={t} />)}
    </div>
  );

  const bloqueDecisiones = decisionesRestantes.length > 0 && (
        <section>
          {/* P42 — jerarquía: la fila de tarjetas es el único bloque "grande"
              del Home; todo lo demás usa el mismo eyebrow chico, para que no
              compitan en volumen visual con lo único importante de hoy. */}
          <h2 className="mb-3 text-[0.88rem] font-semibold uppercase tracking-[0.1em] text-tinta-suave">{t("inicio.dec_titulo")}</h2>
          <div className="space-y-3">
            {decisionesRestantes.slice(0, MAX_DECISIONES - 1).map((d) => (
              <div key={d.id} className="flex flex-wrap items-center gap-4 rounded-[var(--radius-card)] border border-oro/30 bg-crema p-5 sombra-papel">
                <div className="min-w-0 flex-1">
                  <p className="font-display text-[1.02rem] font-bold leading-tight">{d.titulo}</p>
                  <p className="mt-0.5 text-[0.9rem] text-tinta-suave">{d.detalle}</p>
                </div>
                {d.monto != null && (
                  <span className="plata shrink-0 text-xl font-medium text-tinta">{pesoCorto(d.monto)}</span>
                )}
                <button onClick={d.ir} className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-[0.88rem] font-semibold text-crema">
                  {d.cta} <ArrowRight size={14} />
                </button>
              </div>
            ))}
            {decisionesRestantes.length > MAX_DECISIONES - 1 && (
              <button onClick={() => onNavegar("saneamiento")} className="text-[0.88rem] font-semibold text-tinta">
                {t("inicio.dec_ver_todas")} →
              </button>
            )}
          </div>
        </section>
  );

  const bloqueOportunidades = opsRestantes.length > 0 && (
        <section>
          <div className="mb-3 flex items-baseline justify-between">
            <h2 className="text-[0.88rem] font-semibold uppercase tracking-[0.1em] text-tinta-suave">{t("inicio.op_titulo")}</h2>
            <button onClick={() => onNavegar("prioridades")} className="text-[0.88rem] font-semibold text-tinta">{t("inicio.ver_todo")}</button>
          </div>
          <div className="space-y-2">
            {opsRestantes.map((o) => (
              <button
                key={o.id}
                onClick={() => onNavegar("prioridades")}
                className="flex w-full flex-wrap items-center gap-4 rounded-[var(--radius-card)] border border-linea bg-crema p-4 text-left sombra-papel transition-colors hover:border-tinta/25"
              >
                {o.monto != null && (
                  <span className="plata shrink-0 text-xl font-medium text-salvia">{pesoCorto(o.monto)}</span>
                )}
                <span className="min-w-0 flex-1 text-[0.92rem] font-semibold leading-snug text-tinta">{o.titulo}</span>
                <ArrowRight size={15} className="shrink-0 text-tinta-suave" />
              </button>
            ))}
          </div>
        </section>
  );

  const bloqueFeed = (
      /* Lo que Ángela ya hizo: el feed REAL de auditoría, con la esfera */
      <section>
        <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-5 sombra-papel">
          <div className="mb-3 flex items-center gap-3">
            <AngelaMark size={34} estado={decisiones.length > 0 ? "esperando" : "idle"} />
            <h2 className="flex-1 text-[0.88rem] font-semibold uppercase tracking-[0.1em] text-tinta-suave">{t("inicio.hizo_titulo")}</h2>
          </div>
          {iniError ? (
            <p className="text-[0.95rem] font-medium text-rojo-hondo">{t("inicio.error_datos")}</p>
          ) : iniCargando ? (
            /* Skeleton con la forma del feed: cero salto de layout */
            <ul className="space-y-3">
              {[0, 1, 2].map((i) => (
                <li key={i} className="flex items-center gap-3">
                  <span className="skeleton h-7 w-7 rounded-full" />
                  <span className="skeleton h-3.5" style={{ width: `${72 - i * 14}%` }} />
                  <span className="skeleton ml-auto h-3 w-14" />
                </li>
              ))}
            </ul>
          ) : (act?.feed || []).length > 0 ? (
            /* P36·E2 — el feed rediseñado: íconos por tipo, fecha relativa,
               agrupado por día, detalle al tocar, contadores clickeables. */
            <FeedActividad act={act} estructura={estructura} />
          ) : (
            <p className="text-[0.95rem] text-tinta-suave">{t("inicio.ahorro_vacio")}</p>
          )}
        </div>
      </section>
  );

  const bloqueMetricas = (
      /* Métricas en calma + accesos rápidos (solo acciones reales) */
      <div className={`grid grid-cols-2 gap-3 ${metricas.length >= 5 ? "lg:grid-cols-6" : "lg:grid-cols-5"}`}>
        {metricas.map((m) => {
          const Icon = m.icon;
          return (
            <button
              key={m.label}
              onClick={() => onNavegar(m.sec, m.hl)}
              className="flex flex-col rounded-[var(--radius-card)] border border-linea bg-crema p-4 text-left sombra-papel transition-transform hover:-translate-y-0.5"
            >
              <Icon size={16} className={m.color} />
              <p className={`plata mt-1.5 text-2xl font-medium leading-none ${m.color}`}>{m.valor}</p>
              <p className="mt-1 flex-1 text-[0.88rem] text-tinta-suave">{m.label}</p>
              <span className="mt-2 inline-flex items-center gap-1 self-start rounded-full border border-linea px-2.5 py-1 text-[0.88rem] font-semibold text-tinta-suave">
                {t("inicio.metrica_ver")} <ArrowRight size={11} />
              </span>
            </button>
          );
        })}
        <div className="col-span-2 rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel lg:col-span-1">
          <p className="text-[0.86rem] font-semibold uppercase tracking-wide text-tinta-suave">{t("inicio.accesos_titulo")}</p>
          <div className="mt-2 space-y-1">
            {accesos.map((a) => {
              const Icon = a.icon;
              return (
                <button key={a.lk} onClick={a.ir} className="flex w-full items-center gap-2.5 rounded-xl px-2 py-1.5 text-left transition-colors hover:bg-papel-hondo/60">
                  <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-violeta-suave text-violeta"><Icon size={14} /></span>
                  <span className="min-w-0 flex-1 truncate text-[0.88rem] font-medium">{t(a.lk)}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
  );

  const bloquePlata = (
      /* Dónde está la plata: compacto */
      <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-5 sombra-papel">
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="text-[0.88rem] font-semibold uppercase tracking-[0.1em] text-tinta-suave">{t("inicio.donde_plata")}</h2>
          <button onClick={() => onNavegar("inventario", "plata")} className="text-[0.88rem] font-semibold text-tinta">{t("inicio.ver_todo")}</button>
        </div>
        <div className="space-y-1.5">
          {top_inmovilizado.slice(0, vista.inicioTopN).map((p) => {
            const max = top_inmovilizado[0].inmovilizado || 1;
            const pct = Math.max(8, (p.inmovilizado / max) * 100);
            return (
              <div key={p.codigo} className="relative rounded-lg px-3 py-1.5">
                <div className="absolute inset-y-0 left-0 rounded-lg bg-oro/15" style={{ width: `${pct}%` }} />
                <div className="relative flex items-center justify-between gap-3">
                  <span className="truncate text-[0.88rem]">{p.descripcion}</span>
                  <span className="plata shrink-0 text-[0.88rem] font-medium text-hielo">{pesoCorto(p.inmovilizado)}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
  );

  const BLOQUES = {
    cards: bloqueCards,
    decisiones: bloqueDecisiones,
    oportunidades: bloqueOportunidades,
    feed: bloqueFeed,
    metricas: bloqueMetricas,
    plata: bloquePlata,
  };

  return (
    <div className="mx-auto max-w-[1280px] space-y-8">
      {/* 1 · Saludo, como la referencia: el día resumido en una frase */}
      <header className="flex items-end justify-between gap-4">
        <div className="min-w-0">
          <p className="text-[0.95rem] text-tinta-suave">{t("inicio.saludo", { nombre })}</p>
          <h1 className="mt-1 font-display text-[2.1rem] font-bold leading-tight">{t("inicio.hero_titulo")}</h1>
          <p className="mt-1 text-[0.95rem] text-tinta-suave">
            {fila.length > 1 ? t("inicio.hero_sub", { n: fila.length }) : t("inicio.hero_sub_uno")}
          </p>
          {iniError && (
            <p className="mt-2 inline-flex items-center gap-2 rounded-full border border-rojo/30 bg-rojo/[0.05] px-3 py-1 text-[0.88rem] font-semibold text-rojo-hondo">
              {t("inicio.error_datos")}
            </p>
          )}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-2 pb-1">
          {/* P29·A — la píldora de salud solo con el dato (rol sin inventario: nada) */}
          {resumen.salud && <StatusPill nivel={resumen.salud.nivel} label={resumen.salud.label} />}
          <button onClick={() => onPreguntar(t("inicio.enviar_empezar"))} className="text-[0.88rem] font-semibold text-violeta">
            {t("inicio.preguntar_angela")}
          </button>
        </div>
      </header>

      {/* P19·C — las cards que el dueño pidió fijas "arriba del Home" */}
      {(vista.widgets?.inicio || []).some((w) => w.posicion === "top") && (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          {vista.widgets.inicio.filter((w) => w.posicion === "top").map((w) => (
            <Widget key={w.id} widget={w} data={data} onQuitar={(id) => vistaStore.quitarWidget("inicio", id)} />
          ))}
        </div>
      )}

      {/* P19·B — los bloques en EL ORDEN del usuario, con animación sutil:
          motion layout mueve cada bloque a su lugar nuevo sin circo. */}
      {orden.map((id) => BLOQUES[id] && (
        <motion.div key={id} layout transition={{ type: "spring", stiffness: 350, damping: 32 }}>
          {BLOQUES[id]}
        </motion.div>
      ))}

      {/* Widgets que el dueño le pidió a Ángela (los del cuerpo del Home) */}
      {(vista.widgets?.inicio || []).some((w) => w.posicion !== "top") && (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          {vista.widgets.inicio.filter((w) => w.posicion !== "top").map((w) => (
            <Widget key={w.id} widget={w} data={data} onQuitar={(id) => vistaStore.quitarWidget("inicio", id)} />
          ))}
        </div>
      )}
    </div>
  );
}

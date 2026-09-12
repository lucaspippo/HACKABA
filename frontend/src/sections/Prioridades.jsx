import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, Plus, Check, Radar, CalendarClock, CircleDollarSign } from "lucide-react";
import AngelaMark from "../components/AngelaMark";
import { ACENTO, DrillNegocio } from "../components/CardNegocio";
import FiltrosAccion from "../components/FiltrosAccion";
import { useApiMutation, useApiQuery } from "../lib/query";
import { toast } from "../lib/toastStore";
import { equipoStore } from "../lib/equipoStore";
import { equipoReal } from "../lib/equipoReal";
import { useSession } from "../lib/auth";
import { pesoCorto } from "../lib/format";
import { useT, tRol, useLang } from "../lib/i18n";
import { accionDe, estiloAccion } from "../lib/prioridadAccion";
import { buildPrioridadPrompt } from "../lib/prioridadPrompt";

const OVERLAY_BELOW = 760;

function EmptyNoData({ onNavegar, onPreguntar }) {
  const t = useT();
  return (
    <div className="flex items-start gap-4 rounded-[var(--radius-card)] border border-salvia/25 bg-salvia/[0.05] p-6">
      <AngelaMark size={40} />
      <div className="flex-1">
        <p className="text-lg leading-snug text-tinta">{t("prioridades.sin_datos")}</p>
        <button
          onClick={() => (onNavegar ? onNavegar("cargar") : onPreguntar?.(t("oportunidades.enviar_datos")))}
          className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-salvia px-4 py-2 text-sm font-semibold text-crema transition-transform active:scale-95"
        >
          {t("oportunidades.cargar_ventas")} <ArrowRight size={15} />
        </button>
      </div>
    </div>
  );
}

function HotkeyBadge({ children }) {
  return (
    <kbd className="ml-0.5 rounded border border-current/25 px-1 text-2xs font-semibold opacity-70">
      {children}
    </kbd>
  );
}

// A chip only for the two urgency levels the owner actually needs to act on
// today — "this_week" and "later" would show on nearly every card, which is
// noise, not news.
const DEADLINE_CHIP_CLS = {
  overdue: "bg-rojo/10 text-rojo",
  today: "bg-oro/15 text-oro-tinta",
};

function DeadlineChip({ urgency }) {
  const t = useT();
  const cls = DEADLINE_CHIP_CLS[urgency];
  if (!cls) return null;
  return (
    <span className={`ml-1 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-2xs font-semibold ${cls}`}>
      <CalendarClock size={10} /> {t(urgency === "overdue" ? "prioridades.overdue" : "prioridades.due_today")}
    </span>
  );
}

const ICON_TONE = { rojo: "text-rojo", oro: "text-oro-tinta", salvia: "text-salvia", hielo: "text-hielo" };
const BAR_TONE = { rojo: "bg-rojo", oro: "bg-oro", salvia: "bg-salvia", hielo: "bg-hielo" };

function isDueNow(item) {
  const urgency = item.insight?.deadline?.urgency;
  return urgency === "overdue" || urgency === "today";
}

function splitByUrgency(items) {
  const now = [];
  const queue = [];
  for (const item of items) {
    (isDueNow(item) ? now : queue).push(item);
  }
  return { now, queue };
}

function ListHeading({ children, tone = "tinta" }) {
  const toneCls = tone === "rojo" ? "text-rojo" : tone === "oro" ? "text-oro-tinta" : "text-tinta-suave";
  return (
    <h2 className={`sticky top-0 border-y border-linea bg-papel px-4 py-2.5 text-xs font-semibold uppercase tracking-wide ${toneCls}`}>
      {children}
    </h2>
  );
}

function WorkRow({ item, selected, onSelect }) {
  const t = useT();
  const a = ACENTO[item.tono] || ACENTO.salvia;
  const acc = estiloAccion(item);
  const Icon = acc.icon;
  const cifra = item.monto != null && item.monto > 0
    ? pesoCorto(item.monto)
    : (item.cifra_texto || null);
  const urgency = item.insight?.deadline?.urgency;
  const late = urgency === "overdue" || urgency === "today";
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-current={selected || undefined}
      title={item.resumen || undefined}
      className={`relative flex w-full items-center gap-3 border-b border-linea px-4 py-2.5 text-left last:border-0 ${
        selected ? "bg-papel-hondo/70" : "hover:bg-papel-hondo/40"
      } ${item.action_taken ? "opacity-60" : ""}`}
    >
      {selected && (
        <span aria-hidden="true" className={`absolute inset-y-0 left-0 w-0.5 ${BAR_TONE[item.tono] || BAR_TONE.salvia}`} />
      )}
      <Icon size={15} className={`shrink-0 ${ICON_TONE[item.tono] || ICON_TONE.salvia}`} aria-hidden="true" />
      <span className="min-w-0 flex-1 truncate text-sm font-semibold leading-tight text-tinta">
        {item.titulo}
      </span>
      {item.action_taken && (
        <Check size={13} className="shrink-0 text-salvia" aria-label={t("prioridades.done")} />
      )}
      {late && (
        <CalendarClock size={13} className={`shrink-0 ${urgency === "overdue" ? "text-rojo" : "text-oro-tinta"}`}
          aria-label={t(urgency === "overdue" ? "prioridades.overdue" : "prioridades.due_today")} />
      )}
      {cifra && (
        <span className={`plata shrink-0 text-sm font-medium ${a.cifra}`}>{cifra}</span>
      )}
    </button>
  );
}

export default function Prioridades({ onNavegar, onPreguntar }) {
  const t = useT();
  const lang = useLang();
  const langKey = useSession()?.usuario?.idioma || "es";
  const { data, error, isFetching, refetch } = useApiQuery("prioridades");
  const prepararMut = useApiMutation("ordenCompraPreparar");
  const resolverMut = useApiMutation("pisoResolver");
  const feedbackMut = useApiMutation("patronFeedback");
  const [selectedId, setSelectedId] = useState(null);
  const [overlay, setOverlay] = useState(false);
  const [filtro, setFiltro] = useState(null);
  const [adoptados, setAdoptados] = useState({});
  const [eligiendo, setEligiendo] = useState(null);
  const [equipo, setEquipo] = useState([]);
  const [propTrabajando, setPropTrabajando] = useState(false);
  const [feedbackBusy, setFeedbackBusy] = useState(false);
  const [confirmingFloorReport, setConfirmingFloorReport] = useState(null);
  const rootRef = useRef(null);
  const langReady = useRef(false);

  const cargar = () => refetch();
  useEffect(() => {
    if (!langReady.current) { langReady.current = true; return; }
    refetch();
  }, [langKey, refetch]);

  useEffect(() => {
    const el = rootRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(([entry]) => {
      setOverlay(entry.contentRect.width < OVERLAY_BELOW);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const act = data?.act || [];
  const watch = data?.watch || [];
  const todos = useMemo(() => [...act, ...watch], [act, watch]);
  const actFil = useMemo(
    () => (filtro ? act.filter((i) => accionDe(i) === filtro) : act),
    [act, filtro],
  );
  const watchFil = useMemo(
    () => (filtro ? watch.filter((i) => accionDe(i) === filtro) : watch),
    [watch, filtro],
  );
  const byId = Object.fromEntries(todos.map((i) => [i.id, i]));
  const selected = byId[selectedId] || null;
  const visible = useMemo(
    () => (filtro ? todos.filter((i) => accionDe(i) === filtro) : todos),
    [todos, filtro],
  );

  useEffect(() => { setConfirmingFloorReport(null); }, [selectedId]);

  useEffect(() => {
    if (selectedId && visible.some((i) => i.id === selectedId)) return;
    if (overlay) {
      if (selectedId) setSelectedId(null);
      return;
    }
    setSelectedId(visible[0]?.id ?? null);
  }, [visible, overlay, selectedId]);

  // Power-user navigation: arrows walk the visible list, digits fire the
  // Nth quick-action button in the current drill panel's footer (see the
  // `data-quick-action` attributes in drillAcciones), Esc closes the
  // overlay. Ignored while the focus is on a real input so typing in
  // Ángela's chat box or the "adopt" dropdown never gets hijacked.
  useEffect(() => {
    const onKey = (e) => {
      const el = document.activeElement;
      const typing = el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA"
        || el.tagName === "SELECT" || el.isContentEditable);
      if (typing || !visible.length) return;
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        const i = visible.findIndex((it) => it.id === selectedId);
        const step = e.key === "ArrowDown" ? 1 : -1;
        const next = visible[(i + step + visible.length) % visible.length];
        setSelectedId(next.id);
      } else if (e.key === "Escape" && overlay && selectedId) {
        setSelectedId(null);
      } else if (/^[1-9]$/.test(e.key) && selectedId) {
        document.querySelector(`[data-quick-action="${e.key}"]`)?.click();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [visible, selectedId, overlay]);

  const aprobarPropuesta = async (c) => {
    const p = c.propuesta;
    if (!p) return;
    setPropTrabajando(true);
    try {
      const r = await prepararMut.mutateAsync([{
        codigo: p.codigo, producto: p.producto, proveedor: p.proveedor,
        cantidad: p.cantidad, motivo: c.titulo, origen: c.id,
      }]);
      toast(r.mensaje);
      cargar();
    } catch {
      toast(t("oportunidades.prop_error"));
    }
    setPropTrabajando(false);
  };

  const resolverPiso = async (c) => {
    if (confirmingFloorReport !== c.id) {
      setConfirmingFloorReport(c.id);
      return;
    }
    setConfirmingFloorReport(null);
    try {
      await Promise.all((c.reportes || []).map((rid) => resolverMut.mutateAsync([rid])));
      toast(t("oportunidades.piso_resuelta"));
      setSelectedId(null);
      cargar();
    } catch {
      toast(t("oportunidades.piso_error"), "error");
    }
  };

  // Only ids core/oportunidades_neg.py or core/patrones.py actually produced
  // can take feedback (core/pattern_feedback.py, shared by both) — a raw
  // alert or a piso report would just 404 against the endpoint.
  const canGiveFeedback = (item) =>
    (item.origen || []).some((o) => o.startsWith("oportunidad:") || o.startsWith("patron:"));

  const giveFeedback = (item, action) => {
    setFeedbackBusy(true);
    feedbackMut.mutateAsync([item.id, action])
      .then(() => {
        toast(t("aprendizaje.feedback_ok"));
        setSelectedId(null);
        cargar();
      })
      .catch(() => toast(t("aprendizaje.feedback_error"), "error"))
      .finally(() => setFeedbackBusy(false));
  };

  const abrirSelector = async (c) => {
    if (!equipo.length) {
      try { setEquipo(await equipoReal()); } catch { /* network: keep going */ }
    }
    setEligiendo(c.id);
  };
  const adoptar = (c, responsable) => {
    equipoStore.addObjetivo(c.titulo, responsable, t("oportunidades.este_mes"));
    setAdoptados((s) => ({ ...s, [c.id]: true }));
    setEligiendo(null);
    toast(t("oportunidades.toast_adoptado_a", { quien: responsable }));
  };

  // Fixed hotkey slots so the meaning stays consistent across every card:
  // 1 = the primary action (resolve / adopt), 2 = ask Ángela, 3 = view data.
  // A card that skips slot 1 (already adopted, or no piso/adopt action)
  // just leaves that hotkey unbound — 2 and 3 keep their own meaning.
  // One primary button per card: the action that CLOSES it. When Ángela's
  // proposal is live, its own approve button (violeta, inside the panel) is
  // that primary, so "adoptar" steps down to an outline. Ask-Ángela is an
  // outline in her color; "ver datos" is a text link.
  const drillAcciones = (item, closeAfter) => (
    <>
      {item.piso && (
        <span className="inline-flex items-center gap-1.5">
          <button data-quick-action="1" onClick={() => resolverPiso(item)}
            className={`inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-semibold text-crema ${
              confirmingFloorReport === item.id ? "bg-rojo" : "bg-tinta"
            }`}>
            <Check size={14} />
            {confirmingFloorReport === item.id ? t("oportunidades.floor_mark_confirm") : t("oportunidades.piso_marcar")}
            <HotkeyBadge>1</HotkeyBadge>
          </button>
          {confirmingFloorReport === item.id && (
            <button onClick={() => setConfirmingFloorReport(null)}
              className="text-sm font-semibold text-tinta-suave hover:text-tinta">
              {t("aprendizaje.feedback_cancel")}
            </button>
          )}
        </span>
      )}
      {!item.piso && (adoptados[item.id] ? (
        <span className="text-sm font-semibold text-salvia">{t("oportunidades.adoptado")}</span>
      ) : eligiendo === item.id && equipo.length > 0 ? (
        <select autoFocus defaultValue=""
          onChange={(e) => e.target.value && adoptar(item, e.target.value)}
          onBlur={() => setEligiendo(null)}
          className="rounded-full border border-salvia bg-crema px-3.5 py-1.5 text-sm font-semibold text-tinta">
          <option value="" disabled>{t("oportunidades.asignar_a")}</option>
          {equipo.map((p) => (
            <option key={p.username} value={p.nombre}>{p.nombre} — {tRol(p.rol)}</option>
          ))}
        </select>
      ) : (
        <button data-quick-action="1" onClick={() => abrirSelector(item)}
          className={`inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-semibold transition-colors ${
            item.propuesta && !item.action_taken
              ? "border border-linea text-tinta hover:border-tinta"
              : "bg-tinta text-crema hover:bg-tinta/90"}`}>
          <Plus size={14} /> {t("oportunidades.adoptar")} <HotkeyBadge>1</HotkeyBadge>
        </button>
      ))}
      <button data-quick-action="2" onClick={() => { onPreguntar?.(buildPrioridadPrompt(item, t, lang)); closeAfter?.(); }}
        className="inline-flex items-center gap-1.5 rounded-full border border-violeta/40 px-4 py-2 text-sm font-semibold text-violeta transition-colors hover:border-violeta">
        <AngelaMark size={15} /> {t("prioridades.analizar_angela")} <HotkeyBadge>2</HotkeyBadge>
      </button>
      {item.navegar && (
        <button data-quick-action="3" onClick={() => { onNavegar?.(item.navegar); closeAfter?.(); }}
          className="px-2 py-2 text-sm font-semibold text-tinta-suave underline decoration-linea underline-offset-4 hover:text-tinta hover:decoration-tinta">
          {t("oportunidades.ver_datos")} <HotkeyBadge>3</HotkeyBadge>
        </button>
      )}
    </>
  );

  // Where an involucrado's `kind` sends the reader when clicked — mirrors
  // the data-nav-id anchors that exist today: `cliente-${id}` in
  // CuentasCorrientes.jsx, `producto-${id}` in Inventario.jsx.
  const INVOLUCRADO_NAV = {
    client: { section: "cuentas", anchor: (id) => `cliente-${id}` },
    product: { section: "inventario", anchor: (id) => `producto-${id}` },
  };

  const drillProps = (item) => {
    const acc = estiloAccion(item);
    return {
      tono: item.tono,
      titulo: item.titulo,
      monto: item.monto,
      montoLabel: item.monto_label,
      cifraTexto: item.cifra_texto,
      insight: item.insight,
      macro: item.macro,
      origins: item.origen || [],
      fuentes: item.fuentes || [],
      propuesta: item.propuesta,
      propuestaTrabajando: propTrabajando,
      actionTaken: item.action_taken && {
        ...item.action_taken,
        onOpen: () => onNavegar?.(item.action_taken.navigate, item.action_taken.label),
      },
      onAprobarPropuesta: () => aprobarPropuesta(item),
      chip: item.chip,
      chipIcon: acc.icon,
      chipCls: acc.cls,
      onFeedback: canGiveFeedback(item) ? (action) => giveFeedback(item, action) : undefined,
      feedbackBusy,
      // Sources all point at the card's one destination section — there's no
      // per-source routing yet, but it's a real jump instead of dead text.
      onVerFuentes: item.navegar ? () => onNavegar?.(item.navegar) : undefined,
      // Each involucrado routes by its own `kind` (client/product), landing
      // on the real record via the destination screen's data-nav-id anchor
      // (cliente-${id} in CuentasCorrientes.jsx, producto-${id} in
      // Inventario.jsx) — rows without a kind (e.g. Finanzas-sourced text
      // rows) render non-clickable in CardNegocio.jsx already.
      onVerInvolucrado: (iv) => {
        const target = iv.kind && INVOLUCRADO_NAV[iv.kind];
        if (target && iv.id != null) onNavegar?.(target.section, target.anchor(iv.id));
      },
    };
  };

  const cargando = data == null && (!error || isFetching);
  const vacio = data && act.length === 0 && watch.length === 0;

  return (
    <div ref={rootRef} className="flex h-full min-h-0 flex-col">
      <header className="shrink-0 border-b border-linea px-7 py-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-2">
            <Radar size={22} className="text-hielo" />
            <div>
              <h1 className="font-display text-2xl font-bold leading-none">{t("nav.prioridades")}</h1>
              <p className="mt-1.5 text-sm text-tinta-suave">
                {/* `badge`, not act.length: `act` keeps executed cards visible
                    (greyed out, stamped "Hecho") while the badge counts only
                    open work — the header must agree with the sidebar count. */}
                {act.length > 0
                  ? t("prioridades.sub_count", { n: data?.badge ?? act.length })
                  : t("prioridades.sub")}
              </p>
            </div>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-2 pt-0.5">
            {data?.recuperable?.disponible && (() => {
              // The rows below add up to MORE than this figure on purpose:
              // only what is `recuperable` is summed (risk and avoided loss
              // are shown, never added — core/oportunidades_neg.recuperable).
              const k = data.recuperable.componentes?.length ?? 0;
              const n = k + (data.recuperable.excluidos?.length ?? 0);
              return (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-salvia/10 px-2.5 py-1 text-xs font-semibold text-salvia"
                      title={t("prioridades.recoverable_sub", { k, n })}>
                  <CircleDollarSign size={13} aria-hidden="true" />
                  <span className="plata">{t("prioridades.recoverable", { amount: pesoCorto(data.recuperable.total) })}</span>
                  <span className="font-normal text-tinta-suave">({k}/{n})</span>
                </span>
              );
            })()}
            {todos.length > 0 && (
              <p className="hidden items-center gap-1 text-xs text-tinta-suave lg:flex">
                <kbd className="rounded-md border border-linea px-1.5 py-0.5 font-semibold">↑↓</kbd> {t("prioridades.hint_mover")}
                <kbd className="ml-2 rounded-md border border-linea px-1.5 py-0.5 font-semibold">1-3</kbd> {t("prioridades.hint_accion")}
              </p>
            )}
          </div>
        </div>
        {todos.length > 0 && (
          <div className="mt-3.5">
            <FiltrosAccion items={todos} filtro={filtro} onFiltro={setFiltro} />
          </div>
        )}
      </header>

      {cargando && (
        <div className="flex min-h-0 flex-1">
          <div className="w-[min(38%,28rem)] min-w-[280px] space-y-2 border-r border-linea p-4">
            {Array.from({ length: 7 }).map((_, i) => (
              <div key={i} className="h-16 animate-pulse rounded-xl border border-linea/60 bg-papel-hondo/50" />
            ))}
          </div>
          <div className="min-w-0 flex-1 p-6">
            <div className="h-full animate-pulse rounded-[var(--radius-card)] border border-linea/60 bg-papel-hondo/30" />
          </div>
        </div>
      )}

      {error && (
        <div className="m-7 rounded-[var(--radius-card)] border border-rojo/30 bg-crema p-6">
          <p className="text-base text-tinta">{t("prioridades.error")}</p>
          <button onClick={cargar}
            className="mt-3 rounded-full border border-linea px-4 py-2 text-sm font-semibold">
            {t("prioridades.reintentar")}
          </button>
        </div>
      )}

      {vacio && !data?.hay_ventas && (
        <div className="p-7"><EmptyNoData onNavegar={onNavegar} onPreguntar={onPreguntar} /></div>
      )}
      {vacio && data?.hay_ventas && (
        <div className="m-7 rounded-[var(--radius-card)] border border-linea bg-crema p-8 text-center sombra-papel">
          <Radar size={22} className="mx-auto text-tinta-suave" />
          <p className="mt-2 text-base text-tinta">{t("prioridades.vacio")}</p>
        </div>
      )}

      {!cargando && !error && !vacio && (
        <div className="flex min-h-0 flex-1">
          <div className={`${overlay ? "min-w-0 flex-1" : "w-[min(36%,26rem)] min-w-[280px] border-r border-linea"} overflow-y-auto bg-crema`}>
            {(() => {
              const { now, queue } = splitByUrgency(actFil);
              const showNow = now.length > 0 && queue.length > 0;
              return (
                <>
                  {showNow && (
                    <ListHeading tone={now.some((i) => i.insight?.deadline?.urgency === "overdue") ? "rojo" : "oro"}>
                      {t("prioridades.now")}
                    </ListHeading>
                  )}
                  {now.map((item) => (
                    <WorkRow key={item.id} item={item} selected={selectedId === item.id}
                      onSelect={() => setSelectedId(item.id)} />
                  ))}
                  {showNow && queue.length > 0 && (
                    <ListHeading>{t("prioridades.queue")}</ListHeading>
                  )}
                  {queue.map((item) => (
                    <WorkRow key={item.id} item={item} selected={selectedId === item.id}
                      onSelect={() => setSelectedId(item.id)} />
                  ))}
                </>
              );
            })()}
            {watchFil.length > 0 && (
              <>
                <ListHeading tone="oro">{t("prioridades.watch")}</ListHeading>
                {watchFil.map((item) => (
                  <WorkRow key={item.id} item={item} selected={selectedId === item.id}
                    onSelect={() => setSelectedId(item.id)} />
                ))}
              </>
            )}
            {filtro && actFil.length === 0 && watchFil.length === 0 && (
              <p className="px-4 py-8 text-center text-sm text-tinta-suave">
                {t("prioridades.filtro_vacio")}
              </p>
            )}
          </div>
          {!overlay && selected && (
            <div className="min-w-0 flex-1 overflow-y-auto">
              {/* Keyed by card: arrow-key navigation only swaps props, so an
                  unkeyed drill would carry the previous card's local state
                  over — an armed "¿Seguro? Sí, descartar" in FindingFeedback
                  could then dismiss the WRONG finding on one click (and
                  AngelaProposal's `postponed` / BasedOn's `expanded` would
                  leak across cards too). Remounting resets all of them at once,
                  the same way the parent-owned confirmingFloorReport is. */}
              <DrillNegocio key={selectedId} variante="panel" layout="accion" {...drillProps(selected)}
                acciones={drillAcciones(selected)} />
            </div>
          )}
        </div>
      )}

      {overlay && selected && (
        <DrillNegocio key={selectedId} variante="overlay" layout="accion" {...drillProps(selected)}
          onCerrar={() => setSelectedId(null)}
          acciones={drillAcciones(selected, () => setSelectedId(null))} />
      )}
    </div>
  );
}

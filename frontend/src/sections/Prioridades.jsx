import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, Plus, Check, Radar } from "lucide-react";
import AngelaMark from "../components/AngelaMark";
import { ACENTO, DrillNegocio } from "../components/CardNegocio";
import FiltrosAccion from "../components/FiltrosAccion";
import { api } from "../lib/api";
import { toast } from "../lib/toastStore";
import { equipoStore } from "../lib/equipoStore";
import { equipoReal } from "../lib/equipoReal";
import { useSession } from "../lib/auth";
import { pesoCorto } from "../lib/format";
import { useT, tRol } from "../lib/i18n";
import { accionDe, estiloAccion } from "../lib/prioridadAccion";

const OVERLAY_BELOW = 760;

let _cachePrio = { lang: null, data: null };

function EmptyNoData({ onNavegar, onPreguntar }) {
  const t = useT();
  return (
    <div className="flex items-start gap-4 rounded-[var(--radius-card)] border border-salvia/25 bg-salvia/[0.05] p-6">
      <AngelaMark size={40} />
      <div className="flex-1">
        <p className="text-[1.02rem] leading-snug text-tinta">{t("prioridades.sin_datos")}</p>
        <button
          onClick={() => (onNavegar ? onNavegar("cargar") : onPreguntar?.(t("oportunidades.enviar_datos")))}
          className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-salvia px-4 py-2 text-[0.85rem] font-semibold text-crema transition-transform active:scale-95"
        >
          {t("oportunidades.cargar_ventas")} <ArrowRight size={15} />
        </button>
      </div>
    </div>
  );
}

function HotkeyBadge({ children }) {
  return (
    <kbd className="ml-0.5 rounded border border-current/25 px-1 text-[0.64rem] font-semibold opacity-70">
      {children}
    </kbd>
  );
}

function WorkRow({ item, selected, onSelect }) {
  const a = ACENTO[item.tono] || ACENTO.salvia;
  const acc = estiloAccion(item);
  const Icon = acc.icon;
  const cifra = item.monto != null && item.monto > 0
    ? pesoCorto(item.monto)
    : (item.cifra_texto || null);
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-current={selected || undefined}
      className={`flex w-full items-start gap-3 border-b border-linea px-4 py-3 text-left last:border-0 ${
        selected ? "bg-papel-hondo/70" : "hover:bg-papel-hondo/40"
      }`}
    >
      <span className="min-w-0 flex-1">
        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[0.68rem] font-semibold ${acc.cls}`}>
          <Icon size={11} /> {item.chip}
        </span>
        <span className="mt-1 block font-display text-[0.98rem] font-bold leading-tight">{item.titulo}</span>
        {item.resumen && (
          <span className="mt-0.5 block line-clamp-1 text-[0.82rem] leading-snug text-tinta-suave">{item.resumen}</span>
        )}
      </span>
      {cifra && (
        <span className={`plata mt-1 shrink-0 text-[0.95rem] font-medium ${a.cifra}`}>{cifra}</span>
      )}
    </button>
  );
}

export default function Prioridades({ onNavegar, onPreguntar }) {
  const t = useT();
  const langKey = useSession()?.usuario?.idioma || "es";
  const [data, setData] = useState(_cachePrio.lang === langKey ? _cachePrio.data : null);
  const [error, setError] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [overlay, setOverlay] = useState(false);
  const [filtro, setFiltro] = useState(null);
  const [adoptados, setAdoptados] = useState({});
  const [eligiendo, setEligiendo] = useState(null);
  const [equipo, setEquipo] = useState([]);
  const [propResultado, setPropResultado] = useState({});
  const [propTrabajando, setPropTrabajando] = useState(false);
  const [feedbackBusy, setFeedbackBusy] = useState(false);
  const [confirmandoPiso, setConfirmandoPiso] = useState(null);
  const rootRef = useRef(null);

  const cargar = () => {
    setError(null);
    api.prioridades()
      .then((d) => {
        _cachePrio = { lang: langKey, data: d };
        setData(d);
      })
      .catch((e) => setError(e));
  };

  useEffect(() => { cargar(); }, [langKey]);

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

  useEffect(() => { setConfirmandoPiso(null); }, [selectedId]);

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
      const r = await api.ordenCompraPreparar({
        codigo: p.codigo, producto: p.producto, proveedor: p.proveedor,
        cantidad: p.cantidad, motivo: c.titulo, origen: c.id,
      });
      setPropResultado((s) => ({ ...s, [c.id]: r.mensaje }));
      toast(r.mensaje);
    } catch {
      toast(t("oportunidades.prop_error"));
    }
    setPropTrabajando(false);
  };

  const resolverPiso = async (c) => {
    if (confirmandoPiso !== c.id) {
      setConfirmandoPiso(c.id);
      return;
    }
    setConfirmandoPiso(null);
    try {
      await Promise.all((c.reportes || []).map((rid) => api.piso.resolver(rid)));
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
    api.patronFeedback(item.id, action)
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
  const drillAcciones = (item, closeAfter) => (
    <>
      {item.piso && (
        <span className="inline-flex items-center gap-1.5">
          <button data-quick-action="1" onClick={() => resolverPiso(item)}
            className={`inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-[0.84rem] font-semibold text-crema ${
              confirmandoPiso === item.id ? "bg-rojo" : "bg-hielo"
            }`}>
            <Check size={14} />
            {confirmandoPiso === item.id ? t("oportunidades.piso_marcar_confirmar") : t("oportunidades.piso_marcar")}
            <HotkeyBadge>1</HotkeyBadge>
          </button>
          {confirmandoPiso === item.id && (
            <button onClick={() => setConfirmandoPiso(null)}
              className="text-[0.84rem] font-semibold text-tinta-suave hover:text-tinta">
              {t("aprendizaje.feedback_cancelar")}
            </button>
          )}
        </span>
      )}
      {!item.piso && (adoptados[item.id] ? (
        <span className="text-[0.84rem] font-semibold text-salvia">{t("oportunidades.adoptado")}</span>
      ) : eligiendo === item.id && equipo.length > 0 ? (
        <select autoFocus defaultValue=""
          onChange={(e) => e.target.value && adoptar(item, e.target.value)}
          onBlur={() => setEligiendo(null)}
          className="rounded-full border border-salvia bg-crema px-3.5 py-1.5 text-[0.82rem] font-semibold text-tinta">
          <option value="" disabled>{t("oportunidades.asignar_a")}</option>
          {equipo.map((p) => (
            <option key={p.username} value={p.nombre}>{p.nombre} — {tRol(p.rol)}</option>
          ))}
        </select>
      ) : (
        <button data-quick-action="1" onClick={() => abrirSelector(item)}
          className="inline-flex items-center gap-1.5 rounded-full border border-linea px-4 py-2 text-[0.84rem] font-semibold text-tinta transition-colors hover:border-salvia hover:text-salvia">
          <Plus size={14} /> {t("oportunidades.adoptar")} <HotkeyBadge>1</HotkeyBadge>
        </button>
      ))}
      {item.accion_chat && (
        <button data-quick-action="2" onClick={() => { onPreguntar?.(item.accion_chat); closeAfter?.(); }}
          className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-[0.84rem] font-semibold text-crema">
          <AngelaMark size={15} /> {t("oportunidades.accionar_angela")} <HotkeyBadge>2</HotkeyBadge>
        </button>
      )}
      {item.navegar && (
        <button data-quick-action="3" onClick={() => { onNavegar?.(item.navegar); closeAfter?.(); }}
          className="rounded-full border border-linea px-4 py-2 text-[0.84rem] font-semibold text-tinta-suave hover:text-tinta">
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
      porque: item.drill?.porque || [],
      macro: item.macro,
      grafico: item.drill?.grafico,
      involucrados: item.drill?.involucrados || [],
      supuestos: item.drill?.supuestos || [],
      confidence: item.drill?.confidence,
      origen: item.origen || [],
      fuentes: item.fuentes || [],
      propuesta: item.propuesta,
      propuestaTrabajando: propTrabajando,
      propuestaResultado: propResultado[item.id],
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

  const cargando = data === null && !error;
  const vacio = data && act.length === 0 && watch.length === 0;

  return (
    <div ref={rootRef} className="flex h-full min-h-0 flex-col">
      <header className="shrink-0 border-b border-linea px-7 py-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-2">
            <Radar size={22} className="text-hielo" />
            <div>
              <h1 className="font-display text-2xl font-bold leading-none">{t("nav.prioridades")}</h1>
              <p className="mt-1 text-[0.9rem] text-tinta-suave">
                {act.length > 0 ? t("prioridades.sub_conteo", { n: act.length }) : t("prioridades.sub")}
                {data?.recuperable?.disponible && (
                  <span className="plata ml-2 font-semibold text-salvia">
                    · {t("prioridades.recuperable", { monto: pesoCorto(data.recuperable.total) })}
                  </span>
                )}
              </p>
            </div>
          </div>
          {todos.length > 0 && (
            <p className="hidden shrink-0 items-center gap-1 pt-1 text-[0.76rem] text-tinta-suave lg:flex">
              <kbd className="rounded-md border border-linea px-1.5 py-0.5 font-semibold">↑↓</kbd> {t("prioridades.hint_mover")}
              <kbd className="ml-2 rounded-md border border-linea px-1.5 py-0.5 font-semibold">1-3</kbd> {t("prioridades.hint_accion")}
            </p>
          )}
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
          <p className="text-[0.95rem] text-tinta">{t("prioridades.error")}</p>
          <button onClick={cargar}
            className="mt-3 rounded-full border border-linea px-4 py-2 text-[0.84rem] font-semibold">
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
          <p className="mt-2 text-[0.95rem] text-tinta">{t("prioridades.vacio")}</p>
        </div>
      )}

      {!cargando && !error && !vacio && (
        <div className="flex min-h-0 flex-1">
          <div className={`${overlay ? "min-w-0 flex-1" : "w-[min(38%,28rem)] min-w-[280px] border-r border-linea"} overflow-y-auto bg-crema`}>
            {actFil.map((item) => (
              <WorkRow key={item.id} item={item} selected={selectedId === item.id}
                onSelect={() => setSelectedId(item.id)} />
            ))}
            {watchFil.length > 0 && (
              <>
                <h2 className="sticky top-0 border-y border-linea bg-papel px-4 py-2 text-[0.72rem] font-semibold uppercase tracking-wide text-oro-tinta">
                  {t("prioridades.watch")}
                </h2>
                {watchFil.map((item) => (
                  <WorkRow key={item.id} item={item} selected={selectedId === item.id}
                    onSelect={() => setSelectedId(item.id)} />
                ))}
              </>
            )}
            {filtro && actFil.length === 0 && watchFil.length === 0 && (
              <p className="px-4 py-8 text-center text-[0.88rem] text-tinta-suave">
                {t("prioridades.filtro_vacio")}
              </p>
            )}
          </div>
          {!overlay && selected && (
            <div className="min-w-0 flex-1 overflow-y-auto">
              <DrillNegocio variante="panel" {...drillProps(selected)}
                acciones={drillAcciones(selected)} />
            </div>
          )}
        </div>
      )}

      {overlay && selected && (
        <DrillNegocio variante="overlay" {...drillProps(selected)}
          onCerrar={() => setSelectedId(null)}
          acciones={drillAcciones(selected, () => setSelectedId(null))} />
      )}
    </div>
  );
}

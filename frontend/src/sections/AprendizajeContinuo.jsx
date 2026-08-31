import { useEffect, useState } from "react";
import { Lightbulb, Truck, ShieldCheck, CalendarClock, Users2, ArrowRight, Check } from "lucide-react";
import AngelaMark from "../components/AngelaMark";
import { CardNegocio, DrillNegocio } from "../components/CardNegocio";
import { api } from "../lib/api";
import { toast } from "../lib/toastStore";
import { useT } from "../lib/i18n";

// The three reactions the owner can give a live finding — see
// backend/core/db/pattern_feedback_repo.py's ACTIONS for the source of truth.
const FEEDBACK_ACTIONS = [
  { action: "accepted", lk: "aprendizaje.feedback_aceptado" },
  { action: "already_knew", lk: "aprendizaje.feedback_ya_sabia" },
  { action: "dismissed", lk: "aprendizaje.feedback_descartado" },
];

const HISTORY_ACTION_LABEL = {
  accepted: "aprendizaje.historial_accepted",
  dismissed: "aprendizaje.historial_dismissed",
  already_knew: "aprendizaje.historial_already_knew",
};

// This page explains "continuous learning" (backend/core/patrones.py) to the
// owner: patterns nobody asked to have calculated, found by comparing things
// nobody had put side by side before. It's the app's one dedicated place to
// keep making that value visible, not just the moment a card happens to fire.
//
// Each shipped pattern renders through the SAME CardNegocio/DrillNegocio
// anatomy as every other finding in the app (P27·C) — no bespoke layout. If
// the pattern is actually live for this tenant right now, we show the real
// card (fetched from /api/prioridades, the same endpoint Prioridades.jsx
// reads); otherwise we fall back to a clearly-labeled illustrative example
// with the exact shape a live one would take.

const EXAMPLES = [
  {
    id: "combo_no_percibido",
    tono: "salvia",
    chip: "aprendizaje.combo_chip",
    titulo: "aprendizaje.combo_titulo",
    dato: "aprendizaje.combo_dato",
    montoLabel: "aprendizaje.combo_monto_label",
    porque: ["aprendizaje.combo_porque_1", "aprendizaje.combo_porque_2"],
    involucrados: [
      { nombre: "aprendizaje.combo_cliente_1" },
      { nombre: "aprendizaje.combo_cliente_2" },
    ],
    supuestos: ["aprendizaje.combo_supuesto"],
  },
  {
    id: "faltante_caja_patron",
    tono: "oro",
    chip: "aprendizaje.caja_chip",
    titulo: "aprendizaje.caja_titulo",
    dato: "aprendizaje.caja_dato",
    montoLabel: "aprendizaje.caja_monto_label",
    porque: ["aprendizaje.caja_porque_1", "aprendizaje.caja_porque_2"],
    involucrados: [],
    supuestos: ["aprendizaje.caja_supuesto"],
  },
];

const UPCOMING = [
  { icon: Truck, t: "aprendizaje.fut_proveedor_t", d: "aprendizaje.fut_proveedor_d" },
  { icon: ShieldCheck, t: "aprendizaje.fut_riesgo_t", d: "aprendizaje.fut_riesgo_d" },
  { icon: CalendarClock, t: "aprendizaje.fut_estacion_t", d: "aprendizaje.fut_estacion_d" },
  { icon: Users2, t: "aprendizaje.fut_vendedor_t", d: "aprendizaje.fut_vendedor_d" },
];

// A hand-written stand-in with the exact anatomy a live card would have,
// used only when this tenant has no matching live finding right now.
function illustrativeExample(example, t) {
  return {
    id: example.id,
    tono: example.tono,
    chip: t(example.chip),
    titulo: t(example.titulo),
    monto: null,
    montoLabel: t(example.montoLabel),
    cifraTexto: null,
    fuentes: [],
    drill: {
      porque: example.porque.map((k) => t(k)),
      grafico: null,
      involucrados: example.involucrados.map((iv) => ({ nombre: t(iv.nombre) })),
      supuestos: example.supuestos.map((k) => t(k)),
    },
    isIllustrative: true,
    summary: t(example.dato),
  };
}

export default function AprendizajeContinuo({ onPreguntar }) {
  const t = useT();
  const [live, setLive] = useState(null); // { [id]: item } for patterns actually firing right now
  const [selected, setSelected] = useState(null);
  const [handledIds, setHandledIds] = useState(() => new Set()); // fed back on, this session
  const [feedbackBusy, setFeedbackBusy] = useState(false);
  const [history, setHistory] = useState(null);

  useEffect(() => {
    let cancelled = false;
    api.prioridades()
      .then((inbox) => {
        if (cancelled) return;
        const all = [...(inbox?.act || []), ...(inbox?.watch || [])];
        const byId = {};
        for (const example of EXAMPLES) {
          const found = all.find((it) => it.id === example.id);
          if (found) byId[example.id] = found;
        }
        setLive(byId);
      })
      .catch(() => setLive({})); // no live data: the illustrative examples still show
    api.patronHistorial().then((r) => setHistory(r.historial || [])).catch(() => setHistory([]));
    return () => { cancelled = true; };
  }, []);

  const giveFeedback = (cardId, action) => {
    setFeedbackBusy(true);
    api.patronFeedback(cardId, action)
      .then((row) => {
        setHandledIds((prev) => new Set(prev).add(cardId));
        setHistory((prev) => [row, ...(prev || [])]);
        setSelected(null);
        toast(t("aprendizaje.feedback_ok"));
      })
      .catch(() => toast(t("aprendizaje.feedback_error"), "error"))
      .finally(() => setFeedbackBusy(false));
  };

  const cards = EXAMPLES.map((example) => {
    const found = live?.[example.id];
    if (!found) return illustrativeExample(example, t);
    return {
      id: found.id, tono: found.tono, chip: found.chip, titulo: found.titulo,
      monto: found.monto, montoLabel: found.monto_label, cifraTexto: found.cifra_texto,
      fuentes: found.fuentes || [], drill: found.drill, isIllustrative: false,
      summary: found.resumen,
    };
  });

  return (
    <div className="mx-auto max-w-[880px] space-y-8 p-6">
      <div className="flex items-start gap-4 rounded-[var(--radius-card)] border border-violeta/25 bg-violeta/[0.05] p-6">
        <AngelaMark size={40} />
        <div className="flex-1">
          <h1 className="font-display text-xl font-bold leading-tight">{t("aprendizaje.titulo")}</h1>
          <p className="mt-1.5 text-[0.95rem] leading-snug text-tinta">{t("aprendizaje.intro")}</p>
        </div>
      </div>

      <div>
        <h2 className="mb-3 flex items-center gap-1.5 text-[0.8rem] font-semibold uppercase tracking-wide text-tinta-suave">
          <Lightbulb size={14} /> {t("aprendizaje.activo_titulo")}
        </h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {cards.map((c) => (
            <div key={c.id} className="flex flex-col gap-2">
              {handledIds.has(c.id) ? (
                <div className="flex items-center gap-2.5 rounded-[var(--radius-card)] border border-linea bg-papel-hondo/40 p-5 text-[0.9rem] text-tinta-suave">
                  <Check size={16} className="shrink-0 text-salvia" />
                  {t("aprendizaje.feedback_hecho")}
                </div>
              ) : (
                <CardNegocio tono={c.tono} chip={c.chip} titulo={c.titulo} dato={c.summary}
                  monto={c.monto} montoLabel={c.montoLabel} cifraTexto={c.cifraTexto}
                  fuentes={c.fuentes} accion={t("aprendizaje.ver_como")}
                  onClick={() => setSelected(c)} />
              )}
              <span className="self-start rounded-full bg-papel-hondo px-2.5 py-1 text-[0.68rem] font-semibold text-tinta-suave">
                {c.isIllustrative ? t("aprendizaje.chip_ejemplo") : t("aprendizaje.chip_en_tu_negocio")}
              </span>
            </div>
          ))}
        </div>
      </div>

      {history?.length > 0 && (
        <div>
          <h2 className="mb-3 text-[0.8rem] font-semibold uppercase tracking-wide text-tinta-suave">
            {t("aprendizaje.historial_titulo")}
          </h2>
          <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
            {history.map((h) => (
              <div key={h.id} className="flex items-baseline justify-between gap-3 border-b border-linea/60 px-4 py-3 text-[0.86rem] last:border-0">
                <span className="min-w-0 flex-1 truncate">{h.snapshot?.titulo}</span>
                <span className="shrink-0 rounded-full bg-papel-hondo px-2.5 py-1 text-[0.7rem] font-semibold text-tinta-suave">
                  {t(HISTORY_ACTION_LABEL[h.action] || h.action)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <h2 className="mb-3 text-[0.8rem] font-semibold uppercase tracking-wide text-tinta-suave">
          {t("aprendizaje.proximamente_titulo")}
        </h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {UPCOMING.map((f) => {
            const Icon = f.icon;
            return (
              <div key={f.t} className="rounded-[var(--radius-card)] border border-dashed border-linea bg-papel-hondo/40 p-5">
                <Icon size={18} className="text-tinta-suave" />
                <p className="mt-2 font-display text-[1rem] font-bold leading-tight">{t(f.t)}</p>
                <p className="mt-1 text-[0.84rem] leading-snug text-tinta-suave">{t(f.d)}</p>
              </div>
            );
          })}
        </div>
      </div>

      <div className="flex items-start gap-4 rounded-[var(--radius-card)] border border-linea bg-crema p-6 sombra-papel">
        <AngelaMark size={36} />
        <div className="flex-1">
          <p className="text-[0.92rem] leading-snug text-tinta">{t("aprendizaje.cta")}</p>
          <button
            onClick={() => onPreguntar?.(t("aprendizaje.cta_pregunta"))}
            className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-[0.85rem] font-semibold text-crema transition-transform active:scale-95"
          >
            {t("aprendizaje.cta_boton")} <ArrowRight size={15} />
          </button>
        </div>
      </div>

      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-tinta/40 p-4" onClick={() => setSelected(null)}>
          <div onClick={(e) => e.stopPropagation()} className="max-h-[88vh] w-full max-w-xl overflow-y-auto rounded-[var(--radius-card)] border border-linea bg-crema p-6 sombra-alta">
            <DrillNegocio variante="panel" tono={selected.tono} titulo={selected.titulo}
              monto={selected.monto} montoLabel={selected.montoLabel} cifraTexto={selected.cifraTexto}
              porque={selected.drill?.porque || []} grafico={selected.drill?.grafico}
              involucrados={selected.drill?.involucrados || []} supuestos={selected.drill?.supuestos || []}
              fuentes={selected.fuentes || []} />
            {!selected.isIllustrative && (
              <div className="mt-4 rounded-xl border border-linea bg-papel-hondo/40 p-4">
                <p className="text-[0.82rem] font-semibold text-tinta">{t("aprendizaje.feedback_pregunta")}</p>
                <div className="mt-2.5 flex flex-wrap gap-2">
                  {FEEDBACK_ACTIONS.map((f) => (
                    <button key={f.action} disabled={feedbackBusy}
                      onClick={() => giveFeedback(selected.id, f.action)}
                      className="rounded-full border border-linea bg-crema px-3.5 py-1.5 text-[0.82rem] font-semibold text-tinta hover:border-violeta/40 hover:text-violeta disabled:opacity-50">
                      {t(f.lk)}
                    </button>
                  ))}
                </div>
              </div>
            )}
            <button onClick={() => setSelected(null)}
              className="mt-4 w-full rounded-full border border-linea py-2 text-[0.85rem] font-semibold text-tinta-suave hover:text-tinta">
              {t("aprendizaje.cerrar")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

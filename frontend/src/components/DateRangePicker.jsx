import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { CalendarDays, ChevronLeft, ChevronRight, X } from "lucide-react";
import { fecha } from "../lib/format";
import { addDays, ensureHoy, isoHoy, parseIso, toIso } from "../lib/hoy";
import { useLang, useT } from "../lib/i18n";

const WEEKDAYS = { es: ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"], en: ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"] };

function startOfMonth(d) {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}

function monthLabel(d, lang) {
  return new Intl.DateTimeFormat(lang === "en" ? "en-US" : "es-AR", { month: "long", year: "numeric" }).format(d);
}

function daysInGrid(monthDate) {
  const first = startOfMonth(monthDate);
  const startOffset = (first.getDay() + 6) % 7; // Monday-first
  const start = addDays(first, -startOffset);
  const cells = [];
  for (let i = 0; i < 42; i += 1) cells.push(addDays(start, i));
  return cells;
}

function presetsFor(hoy) {
  const today = parseIso(hoy) || new Date();
  const isoToday = toIso(today);
  const monthStart = toIso(new Date(today.getFullYear(), today.getMonth(), 1));
  const lastMonthStart = new Date(today.getFullYear(), today.getMonth() - 1, 1);
  const lastMonthEnd = new Date(today.getFullYear(), today.getMonth(), 0);
  const yearStart = toIso(new Date(today.getFullYear(), 0, 1));
  return [
    { id: "hoy", lk: "crud.rango_hoy", from: isoToday, to: isoToday },
    { id: "7d", lk: "crud.rango_7d", from: toIso(addDays(today, -6)), to: isoToday },
    { id: "30d", lk: "crud.rango_30d", from: toIso(addDays(today, -29)), to: isoToday },
    { id: "mes", lk: "crud.rango_mes", from: monthStart, to: isoToday },
    { id: "mes_pasado", lk: "crud.rango_mes_pasado", from: toIso(lastMonthStart), to: toIso(lastMonthEnd) },
    { id: "anio", lk: "crud.rango_anio", from: yearStart, to: isoToday },
  ];
}

function MonthGrid({ month, from, to, hover, onPick, onHover, today }) {
  const lang = useLang();
  const cells = useMemo(() => daysInGrid(month), [month]);
  const monthIdx = month.getMonth();
  const lo = from && to && from > to ? to : from;
  const hi = from && to && from > to ? from : (to || hover);
  return (
    <div className="w-[16.5rem]">
      <div className="grid grid-cols-7 text-center text-[0.68rem] font-semibold uppercase tracking-wide text-tinta-suave">
        {(WEEKDAYS[lang] || WEEKDAYS.es).map((d) => <span key={d} className="py-1">{d}</span>)}
      </div>
      <div className="grid grid-cols-7">
        {cells.map((d) => {
          const iso = toIso(d);
          const outside = d.getMonth() !== monthIdx;
          const selectedStart = iso === lo;
          const selectedEnd = hi && iso === hi;
          const selected = selectedStart || selectedEnd;
          const mid = lo && hi && iso > lo && iso < hi;
          const isToday = iso === today;
          return (
            <button
              key={iso}
              type="button"
              disabled={outside}
              onMouseEnter={() => onHover(iso)}
              onFocus={() => onHover(iso)}
              onClick={() => onPick(iso)}
              className={`relative h-8 text-[0.8rem] transition-colors ${
                outside ? "text-transparent" : "text-tinta"
              } ${mid ? "bg-violeta-suave" : ""} ${
                selectedStart && hi && hi !== lo ? "rounded-l-full bg-violeta-suave" : ""
              } ${
                selectedEnd && lo && hi !== lo ? "rounded-r-full bg-violeta-suave" : ""
              }`}
            >
              <span className={`inline-flex h-7 w-7 items-center justify-center rounded-full ${
                selected ? "bg-tinta font-semibold text-crema" : ""
              } ${isToday && !selected && !outside ? "ring-1 ring-violeta/50" : ""}`}>
                {outside ? "" : d.getDate()}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default function DateRangePicker({ from, to, onChange }) {
  const t = useT();
  const lang = useLang();
  const [open, setOpen] = useState(false);
  const [hoy, setHoy] = useState(isoHoy);
  const [hover, setHover] = useState(null);
  const [draftFrom, setDraftFrom] = useState(from || "");
  const [draftTo, setDraftTo] = useState(to || "");
  const [view, setView] = useState(() => startOfMonth(parseIso(from) || parseIso(isoHoy()) || new Date()));
  const triggerRef = useRef(null);
  const panelRef = useRef(null);
  const [pos, setPos] = useState(null);

  useEffect(() => { ensureHoy().then(setHoy); }, []);
  useEffect(() => {
    if (!open) {
      setDraftFrom(from || "");
      setDraftTo(to || "");
    }
  }, [from, to, open]);

  useEffect(() => {
    if (!open) return;
    const place = () => {
      const el = triggerRef.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const width = Math.min(560, window.innerWidth - 16);
      let left = r.left;
      if (left + width > window.innerWidth - 8) left = Math.max(8, window.innerWidth - width - 8);
      const below = r.bottom + 8;
      const estHeight = 340;
      const top = below + estHeight > window.innerHeight - 8
        ? Math.max(8, r.top - estHeight - 8)
        : below;
      setPos({ top, left, width });
    };
    place();
    const onDoc = (e) => {
      if (triggerRef.current?.contains(e.target) || panelRef.current?.contains(e.target)) return;
      setOpen(false);
    };
    const onKey = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
    };
  }, [open]);

  const apply = (nextFrom, nextTo) => {
    let a = nextFrom || "";
    let b = nextTo || "";
    if (a && b && a > b) [a, b] = [b, a];
    onChange(a, b);
  };

  const pick = (iso) => {
    if (!draftFrom || (draftFrom && draftTo)) {
      setDraftFrom(iso);
      setDraftTo("");
      setHover(null);
      apply(iso, iso);
      return;
    }
    let a = draftFrom;
    let b = iso;
    if (a > b) [a, b] = [b, a];
    setDraftFrom(a);
    setDraftTo(b);
    apply(a, b);
    setOpen(false);
  };

  const presets = presetsFor(hoy);
  const activePreset = presets.find((p) => p.from === (from || "") && p.to === (to || ""));
  const label = from
    ? (to && to !== from ? `${fecha(from)} – ${fecha(to)}` : fecha(from))
    : t("crud.rango_placeholder");

  const nextMonth = new Date(view.getFullYear(), view.getMonth() + 1, 1);

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        aria-expanded={open}
        aria-haspopup="dialog"
        onClick={(e) => {
          if (e.target.closest("[data-clear-range]")) {
            apply("", "");
            return;
          }
          setOpen((v) => !v);
        }}
        className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[0.82rem] font-semibold transition-colors ${
          from
            ? "border-tinta bg-tinta text-crema"
            : "border-linea text-tinta-suave hover:text-tinta"
        }`}
      >
        <CalendarDays size={13} />
        <span className="max-w-[14rem] truncate">{label}</span>
        {from && (
          <span
            data-clear-range
            className="ml-0.5 rounded-full p-0.5 hover:bg-crema/20"
            aria-hidden
          >
            <X size={12} />
          </span>
        )}
      </button>
      {open && pos && createPortal(
        <div
          ref={panelRef}
          role="dialog"
          aria-label={t("crud.rango_placeholder")}
          style={{ position: "fixed", top: pos.top, left: pos.left, zIndex: 80 }}
          className="sombra-alta flex max-h-[min(28rem,calc(100vh-16px))] overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema"
        >
          <div className="flex w-36 shrink-0 flex-col gap-0.5 border-r border-linea bg-papel p-2">
            {presets.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => { apply(p.from, p.to); setOpen(false); }}
                className={`rounded-xl px-2.5 py-1.5 text-left text-[0.8rem] font-semibold ${
                  activePreset?.id === p.id ? "bg-tinta text-crema" : "text-tinta-suave hover:bg-crema hover:text-tinta"
                }`}
              >
                {t(p.lk)}
              </button>
            ))}
            <button
              type="button"
              onClick={() => { apply("", ""); setOpen(false); }}
              className="mt-auto rounded-xl px-2.5 py-1.5 text-left text-[0.8rem] font-semibold text-tinta-suave hover:text-tinta"
            >
              {t("crud.rango_limpiar")}
            </button>
          </div>
          <div className="p-3">
            <div className="mb-2 flex items-center justify-between">
              <button type="button" onClick={() => setView(new Date(view.getFullYear(), view.getMonth() - 1, 1))}
                className="rounded-lg p-1 text-tinta-suave hover:bg-papel hover:text-tinta" aria-label={t("crud.rango_mes_ant")}>
                <ChevronLeft size={16} />
              </button>
              <div className="flex flex-1 justify-around text-[0.82rem] font-semibold capitalize">
                <span>{monthLabel(view, lang)}</span>
                <span className="hidden sm:inline">{monthLabel(nextMonth, lang)}</span>
              </div>
              <button type="button" onClick={() => setView(new Date(view.getFullYear(), view.getMonth() + 1, 1))}
                className="rounded-lg p-1 text-tinta-suave hover:bg-papel hover:text-tinta" aria-label={t("crud.rango_mes_sig")}>
                <ChevronRight size={16} />
              </button>
            </div>
            <div className="flex gap-4" onMouseLeave={() => setHover(null)}>
              <MonthGrid month={view} from={draftFrom} to={draftTo} hover={hover} onPick={pick} onHover={setHover} today={hoy} />
              <div className="hidden sm:block">
                <MonthGrid month={nextMonth} from={draftFrom} to={draftTo} hover={hover} onPick={pick} onHover={setHover} today={hoy} />
              </div>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-linea pt-3">
              <label className="text-[0.72rem] font-semibold text-tinta-suave">{t("crud.desde")}</label>
              <input type="date" value={draftFrom} onChange={(e) => {
                const v = e.target.value;
                setDraftFrom(v);
                if (v && draftTo) apply(v, draftTo);
                else if (v && !draftTo) apply(v, v);
              }}
                className="rounded-xl border border-linea bg-papel px-2 py-1 text-[0.8rem] outline-none focus:border-tinta/40" />
              <label className="text-[0.72rem] font-semibold text-tinta-suave">{t("crud.hasta")}</label>
              <input type="date" value={draftTo} onChange={(e) => {
                const v = e.target.value;
                setDraftTo(v);
                if (draftFrom && v) apply(draftFrom, v);
              }}
                className="rounded-xl border border-linea bg-papel px-2 py-1 text-[0.8rem] outline-none focus:border-tinta/40" />
            </div>
          </div>
        </div>,
        document.body,
      )}
    </>
  );
}

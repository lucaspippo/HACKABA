import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Check, ChevronDown, Database, FileSpreadsheet, Layers, PencilLine, Search, X } from "lucide-react";
import { useT } from "../lib/i18n";

const CHIP = {
  ink: {
    on: "border-tinta bg-tinta text-crema",
    off: "border-linea text-tinta-suave hover:text-tinta",
  },
  danger: {
    on: "border-rojo bg-rojo text-crema",
    off: "border-rojo/35 text-rojo hover:bg-rojo/5",
  },
  attention: {
    on: "border-oro bg-oro text-crema",
    off: "border-linea text-tinta-suave hover:text-tinta",
  },
};

export function FilterChip({ icon: Icon, active, onClick, children, count, tone = "ink" }) {
  const pal = CHIP[tone] || CHIP.ink;
  return (
    <button
      type="button"
      aria-pressed={!!active}
      onClick={onClick}
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-semibold transition-colors ${
        active ? pal.on : pal.off
      }`}
    >
      {Icon && <Icon size={13} />}
      {children}
      {count != null && count !== "" && (
        <span className={active ? "opacity-80" : "text-tinta-suave/70"}>{count}</span>
      )}
    </button>
  );
}

export function FilterDivider() {
  return <span className="mx-0.5 hidden h-4 w-px bg-linea sm:block" aria-hidden />;
}

export function FilterRail({ children, onClear, clearLabel }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {children}
      {onClear && (
        <button
          type="button"
          onClick={onClear}
          className="inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-1.5 text-sm font-semibold text-tinta-suave hover:text-tinta"
        >
          <X size={12} /> {clearLabel}
        </button>
      )}
    </div>
  );
}

const SOURCE_OPTS = [
  { id: "all", lk: "crud.source_all", icon: Layers },
  { id: "odoo", lk: "crud.source_odoo", icon: Database },
  { id: "csv", lk: "crud.source_csv", icon: FileSpreadsheet },
  { id: "manual", lk: "crud.source_manual", icon: PencilLine },
];

export function SourceChips({ value, onChange, t }) {
  return SOURCE_OPTS.map((o) => (
    <FilterChip key={o.id} icon={o.icon} active={value === o.id} onClick={() => onChange(o.id)}>
      {t(o.lk)}
    </FilterChip>
  ));
}

export function uniqueValues(rows, key) {
  const used = new Set();
  const out = [];
  for (const row of rows || []) {
    const v = row?.[key];
    if (v == null || v === "") continue;
    const s = String(v);
    if (!used.has(s)) {
      used.add(s);
      out.push(s);
    }
  }
  out.sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
  return out;
}

export function FacetSelect({ icon: Icon, label, value, options, onChange, placeholder }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const triggerRef = useRef(null);
  const panelRef = useRef(null);
  const [pos, setPos] = useState(null);
  const opts = options || [];
  const filtered = q.trim()
    ? opts.filter((o) => o.toLowerCase().includes(q.trim().toLowerCase()))
    : opts;
  const shown = value || placeholder || label;

  useEffect(() => {
    if (!open) return;
    const place = () => {
      const el = triggerRef.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const width = Math.max(r.width, 220);
      let left = r.left;
      if (left + width > window.innerWidth - 8) left = Math.max(8, window.innerWidth - width - 8);
      setPos({ top: r.bottom + 6, left, width, maxHeight: Math.min(280, window.innerHeight - r.bottom - 16) });
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

  if (opts.length === 0 && !value) return null;

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        aria-expanded={open}
        aria-haspopup="listbox"
        onClick={() => setOpen((v) => !v)}
        className={`inline-flex max-w-[16rem] items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-semibold transition-colors ${
          value ? "border-tinta bg-tinta text-crema" : "border-linea text-tinta-suave hover:text-tinta"
        }`}
      >
        {Icon && <Icon size={13} className="shrink-0" />}
        <span className="truncate">{shown}</span>
        <ChevronDown size={12} className={`shrink-0 opacity-70 ${open ? "rotate-180" : ""}`} />
      </button>
      {open && pos && createPortal(
        <div
          ref={panelRef}
          role="listbox"
          style={{ position: "fixed", top: pos.top, left: pos.left, width: pos.width, zIndex: 80 }}
          className="sombra-alta overflow-hidden rounded-xl border border-linea bg-crema"
        >
          <div className="relative border-b border-linea">
            <Search size={13} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-tinta-suave" />
            <input
              autoFocus
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={t("crud.facet_buscar")}
              className="w-full bg-transparent py-2 pl-8 pr-3 text-sm outline-none"
            />
          </div>
          <div className="overflow-y-auto py-1" style={{ maxHeight: pos.maxHeight }}>
            <button
              type="button"
              onClick={() => { onChange(""); setOpen(false); setQ(""); }}
              className={`flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm hover:bg-papel ${
                !value ? "font-semibold text-tinta" : "text-tinta-suave"
              }`}
            >
              <span className="w-4">{!value && <Check size={13} />}</span>
              {t("crud.facet_todos")}
            </button>
            {filtered.map((o) => (
              <button
                key={o}
                type="button"
                onClick={() => { onChange(o); setOpen(false); setQ(""); }}
                className={`flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm hover:bg-papel ${
                  value === o ? "font-semibold text-tinta" : "text-tinta"
                }`}
              >
                <span className="w-4">{value === o && <Check size={13} />}</span>
                <span className="truncate">{o}</span>
              </button>
            ))}
            {filtered.length === 0 && (
              <p className="px-3 py-2 text-sm text-tinta-suave">{t("crud.facet_vacio")}</p>
            )}
          </div>
        </div>,
        document.body,
      )}
    </>
  );
}

export function GroupBySelect({ options, value, onChange }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  const triggerRef = useRef(null);
  const panelRef = useRef(null);
  const [pos, setPos] = useState(null);
  const current = options.find((o) => o.key === value);

  useEffect(() => {
    if (!open) return;
    const place = () => {
      const el = triggerRef.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      setPos({ top: r.bottom + 6, left: r.left, minWidth: r.width });
    };
    place();
    const onDoc = (e) => {
      if (triggerRef.current?.contains(e.target) || panelRef.current?.contains(e.target)) return;
      setOpen(false);
    };
    const onKey = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  if (!options?.length) return null;

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-2 text-sm font-semibold ${
          value ? "border-tinta bg-tinta text-crema" : "border-linea text-tinta-suave hover:text-tinta"
        }`}
      >
        <Layers size={15} />
        {value ? t("crud.agrupado", { campo: current?.label || value }) : t("crud.agrupar")}
        <ChevronDown size={12} className="opacity-70" />
      </button>
      {open && pos && createPortal(
        <div
          ref={panelRef}
          role="listbox"
          style={{ position: "fixed", top: pos.top, left: pos.left, minWidth: pos.minWidth, zIndex: 80 }}
          className="sombra-alta overflow-hidden rounded-xl border border-linea bg-crema py-1"
        >
          <button
            type="button"
            onClick={() => { onChange(null); setOpen(false); }}
            className={`block w-full px-3 py-1.5 text-left text-sm hover:bg-papel ${
              !value ? "font-semibold" : "text-tinta-suave"
            }`}
          >
            {t("crud.agrupar_ninguno")}
          </button>
          {options.map((o) => (
            <button
              key={o.key}
              type="button"
              onClick={() => { onChange(o.key); setOpen(false); }}
              className={`block w-full px-3 py-1.5 text-left text-sm hover:bg-papel ${
                value === o.key ? "font-semibold" : ""
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>,
        document.body,
      )}
    </>
  );
}

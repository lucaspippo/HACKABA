import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { Search, ChevronUp, ChevronDown, ChevronsUpDown, Plus, Download, ChevronRight } from "lucide-react";
import { GroupBySelect } from "./FilterRail";
import { num } from "../lib/format";
import { useT } from "../lib/i18n";

export { SourceChips } from "./FilterRail";

export function SourceBadge({ source, t }) {
  const odoo = source === "odoo";
  const manual = source === "manual";
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
      odoo ? "bg-violeta/12 text-violeta"
        : manual ? "bg-salvia/15 text-salvia"
          : "bg-papel-hondo text-tinta-suave"}`}>
      {t(odoo ? "crud.source_odoo" : manual ? "crud.source_manual" : "crud.source_csv")}
    </span>
  );
}

function groupValue(fila, col) {
  const raw = col.groupBy ? col.groupBy(fila) : fila[col.key];
  if (raw == null || raw === "") return "";
  return String(raw);
}

// Shared CRUD datagrid: search, optional facet slot, sortable columns,
// group-by, create + CSV in the header, and optional infinite-scroll.
export default function TablaCRUD({
  columnas, filas, idDe = (f) => f.id, q, onQ, buscarPlaceholder,
  acciones, vacio, accionHeader,
  titulo, conteo,
  onCrear, crearLabel,
  onExport, exportando,
  filtros,
  onSort, orden: ordenExterno,
  onLoadMore, hasMore, cargandoMas,
  cargando,
  onLimpiar,
}) {
  const t = useT();
  const [ordenLocal, setOrdenLocal] = useState({ campo: null, dir: 1 });
  const orden = onSort ? (ordenExterno || { campo: null, dir: 1 }) : ordenLocal;
  const sentinel = useRef(null);
  const groupables = useMemo(
    () => columnas.filter((c) => c.groupable).map((c) => ({ key: c.key, label: c.label })),
    [columnas],
  );
  const [groupKey, setGroupKey] = useState(null);
  const [collapsed, setCollapsed] = useState(() => new Set());

  const ordenadas = useMemo(() => {
    if (onSort || !orden.campo) return filas;
    const col = columnas.find((c) => c.key === orden.campo);
    const val = col?.ordenarPor || ((f) => f[orden.campo]);
    return [...filas].sort((a, b) => {
      const va = val(a), vb = val(b);
      if (va == null) return 1;
      if (vb == null) return -1;
      if (typeof va === "string") return va.localeCompare(vb) * orden.dir;
      return (va - vb) * orden.dir;
    });
  }, [filas, orden, columnas, onSort]);

  const grouped = useMemo(() => {
    if (!groupKey) return null;
    const col = columnas.find((c) => c.key === groupKey);
    if (!col) return null;
    const map = new Map();
    for (const fila of ordenadas) {
      const k = groupValue(fila, col);
      if (!map.has(k)) map.set(k, []);
      map.get(k).push(fila);
    }
    return { col, buckets: [...map.entries()] };
  }, [groupKey, ordenadas, columnas]);

  const clickCol = (key, sortable) => {
    if (!sortable) return;
    if (onSort) {
      const nextDir = orden.campo === key ? -orden.dir : 1;
      onSort(key, nextDir);
      return;
    }
    setOrdenLocal((o) => (o.campo === key ? { campo: key, dir: -o.dir } : { campo: key, dir: 1 }));
  };

  useEffect(() => {
    if (!onLoadMore || !hasMore) return;
    const el = sentinel.current;
    if (!el) return;
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) onLoadMore();
    }, { rootMargin: "160px" });
    io.observe(el);
    return () => io.disconnect();
  }, [onLoadMore, hasMore, ordenadas.length]);

  useEffect(() => { setCollapsed(new Set()); }, [groupKey]);

  const toggleGroup = (key) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const toolbar = onQ || onCrear || onExport || titulo || groupables.length > 0;
  const colCount = columnas.length + (acciones ? 1 : 0);

  const renderRows = (rows) => rows.map((fila) => (
    <tr key={idDe(fila)} className="border-b border-linea/70 last:border-0 hover:bg-papel-hondo/30">
      {columnas.map((c) => (
        <td key={c.key} className={`px-4 py-2.5 ${c.align === "right" ? "text-right" : ""} ${c.plata ? "plata" : ""}`}>
          {c.render ? c.render(fila) : (fila[c.key] ?? "—")}
        </td>
      ))}
      {acciones && <td className="px-4 py-2.5">{acciones(fila)}</td>}
    </tr>
  ));

  return (
    <div className="space-y-3">
      <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
        {toolbar && (
          <div className="flex flex-wrap items-center gap-3 border-b border-linea p-4">
            {titulo && <h2 className="font-display text-lg font-bold">{titulo}</h2>}
            {conteo != null && <span className="text-sm text-tinta-suave">{conteo}</span>}
            {onQ && (
              <div className={`relative ${titulo ? "ml-auto" : ""} max-w-sm min-w-[12rem] flex-1`}>
                <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-tinta-suave" />
                <input value={q} onChange={(e) => onQ(e.target.value)} placeholder={buscarPlaceholder}
                  className="w-full rounded-full border border-linea bg-papel py-2 pl-9 pr-3 text-sm outline-none focus:border-tinta/40" />
              </div>
            )}
            {groupables.length > 0 && (
              <GroupBySelect options={groupables} value={groupKey} onChange={setGroupKey} />
            )}
            {onExport && (
              <button type="button" onClick={onExport} disabled={exportando}
                className="inline-flex items-center gap-1.5 rounded-full border border-linea px-3.5 py-2 text-sm font-semibold text-tinta-suave hover:text-tinta disabled:opacity-50">
                <Download size={15} /> {exportando ? "…" : "CSV"}
              </button>
            )}
            {onCrear && (
              <button type="button" onClick={onCrear}
                className={`inline-flex items-center gap-1.5 rounded-full bg-violeta px-3.5 py-2 text-sm font-semibold text-crema ${titulo || onQ ? "" : "ml-auto"}`}>
                <Plus size={15} /> {crearLabel}
              </button>
            )}
          </div>
        )}
        {filtros && (
          <div className="border-b border-linea px-4 py-2.5">
            {filtros}
          </div>
        )}

        {cargando && ordenadas.length === 0 ? (
          <p className="px-4 py-8 text-sm text-tinta-suave">{vacio}</p>
        ) : ordenadas.length === 0 ? (
          <div className="px-4 py-8 text-center">
            <p className="text-sm text-tinta-suave">{vacio}</p>
            {onLimpiar && (
              <button type="button" onClick={onLimpiar}
                className="mt-3 text-sm font-semibold text-hielo hover:underline">
                {t("crud.limpiar_filtros")}
              </button>
            )}
          </div>
        ) : (
          <div className={onLoadMore ? "max-h-[min(70vh,40rem)] overflow-auto" : "overflow-x-auto"}>
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 z-[1] bg-crema">
                <tr className="border-b border-linea text-xs uppercase tracking-wide text-tinta-suave">
                  {columnas.map((c) => (
                    <th key={c.key} onClick={() => clickCol(c.key, c.sortable)}
                      className={`px-4 py-2.5 font-semibold ${c.align === "right" ? "text-right" : ""} ${c.sortable ? "cursor-pointer select-none hover:text-tinta" : ""}`}>
                      <span className={`inline-flex items-center gap-1 ${c.align === "right" ? "flex-row-reverse" : ""}`}>
                        {c.label}
                        {c.sortable && (
                          orden.campo === c.key
                            ? (orden.dir === 1 ? <ChevronUp size={12} /> : <ChevronDown size={12} />)
                            : <ChevronsUpDown size={12} className="opacity-40" />
                        )}
                      </span>
                    </th>
                  ))}
                  {acciones && <th className="px-4 py-2.5">{accionHeader || ""}</th>}
                </tr>
              </thead>
              <tbody>
                {grouped ? grouped.buckets.map(([key, rows]) => {
                  const closed = collapsed.has(key);
                  const title = key === "" ? t("crud.sin_valor") : (
                    grouped.col.groupLabel ? grouped.col.groupLabel(key, rows) : key
                  );
                  return (
                    <Fragment key={key || "__empty"}>
                      <tr className="border-b border-linea bg-papel-hondo/70">
                        <td colSpan={colCount} className="px-3 py-1.5">
                          <button
                            type="button"
                            onClick={() => toggleGroup(key)}
                            aria-expanded={!closed}
                            className="flex w-full items-center gap-2 text-left text-sm font-semibold text-tinta"
                          >
                            <ChevronRight size={14} className={`shrink-0 text-tinta-suave transition-transform ${closed ? "" : "rotate-90"}`} />
                            <span className="min-w-0 flex-1 truncate">{title}</span>
                            <span className="plata text-xs font-normal text-tinta-suave">
                              {t("crud.grupo_n", { n: num(rows.length) })}
                            </span>
                          </button>
                        </td>
                      </tr>
                      {!closed && renderRows(rows)}
                    </Fragment>
                  );
                }) : renderRows(ordenadas)}
              </tbody>
            </table>
            {onLoadMore && (
              <div ref={sentinel} className="px-4 py-3 text-center text-sm text-tinta-suave">
                {cargandoMas ? "…" : hasMore ? "" : ""}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}


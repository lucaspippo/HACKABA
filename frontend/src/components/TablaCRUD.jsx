import { useEffect, useMemo, useRef, useState } from "react";
import { Search, ChevronUp, ChevronDown, ChevronsUpDown, Plus, Download } from "lucide-react";

// Shared CRUD datagrid: search, optional facet slot, sortable columns,
// create + CSV in the header (same chrome as Inventario "Todo tu stock"),
// and optional infinite-scroll loading of further pages.
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
}) {
  const [ordenLocal, setOrdenLocal] = useState({ campo: null, dir: 1 });
  const orden = onSort ? (ordenExterno || { campo: null, dir: 1 }) : ordenLocal;
  const sentinel = useRef(null);

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

  const toolbar = onQ || onCrear || onExport || titulo;

  return (
    <div className="space-y-3">
      <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
        {toolbar && (
          <div className="flex flex-wrap items-center gap-3 border-b border-linea p-4">
            {titulo && <h2 className="font-display text-[1.1rem] font-bold">{titulo}</h2>}
            {conteo != null && <span className="text-[0.8rem] text-tinta-suave">{conteo}</span>}
            {onQ && (
              <div className={`relative ${titulo ? "ml-auto" : ""} max-w-sm min-w-[12rem] flex-1`}>
                <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-tinta-suave" />
                <input value={q} onChange={(e) => onQ(e.target.value)} placeholder={buscarPlaceholder}
                  className="w-full rounded-full border border-linea bg-papel py-2 pl-9 pr-3 text-[0.86rem] outline-none focus:border-tinta/40" />
              </div>
            )}
            {onExport && (
              <button type="button" onClick={onExport} disabled={exportando}
                className="inline-flex items-center gap-1.5 rounded-full border border-linea px-3.5 py-2 text-[0.86rem] font-semibold text-tinta-suave hover:text-tinta disabled:opacity-50">
                <Download size={15} /> {exportando ? "…" : "CSV"}
              </button>
            )}
            {onCrear && (
              <button type="button" onClick={onCrear}
                className={`inline-flex items-center gap-1.5 rounded-full bg-violeta px-3.5 py-2 text-[0.86rem] font-semibold text-crema ${titulo || onQ ? "" : "ml-auto"}`}>
                <Plus size={15} /> {crearLabel}
              </button>
            )}
          </div>
        )}
        {filtros && (
          <div className="flex flex-wrap items-center gap-2 border-b border-linea px-4 py-2.5">
            {filtros}
          </div>
        )}

        {cargando && ordenadas.length === 0 ? (
          <p className="px-4 py-8 text-[0.9rem] text-tinta-suave">{vacio}</p>
        ) : ordenadas.length === 0 ? (
          <p className="px-4 py-8 text-[0.9rem] text-tinta-suave">{vacio}</p>
        ) : (
          <div className={onLoadMore ? "max-h-[min(70vh,40rem)] overflow-auto" : "overflow-x-auto"}>
            <table className="w-full text-left text-[0.86rem]">
              <thead className="sticky top-0 bg-crema">
                <tr className="border-b border-linea text-[0.72rem] uppercase tracking-wide text-tinta-suave">
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
                {ordenadas.map((fila) => (
                  <tr key={idDe(fila)} className="border-b border-linea/70 last:border-0 hover:bg-papel-hondo/30">
                    {columnas.map((c) => (
                      <td key={c.key} className={`px-4 py-2.5 ${c.align === "right" ? "text-right" : ""} ${c.plata ? "plata" : ""}`}>
                        {c.render ? c.render(fila) : (fila[c.key] ?? "—")}
                      </td>
                    ))}
                    {acciones && <td className="px-4 py-2.5">{acciones(fila)}</td>}
                  </tr>
                ))}
              </tbody>
            </table>
            {onLoadMore && (
              <div ref={sentinel} className="px-4 py-3 text-center text-[0.8rem] text-tinta-suave">
                {cargandoMas ? "…" : hasMore ? "" : ""}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function SourceChips({ value, onChange, t }) {
  const opts = [
    { id: "all", lk: "crud.source_all" },
    { id: "odoo", lk: "crud.source_odoo" },
    { id: "csv", lk: "crud.source_csv" },
    { id: "manual", lk: "crud.source_manual" },
  ];
  return opts.map((o) => (
    <button key={o.id} type="button" onClick={() => onChange(o.id)}
      className={`rounded-full px-3 py-1 text-[0.82rem] font-semibold ${
        value === o.id ? "bg-tinta text-crema" : "border border-linea text-tinta-suave hover:text-tinta"}`}>
      {t(o.lk)}
    </button>
  ));
}

export function SourceBadge({ source, t }) {
  const odoo = source === "odoo";
  const manual = source === "manual";
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-[0.72rem] font-semibold ${
      odoo ? "bg-violeta/12 text-violeta"
        : manual ? "bg-salvia/15 text-salvia"
          : "bg-papel-hondo text-tinta-suave"}`}>
      {t(odoo ? "crud.source_odoo" : manual ? "crud.source_manual" : "crud.source_csv")}
    </span>
  );
}

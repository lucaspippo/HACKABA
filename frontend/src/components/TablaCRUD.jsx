import { useMemo, useState } from "react";
import { Search, ChevronUp, ChevronDown, ChevronsUpDown } from "lucide-react";

// Tabla compartida por las pantallas CRUD del inventario (Ubicaciones,
// Proveedores, Lotes, Órdenes de compra): mismo look — una fila por
// registro, buscador arriba, columnas ordenables por click — en vez de
// que cada pantalla inventara su propia lista/tarjetas.
export default function TablaCRUD({
  columnas, filas, idDe = (f) => f.id, q, onQ, buscarPlaceholder,
  acciones, vacio, accionHeader,
}) {
  const [orden, setOrden] = useState({ campo: null, dir: 1 });

  const ordenadas = useMemo(() => {
    if (!orden.campo) return filas;
    const col = columnas.find((c) => c.key === orden.campo);
    const val = col?.ordenarPor || ((f) => f[orden.campo]);
    return [...filas].sort((a, b) => {
      const va = val(a), vb = val(b);
      if (va == null) return 1;
      if (vb == null) return -1;
      if (typeof va === "string") return va.localeCompare(vb) * orden.dir;
      return (va - vb) * orden.dir;
    });
  }, [filas, orden, columnas]);

  const clickCol = (key, sortable) => {
    if (!sortable) return;
    setOrden((o) => (o.campo === key ? { campo: key, dir: -o.dir } : { campo: key, dir: 1 }));
  };

  return (
    <div className="space-y-3">
      {onQ && (
        <div className="relative max-w-sm">
          <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-tinta-suave" />
          <input value={q} onChange={(e) => onQ(e.target.value)} placeholder={buscarPlaceholder}
            className="w-full rounded-full border border-linea bg-papel py-2 pl-9 pr-3 text-[0.86rem] outline-none focus:border-tinta/40" />
        </div>
      )}

      {ordenadas.length === 0 ? (
        <p className="text-[0.9rem] text-tinta-suave">{vacio}</p>
      ) : (
        <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
          <table className="w-full text-left text-[0.86rem]">
            <thead>
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
        </div>
      )}
    </div>
  );
}

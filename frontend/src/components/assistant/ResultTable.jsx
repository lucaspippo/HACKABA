import { peso, num } from "../../lib/format";

// Formatting heuristic by column name: same idea as the backend's
// _con_pesos() (every amount displays in pesos), but purely presentational —
// it doesn't change the number, only how it prints.
const MONEY_KEYS = /(monto|inmovilizado|precio|costo|saldo|total|plata|deuda|importe|venta)/i;

function formatCell(key, value) {
  if (value == null) return "—";
  if (typeof value === "number") {
    return MONEY_KEYS.test(key) ? peso(value) : num(value);
  }
  if (typeof value === "boolean") return value ? "sí" : "no";
  if (Array.isArray(value)) return value.join(", ");
  return String(value);
}

function titleForKey(key) {
  return key.replaceAll("_", " ");
}

// Compact, dependency-free table sharing the chat's palette (bg-crema,
// border-linea). `rows` is an array of homogeneous objects; columns come
// from the UNION of their keys (up to 6, so it fits the chat's narrow panel).
export default function ResultTable({ rows, limit = 8 }) {
  if (!Array.isArray(rows) || rows.length === 0) return null;
  const keys = [...new Set(rows.flatMap((r) => Object.keys(r || {})))]
    .filter((k) => !Array.isArray(rows[0]?.[k]) || typeof rows[0][k][0] !== "object")
    .slice(0, 6);
  if (keys.length === 0) return null;
  const visible = rows.slice(0, limit);

  return (
    <div className="mt-2 overflow-x-auto rounded-xl border border-linea">
      <table className="w-full text-left text-xs">
        <thead>
          <tr className="border-b border-linea bg-papel/60">
            {keys.map((c) => (
              <th key={c} className="whitespace-nowrap px-2.5 py-1.5 font-semibold capitalize text-tinta-suave">
                {titleForKey(c)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {visible.map((r, i) => (
            <tr key={i} className={i % 2 ? "bg-crema/40" : ""}>
              {keys.map((c) => (
                <td key={c} className="whitespace-nowrap px-2.5 py-1.5 tabular-nums text-tinta">
                  {formatCell(c, r[c])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > limit && (
        <p className="border-t border-linea px-2.5 py-1 text-xs text-tinta-suave">
          +{rows.length - limit} más
        </p>
      )}
    </div>
  );
}

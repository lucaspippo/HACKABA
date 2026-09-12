import { peso, num } from "../../lib/format";

// Heurística de formato por nombre de columna: la misma idea que _con_pesos()
// en el backend (todo monto se ve en pesos), pero puramente de presentación —
// no cambia el número, sólo cómo se imprime.
const CLAVES_PLATA = /(monto|inmovilizado|precio|costo|saldo|total|plata|deuda|importe|venta)/i;

function formatearCelda(clave, valor) {
  if (valor == null) return "—";
  if (typeof valor === "number") {
    return CLAVES_PLATA.test(clave) ? peso(valor) : num(valor);
  }
  if (typeof valor === "boolean") return valor ? "sí" : "no";
  if (Array.isArray(valor)) return valor.join(", ");
  return String(valor);
}

function tituloDeClave(clave) {
  return clave.replaceAll("_", " ");
}

// Tabla compacta y sin dependencias: misma paleta que el resto del chat de
// Ángela (bg-crema, border-linea). `filas` es un array de objetos homogéneos;
// las columnas salen de la UNIÓN de sus claves (hasta 6, para que entre en el
// panel angosto del chat).
export default function AngelaTable({ filas, limite = 8 }) {
  if (!Array.isArray(filas) || filas.length === 0) return null;
  const claves = [...new Set(filas.flatMap((f) => Object.keys(f || {})))]
    .filter((k) => !Array.isArray(filas[0]?.[k]) || typeof filas[0][k][0] !== "object")
    .slice(0, 6);
  if (claves.length === 0) return null;
  const visibles = filas.slice(0, limite);

  return (
    <div className="mt-2 overflow-x-auto rounded-xl border border-linea">
      <table className="w-full text-left text-[0.78rem]">
        <thead>
          <tr className="border-b border-linea bg-papel/60">
            {claves.map((c) => (
              <th key={c} className="whitespace-nowrap px-2.5 py-1.5 font-semibold capitalize text-tinta-suave">
                {tituloDeClave(c)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {visibles.map((f, i) => (
            <tr key={i} className={i % 2 ? "bg-crema/40" : ""}>
              {claves.map((c) => (
                <td key={c} className="whitespace-nowrap px-2.5 py-1.5 tabular-nums text-tinta">
                  {formatearCelda(c, f[c])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {filas.length > limite && (
        <p className="border-t border-linea px-2.5 py-1 text-[0.72rem] text-tinta-suave">
          +{filas.length - limite} más
        </p>
      )}
    </div>
  );
}

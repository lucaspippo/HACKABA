import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { SERIES } from "../../lib/paleta";
import { gridProps, ejeX, ejeY, tooltipProps } from "../charts/tema";
import { peso, num } from "../../lib/format";

// Mini gráfico de barras para puntos {x, y} que Ángela trajo con una
// herramienta de consulta (consultar_serie con pocos puntos no-temporales:
// el top de un ranking). Las series temporales completas no viajan al chat
// —quedan en el widget del panel—, así que esto es siempre un puñado de
// categorías, nunca una línea de tiempo.
export default function AngelaMiniChart({ puntos, formato = "moneda" }) {
  if (!Array.isArray(puntos) || puntos.length === 0) return null;
  const fmt = formato === "moneda" ? peso : num;
  const datos = puntos.slice(0, 8).map((p) => ({ nombre: String(p.x ?? p.etiqueta ?? ""), valor: p.y ?? p.valor ?? 0 }));

  return (
    <div className="mt-2 h-40 w-full rounded-xl border border-linea bg-papel/40 p-2">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={datos} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid {...gridProps} />
          <XAxis dataKey="nombre" {...ejeX()} interval={0} angle={-15} textAnchor="end" height={36} />
          <YAxis {...ejeY()} width={40} tickFormatter={(v) => fmt(v)} />
          <Tooltip {...tooltipProps} formatter={(v) => fmt(v)} />
          <Bar dataKey="valor" radius={[4, 4, 0, 0]}>
            {datos.map((_, i) => (
              <Cell key={i} fill={SERIES[i % SERIES.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

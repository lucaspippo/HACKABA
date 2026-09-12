import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { SERIES } from "../../lib/paleta";
import { gridProps, ejeX, ejeY, tooltipProps } from "../charts/tema";
import { peso, num } from "../../lib/format";

// Mini bar chart for {x, y} points a tool result carried (a consultar_serie
// with a handful of non-temporal points: the top of a ranking). Full
// temporal series don't travel to the chat — they live in the panel's
// widget — so this is always a handful of categories, never a timeline.
export default function MiniChart({ points, format = "moneda" }) {
  if (!Array.isArray(points) || points.length === 0) return null;
  const fmt = format === "moneda" ? peso : num;
  const data = points.slice(0, 8).map((p) => ({ name: String(p.x ?? p.etiqueta ?? ""), value: p.y ?? p.valor ?? 0 }));

  return (
    <div className="mt-2 h-40 w-full rounded-xl border border-linea bg-papel/40 p-2">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid {...gridProps} />
          <XAxis dataKey="name" {...ejeX()} interval={0} angle={-15} textAnchor="end" height={36} />
          <YAxis {...ejeY()} width={40} tickFormatter={(v) => fmt(v)} />
          <Tooltip {...tooltipProps} formatter={(v) => fmt(v)} />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {data.map((_, i) => (
              <Cell key={i} fill={SERIES[i % SERIES.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

import { Loader2, Wrench } from "lucide-react";
import ResultTable from "./ResultTable";
import MiniChart from "./MiniChart";
import { peso, num } from "../../lib/format";

// Human labels for the most common tools — everything else falls back to the
// tool name with underscores turned into spaces; no need to keep an entry
// for each of angela.py's ~40 tools for this to read well.
const LABELS = {
  resumen_negocio: "Mirando el resumen del negocio",
  plata_en: "Calculando plata inmovilizada",
  buscar_productos: "Buscando productos",
  top_inmovilizado: "Buscando dónde está la plata parada",
  listar_grupo: "Listando el grupo",
  navegar_a: "Llevándote a la sección",
  consultar_serie: "Consultando los datos",
  cuentas_corrientes: "Revisando cuentas corrientes",
  consultar_deposito: "Revisando el depósito",
  consultar_envios: "Revisando envíos",
  consultar_cruces: "Cruzando comprobantes",
  consultar_evolucion: "Mirando la evolución",
  consultar_compras: "Revisando compras",
  estado_caja: "Mirando la caja",
  crear_widget: "Armando un widget para tu panel",
  crear_recordatorio: "Anotando el recordatorio",
  mis_recordatorios: "Buscando tus recordatorios",
  crear_objetivo: "Creando el objetivo",
  proponer_correccion: "Calculando el impacto de la corrección",
  aplicar_correccion_en_lote: "Aplicando la corrección",
  generar_documento: "Generando el documento",
  consultar_manual: "Revisando el manual",
};

function labelFor(toolName) {
  return LABELS[toolName] || toolName.replaceAll("_", " ");
}

// A "small" object (few scalar keys) renders as a compact key/value grid —
// the generic fallback for tools with no dedicated renderer above.
function GenericResult({ result }) {
  if (result == null) return null;
  if (typeof result !== "object" || Array.isArray(result)) {
    return <p className="mt-1 text-[0.82rem] text-tinta">{String(result)}</p>;
  }
  if (result.error) {
    return <p className="mt-1 text-[0.82rem] text-rojo-hondo">{String(result.error || result.motivo)}</p>;
  }
  const entries = Object.entries(result).filter(
    ([, v]) => v == null || typeof v === "string" || typeof v === "number" || typeof v === "boolean"
  );
  if (entries.length === 0) return null;
  return (
    <dl className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-1 text-[0.8rem]">
      {entries.slice(0, 8).map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="capitalize text-tinta-suave">{k.replaceAll("_", " ")}</dt>
          <dd className="tabular-nums text-tinta">
            {typeof v === "number" ? (/monto|inmovilizado|precio|costo|saldo|total|plata|deuda/i.test(k) ? peso(v) : num(v)) : String(v ?? "—")}
          </dd>
        </div>
      ))}
    </dl>
  );
}

// Dispatch by the SHAPE of the result, not by tool name: any of angela.py's
// ~40 tools that returns `items`/a list of homogeneous objects renders as a
// table; a non-temporal `consultar_serie` with `top` renders as a mini chart;
// everything else falls back to the generic key/value summary. That way a
// new backend tool already gets a reasonable UI without touching the
// frontend.
function Result({ toolName, result }) {
  if (result == null) return null;
  if (toolName === "navegar_a" && result.navegado_a) {
    return <p className="mt-1 text-[0.82rem] text-tinta-suave">→ te llevé a <b className="text-tinta">{result.navegado_a}</b></p>;
  }
  const items = Array.isArray(result.items) ? result.items
    : Array.isArray(result.recordatorios) ? result.recordatorios
    : Array.isArray(result) ? result
    : null;
  if (items && items.length && typeof items[0] === "object") {
    return (
      <>
        {result.total_inmovilizado_listado != null && (
          <p className="mt-1 text-[0.82rem] text-tinta">
            Total: <b>{peso(result.total_inmovilizado_listado)}</b>
          </p>
        )}
        <ResultTable rows={items} />
      </>
    );
  }
  if (Array.isArray(result.series)) {
    const withTop = result.series.find((s) => Array.isArray(s.top) && s.top.length);
    if (withTop) return <MiniChart points={withTop.top} />;
  }
  return <GenericResult result={result} />;
}

// The card representing ONE tool call inside a message: a badge with the
// name while it runs, the rendered result (by shape) once it arrives.
export default function ToolCallCard({ part }) {
  const isRunning = part.status?.type === "running" && part.result === undefined;
  return (
    <div className="my-1.5 rounded-xl border border-linea/70 bg-papel/50 px-3 py-2">
      <div className="flex items-center gap-2 text-[0.8rem] font-medium text-tinta-suave">
        {isRunning ? (
          <Loader2 size={14} className="shrink-0 animate-spin text-violeta" />
        ) : (
          <Wrench size={14} className="shrink-0 text-violeta" />
        )}
        <span>{labelFor(part.toolName)}</span>
      </div>
      {!isRunning && <Result toolName={part.toolName} result={part.result} />}
    </div>
  );
}

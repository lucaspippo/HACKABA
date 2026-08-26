import { Loader2, Wrench } from "lucide-react";
import AngelaTable from "./AngelaTable";
import AngelaMiniChart from "./AngelaMiniChart";
import { peso, num } from "../../lib/format";

// Nombres humanos para las tools más comunes (P·chat) — el resto cae al
// nombre de la tool con guiones bajos como espacios; no hace falta mantener
// una entrada por cada una de las ~40 tools de angela.py para que se lea bien.
const ETIQUETAS = {
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

function etiquetaDe(toolName) {
  return ETIQUETAS[toolName] || toolName.replaceAll("_", " ");
}

// Un objeto "chico" (pocas claves escalares) se muestra como grilla clave/valor
// compacta — el fallback genérico para tools sin renderer dedicado arriba.
function ResultadoGenerico({ result }) {
  if (result == null) return null;
  if (typeof result !== "object" || Array.isArray(result)) {
    return <p className="mt-1 text-[0.82rem] text-tinta">{String(result)}</p>;
  }
  if (result.error) {
    return <p className="mt-1 text-[0.82rem] text-rojo-hondo">{String(result.error || result.motivo)}</p>;
  }
  const entradas = Object.entries(result).filter(
    ([, v]) => v == null || typeof v === "string" || typeof v === "number" || typeof v === "boolean"
  );
  if (entradas.length === 0) return null;
  return (
    <dl className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-1 text-[0.8rem]">
      {entradas.slice(0, 8).map(([k, v]) => (
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

// Dispatcher por FORMA del resultado, no por nombre de tool: cualquiera de las
// ~40 tools de angela.py que devuelva `items`/una lista de objetos homogéneos
// sale como tabla; una `consultar_serie` no-temporal con `top` sale como mini
// gráfico; todo lo demás cae al resumen genérico clave/valor. Así una tool
// nueva en el backend ya tiene una UI razonable sin tocar el frontend.
function Resultado({ toolName, result }) {
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
        <AngelaTable filas={items} />
      </>
    );
  }
  if (Array.isArray(result.series)) {
    const conTop = result.series.find((s) => Array.isArray(s.top) && s.top.length);
    if (conTop) return <AngelaMiniChart puntos={conTop.top} />;
  }
  return <ResultadoGenerico result={result} />;
}

// La card que representa UN tool-call dentro del mensaje: badge con el
// nombre mientras corre, resultado renderizado (por forma) cuando llega.
export default function ToolCallCard({ part }) {
  const corriendo = part.status?.type === "running" && part.result === undefined;
  return (
    <div className="my-1.5 rounded-xl border border-linea/70 bg-papel/50 px-3 py-2">
      <div className="flex items-center gap-2 text-[0.8rem] font-medium text-tinta-suave">
        {corriendo ? (
          <Loader2 size={14} className="shrink-0 animate-spin text-violeta" />
        ) : (
          <Wrench size={14} className="shrink-0 text-violeta" />
        )}
        <span>{etiquetaDe(part.toolName)}</span>
      </div>
      {!corriendo && <Resultado toolName={part.toolName} result={part.result} />}
    </div>
  );
}

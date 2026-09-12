import { useState } from "react";
import { ClipboardList, Truck, MapPin, Lock, TriangleAlert, Loader2 } from "lucide-react";
import { useApiQuery } from "../lib/query";
import ReporteForm from "./ReporteForm";
import { useT } from "../lib/i18n";

// ARMADO DE PEDIDOS — la primera superficie que tiene este oficio.
//
// Brian arma pedidos ocho horas por día y hasta hoy su acción destacada era
// "cargar remito con foto", que es el trabajo del que recibe. Su rol ya está
// partido (lib/roles.js); esto es la pantalla.
//
// LO QUE ESTA PANTALLA NO HACE, Y POR QUÉ. No hay picking renglón por renglón,
// porque no hay renglones: el apartado `logistica` del ERP trae
// {pedido, cliente, direccion, estado, fecha_prevista, transporte} y nada que
// una un pedido con sus productos. Inventar esos renglones sería exactamente
// lo que este producto no hace. Se dice en pantalla —igual que el bloque FIFO
// del depósito— en vez de simularlo con datos de mentira.
//
// Lo que sí resuelve, que es lo que hoy no existe: qué pedidos hay que armar,
// y el faltante dirigido cuando no hay stock — que hoy se grita al galpón y no
// queda en ningún lado.

export default function Armado({ onCerrada }) {
  const t = useT();
  const { data, isLoading } = useApiQuery("paradasProximas");
  const [reporte, setReporte] = useState(null);
  const pedidos = isLoading ? null : (data?.paradas || []);

  if (!pedidos) return <div className="py-10 text-center"><Loader2 size={18} className="mx-auto animate-spin text-tinta-suave" /></div>;

  const porDia = pedidos.reduce((acc, p) => {
    (acc[p.dia] ||= []).push(p);
    return acc;
  }, {});

  return (
    <div className="pb-2">
      {pedidos.length === 0 ? (
        <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-6 text-center">
          <p className="text-sm text-tinta-suave">{t("armado.sin_pedidos")}</p>
        </div>
      ) : (
        Object.entries(porDia).map(([dia, lista]) => (
          <section key={dia} className="mb-5">
            <h2 className="mb-2 text-2xs font-semibold uppercase tracking-wide text-tinta-suave">
              {t("armado.para_el_dia", { dia, n: lista.length })}
            </h2>
            <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
              {lista.map((p) => (
                <div key={p.pedido} className="border-b border-linea px-4 py-3 last:border-0">
                  <div className="flex items-baseline gap-2">
                    <span className="plata text-sm font-semibold">{p.pedido}</span>
                    <span className="min-w-0 flex-1 truncate text-sm">{p.cliente}</span>
                  </div>
                  <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-tinta-suave">
                    <span className="inline-flex items-center gap-1"><MapPin size={12} />{p.direccion}</span>
                    <span className="inline-flex items-center gap-1"><Truck size={12} />{p.transporte}</span>
                  </p>
                </div>
              ))}
            </div>
          </section>
        ))
      )}

      {/* El faltante dirigido: lo que hoy se grita al galpón y no queda en
          ningún lado. Va al mismo riel que el resto de los reportes, con el
          destinatario que Ángela propone y la persona confirma. */}
      <button onClick={() => setReporte("faltante")}
        className="flex min-h-14 w-full items-center gap-3 rounded-[var(--radius-card)] border border-rojo/30 bg-rojo/[0.04] px-4 py-3 text-left sombra-papel active:scale-[0.99]">
        <TriangleAlert size={19} className="shrink-0 text-rojo-hondo" />
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-semibold leading-snug text-tinta">{t("armado.sin_stock")}</span>
          <span className="block text-xs leading-snug text-tinta-suave">{t("armado.sin_stock_sub")}</span>
        </span>
      </button>

      {/* El dato que NO está, dicho donde se usaría — mismo criterio que el
          bloque FIFO del depósito: el placeholder sólo donde el dato falta. */}
      <div className="mt-4 rounded-[var(--radius-card)] border border-dashed border-linea bg-papel-hondo/40 p-4">
        <div className="flex items-center gap-2 text-tinta-suave">
          <Lock size={15} />
          <p className="text-sm font-semibold">{t("armado.sin_renglones_t")}</p>
        </div>
        <p className="mt-1.5 text-sm leading-snug text-tinta-suave">{t("armado.sin_renglones_d")}</p>
      </div>

      {reporte && (
        <ReporteForm tipo={reporte} onCerrar={() => setReporte(null)} onListo={onCerrada} />
      )}
    </div>
  );
}

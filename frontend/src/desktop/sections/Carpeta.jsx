import { useEffect, useState } from "react";
import { FileText, Check, TriangleAlert, Download, ChevronRight, Truck } from "lucide-react";
import AngelaSays from "../../components/AngelaSays";
import { api } from "../../lib/api";
import { useApiQuery } from "../../lib/query";
import { toast } from "../../lib/toastStore";
import { peso } from "../../lib/format";
import { useT } from "../../lib/i18n";

// ============================================================================
// LA CARPETA DE UNA ENTREGA — el copiloto de los papeles.
// ----------------------------------------------------------------------------
// Casi todos los campos de estos documentos YA ESTÁN en el sistema: en el
// pedido de logística, en la cuenta del cliente, en los renglones de su pedido
// abierto y en las reglas de la casa. Lo que hoy hace una persona es copiarlos
// a mano de una pantalla a dos formularios, y cada copia es una chance de que
// un número no cuadre.
//
// Las dos decisiones que sostienen la pantalla, y que NO se negocian:
//
//   1. CADA CAMPO DICE DE DÓNDE SALIÓ. No "generado por el sistema" — «pedido
//      P-4401», «cuenta corriente de Doña Elsa», «regla de la casa k01». El
//      valor del copiloto no es que escriba rápido: es que se pueda auditar
//      casillero por casillero.
//   2. EL DOCUMENTO INCOMPLETO SE MUESTRA IGUAL, con los huecos marcados y el
//      conteo de lo que falta. La pregunta que tiene alguien no es "generalo
//      cuando esté todo": es "qué falta".
//
// Y el CONTROL CRUZADO, que ningún formulario hace solo: que el total del
// remito, el total del pedido abierto y el saldo de la cuenta digan lo mismo.
// Es trivial cuando los tres salen de la misma fuente — que es el punto.
// ============================================================================

const ESTADO_CLS = {
  completo: "border-salvia/40",
  falta: "border-rojo/50",
  opcional: "border-linea",
};

export default function Carpeta({ onPreguntar }) {
  const t = useT();
  const { data: pedidosData, isPending: pedidosPending, isError: pedidosError } = useApiQuery("carpetaPedidos");
  const pedidos = pedidosError ? [] : pedidosData?.pedidos;
  const [sel, setSel] = useState(null);
  const [docId, setDocId] = useState(null);
  const { data: carpeta, isError: carpetaError } = useApiQuery("carpeta", [sel], { enabled: !!sel });
  const { data: doc, isError: docError } = useApiQuery("carpetaDocumento", [sel, docId], { enabled: !!sel && !!docId });

  useEffect(() => {
    if (sel == null && pedidos?.length) setSel(pedidos[0].numero);
  }, [pedidos, sel]);

  useEffect(() => {
    setDocId(null);
  }, [sel]);

  useEffect(() => {
    if (!docId && carpeta?.documentos?.length) setDocId(carpeta.documentos[0].id);
  }, [carpeta, docId]);

  if (pedidosPending || pedidos === undefined) return <div className="h-64 animate-pulse rounded-[var(--radius-card)] bg-papel-hondo/50" />;
  if (!pedidos.length) return <p className="text-sm text-tinta-suave">{t("carpeta.sin_pedidos")}</p>;

  return (
    <div className="space-y-4">
      <AngelaSays>{t("carpeta.sub")}</AngelaSays>
      <div className="grid gap-5 lg:grid-cols-[18rem_1fr]">
        <aside className="space-y-1">
          <p className="px-1 pb-1 text-xs font-semibold uppercase tracking-[0.12em] text-tinta-suave">
            {t("carpeta.pedidos")}
          </p>
          <div className="max-h-[32rem] overflow-y-auto rounded-[var(--radius-card)] border border-linea bg-crema">
            {pedidos.map((p) => (
              <button key={p.numero} onClick={() => setSel(p.numero)}
                className={`flex w-full items-center gap-2 border-b border-linea px-3 py-2 text-left last:border-0 ${
                  sel === p.numero ? "bg-papel-hondo/70" : "hover:bg-papel-hondo/40"}`}>
                <Truck size={14} className="shrink-0 text-tinta-suave" />
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-semibold leading-tight">{p.numero}</span>
                  <span className="block truncate text-xs text-tinta-suave">{p.cliente}</span>
                </span>
                {sel === p.numero && <ChevronRight size={14} className="shrink-0 text-tinta-suave" />}
              </button>
            ))}
          </div>
        </aside>

        <div className="min-w-0 space-y-4">
          {carpeta && !carpetaError && (
            <>
              <ControlCruzado cc={carpeta.control_cruzado} />
              <div className="flex flex-wrap gap-2">
                {carpeta.documentos.map((d) => (
                  <button key={d.id} onClick={() => setDocId(d.id)}
                    className={`flex items-center gap-2 rounded-full border px-3.5 py-2 text-sm font-semibold transition-colors ${
                      docId === d.id ? "border-tinta text-tinta" : "border-linea text-tinta-suave hover:text-tinta"}`}>
                    <FileText size={14} />
                    {d.titulo}
                    <span className={`text-xs font-normal ${d.completitud.faltan ? "text-rojo" : "text-salvia"}`}>
                      {d.completitud.faltan
                        ? t("carpeta.falta_n", { n: d.completitud.faltan })
                        : t("carpeta.completo")}
                    </span>
                  </button>
                ))}
              </div>
            </>
          )}
          {doc && !docError && <Documento doc={doc} onPreguntar={onPreguntar} />}
        </div>
      </div>
    </div>
  );
}

function ControlCruzado({ cc }) {
  const t = useT();
  if (!cc) return null;
  const Icon = cc.ok ? Check : TriangleAlert;
  return (
    <div className={`rounded-[var(--radius-card)] border p-4 ${
      cc.ok ? "border-salvia/30 bg-salvia/[0.05]" : "border-rojo/30 bg-rojo/[0.05]"}`}>
      <p className={`flex items-center gap-1.5 text-sm font-semibold ${cc.ok ? "text-salvia" : "text-rojo"}`}>
        <Icon size={15} /> {t("carpeta.control")} · {cc.ok ? t("carpeta.control_ok") : t("carpeta.control_mal")}
      </p>
      <ul className="mt-2 space-y-1">
        {(cc.checks || []).map((c, i) => (
          <li key={i} className="flex flex-wrap items-baseline gap-x-2 text-xs text-tinta-suave">
            {c.ok ? <Check size={11} className="text-salvia" /> : <TriangleAlert size={11} className="text-rojo" />}
            <span className="text-tinta">{c.que}</span>
            <span className="plata">
              {typeof c.a === "number" ? peso(c.a) : c.a} · {typeof c.b === "number" ? peso(c.b) : c.b}
            </span>
          </li>
        ))}
      </ul>
      {cc.nota && <p className="mt-2 text-xs leading-snug text-tinta-suave">{cc.nota}</p>}
    </div>
  );
}

function Documento({ doc }) {
  const t = useT();
  const [bajando, setBajando] = useState(false);
  const c = doc.completitud;

  const descargar = async () => {
    setBajando(true);
    try {
      const b = await api.blobPost("/api/documentos/pdf", { documento: doc });
      const url = URL.createObjectURL(b);
      const a = document.createElement("a");
      a.href = url; a.download = `${doc.id}-${doc.numero}.pdf`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch {
      toast(t("carpeta.error_pdf"), "error");
    }
    setBajando(false);
  };

  return (
    <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-5 sombra-papel">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-xl font-bold leading-tight">{doc.titulo}</h2>
          <p className="mt-0.5 text-sm text-tinta-suave">
            {doc.numero} · {doc.subtitulo}
          </p>
        </div>
        <button onClick={descargar} disabled={bajando}
          className="inline-flex items-center gap-1.5 rounded-full bg-tinta px-4 py-2 text-sm font-semibold text-crema disabled:opacity-50">
          <Download size={14} /> {bajando ? t("carpeta.bajando") : t("carpeta.descargar")}
        </button>
      </div>

      {/* Lo que falta, al frente y contado. No es "generalo cuando esté todo". */}
      {c?.faltan > 0 && (
        <p className="mt-3 rounded-xl border border-rojo/25 bg-rojo/[0.05] px-3 py-2 text-sm text-rojo-hondo">
          {t("carpeta.que_falta", { campos: c.que_falta.join(", ") })}
        </p>
      )}

      {doc.secciones.map((s, i) => (
        <section key={i} className="mt-5">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-tinta-suave">{s.titulo}</h3>
          <div className="mt-2 grid gap-x-6 gap-y-3 sm:grid-cols-2">
            {s.campos.map((f, j) => (
              <div key={j} className={`border-l-2 pl-2.5 ${ESTADO_CLS[f.estado] || ESTADO_CLS.opcional}`}>
                <p className="text-2xs uppercase tracking-wide text-tinta-suave">{f.etiqueta}</p>
                <p className={`text-sm leading-snug ${f.valor == null || f.valor === "" ? "italic text-rojo" : "text-tinta"}`}>
                  {f.valor == null || f.valor === "" ? t("carpeta.falta") : String(f.valor)}
                </p>
                {/* La fuente: lo que hace auditable el casillero. */}
                {f.fuente && (
                  <p className="mt-0.5 text-2xs text-hielo">{t("carpeta.de")} {f.fuente}</p>
                )}
              </div>
            ))}
          </div>
        </section>
      ))}

      {doc.renglones?.length > 0 && (
        <section className="mt-5">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-tinta-suave">
            {t("carpeta.renglones")}
          </h3>
          <div className="mt-2 overflow-x-auto">
            <table className="w-full min-w-[30rem] text-sm">
              <thead>
                <tr className="border-b border-linea text-2xs uppercase tracking-wide text-tinta-suave">
                  {Object.keys(doc.renglones[0]).filter((k) => k !== "fuente").map((k) => (
                    <th key={k} className="px-2 py-1.5 text-left font-semibold">{k}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {doc.renglones.map((r, i) => (
                  <tr key={i} className="border-b border-linea/60 last:border-0">
                    {Object.entries(r).filter(([k]) => k !== "fuente").map(([k, v]) => (
                      <td key={k} className="px-2 py-1.5">{v == null ? "—" : String(v)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {doc.nota_legal && (
        <p className="mt-4 border-t border-linea pt-3 text-xs leading-snug text-tinta-suave">
          {doc.nota_legal}
        </p>
      )}
    </div>
  );
}

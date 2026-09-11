import { useEffect, useState } from "react";
import { FileText, Download, ClipboardList, FileBarChart2, Mail, Receipt, PenLine, ArrowRight } from "lucide-react";
import AngelaMark from "../../components/AngelaMark";
import { api } from "../../lib/api";
import { toast } from "../../lib/toastStore";
import { useT, useLang } from "../../lib/i18n";

// Descarga un blob con nombre de archivo (el PDF real de P17).
function bajarBlob(blob, nombre) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nombre;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}

// Documentos entregables: Ángela propone, el usuario edita acá, y genera el PDF
// (imprimir → guardar como PDF). El flujo conversacional sigue por el chat de Ángela.
//
// P11·B11 — la pantalla vacía dejó de ser "un vacío con dos botones": una
// grilla de tarjetas por tipo de documento que Ángela YA sabe generar. Cada
// tarjeta usa el patrón chips (label visible traducido; payload en ES, que el
// motor entiende) y dispara el flujo EXISTENTE: onPreguntar → Ángela → acción
// {type:"documento"} → card de descarga EN el chat (P24·B: sin preview
// en pantalla — descalzaba números); acá quedan la grilla y los generados.
export default function Documentos({ onPreguntar }) {
  const t = useT();
  const lang = useLang();
  const [generados, setGenerados] = useState([]);
  const refrescarListado = () =>
    api.documentosListado().then((d) => setGenerados(d.documentos || [])).catch(() => {});
  // El listado se repide al cambiar de idioma: el `label` lo traduce el servidor
  // (ver /api/documentos/listado), igual que el resto de los textos del backend.
  useEffect(() => { refrescarListado(); }, [lang]);


    return (
      <div className="space-y-4">
        <header>
          <h1 className="font-display text-3xl font-bold">{t("documentos.titulo")}</h1>
          <p className="mt-1 text-[0.95rem] text-tinta-suave">{t("documentos.grid_sub")}</p>
        </header>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {/* P39·2 — el reporte de cierres por local: LA tarea semanal que una
              persona hacía imputando a mano en un Excel. Es el primero de la
              grilla porque es el que más trabajo reemplaza. */}
          <CartaDoc icon={Receipt} titulo={t("documentos.card_cierres_t")} detalle={t("documentos.card_cierres_d")}
            onGenerar={() => onPreguntar?.(t("documentos.card_cierres_enviar"))} cta={t("documentos.card_generar")} />
          <CartaDoc icon={ClipboardList} titulo={t("documentos.card_orden_t")} detalle={t("documentos.card_orden_d")}
            onGenerar={() => onPreguntar?.(t("documentos.card_orden_enviar"))} cta={t("documentos.card_generar")} />
          <CartaDoc icon={FileBarChart2} titulo={t("documentos.card_resumen_t")} detalle={t("documentos.card_resumen_d")}
            onGenerar={() => onPreguntar?.(t("documentos.card_resumen_enviar"))} cta={t("documentos.card_generar")} />
          <CartaDoc icon={Mail} titulo={t("documentos.card_carta_t")} detalle={t("documentos.card_carta_d")}
            onGenerar={() => onPreguntar?.(t("documentos.card_carta_enviar"))} cta={t("documentos.card_generar")} />
          <CartaDocInput icon={Receipt} titulo={t("documentos.card_estado_t")} detalle={t("documentos.card_estado_d")}
            placeholder={t("documentos.card_estado_ph")} cta={t("documentos.card_generar")}
            onGenerar={(v) => onPreguntar?.(t("documentos.card_estado_enviar", { nombre: v }))} />
          <CartaDocInput icon={PenLine} titulo={t("documentos.card_otro_t")} detalle={t("documentos.card_otro_d")}
            placeholder={t("documentos.card_otro_ph")} cta={t("documentos.card_pedir")}
            onGenerar={(v) => onPreguntar?.(v)} ancho="sm:col-span-2 xl:col-span-2" />
        </div>

        {/* Los PDFs YA generados: fecha + quién los pidió, re-descargables */}
        {generados.length > 0 && (
          <section>
            <h2 className="mb-2 mt-6 font-display text-[1.1rem] font-bold">{t("documentos.generados_t")}</h2>
            <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
              {generados.map((g) => (
                <div key={g.id} className="flex items-center gap-3 border-b border-linea px-4 py-2.5 last:border-0">
                  <FileText size={16} className="shrink-0 text-tinta-suave" />
                  <div className="min-w-0 flex-1">
                    {/* P43·C5.3 — el label sigue el idioma de la pantalla; el
                        PDF conserva el suyo. Cuando no coinciden se avisa, en
                        vez de mostrar un título en otro idioma sin explicación. */}
                    <p className="truncate text-[0.9rem] font-semibold text-tinta">{g.label || g.titulo}</p>
                    <p className="text-[0.76rem] text-tinta-suave">
                      {t("documentos.generado_meta", { fecha: g.fecha, usuario: g.usuario })}
                      {g.lang && lang && g.lang !== lang && (
                        <span className="ml-1.5 rounded-full border border-linea px-1.5 py-px text-[0.68rem] uppercase">
                          {t("documentos.pdf_en_idioma", { idioma: g.lang.toUpperCase() })}
                        </span>
                      )}
                    </p>
                  </div>
                  <button
                    onClick={() => api.blob(`/api/documentos/archivo/${g.id}`)
                      .then((b) => bajarBlob(b, `${g.tipo}-${g.fecha}.pdf`))
                      .catch(() => toast(t("api.error_generico"), "error"))}
                    className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-linea px-3 py-1.5 text-[0.8rem] font-semibold text-tinta-suave hover:text-tinta"
                  >
                    <Download size={13} /> PDF
                  </button>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    );
}

function CartaDoc({ icon: Icon, titulo, detalle, onGenerar, cta }) {
  return (
    <div className="flex flex-col rounded-[var(--radius-card)] border border-linea bg-crema p-5 sombra-papel">
      <Icon size={20} className="text-violeta" />
      <h3 className="mt-2 font-display text-[1.05rem] font-bold leading-tight">{titulo}</h3>
      <p className="mt-1 flex-1 text-[0.86rem] leading-snug text-tinta-suave">{detalle}</p>
      <button onClick={onGenerar}
        className="mt-3 inline-flex items-center gap-1.5 self-start rounded-full border border-violeta/30 px-4 py-1.5 text-[0.84rem] font-semibold text-violeta transition-colors hover:bg-violeta hover:text-crema">
        {cta} <ArrowRight size={13} />
      </button>
    </div>
  );
}

function CartaDocInput({ icon: Icon, titulo, detalle, placeholder, cta, onGenerar, ancho = "" }) {
  const [valor, setValor] = useState("");
  const mandar = () => { if (valor.trim()) onGenerar(valor.trim()); };
  return (
    <div className={`flex flex-col rounded-[var(--radius-card)] border border-linea bg-crema p-5 sombra-papel ${ancho}`}>
      <Icon size={20} className="text-violeta" />
      <h3 className="mt-2 font-display text-[1.05rem] font-bold leading-tight">{titulo}</h3>
      <p className="mt-1 flex-1 text-[0.86rem] leading-snug text-tinta-suave">{detalle}</p>
      <div className="mt-3 flex gap-2">
        <input value={valor} onChange={(e) => setValor(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && mandar()}
          placeholder={placeholder}
          className="min-w-0 flex-1 rounded-full border border-linea bg-papel px-3.5 py-1.5 text-[0.84rem] outline-none focus:border-tinta/40" />
        <button onClick={mandar} disabled={!valor.trim()}
          className="shrink-0 rounded-full border border-violeta/30 px-4 py-1.5 text-[0.84rem] font-semibold text-violeta transition-colors hover:bg-violeta hover:text-crema disabled:opacity-40">
          {cta}
        </button>
      </div>
    </div>
  );
}

function Campo({ label, valor, onChange }) {
  return (
    <label className="block">
      <span className="text-[0.74rem] font-semibold uppercase tracking-wide text-tinta-suave">{label}</span>
      <input value={valor} onChange={(e) => onChange(e.target.value)}
        className="mt-0.5 w-full rounded border border-linea bg-transparent px-2 py-1 text-[0.9rem] text-tinta outline-none focus:border-tinta/40 print:border-0" />
    </label>
  );
}

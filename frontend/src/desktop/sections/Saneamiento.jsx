import { useEffect, useState } from "react";
import StagingArea from "./StagingArea";
import { ShieldCheck, Sparkles, RotateCcw, Check, ArrowRight, Lock, X, Download } from "lucide-react";
import AngelaMark from "../../components/AngelaMark";
import PanelDecision from "../../components/PanelDecision";
import { CATEGORIAS_CON_PROPUESTA } from "../../lib/decisiones";
import { api } from "../../lib/api";
import { resaltarPorId } from "../../lib/navGuiada";
import { equipoStore } from "../../lib/equipoStore";
import { responsableVerificacion } from "../../lib/equipoReal";
import { focoStore } from "../../lib/focoStore";
import { peso, pesoCorto, num } from "../../lib/format";
import { useT } from "../../lib/i18n";

// Cuando Ángela corrige un grupo, delega sola la verificación al responsable
// REAL del tenant (lib/equipoReal, P9·C2): nada de nombres hardcodeados.
// La tarea se genera en el idioma activo al momento de delegar (recibe t).
const RESPONSABLE = {
  fantasma: { tarea: (n, t) => t("saneamiento.tarea_fantasma", { n }) },
  balanza: { tarea: (n, t) => t("saneamiento.tarea_balanza", { n }) },
};

const CORREGIBLES = ["fantasma", "balanza"];

// Color del registro según su EstadoCalidad (el "marcado por color" del spec).
const COLOR_ESTADO = {
  inconsistente: { barra: "bg-rojo", txt: "text-rojo" },
  mal_configurado: { barra: "bg-oro", txt: "text-oro-tinta" },
  incompleto: { barra: "bg-oro", txt: "text-oro-tinta" },
  desactualizado: { barra: "bg-oro", txt: "text-oro-tinta" },
  completo: { barra: "bg-salvia", txt: "text-salvia" },
};

// Categoría del libro → grupo del inventario (para el filtro al navegar).
const INV_GRUPO = { fantasma: "fantasmas", balanza: "balanza", negativo: "negativos", sin_precio: "sin_pvp", costo_viejo: "costo_viejo" };

export default function Saneamiento({ user, highlight, onNavegar, onPreguntar, onRecargar, onStagingCambio }) {
  const t = useT();
  // P24·G — la fusión: UNA sección para "¿qué datos necesitan algo de mí?",
  // con los DOS flujos bien separados por atrás: (a) errores en datos que YA
  // viven en el sistema/ERP (se corrigen), (b) cargas retenidas en revisión
  // que NO entraron al ERP (se resuelven y recién ahí entran).
  const [subtab, setSubtab] = useState("errores");
  const [enRevision, setEnRevision] = useState(0);
  useEffect(() => {
    api.stagingListar().then((d) => setEnRevision(d.batches.length)).catch(() => {});
  }, []);
  useEffect(() => {
    if (highlight === "revision") setSubtab("revision");
  }, [highlight]);
  const [libro, setLibro] = useState(null);
  const [anomalias, setAnomalias] = useState([]);
  const [preview, setPreview] = useState(null); // {categoria, ...proponer}
  const [resultado, setResultado] = useState(null); // {...aplicar}
  const [delegadoA, setDelegadoA] = useState(null); // responsable real de verificar
  const [trabajando, setTrabajando] = useState(false);
  const [deltaCount, setDeltaCount] = useState(0);
  const [deltaCerrado, setDeltaCerrado] = useState(false);

  const cargar = () => {
    api.calidad().then(setLibro).catch(() => {});
    api.anomalias().then((d) => setAnomalias(d.anomalias)).catch(() => {});
    api.syncDelta("generico").then((d) => setDeltaCount(d.registros)).catch(() => {});
  };
  useEffect(() => {
    cargar();
  }, []);

  const exportarDelta = async (formato) => {
    const d = await api.syncDelta(formato);
    const blob = new Blob([d.csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `polpilot-delta-${formato}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Lleva al inventario mostrando SOLO esos productos, marcados (no toda la lista).
  const verEnInventario = (a) => {
    focoStore.set({ titulo: a.titulo, codigos: a.codigos || [] });
    onNavegar?.("inventario", "foco");
  };

  // Cuando llegás desde un producto problemático del inventario, la categoría
  // queda titilando hasta que la tocás (navegación guiada, ver lib/navGuiada).
  // P14: si la categoría tiene corrección automática, la propuesta se abre
  // sola — "Ver propuesta" (Home) aterriza EN la propuesta, no cerca de ella.
  useEffect(() => {
    if (!highlight || !libro) return;
    if (CATEGORIAS_CON_PROPUESTA.includes(highlight) &&
        libro.grupos.some((g) => g.categoria === highlight && g.cantidad > 0)) {
      abrirPreview(highlight);
    }
    return resaltarPorId(`san-${highlight}`, 300);
  }, [highlight, libro]);

  const abrirPreview = async (cat) => {
    setResultado(null);
    const p = await api.saneamientoProponer(cat);
    setPreview(p);
  };

  const aplicar = async (cat) => {
    setTrabajando(true);
    const r = await api.saneamientoAplicar(cat, user?.nombre || "dueño");
    setResultado(r);
    setPreview(null);
    // Ángela delega sola: genera una tarea de verificación para el responsable
    // REAL del tenant (P9·C2, M3).
    const resp = RESPONSABLE[cat];
    if (resp) {
      const quien = await responsableVerificacion().catch(() => "");
      if (quien) {
        equipoStore.addRecordatorio(resp.tarea(r.corregidos, t), quien);
        setDelegadoA(quien);
      }
    }
    await cargar();
    setTrabajando(false);
  };

  const revertir = async (vid) => {
    setTrabajando(true);
    await api.saneamientoRevertir(vid, user?.nombre || "dueño");
    setResultado(null);
    await cargar();
    setTrabajando(false);
  };

  if (!libro) return <p className="py-10 text-center text-sm text-tinta-suave">{t("saneamiento.cargando")}</p>;

  return (
    <div className="space-y-6">
      <header className="flex items-center gap-2">
        <ShieldCheck size={24} className="text-tinta-suave" />
        <div>
          <h1 className="font-display text-3xl font-bold leading-none">{t("saneamiento.titulo")}</h1>
          <p className="mt-1 text-[0.95rem] text-tinta-suave">
            {t("saneamiento.sub_fusion")}
          </p>
        </div>
      </header>

      {/* P24·G — los dos bloques, en lenguaje de dueño */}
      <div className="flex gap-2 border-b border-linea">
        {[
          { id: "errores", lk: "saneamiento.tab_errores", n: libro.total_issues },
          { id: "revision", lk: "saneamiento.tab_revision", n: enRevision },
        ].map((tb) => (
          <button key={tb.id} onClick={() => setSubtab(tb.id)}
            className={`-mb-px flex items-center gap-2 border-b-2 px-1 py-2.5 text-[0.92rem] font-semibold transition-colors ${
              subtab === tb.id ? "border-tinta text-tinta" : "border-transparent text-tinta-suave hover:text-tinta"
            }`}>
            {t(tb.lk)}
            {tb.n > 0 && (
              <span className="grid h-5 min-w-5 place-items-center rounded-full bg-oro px-1 text-[0.7rem] font-bold text-crema">{num(tb.n)}</span>
            )}
          </button>
        ))}
      </div>

      {subtab === "revision" ? (
        <StagingArea onCambio={(n) => { setEnRevision(n); onStagingCambio?.(n); }} onRecargar={onRecargar} />
      ) : (
      <>

      {/* Intro de Ángela con el total */}
      <div className="flex items-start gap-4 rounded-[var(--radius-card)] border border-violeta/15 bg-violeta/[0.04] p-5">
        <AngelaMark size={40} estado={trabajando ? "ejecutando" : preview ? "esperando" : "idle"} />
        <p className="text-[1.02rem] leading-snug text-tinta">
          {t("saneamiento.intro_1")} <b>{num(libro.total_issues)}</b> {t("saneamiento.intro_2")}{" "}
          <b className="plata text-hielo">{peso(libro.impacto_total)}</b> {t("saneamiento.intro_3")} <b>{t("saneamiento.intro_4")}</b> {t("saneamiento.intro_5")}
        </p>
      </div>

      {/* Resultado de una corrección recién aplicada */}
      {resultado && (
        <div className="flex items-start gap-3 rounded-[var(--radius-card)] border border-salvia/40 bg-salvia/[0.07] p-5">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-salvia text-crema">
            <Check size={18} />
          </span>
          <div className="flex-1">
            <p className="text-[1rem] leading-snug text-tinta">{resultado.mensaje}</p>
            {RESPONSABLE[resultado.categoria] && delegadoA && (
              <p className="mt-1 text-[0.86rem] text-tinta-suave">
                {t("saneamiento.verif_delegada", { quien: delegadoA })}
              </p>
            )}
            <button
              onClick={() => revertir(resultado.version_backup)}
              disabled={trabajando}
              className="mt-2.5 inline-flex items-center gap-1.5 rounded-full border border-linea bg-crema px-3.5 py-1.5 text-[0.82rem] font-semibold text-tinta-suave hover:text-rojo"
            >
              <RotateCcw size={14} /> {t("saneamiento.revertir")}
            </button>
          </div>
        </div>
      )}

      {/* Sync con tu sistema original: exportar SOLO los registros corregidos (delta) */}
      {deltaCount > 0 && !deltaCerrado && (
        <div className="relative flex items-start gap-3 rounded-[var(--radius-card)] border border-hielo/25 bg-hielo-claro p-5">
          <button onClick={() => setDeltaCerrado(true)} title={t("saneamiento.cerrar")} className="absolute right-3 top-3 text-tinta-suave hover:text-tinta"><X size={16} /></button>
          <AngelaMark size={32} />
          <div className="flex-1 pr-6">
            <p className="text-[1rem] leading-snug text-tinta">
              {t("saneamiento.delta_1")} <b>{deltaCount}</b> {deltaCount === 1 ? t("saneamiento.delta_registro") : t("saneamiento.delta_registros")} {t("saneamiento.delta_2")}
              <b> {t("saneamiento.delta_solo")}</b> {t("saneamiento.delta_3")}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <button onClick={() => exportarDelta("faro")} className="inline-flex items-center gap-1.5 rounded-full bg-tinta px-4 py-2 text-[0.84rem] font-semibold text-crema">
                <Download size={14} /> {t("saneamiento.delta_faro")}
              </button>
              <button onClick={() => exportarDelta("tango")} className="inline-flex items-center gap-1.5 rounded-full border border-tinta/25 px-4 py-2 text-[0.84rem] font-semibold text-tinta">
                <Download size={14} /> {t("saneamiento.delta_tango")}
              </button>
              <button onClick={() => exportarDelta("generico")} className="inline-flex items-center gap-1.5 rounded-full border border-linea px-4 py-2 text-[0.84rem] font-semibold text-tinta-suave">
                <Download size={14} /> {t("saneamiento.delta_generico")}
              </button>
            </div>
            <p className="mt-2 text-[0.76rem] text-tinta-suave">{t("saneamiento.delta_nota")}</p>
          </div>
        </div>
      )}

      {/* Libro triado: una tarjeta por categoría, coloreada por estado */}
      <div className="space-y-3">
        {libro.grupos.map((g) => {
          const col = COLOR_ESTADO[g.estado] || COLOR_ESTADO.incompleto;
          const corregible = CORREGIBLES.includes(g.categoria);
          const enPreview = preview?.categoria === g.categoria;
          const impacto = g.impacto_pesos > 0 ? t("saneamiento.en_juego", { monto: pesoCorto(g.impacto_pesos) }) : t("saneamiento.n_productos", { n: num(g.cantidad) });

          return (
            <div key={g.categoria} data-nav-id={`san-${g.categoria}`} className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
              <div className="flex items-stretch">
                <div className={`w-1.5 shrink-0 ${col.barra}`} />
                <div className="flex-1 p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-baseline gap-2">
                        <span className="plata text-2xl font-medium">{num(g.cantidad)}</span>
                        <h3 className="font-display text-[1.1rem] font-bold">{g.label}</h3>
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <span className="rounded-full bg-papel-hondo px-2.5 py-0.5 text-[0.72rem] font-semibold uppercase tracking-wide text-tinta-suave">
                          {impacto}
                        </span>
                        <span className={`text-[0.74rem] font-semibold uppercase tracking-wide ${col.txt}`}>
                          {(g.estado_label || g.estado).replace("_", " ")}
                        </span>
                      </div>
                    </div>

                    <div className="flex shrink-0 flex-col items-end gap-2">
                      <button
                        onClick={() => {
                          onNavegar?.("inventario", INV_GRUPO[g.categoria]);
                          onPreguntar?.(corregible
                            ? `Quiero corregir los ${g.label.toLowerCase()}`
                            : `¿Cómo resuelvo los ${g.label.toLowerCase()}? Mostrame qué recomendás.`);
                        }}
                        className="inline-flex items-center gap-2 rounded-full bg-violeta px-4 py-2 text-[0.85rem] font-semibold text-crema transition-transform active:scale-95"
                      >
                        <AngelaMark size={18} /> {corregible ? t("saneamiento.corrija_angela") : t("saneamiento.revisar_angela")}
                      </button>
                      <button
                        onClick={() => onNavegar?.("inventario", INV_GRUPO[g.categoria])}
                        className="inline-flex items-center gap-1.5 rounded-full border border-linea px-3.5 py-1.5 text-[0.78rem] font-semibold text-tinta-suave hover:text-tinta"
                      >
                        <ArrowRight size={13} /> {t("saneamiento.ver_inventario")}
                      </button>
                    </div>
                  </div>

                  {/* Preview antes/después: el patrón de decisión unificado (P14) */}
                  {enPreview && preview.auto && (
                    <PanelDecision
                      className="mt-4"
                      impacto={preview.impacto_pesos}
                      extra={<button onClick={() => setPreview(null)} className="text-tinta-suave hover:text-tinta"><X size={16} /></button>}
                      acciones={
                        <>
                          <button
                            onClick={() => aplicar(g.categoria)}
                            disabled={trabajando}
                            className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-[0.85rem] font-semibold text-crema disabled:opacity-50"
                          >
                            <Check size={15} /> {trabajando ? t("saneamiento.corrigiendo") : t("saneamiento.dale_corregilo")}
                          </button>
                          <button onClick={() => setPreview(null)} className="rounded-full border border-linea px-4 py-2 text-[0.85rem] font-semibold text-tinta-suave">
                            {t("saneamiento.ahora_no")}
                          </button>
                          <span className="ml-auto text-[0.76rem] text-tinta-suave">{t("saneamiento.backup_nota")}</span>
                        </>
                      }
                    >
                      <p className="flex items-center gap-1.5 text-[0.86rem] font-semibold text-violeta">
                        <Sparkles size={14} /> {t("saneamiento.preview_hacer")} {preview.accion}
                      </p>
                      <div className="mt-3 space-y-1.5">
                        {preview.muestra.map((m) => (
                          <div key={m.codigo} className="flex items-center gap-2 text-[0.84rem]">
                            <span className="min-w-0 flex-1 truncate text-tinta">{m.descripcion}</span>
                            <span className="plata text-tinta-suave line-through">{String(m.antes)}</span>
                            <ArrowRight size={13} className="text-tinta-suave" />
                            <span className="plata font-semibold text-salvia">{String(m.despues)}</span>
                          </div>
                        ))}
                        {preview.cantidad > preview.muestra.length && (
                          <p className="text-[0.78rem] text-tinta-suave">{t("saneamiento.preview_mas", { n: num(preview.cantidad - preview.muestra.length) })}</p>
                        )}
                      </div>
                    </PanelDecision>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Anomalías de negocio sobre los datos existentes */}
      {anomalias.length > 0 && (
        <section>
          <h2 className="mb-1 mt-2 font-display text-[1.3rem] font-bold">{t("saneamiento.anomalias_titulo")}</h2>
          <p className="mb-3 text-[0.9rem] text-tinta-suave">
            {t("saneamiento.anomalias_sub")}
          </p>
          <div className="space-y-3">
            {anomalias.map((a) => (
              <div key={a.tipo} className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
                <div className="flex items-stretch">
                  <div className="w-1.5 shrink-0 bg-oro" />
                  <div className="flex-1 p-5">
                    <div className="flex items-baseline gap-2">
                      <span className="plata text-2xl font-medium">{num(a.items)}</span>
                      <h3 className="font-display text-[1.1rem] font-bold">{a.titulo}</h3>
                    </div>
                    <p className="mt-1.5 max-w-2xl text-[0.9rem] leading-snug text-tinta-suave">{a.descripcion}</p>
                    {a.impacto_pesos > 0 && (
                      <span className="mt-2 inline-block rounded-full bg-papel-hondo px-2.5 py-0.5 text-[0.72rem] font-semibold uppercase tracking-wide text-tinta-suave">
                        {t("saneamiento.en_juego", { monto: pesoCorto(a.impacto_pesos) })}
                      </span>
                    )}
                    <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-linea pt-3">
                      <button onClick={() => onPreguntar?.(`¿cómo corrijo ${a.titulo.toLowerCase()}? Mostrame qué recomendás.`)}
                        className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-3.5 py-1.5 text-[0.82rem] font-semibold text-crema">
                        <AngelaMark size={16} /> {t("saneamiento.arreglar_angela")}
                      </button>
                      <button onClick={() => verEnInventario(a)}
                        className="inline-flex items-center gap-1.5 rounded-full border border-linea px-3.5 py-1.5 text-[0.82rem] font-semibold text-tinta-suave hover:text-tinta">
                        <ArrowRight size={14} /> {t("saneamiento.ver_productos_inv")}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
      </>
      )}
    </div>
  );
}

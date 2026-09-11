import { useEffect, useState } from "react";
import { Sparkles, Shield, ArrowRight } from "lucide-react";
import AngelaMark from "../components/AngelaMark";
import { DrillNegocio } from "../components/CardNegocio";
import { cargarSenales } from "../lib/centroAlertas";
import { construirAlertas } from "../lib/alertasNegocio";
import { api } from "../lib/api";
import { useSession } from "../lib/auth";
import { pesoCorto } from "../lib/format";
import { useT } from "../lib/i18n";

// P35·E3 — INSIGHTS (mobile): la fusión de Alertas + Oportunidades en UNA lista
// de FILAS compactas (no cards grandes). Mismas fuentes que desktop (cero datos
// nuevos): cargarSenales()+construirAlertas para las alertas, api.oportunidades
// para las oportunidades. Los RIESGOS (exposición) van SEPARADOS, jamás
// mezclados con el capital capturable. Al tocar una fila se abre el detalle
// (DrillNegocio: el porqué + "Crucé: [fuentes]" + la acción).

// cache de sesión por idioma (revisita instantánea, patrón P32·1)
let _cacheIns = { lang: null, senales: null, cards: null };

const DOT = { rojo: "bg-rojo", oro: "bg-oro", azul: "bg-violeta", salvia: "bg-salvia" };

export default function InsightsMobile({ onPreguntar, onNavegar }) {
  const t = useT();
  const langKey = useSession()?.usuario?.idioma || "es";
  const [senales, setSenales] = useState(_cacheIns.lang === langKey ? _cacheIns.senales : null);
  const [cards, setCards] = useState(_cacheIns.lang === langKey ? _cacheIns.cards : null);
  const [filtro, setFiltro] = useState("todo");     // todo | alertas | oport
  const [abierta, setAbierta] = useState(null);

  useEffect(() => {
    let vivo = true;
    (async () => {
      const [s, ops] = await Promise.all([
        cargarSenales().catch(() => null),
        api.oportunidades().then((d) => d.cards || []).catch(() => []),
      ]);
      _cacheIns = { lang: langKey, senales: s, cards: ops };
      if (vivo) { setSenales(s); setCards(ops); }
    })();
    return () => { vivo = false; };
  }, [langKey]);

  const cargando = senales === null && cards === null;

  // --- modelo unificado de filas (mismas fuentes que desktop) ---
  const alertas = construirAlertas(senales, t, onNavegar).map((a) => ({ ...a, kind: "alerta" }));
  const capturables = (cards || [])
    .filter((c) => c.naturaleza !== "riesgo")
    .map((c) => ({
      kind: "oport", id: c.id, tono: "salvia", icon: Sparkles,
      titulo: c.titulo, detalle: c.resumen, monto: c.monto, fuentes: c.fuentes,
      porque: c.drill?.porque || [], grafico: c.drill?.grafico,
      involucrados: c.drill?.involucrados || [], supuestos: c.drill?.supuestos || [],
      macro: c.macro, chat: c.accion_chat, navegar: c.navegar,
    }));
  const riesgos = (cards || [])
    .filter((c) => c.naturaleza === "riesgo")
    .map((c) => ({
      kind: "riesgo", id: c.id, tono: "oro", icon: Shield,
      titulo: c.titulo, detalle: c.resumen, monto: c.monto, montoLabel: c.monto_label,
      fuentes: c.fuentes, porque: c.drill?.porque || [], grafico: c.drill?.grafico,
      involucrados: c.drill?.involucrados || [], supuestos: c.drill?.supuestos || [],
      macro: c.macro, chat: c.accion_chat, navegar: c.navegar,
    }));

  // el filtro decide qué entra en la lista principal; SIEMPRE por $ desc.
  const base = filtro === "alertas" ? alertas : filtro === "oport" ? capturables : [...alertas, ...capturables];
  const lista = [...base].sort((x, y) => (y.monto || 0) - (x.monto || 0));
  const mostrarRiesgos = filtro !== "alertas" && riesgos.length > 0;

  const FILTROS = [
    { id: "todo", lk: "insights.f_todo" },
    { id: "alertas", lk: "insights.f_alertas" },
    { id: "oport", lk: "insights.f_oport" },
  ];

  const Fila = ({ item }) => {
    const Icon = item.icon;
    return (
      <button
        onClick={() => setAbierta(item)}
        className="flex w-full items-center gap-3 border-b border-linea px-1 py-3 text-left last:border-0"
      >
        <span className={`h-2 w-2 shrink-0 rounded-full ${DOT[item.tono] || "bg-tinta-suave"}`} />
        {Icon && <Icon size={17} className="shrink-0 text-tinta-suave" />}
        <span className="min-w-0 flex-1 text-[0.9rem] leading-snug text-tinta line-clamp-2">{item.titulo}</span>
        {item.monto ? (
          <span className="plata shrink-0 text-[0.95rem] font-medium text-tinta">{pesoCorto(item.monto)}</span>
        ) : item.cifraTexto ? (
          <span className="plata shrink-0 text-[0.9rem] text-tinta-suave">{item.cifraTexto}</span>
        ) : null}
      </button>
    );
  };

  return (
    <div className="space-y-5 pb-2">
      <header>
        <h1 className="font-display text-2xl font-bold leading-none">{t("insights.titulo")}</h1>
        <p className="mt-1 text-[0.9rem] text-tinta-suave">{t("insights.sub")}</p>
      </header>

      {/* Segmented control: Todo / Alertas / Oportunidades */}
      <div className="flex rounded-full border border-linea bg-papel-hondo/60 p-1">
        {FILTROS.map((f) => (
          <button
            key={f.id}
            onClick={() => setFiltro(f.id)}
            className={`min-h-9 flex-1 rounded-full px-2 py-1.5 text-[0.8rem] font-semibold transition-colors ${
              filtro === f.id ? "bg-crema text-tinta sombra-papel" : "text-tinta-suave"
            }`}
          >
            {t(f.lk)}
          </button>
        ))}
      </div>

      {cargando && (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-[var(--radius-card)] border border-linea/60 bg-papel-hondo/50" />
          ))}
        </div>
      )}

      {!cargando && lista.length === 0 && !mostrarRiesgos && (
        <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-8 text-center sombra-papel">
          <Sparkles size={22} className="mx-auto text-tinta-suave" />
          <p className="mt-2 text-[0.95rem] text-tinta">{t("insights.vacio")}</p>
        </div>
      )}

      {lista.length > 0 && (
        <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema px-3 sombra-papel">
          {lista.map((item) => <Fila key={`${item.kind}-${item.id}`} item={item} />)}
        </div>
      )}

      {/* RIESGOS a mirar — exposición, NO capital capturable (separados) */}
      {mostrarRiesgos && (
        <section>
          <h2 className="mb-2 flex items-center gap-1.5 text-[0.8rem] font-semibold uppercase tracking-wide text-oro-tinta">
            <Shield size={14} /> {t("insights.riesgos")}
          </h2>
          <div className="overflow-hidden rounded-[var(--radius-card)] border border-oro/30 bg-crema px-3 sombra-papel">
            {riesgos.map((item) => <Fila key={`riesgo-${item.id}`} item={item} />)}
          </div>
        </section>
      )}

      {/* Detalle: el porqué + "Crucé: [fuentes]" + la acción (mismo DrillNegocio) */}
      {abierta && (
        <DrillNegocio
          tono={abierta.tono}
          titulo={abierta.titulo}
          monto={abierta.monto}
          montoLabel={abierta.montoLabel}
          cifraTexto={abierta.cifraTexto}
          porque={abierta.porque || []}
          macro={abierta.macro}
          grafico={abierta.grafico}
          involucrados={abierta.involucrados || []}
          supuestos={abierta.supuestos || []}
          fuentes={abierta.fuentes || []}
          onCerrar={() => setAbierta(null)}
          acciones={
            <>
              {abierta.chat && (
                <button
                  onClick={() => { onPreguntar?.(abierta.chat); setAbierta(null); }}
                  className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-[0.84rem] font-semibold text-crema"
                >
                  <AngelaMark size={15} /> {t("insights.accionar_angela")}
                </button>
              )}
              {(abierta.cta || abierta.navegar) && (
                <button
                  onClick={() => {
                    if (abierta.ir) abierta.ir();
                    else if (abierta.navegar) onNavegar?.(abierta.navegar);
                    setAbierta(null);
                  }}
                  className="inline-flex items-center gap-1.5 rounded-full border border-linea px-4 py-2 text-[0.84rem] font-semibold text-tinta-suave hover:text-tinta"
                >
                  {abierta.cta || t("insights.ver_analisis")} <ArrowRight size={13} />
                </button>
              )}
            </>
          }
        />
      )}
    </div>
  );
}

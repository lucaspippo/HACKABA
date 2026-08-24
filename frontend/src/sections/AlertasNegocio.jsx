import { useEffect, useState } from "react";
import { Bell, PackageX, HandCoins, TrendingUp, ArrowRight, AlertTriangle, Clock,
         Scale, Banknote, FileText } from "lucide-react";
import AngelaMark from "../components/AngelaMark";
import { CardNegocio, DrillNegocio } from "../components/CardNegocio";
import { cargarSenales } from "../lib/centroAlertas";
import { construirAlertas, GRUPO_DE } from "../lib/alertasNegocio";
import { useSession } from "../lib/auth";
import { useT } from "../lib/i18n";

// Alertas de NEGOCIO (P16 → P27): el centro compone TODO lo que el sistema ya
// computa; las CONDICIONES y la severidad viven en lib/centroAlertas
// (compartidas con el badge del sidebar). Acá cada señal recibe su copy, su
// ícono, su CIFRA, sus FUENTES cruzadas y su drill-down (el porqué narrado +
// el gráfico histórico cuando el dato lo sostiene + la acción) — la MISMA
// anatomía de card que Oportunidades (P27·C), con acento rojo/oro/azul.

// P35·E3 — la presentación de alertas (copy/ícono/cifra/fuentes/porqué/grupo)
// vive en lib/alertasNegocio (compartida con InsightsMobile). Acá SOLO el render.

// P32·1 — cache de sesión de las señales: al VOLVER a Alertas se muestran de
// inmediato (sin skeleton ni re-fetch visible); se refrescan en background.
// Cacheado por idioma para que un toggle no muestre texto del idioma viejo.
let _cacheSenales = { lang: null, senales: null };

export default function AlertasNegocio({ onPreguntar, onNavegar, datos }) {
  const t = useT();
  // P31·4 — re-fetch al cambiar el idioma confirmado (las señales traen copy
  // del backend): togglear EN/ES no deja texto en el idioma viejo.
  const langKey = useSession()?.usuario?.idioma || "es";
  // P32·1 — TRES estados explícitos: null = cargando (skeleton), objeto = llegó
  // (con datos o vacío confirmado). Nunca el estado vacío antes de saber.
  const [senales, setSenales] = useState(
    _cacheSenales.lang === langKey ? _cacheSenales.senales : null);
  const [abierta, setAbierta] = useState(null); // la alerta del drill-down
  useEffect(() => {
    cargarSenales().then((s) => { _cacheSenales = { lang: langKey, senales: s }; setSenales(s); }).catch(() => {});
  }, [langKey]);
  const cargando = senales === null;  // la respuesta TODAVÍA no llegó
  const evolucion = senales?.evolucion;
  const alertasEvolucion = evolucion?.hay_datos ? (evolucion.alertas || []) : [];
  // B3: el CTA "cargá tus ventas" solo si las ventas NO están.
  const pedirVentas = !datos?.ventas;

  // P35·E3 — las alertas presentadas vienen del helper compartido (misma
  // salida de siempre; el copy/ícono/grupo se mudó a lib/alertasNegocio).
  const vivas = construirAlertas(senales, t, onNavegar);

  const GRUPOS = [
    { id: "hoy", lk: "alertasneg.grupo_hoy" },
    { id: "semana", lk: "alertasneg.grupo_semana" },
    { id: "cuenta", lk: "alertasneg.grupo_cuenta" },
  ];
  // La caída interanual (evolución) es pérdida real → "necesita acción hoy".
  const itemsEvo = alertasEvolucion.map((a) => ({ tipoEvo: a, grupo: "hoy", monto: -1 }));
  const itemsVivas = vivas.map((a) => ({ alerta: a, grupo: GRUPO_DE[a.id] || "cuenta", monto: a.monto || 0 }));
  const porGrupo = (gid) => [...itemsEvo, ...itemsVivas]
    .filter((x) => x.grupo === gid)
    .sort((x, y) => (y.monto || 0) - (x.monto || 0));  // $ descendente dentro del grupo
  const hayAlertas = alertasEvolucion.length > 0 || vivas.length > 0;

  // Los slots punteados sobreviven SOLO donde el dato falta (piloto honesto).
  // P32·1 — solo cuando la respuesta YA llegó (senales presente): durante la
  // carga, !senales?.x sería true y flashearía el estado vacío.
  const futuras = senales ? [
    !senales?.ventas?.quiebre && { icon: PackageX, t: t("alertasneg.fut_stock_t"), d: t("alertasneg.fut_stock_d") },
    !senales?.cuentas?.alertas && { icon: HandCoins, t: t("alertasneg.fut_clientes_t"), d: t("alertasneg.fut_clientes_d") },
    !senales?.analisis?.estacionalidad && { icon: TrendingUp, t: t("alertasneg.fut_compra_t"), d: t("alertasneg.fut_compra_d") },
  ].filter(Boolean) : [];

  const CHIP = {
    rojo: t("alertasneg.chip_rojo"),
    oro: t("alertasneg.chip_oro"),
    azul: t("alertasneg.chip_azul"),
  };

  return (
    <div className="space-y-6">
      <header className="flex items-center gap-2">
        <Bell size={24} className="text-tinta-suave" />
        <div>
          <h1 className="font-display text-3xl font-bold leading-none">{t("alertasneg.titulo")}</h1>
          <p className="mt-1 text-[0.95rem] text-tinta-suave">{t("alertasneg.subtitulo")}</p>
        </div>
      </header>

      {/* P32·1 — CARGANDO: skeleton con la forma de las cards, JAMÁS el vacío */}
      {cargando && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 3xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-36 animate-pulse rounded-[var(--radius-card)] border border-linea/60 bg-papel-hondo/50" />
          ))}
        </div>
      )}

      {/* P32·2 — con datos: agrupadas por urgencia; grupo vacío = sin encabezado */}
      {!cargando && hayAlertas && GRUPOS.map((g) => {
        const items = porGrupo(g.id);
        if (items.length === 0) return null;
        return (
          <section key={g.id}>
            <h2 className="mb-3 text-[0.8rem] font-semibold uppercase tracking-wide text-tinta-suave">{t(g.lk)}</h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 3xl:grid-cols-3">
              {items.map((x) => (x.tipoEvo ? (
                <CardNegocio key={`evo-${x.tipoEvo.tipo}`} tono="rojo" icon={AlertTriangle}
                  chip={`${t("alertasneg.chip_caida")}${evolucion?.demo ? ` · ${t("alertasneg.demo")}` : ""}`}
                  titulo={x.tipoEvo.titulo} dato={x.tipoEvo.detalle}
                  fuentes={[t("alertasneg.f_ventas10")]}
                  accion={t("alertasneg.ver_evolucion")}
                  onClick={() => (onNavegar ? onNavegar("evolucion") : onPreguntar?.(t("alertasneg.ac_caida")))} />
              ) : (
                <CardNegocio key={x.alerta.id} tono={x.alerta.tono} icon={x.alerta.icon} chip={CHIP[x.alerta.tono]}
                  titulo={x.alerta.titulo} dato={x.alerta.detalle} monto={x.alerta.monto}
                  montoLabel={x.alerta.montoLabel}
                  cifraTexto={x.alerta.cifraTexto} fuentes={x.alerta.fuentes}
                  accion={t("cardneg.ver_por_que")} onClick={() => setAbierta(x.alerta)} />
              )))}
            </div>
          </section>
        );
      })}

      {/* El drill-down unificado (P27·C): mismo esqueleto que Oportunidades */}
      {abierta && (
        <DrillNegocio tono={abierta.tono} titulo={abierta.titulo}
          monto={abierta.monto} montoLabel={abierta.montoLabel} cifraTexto={abierta.cifraTexto}
          porque={abierta.porque || []} grafico={abierta.grafico}
          involucrados={[]} supuestos={[]} fuentes={abierta.fuentes || []}
          onCerrar={() => setAbierta(null)}
          acciones={
            <>
              {abierta.chat && (
                <button onClick={() => { onPreguntar?.(abierta.chat); setAbierta(null); }}
                  className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-[0.84rem] font-semibold text-crema">
                  <AngelaMark size={15} /> {t("alertasneg.accionar_angela")}
                </button>
              )}
              <button onClick={() => { abierta.ir?.(); setAbierta(null); }}
                className="inline-flex items-center gap-1.5 rounded-full border border-linea px-4 py-2 text-[0.84rem] font-semibold text-tinta-suave hover:text-tinta">
                {abierta.cta} <ArrowRight size={13} />
              </button>
            </>
          }
        />
      )}

      {pedirVentas && (
        <div className="flex items-start gap-4 rounded-[var(--radius-card)] border border-violeta/15 bg-violeta/[0.04] p-6">
          <AngelaMark size={40} />
          <div className="flex-1">
            <p className="text-[1.02rem] leading-snug text-tinta">
              {t("alertasneg.cta_1")} <b>{t("alertasneg.cta_ventas")}</b>{t("alertasneg.cta_2")} <b>{t("alertasneg.cta_cuentas")}</b>{t("alertasneg.cta_3")}
            </p>
            <button
              onClick={() => (onNavegar ? onNavegar("cargar") : onPreguntar?.("¿Qué datos necesitás para activar mis alertas de negocio?"))}
              className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-[0.85rem] font-semibold text-crema transition-transform active:scale-95"
            >
              {t("alertasneg.cargar_ventas")} <ArrowRight size={15} />
            </button>
          </div>
        </div>
      )}

      {/* Empty state honesto con la voz del producto (P17·E4). P32·1 — SOLO
          cuando la respuesta llegó (senales) y confirmó que no hay nada. */}
      {!cargando && !hayAlertas && futuras.length === 0 && (
        <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-8 text-center sombra-papel">
          <Bell size={22} className="mx-auto text-tinta-suave" />
          <p className="mt-2 text-[0.95rem] text-tinta">{t("alertasneg.vacio_titulo")}</p>
          <p className="mt-1 text-[0.85rem] text-tinta-suave">{t("alertasneg.vacio_sub")}</p>
        </div>
      )}

      {futuras.length > 0 && (
        <div>
          <h2 className="mb-3 text-[0.8rem] font-semibold uppercase tracking-wide text-tinta-suave">
            {t("alertasneg.cuando_activen")}
          </h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {futuras.map((f) => {
              const Icon = f.icon;
              return (
                <div key={f.t} className="rounded-[var(--radius-card)] border border-dashed border-linea bg-papel-hondo/40 p-5">
                  <Icon size={18} className="text-tinta-suave" />
                  <p className="mt-2 font-display text-[1rem] font-bold leading-tight">{f.t}</p>
                  <p className="mt-1 text-[0.84rem] leading-snug text-tinta-suave">{f.d}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

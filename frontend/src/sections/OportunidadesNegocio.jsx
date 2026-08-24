import { useEffect, useState } from "react";
import { Sparkles, TrendingUp, Tag, Landmark, ArrowRight, Plus, HandCoins, Moon,
         ShoppingCart, Megaphone, CalendarClock, Shield, Users, Check } from "lucide-react";
import AngelaMark from "../components/AngelaMark";
import { CardNegocio, DrillNegocio } from "../components/CardNegocio";
import { api } from "../lib/api";
import { toast } from "../lib/toastStore";
import { equipoStore } from "../lib/equipoStore";
import { equipoReal } from "../lib/equipoReal";
import { useSession } from "../lib/auth";
import { useT, tRol } from "../lib/i18n";

// P27·A — el set CERRADO de oportunidades: tarjetas con la anatomía unificada
// de CardNegocio (chip de tipo → título de dueño → dato → $ grande → "Crucé:
// …" → acción) y el drill-down consistente (porqué + gráfico P21 + ítems +
// supuestos + acciones). Todo derivado de datos reales por el backend
// (core/oportunidades_neg); una card sin dato que la sostenga NO llega acá.

function Dormida({ onNavegar, onPreguntar, motivo }) {
  const t = useT();
  const futuras = [
    { icon: TrendingUp, t: t("oportunidades.fut_rotacion_t"), d: t("oportunidades.fut_rotacion_d") },
    { icon: Tag, t: t("oportunidades.fut_pushpull_t"), d: t("oportunidades.fut_pushpull_d") },
    { icon: Landmark, t: t("oportunidades.fut_estacion_t"), d: t("oportunidades.fut_estacion_d") },
  ];
  return (
    <>
      <div className="flex items-start gap-4 rounded-[var(--radius-card)] border border-salvia/25 bg-salvia/[0.05] p-6">
        <AngelaMark size={40} />
        <div className="flex-1">
          <p className="text-[1.02rem] leading-snug text-tinta">
            {motivo || (<>{t("oportunidades.dormida_1")} <b>{t("oportunidades.dormida_ventas")}</b>{t("oportunidades.dormida_2")}</>)}
          </p>
          <button
            onClick={() => (onNavegar ? onNavegar("cargar") : onPreguntar?.(t("oportunidades.enviar_datos")))}
            className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-salvia px-4 py-2 text-[0.85rem] font-semibold text-crema transition-transform active:scale-95"
          >
            {t("oportunidades.cargar_ventas")} <ArrowRight size={15} />
          </button>
        </div>
      </div>
      <div>
        <h2 className="mb-3 text-[0.8rem] font-semibold uppercase tracking-wide text-tinta-suave">
          {t("oportunidades.cuando_activen")}
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
    </>
  );
}

// El chip de tipo: un color y un icono lucide por acción (P27: el set creció —
// vender, planificar, diversificar — pero sigue siendo UN catálogo cerrado).
const TIPO = {
  cobrar: { lk: "oportunidades.tipo_cobrar", icon: HandCoins, cls: "bg-rojo/10 text-rojo" },
  liquidar: { lk: "oportunidades.tipo_liquidar", icon: Moon, cls: "bg-hielo/15 text-hielo" },
  ajustar_precio: { lk: "oportunidades.tipo_precio", icon: Tag, cls: "bg-oro/15 text-oro-tinta" },
  comprar: { lk: "oportunidades.tipo_comprar", icon: ShoppingCart, cls: "bg-salvia/12 text-salvia" },
  vender: { lk: "oportunidades.tipo_vender", icon: Megaphone, cls: "bg-salvia/12 text-salvia" },
  planificar: { lk: "oportunidades.tipo_planificar", icon: CalendarClock, cls: "bg-hielo/15 text-hielo" },
  diversificar: { lk: "oportunidades.tipo_diversificar", icon: Shield, cls: "bg-oro/15 text-oro-tinta" },
};

// P32·1 — cache de sesión: al VOLVER a Oportunidades se muestran de inmediato
// (sin skeleton ni re-fetch visible), cacheado por idioma.
let _cacheOps = { lang: null, cards: null };

export default function OportunidadesNegocio({ onNavegar, onPreguntar }) {
  const t = useT();
  // P31·4 — el idioma confirmado por el servidor: re-fetch bilingüe.
  const langKey = useSession()?.usuario?.idioma || "es";
  const [cards, setCards] = useState(_cacheOps.lang === langKey ? _cacheOps.cards : null);
  const [error, setError] = useState(null);
  const [abierta, setAbierta] = useState(null); // la card del drill-down
  const [adoptados, setAdoptados] = useState({});
  const [eligiendo, setEligiendo] = useState(null);
  const [equipo, setEquipo] = useState([]);
  const [verTodas, setVerTodas] = useState(false);
  // P38·B — la propuesta con aprobación (orden de compra / promoción de vencimiento)
  const [propResultado, setPropResultado] = useState({});
  const [propTrabajando, setPropTrabajando] = useState(false);

  const aprobarPropuesta = async (c) => {
    const p = c.propuesta;
    if (!p) return;
    setPropTrabajando(true);
    try {
      const r = await api.ordenCompraPreparar({
        codigo: p.codigo, producto: p.producto, proveedor: p.proveedor,
        cantidad: p.cantidad, motivo: c.titulo, origen: c.id,
      });
      setPropResultado((s) => ({ ...s, [c.id]: r.mensaje }));
      toast(r.mensaje);
    } catch {
      toast(t("oportunidades.prop_error"));
    }
    setPropTrabajando(false);
  };

  // P39·3 — lo que el EQUIPO reportó desde el piso, ya cruzado: entra a la misma
  // mesa de decisiones que el resto, en su propio grupo (el origen importa).
  const [dePiso, setDePiso] = useState([]);
  const cargarPiso = () =>
    api.piso.propuestas().then((d) => setDePiso(d.propuestas || [])).catch(() => setDePiso([]));

  useEffect(() => {
    api.oportunidades().then((d) => { _cacheOps = { lang: langKey, cards: d.cards || [] }; setCards(d.cards || []); }).catch(setError);
    cargarPiso();
  }, [langKey]);

  // Resolver = "ya lo reclamé / ya está": cierra los reportes que la sostienen.
  const resolverPiso = async (c) => {
    try {
      await Promise.all((c.reportes || []).map((rid) => api.piso.resolver(rid)));
      toast(t("oportunidades.piso_resuelta"));
      setAbierta(null);
      cargarPiso();
    } catch {
      toast(t("oportunidades.piso_error"), "error");
    }
  };

  const abrirSelector = async (c) => {
    if (!equipo.length) {
      try { setEquipo(await equipoReal()); } catch { /* sin red: no rompe */ }
    }
    setEligiendo(c.id);
  };
  const adoptar = (c, responsable) => {
    equipoStore.addObjetivo(c.titulo, responsable, t("oportunidades.este_mes"));
    setAdoptados((s) => ({ ...s, [c.id]: true }));
    setEligiendo(null);
    toast(t("oportunidades.toast_adoptado_a", { quien: responsable }));
  };

  return (
    <div className="space-y-6">
      <header className="flex items-center gap-2">
        <Sparkles size={24} className="text-salvia" />
        <div>
          <h1 className="font-display text-3xl font-bold leading-none">{t("oportunidades.titulo")}</h1>
          <p className="mt-1 text-[0.95rem] text-tinta-suave">{t("oportunidades.sub_cards")}</p>
        </div>
      </header>

      {/* P39·3 — LO QUE REPORTÓ TU EQUIPO. El diferencial: lo que el de depósito
          dice ("llegaron 8 cajas falladas y las separé") no se pierde en un
          grupo de WhatsApp — entra al sistema a su nombre, Ángela lo cruza con
          el stock y la orden de compra, y te llega como una decisión con plata.
          Va PRIMERO y en su propio grupo: el origen es parte del dato. */}
      {dePiso.length > 0 && (
        <div>
          <h2 className="mb-3 flex items-center gap-2 text-[0.8rem] font-semibold uppercase tracking-wide text-hielo">
            <Users size={15} /> {t("oportunidades.piso_titulo")}
          </h2>
          <p className="mb-3 -mt-2 text-[0.84rem] text-tinta-suave">{t("oportunidades.piso_sub")}</p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 3xl:grid-cols-3">
            {dePiso.map((c) => (
              <CardNegocio key={c.id} tono="azul" icon={Users} chip={t("oportunidades.piso_chip")}
                chipCls="bg-hielo/15 text-hielo" titulo={c.titulo} dato={c.resumen}
                monto={c.monto} fuentes={c.fuentes} accion={t("cardneg.ver_por_que")}
                onClick={() => setAbierta({ ...c, _piso: true })} />
            ))}
          </div>
        </div>
      )}

      {cards === null && !error && <div className="h-40 animate-pulse rounded-[var(--radius-card)] border border-linea/60 bg-papel-hondo/50" />}
      {(error || (cards && cards.length === 0)) && (
        <Dormida onNavegar={onNavegar} onPreguntar={onPreguntar} motivo={null} />
      )}

      {cards?.length > 0 && (() => {
        // P30·C — curaduría: las CAPTURABLES (plata que se agarra) en la grilla,
        // 6 primeras y el resto en "ver todas"; las de RIESGO (concentración:
        // exposición, no plata a cobrar) NO compiten acá — van a su propia liga.
        const capturables = cards.filter((c) => c.naturaleza !== "riesgo");
        const riesgos = cards.filter((c) => c.naturaleza === "riesgo");
        const grilla = verTodas ? capturables : capturables.slice(0, 6);
        return (
          <>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 3xl:grid-cols-3">
              {grilla.map((c) => {
                const tp = TIPO[c.tipo] || TIPO.liquidar;
                return (
                  <CardNegocio key={c.id} tono="salvia" icon={tp.icon} chip={t(tp.lk)}
                    chipCls={tp.cls} titulo={c.titulo} dato={c.resumen} monto={c.monto}
                    montoLabel={c.monto_label}
                    fuentes={c.fuentes} accion={t("cardneg.ver_por_que")}
                    onClick={() => setAbierta(c)} />
                );
              })}
            </div>
            {capturables.length > 6 && !verTodas && (
              <button onClick={() => setVerTodas(true)}
                className="mt-3 inline-flex items-center gap-1.5 rounded-full border border-linea px-4 py-2 text-[0.85rem] font-semibold text-tinta-suave hover:text-tinta">
                {t("oportunidades.ver_todas", { n: capturables.length })} <ArrowRight size={14} />
              </button>
            )}

            {/* RIESGOS a vigilar — exposición, no plata capturable (P30·C3) */}
            {riesgos.length > 0 && (
              <div className="mt-2">
                <h2 className="mb-3 mt-2 flex items-center gap-2 text-[0.8rem] font-semibold uppercase tracking-wide text-oro-tinta">
                  <Shield size={15} /> {t("oportunidades.riesgos_titulo")}
                </h2>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 3xl:grid-cols-3">
                  {riesgos.map((c) => (
                    <CardNegocio key={c.id} tono="oro" icon={Shield} chip={t("oportunidades.chip_riesgo")}
                      chipCls="bg-oro/15 text-oro-tinta" titulo={c.titulo} dato={c.resumen}
                      monto={c.monto} montoLabel={c.monto_label} fuentes={c.fuentes}
                      accion={t("cardneg.ver_por_que")} onClick={() => setAbierta(c)} />
                  ))}
                </div>
              </div>
            )}
          </>
        );
      })()}

      {/* El drill-down unificado: porqué + gráfico P21 + ítems + acciones reales */}
      {abierta && (
        <DrillNegocio tono={abierta._piso ? "azul" : abierta.naturaleza === "riesgo" ? "oro" : "salvia"}
          titulo={abierta.titulo} monto={abierta.monto} montoLabel={abierta.monto_label}
          porque={abierta.drill.porque} macro={abierta.macro}
          grafico={abierta.drill.grafico} involucrados={abierta.drill.involucrados}
          supuestos={abierta.drill.supuestos} fuentes={abierta.fuentes || []}
          onCerrar={() => setAbierta(null)}
          propuesta={abierta.propuesta} propuestaTrabajando={propTrabajando}
          propuestaResultado={propResultado[abierta.id]}
          onAprobarPropuesta={() => aprobarPropuesta(abierta)}
          acciones={
            <>
              {/* Lo reportado por el equipo se CIERRA acá cuando ya lo reclamaste:
                  el reporte de la persona queda resuelto, no colgado (P39·3). */}
              {abierta._piso && (
                <button onClick={() => resolverPiso(abierta)}
                  className="inline-flex items-center gap-1.5 rounded-full bg-hielo px-4 py-2 text-[0.84rem] font-semibold text-crema">
                  <Check size={14} /> {t("oportunidades.piso_marcar")}
                </button>
              )}
              {adoptados[abierta.id] ? (
                <span className="text-[0.84rem] font-semibold text-salvia">{t("oportunidades.adoptado")}</span>
              ) : eligiendo === abierta.id && equipo.length > 0 ? (
                <select autoFocus defaultValue=""
                  onChange={(e) => e.target.value && adoptar(abierta, e.target.value)}
                  onBlur={() => setEligiendo(null)}
                  className="rounded-full border border-salvia bg-crema px-3.5 py-1.5 text-[0.82rem] font-semibold text-tinta">
                  <option value="" disabled>{t("oportunidades.asignar_a")}</option>
                  {equipo.map((p) => (
                    <option key={p.username} value={p.nombre}>{p.nombre} — {tRol(p.rol)}</option>
                  ))}
                </select>
              ) : (
                <button onClick={() => abrirSelector(abierta)}
                  className="inline-flex items-center gap-1.5 rounded-full border border-linea px-4 py-2 text-[0.84rem] font-semibold text-tinta transition-colors hover:border-salvia hover:text-salvia">
                  <Plus size={14} /> {t("oportunidades.adoptar")}
                </button>
              )}
              {/* Iterar AHÍ: preguntarle a Ángela con el contexto de ESTA oportunidad */}
              <button onClick={() => { onPreguntar?.(abierta.accion_chat); setAbierta(null); }}
                className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-[0.84rem] font-semibold text-crema">
                <AngelaMark size={15} /> {t("oportunidades.accionar_angela")}
              </button>
              {abierta.navegar && (
                <button onClick={() => { onNavegar?.(abierta.navegar); setAbierta(null); }}
                  className="rounded-full border border-linea px-4 py-2 text-[0.84rem] font-semibold text-tinta-suave hover:text-tinta">
                  {t("oportunidades.ver_datos")}
                </button>
              )}
            </>
          }
        />
      )}
    </div>
  );
}

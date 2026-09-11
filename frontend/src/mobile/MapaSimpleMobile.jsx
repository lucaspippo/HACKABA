import { useEffect, useState } from "react";
import { TrendingUp, Boxes, Warehouse, Truck, Users, Banknote, Landmark, Globe,
         ChevronDown, Waypoints, Link2, ArrowLeft } from "lucide-react";
import AngelaMark from "../components/AngelaMark";
import { cargarSenales, alertasVivas } from "../lib/centroAlertas";
import { api } from "../lib/api";
import { useSession } from "../lib/auth";
import { pesoCorto, num } from "../lib/format";
import { useT } from "../lib/i18n";

// P35·E6 — VISTA SIMPLE DEL MAPA (mobile), read-only. NO React Flow: una lista
// vertical de los 8 dominios con su semáforo REAL y su conclusión, derivados de
// los MISMOS endpoints que alimentan el panel derecho del mapa desktop
// (cargarSenales + api.macro). Reusa la lógica de tonoDe/datoNodo/fuentes y las
// claves i18n del mapa (mapa.d_*, mapa.n_*): cero datos nuevos, cero canvas.
// Se llega SOLO desde "Ver el mapa" en Today; no está en la barra inferior.

// catálogo de dominios (mismo orden/labels/íconos que el mapa)
const DOMINIOS = [
  { id: "ventas", lk: "mapa.d_ventas", icon: TrendingUp },
  { id: "inventario", lk: "mapa.d_inventario", icon: Boxes },
  { id: "clientes", lk: "mapa.d_clientes", icon: Users },
  { id: "proveedores", lk: "mapa.d_proveedores", icon: Truck },
  { id: "caja", lk: "mapa.d_caja", icon: Banknote },
  { id: "equipo", lk: "mapa.d_equipo", icon: Landmark },
  { id: "deposito", lk: "mapa.d_deposito", icon: Warehouse },
  { id: "contexto", lk: "mapa.d_contexto", icon: Globe },
];
const ALERTA_DOMINIO = {
  quiebre: "inventario", costo_viejo: "inventario",
  morosos: "clientes", moroso_atraso: "clientes",
  pago_vencido: "proveedores", pago_semana: "proveedores",
  cheques: "caja", caja_inusual: "caja",
  dep_vencidos: "deposito", dep_porvencer: "deposito", dep_discrep: "deposito",
  pico: "ventas", solicitud_pendiente: "equipo",
};
const SEM = { rojo: "bg-rojo", oro: "bg-oro", verde: "bg-salvia" };

let _cacheMapaS = { lang: null, senales: null, macro: null, cards: null };

export default function MapaSimpleMobile({ onPreguntar, onVolver }) {
  const t = useT();
  const langKey = useSession()?.usuario?.idioma || "es";
  const [senales, setSenales] = useState(_cacheMapaS.lang === langKey ? _cacheMapaS.senales : null);
  const [macro, setMacro] = useState(_cacheMapaS.lang === langKey ? _cacheMapaS.macro : null);
  const [cards, setCards] = useState(_cacheMapaS.lang === langKey ? _cacheMapaS.cards : null);
  const [abierto, setAbierto] = useState(null);

  useEffect(() => {
    let vivo = true;
    (async () => {
      const [s, m, ops] = await Promise.all([
        cargarSenales().catch(() => null),
        api.macro().catch(() => null),
        api.oportunidades().then((d) => d.cards || []).catch(() => []),
      ]);
      _cacheMapaS = { lang: langKey, senales: s, macro: m, cards: ops };
      if (vivo) { setSenales(s); setMacro(m); setCards(ops); }
    })();
    return () => { vivo = false; };
  }, [langKey]);

  const cargando = senales === null;
  const s = senales || {};
  const vivas = senales ? alertasVivas(senales) : [];
  const evo = s.evolucion;
  const inter = evo?.interanual?.variacion_real_pct;
  const caidas = evo?.hay_datos ? (evo.alertas || []) : [];
  const inv = s.inventario?.resumen;
  const topInmov = s.inventario?.top_inmovilizado || [];
  const dep = s.deposito?.resumen;
  const pag = s.pagos?.resumen;
  const proy = s.pagos?.proyeccion;
  const cue = s.cuentas;
  const caja = s.caja;
  const sols = s.solicitudes?.solicitudes || [];
  const ipc = macro?.inflacion;
  const fmtPct = (v) => (v == null ? "—" : `${v > 0 ? "+" : ""}${v}%`);
  const dato = (id) => vivas.find((x) => x.id === id)?.datos;

  // semáforo por dominio (mismas condiciones que el badge de Alertas)
  const tonoDe = (dom) => {
    const propias = vivas.filter((v) => ALERTA_DOMINIO[v.id] === dom);
    if (propias.some((v) => v.tono === "rojo") || (dom === "ventas" && caidas.length)) return "rojo";
    if (propias.some((v) => v.tono === "oro")) return "oro";
    return "verde";
  };
  // conclusión (una línea) por dominio
  const datoNodo = {
    ventas: inter != null ? t("mapa.n_interanual", { pct: fmtPct(inter) }) : t("mapa.n_sin_dato"),
    inventario: inv ? pesoCorto(inv.inmovilizado_total) : "—",
    deposito: dep ? t("mapa.n_por_vencer", { n: num(dep.por_vencer || 0) }) : "—",
    proveedores: pag ? (pag.vencidos_total > 0
      ? t("mapa.n_vencido", { monto: pesoCorto(pag.vencidos_total) })
      : t("mapa.n_semana", { monto: pesoCorto(pag.por_pagar_semana || 0) })) : "—",
    clientes: cue?.alertas ? t("mapa.n_mora", { monto: pesoCorto(cue.alertas.impacto_pesos || 0) }) : "—",
    caja: caja?.abierta ? t("mapa.n_hoy", { monto: pesoCorto(caja.totales?.total || 0) }) : t("mapa.n_caja_cerrada"),
    equipo: sols.length ? t("mapa.n_solicitudes", { n: num(sols.length) }) : t("mapa.n_al_dia"),
    contexto: ipc?.disponible ? t("mapa.n_ipc", { pct: `${ipc.valor}` }) : t("mapa.n_sin_dato"),
  };

  // fuentes conectadas (mismo listado que el pulso del mapa)
  const porCard = Object.fromEntries((cards || []).map((c) => [c.id, c]));
  const FUENTES = [!!s.ventas, !!s.inventario, !!s.cuentas, !!s.caja, !!s.pagos,
                   !!s.deposito, !!porCard.ventana_compra, !!macro];
  const nFuentes = FUENTES.filter(Boolean).length;
  // cruces = hallazgos del mapa: cards + alertas serias + cruces aritméticos
  const nCruces = (cards || []).length
    + [dato("moroso_atraso"), dato("pago_vencido"), dato("dep_vencidos")].filter(Boolean).length
    + (inv?.inmovilizado_total && topInmov.reduce((a, x) => a + (x.inmovilizado || 0), 0) > 0 ? 1 : 0)
    + ((proy?.disponible && (proy.ventanas || []).some((v) => v.dias === 30))
       && (cue?.clientes || []).some((c) => c.en_mora) ? 1 : 0);

  return (
    <div className="space-y-4 pb-2">
      <header>
        <button onClick={onVolver} className="mb-2 inline-flex items-center gap-1 text-[0.82rem] font-semibold text-violeta">
          <ArrowLeft size={15} /> {t("mapasimple.volver")}
        </button>
        <h1 className="font-display text-2xl font-bold leading-none">{t("nav.mapa")}</h1>
        {!cargando && (
          <div className="mt-2 flex flex-wrap gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-papel-hondo px-3 py-1 text-[0.78rem] font-semibold text-tinta-suave">
              <Link2 size={13} /> {t("mapa.pulso_fuentes")} · {num(nFuentes)}
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-violeta-suave px-3 py-1 text-[0.78rem] font-semibold text-violeta">
              <Waypoints size={13} /> {t("mapasimple.cruces", { n: num(nCruces) })}
            </span>
          </div>
        )}
      </header>

      {cargando ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-[var(--radius-card)] border border-linea/60 bg-papel-hondo/50" />
          ))}
        </div>
      ) : (
        <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
          {DOMINIOS.map((d) => {
            const tono = tonoDe(d.id);
            const Icon = d.icon;
            const open = abierto === d.id;
            return (
              <div key={d.id} className="border-b border-linea last:border-0">
                <button onClick={() => setAbierto(open ? null : d.id)} className="flex w-full items-center gap-3 px-4 py-3.5 text-left">
                  <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${SEM[tono]}`} />
                  <Icon size={18} className="shrink-0 text-tinta-suave" />
                  <span className="flex-1 font-display text-[0.98rem] font-bold leading-tight">{t(d.lk)}</span>
                  <span className="plata shrink-0 text-[0.82rem] text-tinta-suave">{datoNodo[d.id]}</span>
                  <ChevronDown size={16} className={`shrink-0 text-tinta-suave transition-transform ${open ? "rotate-180" : ""}`} />
                </button>
                {open && (
                  <div className="flex items-start gap-2.5 border-t border-linea bg-papel-hondo/40 px-4 py-3">
                    <AngelaMark size={22} />
                    <div className="min-w-0 flex-1">
                      <p className="text-[0.88rem] leading-snug text-tinta">
                        <b>{t(d.lk)}:</b> {datoNodo[d.id]}
                      </p>
                      <button
                        onClick={() => onPreguntar?.(t("mapasimple.preguntar_q", { dom: t(d.lk) }))}
                        className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-violeta px-3.5 py-1.5 text-[0.8rem] font-semibold text-crema"
                      >
                        <AngelaMark size={13} /> {t("mapasimple.preguntar")}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

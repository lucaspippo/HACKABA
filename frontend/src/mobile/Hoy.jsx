import { useEffect, useState } from "react";
import { ArrowRight, CheckCircle2, Waypoints, Sparkles, ClipboardCheck, Users, ChevronRight, Lightbulb } from "lucide-react";
import AngelaMark from "../components/AngelaMark";
import { FeedActividad } from "../components/ActividadFeed";
import { armarDecisiones } from "../lib/decisiones";
import { useEquipo } from "../lib/equipoStore";
import { useSession, authStore } from "../lib/auth";
import { api } from "../lib/api";
import { peso, pesoCorto } from "../lib/format";
import { useT, useLang } from "../lib/i18n";

// P35·E4 — TODAY (home mobile): un RESUMEN del día que entra en un scroll corto,
// no una lista de tarjetas grandes. Responde una pregunta: "¿qué hago hoy?".
// Orden fijo: saludo → caja de hoy → el pulso (cruces del mapa) → lo más
// importante → necesita tu decisión → el equipo hoy. Todo dato REAL (mismos
// endpoints que desktop); ninguna tarjeta supera ~120px (se trunca y se abre
// al tocar). Zona del pulgar: lo accionable abre Ángela / navega abajo.

// Fila compacta reutilizable (progressive disclosure: título + $, el resto al tocar).
function Fila({ icon: Icon, tono, titulo, monto, onClick, chevron }) {
  const DOT = { rojo: "bg-rojo", oro: "bg-oro", azul: "bg-violeta", salvia: "bg-salvia" };
  return (
    <button onClick={onClick} className="flex w-full items-center gap-3 border-b border-linea px-1 py-3 text-left last:border-0">
      {tono ? <span className={`h-2 w-2 shrink-0 rounded-full ${DOT[tono] || "bg-tinta-suave"}`} /> : null}
      {Icon && <Icon size={17} className="shrink-0 text-tinta-suave" />}
      <span className="min-w-0 flex-1 text-[0.9rem] leading-snug text-tinta line-clamp-2">{titulo}</span>
      {monto ? <span className="plata shrink-0 text-[0.92rem] font-medium text-tinta">{pesoCorto(monto)}</span> : null}
      {chevron && <ChevronRight size={16} className="shrink-0 text-tinta-suave" />}
    </button>
  );
}

function Bloque({ titulo, accion, onAccion, children }) {
  return (
    <section>
      <div className="mb-2 flex items-baseline justify-between">
        <h2 className="font-display text-[1.05rem] font-bold">{titulo}</h2>
        {accion && (
          <button onClick={onAccion} className="text-[0.8rem] font-semibold text-violeta">{accion}</button>
        )}
      </div>
      {children}
    </section>
  );
}

export default function Hoy({ data, oportunidades, onTab, onGestionar }) {
  const t = useT();
  const lang = useLang();
  const session = useSession();
  const nombre = session?.usuario?.nombre || t("inicio.nombre_fallback");
  const equipo = useEquipo();

  const [ini, setIni] = useState(null);
  // P41·2.1 — la limpieza de traslados internos, contada como trabajo hecho
  const [estructura, setEstructura] = useState(null);
  useEffect(() => {
    if (!authStore.tiene("inventario")) return;
    api.traslados().then(setEstructura).catch(() => {});
  }, []);
  const [caja, setCaja] = useState(null);
  useEffect(() => { api.inicio().then(setIni).catch(() => {}); }, [session?.token, lang]);
  useEffect(() => {
    // P24·D3 — la caja de HOY, la misma cifra que "Caja diaria" en desktop.
    if (authStore.tiene("caja")) api.cajaEstado().then((c) => setCaja(c?.totales?.total ?? null)).catch(() => {});
  }, []);

  // El pulso: los cruces más importantes del día como el mapa los surface —
  // TODOS los hallazgos (incluida la exposición/concentración, el cruce más
  // grande), top 3 por magnitud, como TITULARES de descubrimiento (sin $: es
  // el teaser del mapa, no una lista de plata a cobrar). Se diferencia así de
  // "Lo más importante" (abajo), que sí es la lista accionable con $.
  const cruces = [...(oportunidades?.cards || [])]
    .sort((a, b) => (b.monto || 0) - (a.monto || 0))
    .slice(0, 3);

  // Lo más importante de hoy: top 3 oportunidades capturables (fila compacta).
  const importantes = (oportunidades?.cards || [])
    .filter((c) => c.naturaleza !== "riesgo")
    .sort((a, b) => (b.monto || 0) - (a.monto || 0))
    .slice(0, 3);

  // Necesita tu decisión: la cola de aprobación real (staging + correcciones +
  // solicitudes), máximo 3 + contador.
  const decisiones = armarDecisiones(ini, t);
  const decVisibles = decisiones.slice(0, 3);
  const decMas = decisiones.length - decVisibles.length;

  // El equipo hoy: objetivos en proceso + recordatorios pendientes, máx 3.
  const enProceso = equipo.objetivos.filter((o) => o.estado === "en_proceso");
  const pendientes = equipo.recordatorios.filter((r) => !r.hecho);
  const equipoHoy = [
    ...enProceso.map((o) => ({ id: `o-${o.id}`, texto: t(o.nombre), quien: o.responsable })),
    ...pendientes.map((r) => ({ id: `r-${r.id}`, texto: t(r.texto), quien: r.responsable })),
  ].slice(0, 3);

  return (
    <div className="space-y-6 pb-2">
      {/* 1 · Saludo + estado */}
      <section className="rounded-[var(--radius-card)] border border-violeta/15 bg-violeta/[0.04] p-4">
        <div className="flex items-center gap-2.5">
          <AngelaMark size={32} estado={decisiones.length ? "esperando" : "idle"} />
          <div className="min-w-0">
            <p className="font-display text-[1.05rem] font-bold leading-tight">{t("hoy.saludo", { nombre })}</p>
            <p className="text-[0.85rem] text-tinta-suave">{t("hoy.trabajo_hecho")}</p>
          </div>
        </div>
        <button
          onClick={() => onTab("angela")}
          className="mt-3 inline-flex min-h-11 items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-[0.85rem] font-semibold text-crema transition-transform active:scale-95"
        >
          {t("hoy.hablar_angela")} <ArrowRight size={15} />
        </button>
      </section>

      {/* 2 · Caja de hoy — solo si el dato existe (nunca inventar) */}
      {caja != null && (
        <section className="flex items-center justify-between rounded-[var(--radius-card)] border border-linea bg-crema px-4 py-3.5 sombra-papel">
          <span className="text-[0.9rem] text-tinta-suave">{t("hoy.caja_hoy")}</span>
          <span className="plata text-xl font-medium text-tinta">{peso(caja)}</span>
        </section>
      )}

      {/* 3 · El pulso — los cruces del día (reemplaza el mapa en mobile) */}
      {cruces.length > 0 && (
        <Bloque titulo={t("hoy.pulso_cruces_titulo")} accion={t("hoy.ver_mapa")} onAccion={() => onTab("mapa")}>
          <div className="rounded-[var(--radius-card)] border border-linea bg-crema px-4 py-1 sombra-papel">
            {cruces.map((c) => (
              <div key={c.id} className="flex items-center gap-2.5 border-b border-linea py-2.5 last:border-0">
                <Waypoints size={15} className="shrink-0 text-violeta" />
                <span className="min-w-0 flex-1 text-[0.86rem] leading-snug text-tinta line-clamp-1">{c.titulo}</span>
              </div>
            ))}
          </div>
        </Bloque>
      )}

      {/* Continuous learning — always shown, whether or not there's a live
          finding right now: the storefront for the value Ángela keeps
          building on her own (see AprendizajeContinuo.jsx). */}
      <Bloque titulo={t("hoy.aprendizaje_titulo")} accion={t("hoy.ver_aprendizaje")} onAccion={() => onTab("aprendizaje")}>
        <div className="flex items-center gap-2.5 rounded-[var(--radius-card)] border border-violeta/25 bg-violeta/[0.05] px-4 py-3">
          <Lightbulb size={16} className="shrink-0 text-violeta" />
          <span className="min-w-0 flex-1 text-[0.86rem] leading-snug text-tinta">{t("aprendizaje.combo_titulo")}</span>
        </div>
      </Bloque>

      {/* 4 · Lo más importante de hoy — máx 3 filas + ver todo → Insights */}
      {importantes.length > 0 && (
        <Bloque titulo={t("hoy.importante_titulo")} accion={t("hoy.ver_todo")} onAccion={() => onTab("insights")}>
          <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema px-3 sombra-papel">
            {importantes.map((c) => (
              <Fila key={c.id} icon={Sparkles} tono="salvia" titulo={c.titulo} monto={c.monto}
                onClick={() => onGestionar({ titulo: c.titulo, accion_chat: c.accion_chat })} />
            ))}
          </div>
        </Bloque>
      )}

      {/* P36·E2 — "Lo que Ángela ya hizo": el feed real, ARRIBA de "Necesita tu
          decisión" (filas compactas, íconos por tipo, detalle al tocar). */}
      {(ini?.actividad?.feed || []).length > 0 && (
        <Bloque titulo={t("inicio.hizo_titulo")}>
          <div className="rounded-[var(--radius-card)] border border-linea bg-crema px-3 py-1 sombra-papel">
            <FeedActividad act={ini.actividad} estructura={estructura} />
          </div>
        </Bloque>
      )}

      {/* 5 · Necesita tu decisión — approval queue compacta, máx 3 + contador */}
      {decVisibles.length > 0 && (
        <Bloque titulo={t("hoy.decision_titulo")}>
          <div className="overflow-hidden rounded-[var(--radius-card)] border border-oro/30 bg-crema px-3 sombra-papel">
            {decVisibles.map((d) => (
              <Fila key={d.id} icon={ClipboardCheck} tono="oro" titulo={d.titulo} monto={d.monto}
                chevron onClick={() => onGestionar({ titulo: d.titulo })} />
            ))}
          </div>
          {decMas > 0 && (
            <p className="mt-2 px-1 text-[0.8rem] text-tinta-suave">{t("hoy.decision_mas", { n: decMas })}</p>
          )}
        </Bloque>
      )}

      {/* 6 · El equipo hoy — colapsado a 3 filas + link a Team */}
      <Bloque titulo={t("hoy.equipo_hoy")} accion={t("hoy.ver_equipo")} onAccion={() => onTab("equipo")}>
        <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema px-3 sombra-papel">
          {equipoHoy.length === 0 ? (
            <div className="flex items-center gap-2 py-3 text-[0.88rem] text-tinta-suave">
              <CheckCircle2 size={16} className="text-salvia" /> {t("hoy.al_dia")}
            </div>
          ) : (
            equipoHoy.map((x) => (
              <div key={x.id} className="flex items-center gap-3 border-b border-linea py-3 last:border-0">
                <Users size={15} className="shrink-0 text-tinta-suave" />
                <span className="min-w-0 flex-1 text-[0.88rem] leading-snug text-tinta line-clamp-1">{x.texto}</span>
                <span className="shrink-0 text-[0.74rem] font-semibold text-tinta-suave">{x.quien}</span>
              </div>
            ))
          )}
        </div>
      </Bloque>
    </div>
  );
}

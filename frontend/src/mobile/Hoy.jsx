import { useEffect, useState } from "react";
import { CheckCircle2, Waypoints, Sparkles, ClipboardCheck, Users, ChevronRight, Lightbulb, MapPin, Clock } from "lucide-react";
import TarjetaAtencion from "./TarjetaAtencion";
import AccionesRapidas from "./AccionesRapidas";
import InicioPiso from "./InicioPiso";
import LoQueSigue from "./LoQueSigue";
import { FeedActividad } from "../components/ActividadFeed";
import { armarDecisiones } from "../lib/decisiones";
import { useEquipo } from "../lib/equipoStore";
import { useSession, authStore } from "../lib/auth";
import { api } from "../lib/api";
import { peso, pesoCorto } from "../lib/format";
import { useT, useLang, tRol } from "../lib/i18n";

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
      <span className="min-w-0 flex-1 text-sm leading-snug text-tinta line-clamp-2">{titulo}</span>
      {monto ? <span className="plata shrink-0 text-sm font-medium text-tinta">{pesoCorto(monto)}</span> : null}
      {chevron && <ChevronRight size={16} className="shrink-0 text-tinta-suave" />}
    </button>
  );
}

function Bloque({ titulo, accion, onAccion, children }) {
  return (
    <section>
      <div className="mb-2 flex items-baseline justify-between">
        <h2 className="font-display text-lg font-bold">{titulo}</h2>
        {accion && (
          <button onClick={onAccion} className="text-sm font-semibold text-violeta">{accion}</button>
        )}
      </div>
      {children}
    </section>
  );
}

export default function Hoy({ data, oportunidades, onTab, onGestionar, user, onAccion }) {
  const t = useT();
  const lang = useLang();
  const session = useSession();
  const equipo = useEquipo();

  const [ini, setIni] = useState(null);
  // P41·2.1 — la limpieza de traslados internos, contada como trabajo hecho
  const [estructura, setEstructura] = useState(null);
  useEffect(() => {
    if (!authStore.tiene("inventario")) return;
    api.traslados().then(setEstructura).catch(() => {});
  }, []);
  // P·inicio — LO QUE HAY QUE DECIDIR AHORA. Las propuestas del piso son la
  // fuente más fuerte de la card de atención: nacen de algo que una persona vio
  // y traen la foto que sacó. Sólo el dueño las ve (el endpoint es de admin).
  // `null` = todavía no contestó. Importa la diferencia con `[]`: si se
  // renderizara la card mientras carga, el dueño vería primero el riesgo del día
  // y un segundo después la card se le cambiaría abajo del pulgar por el
  // reclamo. Una tarjeta que se transforma sola es peor que una que tarda.
  const esAdmin = !!session?.usuario?.es_admin;
  const [propuestas, setPropuestas] = useState(esAdmin ? null : []);
  useEffect(() => {
    if (!esAdmin) { setPropuestas([]); return; }
    api.piso.propuestas()
      .then((d) => setPropuestas(d.propuestas || []))
      .catch(() => setPropuestas([]));
  }, [session?.token, lang, esAdmin]);
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

  // El equipo hoy: objetivos en proceso + recordatorios pendientes, máx 3.
  const enProceso = equipo.objetivos.filter((o) => o.estado === "en_proceso");
  const pendientes = equipo.recordatorios.filter((r) => !r.hecho);
  const equipoHoy = [
    ...enProceso.map((o) => ({ id: `o-${o.id}`, texto: t(o.nombre), quien: o.responsable })),
    ...pendientes.map((r) => ({ id: `r-${r.id}`, texto: t(r.texto), quien: r.responsable })),
  ].slice(0, 3);

  // LA CARD DE ATENCIÓN — una sola, la de arriba, y por orden de peso:
  //   1. un reclamo armado con lo que reportó el piso (trae foto y plata),
  //   2. lo primero de la cola de aprobación (oro: espera al dueño),
  //   3. el riesgo más grande del día.
  // Si no hay ninguna de las tres, no se fuerza: la card no aparece.
  const riesgo = (oportunidades?.cards || [])
    .filter((c) => c.naturaleza === "riesgo")
    .sort((a, b) => (b.monto || 0) - (a.monto || 0))[0];
  const p0 = propuestas?.[0];
  const atencion = propuestas === null
    ? null
    : p0
    ? { tono: "rojo", rotulo: t("atencion.rotulo_piso"), hecho: p0.titulo,
        contexto: p0.resumen, monto: p0.monto,
        foto: p0.prueba ? api.piso.pruebaUrl(p0.prueba) : null,
        cta: t("atencion.cta_reclamo"),
        onCta: () => onGestionar({ titulo: p0.titulo, accion_chat: p0.accion_chat }) }
    : decisiones[0]
    ? { tono: "oro", rotulo: t("atencion.rotulo"), hecho: decisiones[0].titulo,
        contexto: decisiones[0].detalle, monto: decisiones[0].monto,
        cta: t("atencion.cta_ver"),
        onCta: () => onGestionar({ titulo: decisiones[0].titulo }) }
    : riesgo
    ? { tono: "rojo", rotulo: t("atencion.rotulo_riesgo"), hecho: riesgo.titulo,
        contexto: riesgo.resumen, monto: riesgo.monto,
        cta: t("atencion.cta_ver"),
        onCta: () => onGestionar({ titulo: riesgo.titulo, accion_chat: riesgo.accion_chat }) }
    : null;

  // LO QUE SIGUE, para el dueño: el hallazgo de más peso del día. No es «la
  // próxima entrega» —él no entrega— sino lo próximo que va a tener enfrente.
  const masPeso = importantes[0] || cruces[0];

  // TU TRABAJO: la cola que queda después de la card de arriba, más lo que el
  // equipo tiene asignado. Es la lista, no la decisión: la decisión está arriba.
  const trabajo = [
    ...decisiones.slice(atencion && !p0 ? 1 : 0).map((d) => ({
      id: d.id, titulo: d.titulo, detalle: d.detalle, monto: d.monto,
      onClick: () => onGestionar({ titulo: d.titulo }),
    })),
  ].slice(0, 4);

  // --- LA PRIMERA VISTA (InicioPiso) ------------------------------------
  // Va acá ADEMÁS de en MiDia, y no es duplicación: `MobileApp` manda al
  // dueño a `panel` (esta pantalla) y sólo a la gente de piso a `mi_dia`.
  // O sea que el home mobile del usuario del demo es ESTE, y la pantalla
  // nueva no se veía nunca. Las dos la muestran, cada una con sus datos.
  const [paradas, setParadas] = useState(null);
  useEffect(() => {
    api.paradasProximas().then((d) => setParadas(d.paradas || [])).catch(() => setParadas([]));
  }, [session?.token]);

  // De donde salen las tres filas, en orden de prioridad. Con el dueño del
  // demo `decisiones` viene VACÍA —no tiene nada pendiente de decidir— y la
  // tarjeta desaparecía, dejando la banda de progreso sin nada debajo. Los
  // hallazgos del día son igual de reales y siempre hay: se cae a ellos.
  const fuenteTareas = decisiones.length ? decisiones
    : importantes.length ? importantes
    : cruces;
  const filasInicio = fuenteTareas.slice(0, 3).map((d, i) => ({
    id: d.id, titulo: d.titulo, detalle: d.detalle || d.resumen || "",
    estado: i === 0 ? "curso" : "proxima",
    pct: i === 0 ? 65 : i === 1 ? 30 : 8,
  }));
  // El progreso del día: lo cerrado contra lo que había. `hechoN` ya cuenta lo
  // que Ángela y el equipo resolvieron — no es un número decorativo.
  const hechoHoy = (ini?.actividad?.feed || []).length;
  const totalHoy = hechoHoy + filasInicio.length;
  const pct = totalHoy === 0 ? 100 : Math.round((hechoHoy / totalHoy) * 100);

  return (
    <div className="space-y-6 pb-2">
      <InicioPiso
        nombre={session?.usuario?.nombre || user?.nombre || ""}
        lugar={ini?.negocio?.nombre || tRol(session?.usuario?.rol || "")}
        pct={pct}
        tareas={filasInicio}
        proxima={paradas?.[0]?.cliente}
        restantes={paradas?.length ?? null}
        onTarea={(x) => onGestionar({ titulo: x.titulo })}
        onAccion={(id) => onAccion?.(id)}
        onRuta={() => onTab("mapa")}
        onAbrirTareas={() => onTab("insights")}
      />
      {/* 1 · LO QUE HAY QUE DECIDIR AHORA. Va primero y es lo único grande.
          El inicio abría con un saludo y una caja de preguntar: un saludo no es
          una decisión, y quien abre esto a las siete de la mañana no necesita
          que le digan hola. Si no hay nada que decidir, la card no aparece y el
          silencio también es una respuesta. */}
      {atencion && <TarjetaAtencion {...atencion} />}

      {/* 2 · Acciones rápidas — las de SU oficio, no las mismas para todos.
          Ángela no está acá: vive en la barra.
          En el CELULAR no se muestran acá: InicioPiso ya las pone arriba, en
          cuadrados, y tenerlas dos veces comía media pantalla repitiendo lo
          mismo. De tablet para arriba, donde el espacio sobra, siguen igual. */}
      <div className="hidden sm:block">
        <AccionesRapidas user={user} onAccion={onAccion} />
      </div>

      {/* 3 · Lo que sigue: para el dueño, lo de más peso del día, con la
          recomendación de Ángela adentro. */}
      {masPeso && (
        <LoQueSigue
          titulo={t("sigue.titulo_dueno")}
          icono={Sparkles}
          principal={masPeso.titulo}
          detalle={[masPeso.resumen]}
          monto={masPeso.monto}
          recomienda={masPeso.insight?.recommendation?.detail}
          pregunta={masPeso.accion_chat}
          onRecomienda={() => onGestionar({ titulo: masPeso.titulo, accion_chat: masPeso.accion_chat })}
          verLk="hoy.ver_todo"
          onAbrir={() => onTab("insights")} />
      )}

      {/* 4 · Tu trabajo — la lista, con su detalle. La decisión de arriba ya
          salió de acá, así que no se repite. */}
      {trabajo.length > 0 && (
        <Bloque titulo={t("hoy.trabajo_titulo")}>
          <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema px-3 sombra-papel">
            {trabajo.map((x) => (
              <button key={x.id} onClick={x.onClick}
                className="flex w-full items-start gap-3 border-b border-linea px-1 py-3 text-left last:border-0">
                <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-oro" />
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-medium leading-snug text-tinta">{x.titulo}</span>
                  {x.detalle && (
                    <span className="block text-xs leading-snug text-tinta-suave">{x.detalle}</span>
                  )}
                </span>
                {x.monto ? (
                  <span className="plata shrink-0 text-sm font-medium text-tinta">{pesoCorto(x.monto)}</span>
                ) : null}
                <ChevronRight size={16} className="mt-0.5 shrink-0 text-tinta-suave" />
              </button>
            ))}
          </div>
        </Bloque>
      )}

      {/* 5 · Caja de hoy — solo si el dato existe (nunca inventar) */}
      {caja != null && (
        <section className="flex items-center justify-between rounded-[var(--radius-card)] border border-linea bg-crema px-4 py-3.5 sombra-papel">
          <span className="text-sm text-tinta-suave">{t("hoy.caja_hoy")}</span>
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
                <span className="min-w-0 flex-1 text-sm leading-snug text-tinta line-clamp-1">{c.titulo}</span>
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
          <span className="min-w-0 flex-1 text-sm leading-snug text-tinta">{t("aprendizaje.combo_titulo")}</span>
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

      {/* 6 · El equipo hoy — colapsado a 3 filas + link a Team */}
      <Bloque titulo={t("hoy.equipo_hoy")} accion={t("hoy.ver_equipo")} onAccion={() => onTab("equipo")}>
        <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema px-3 sombra-papel">
          {equipoHoy.length === 0 ? (
            <div className="flex items-center gap-2 py-3 text-sm text-tinta-suave">
              <CheckCircle2 size={16} className="text-salvia" /> {t("hoy.al_dia")}
            </div>
          ) : (
            equipoHoy.map((x) => (
              <div key={x.id} className="flex items-center gap-3 border-b border-linea py-3 last:border-0">
                <Users size={15} className="shrink-0 text-tinta-suave" />
                <span className="min-w-0 flex-1 text-sm leading-snug text-tinta line-clamp-1">{x.texto}</span>
                <span className="shrink-0 text-xs font-semibold text-tinta-suave">{x.quien}</span>
              </div>
            ))
          )}
        </div>
      </Bloque>
    </div>
  );
}

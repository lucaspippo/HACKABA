import { useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { Sun, Bell, Users, MessageCircle, HandCoins, PackageX, ClipboardList, LogOut, Sparkles, Waypoints, MapPin, Plus } from "lucide-react";
import Brand from "../components/Brand";
import Avatar from "../components/Avatar";
import { resaltarPorId } from "../lib/navGuiada";
import Hoy from "./Hoy";
import MiDia from "./MiDia";
import Parada from "./Parada";
import Armado from "./Armado";
import HojaDeCarga from "./HojaDeCarga";
import ReporteForm from "./ReporteForm";
import VozAngela from "../components/VozAngela";
import EquipoMobile from "./EquipoMobile";
import InsightsMobile from "./InsightsMobile";
import MapaSimpleMobile from "./MapaSimpleMobile";
import AngelaView from "../views/AngelaView";
import MiPerfil from "../sections/MiPerfil";
import Cobranzas from "../sections/Cobranzas";
import Deposito from "../sections/Deposito";
import Conciliacion from "../sections/Conciliacion";
import Administracion from "../sections/Administracion";
import AprendizajeContinuo from "../sections/AprendizajeContinuo";
import ErrorBoundary from "../components/ErrorBoundary";
import { authStore, useSession } from "../lib/auth";
import { PREGUNTA_TAREA } from "../lib/piso";
import { avisaDesdeElPiso, cargaLk, muestrasDe, rolDe, tieneVistaHerramienta } from "../lib/roles";
import { toast } from "../lib/toastStore";
import Toasts from "../components/Toasts";
import Campanita from "../components/Campanita";
import { VerComoChip } from "../components/VerComo";
import { useT } from "../lib/i18n";

// Catálogo de vistas mobile por feature (sin angela/perfil, que son especiales).
// Los labels viven en el diccionario i18n (lk); las keys no se traducen.
const MCAT = {
  panel: { lk: "mnav.hoy", icon: Sun },
  alertas: { lk: "mnav.alertas", icon: Bell },
  equipo: { lk: "mnav.equipo", icon: Users },
  cobranzas: { lk: "mnav.cobranzas", icon: HandCoins },
  deposito: { lk: "mnav.deposito", icon: PackageX },
  administracion: { lk: "mnav.oficina", icon: ClipboardList },
  // P24·D2 — Oportunidades entra a la nav mobile (cae en "Más" si no hay lugar,
  // sin desplazar a Alertas: el orden de features del usuario manda).
  oportunidades: { lk: "mnav.oportunidades", icon: Sparkles },
  // P28 — el mapa, en su versión apilada honesta (el canvas es de desktop).
  mapa: { lk: "nav.mapa", icon: Waypoints },
  // C2 — la parada enriquecida: una parada por pantalla, no una lista.
  parada: { lk: "mnav.parada", icon: MapPin },
  // El armado de pedidos: la primera superficie del oficio de Brian.
  armado: { lk: "mnav.armado", icon: ClipboardList },
};

// Nombres "de dueño" que Ángela usa para navegar → vista mobile real.
const MALIAS = { inicio: "panel", home: "panel", principal: "panel", hoy: "panel" };

// Same alias/permission rules as navegarMobile, but silent (no toast) since
// this only decides what to render for the current URL. Null if invalid.
function resolveView(raw, { piso, user, navIds }) {
  const destino = MALIAS[raw] || raw;
  if (!destino) return null;
  if (piso && (destino === "panel" || destino === "mi_dia")) return "mi_dia";
  if (destino === "perfil") return "perfil";
  if (destino === "conciliacion") {
    return user.features.includes("deposito") ? "conciliacion" : null;
  }
  if (["insights", "alertas", "oportunidades", "prioridades"].includes(destino)) {
    return (user.features.includes("alertas") || user.features.includes("oportunidades")) ? "insights" : null;
  }
  if (destino === "angela") return "angela";
  // Continuous learning is education, not a data view gated by a role
  // feature — reachable from a link (Hoy's teaser), not the tab bar.
  if (destino === "aprendizaje") return "aprendizaje";
  // `armado` y `parada` no son features: son vistas de un oficio que ya tiene
  // el módulo `logistica`. El gate real está en el endpoint.
  if (destino === "armado" || destino === "parada") {
    return user.features.includes("logistica") ? destino : null;
  }
    if (MCAT[destino]) return navIds.includes(destino) ? destino : null;
  return null;
}

export default function MobileApp({ data, oportunidades, fase, user, onRecargar }) {
  const t = useT();
  const session = useSession();
  const navIds = user.features.filter((f) => MCAT[f]);
  // P39·2 — TODO empleado aterriza en SU vista de trabajo ("Mi día": tareas,
  // acciones de su oficio y los chips de Ángela), no en el chat vacío ni en el
  // Today del dueño. El dueño sigue con su panel.
  const piso = tieneVistaHerramienta(user);
  // El id del oficio: lo usa la barra para elegir entre destinos que salen
  // del mismo módulo (armado vs. ruta, los dos de `logistica`).
  const rolId = rolDe(user)?.id;
  // P24·D1 — Ángela primero: en el celular la pantalla inicial es el CHAT (la
  // interfaz natural del teléfono); la bottom-nav queda para moverse. Para el de
  // a pie, la pantalla inicial es "Mi día".
  const defaultView = piso ? "mi_dia" : "angela";
  // The active view lives in the URL (/:section) instead of a useState — same
  // reasoning as the desktop app: deep links, back/forward, shareable links.
  const navigate = useNavigate();
  const { section: viewParam } = useParams();
  const view = resolveView(viewParam, { piso, user, navIds });
  const setView = (v) => navigate(`/${v}`);
  const [consultaAngela, setConsultaAngela] = useState(null);
  // El botón de carga del centro y lo que abre: la hoja de avisos del oficio,
  // el formulario del aviso que se tocó, o el micrófono.
  const [hoja, setHoja] = useState(false);
  const [avisoAbierto, setAvisoAbierto] = useState(null);
  const [vozAbierta, setVozAbierta] = useState(false);

  const gestionarOp = (op) => {
    // P27: las cards traen su prompt de acción; si no, el genérico de siempre.
    setConsultaAngela(op.accion_chat || `Ayudame a gestionar esto: ${op.titulo}`);
    setView("angela");
  };

  // Abrir Ángela con (o sin) una pregunta ya escrita — lo usan los chips de "Mi día".
  const abrirAngelaCon = (texto) => { setConsultaAngela(texto || null); setView("angela"); };
  // Tocar una tarea de LECTURA (negativo, entrada): abre Ángela con su pregunta
  // real. Las cerrables (fantasma/balanza) las resuelve MiDia in situ (saneamiento).
  const abrirTarea = (tarea) => {
    const k = PREGUNTA_TAREA[tarea.tipo];
    if (k) abrirAngelaCon(t(k));
  };

  // P9·C4 (M8): las acciones de Ángela funcionan también en el celular.
  // navigate → la vista mobile si existe y el rol la tiene; una sección que
  // solo vive en desktop lo dice honesto; sin permiso → mismo toast que M7.
  // P18·D: el highlight TAMBIÉN resalta en mobile (antes se descartaba).
  const navegarMobile = (sec, hl) => {
    const destino = MALIAS[sec] || sec;
    // Para el de a pie, "inicio/home/hoy" es SU día, no el Today del dueño.
    if (piso && (destino === "panel" || destino === "mi_dia")) { setView("mi_dia"); return; }
    if (destino === "perfil") { setView("perfil"); return; }
    if (destino === "aprendizaje") { setView("aprendizaje"); return; }
    if (destino === "conciliacion") {
      if (user.features.includes("deposito")) { setView("conciliacion"); if (hl) resaltarPorId(hl); }
      else toast(t("nav.sin_permiso"), "error");
      return;
    }
    // P35·E2/E3 — Alertas y Oportunidades se fusionaron en "Insights" en mobile.
    if (["insights", "alertas", "oportunidades", "prioridades"].includes(destino)) {
      if (user.features.includes("alertas") || user.features.includes("oportunidades")) {
        setView("insights");
        if (hl) resaltarPorId(hl);
      } else toast(t("nav.sin_permiso"), "error");
      return;
    }
    if (MCAT[destino]) {
      if (navIds.includes(destino)) {
        setView(destino);
        if (hl) resaltarPorId(hl);
      } else toast(t("nav.sin_permiso"), "error");
      return;
    }
    toast(t("mnav.solo_desktop"));
  };

  // P35·E2 — Barra inferior FIJA y simétrica: 5 slots en orden fijo con Ángela
  // al centro (botón circular). Se OCULTA el slot cuya feature el rol no tiene
  // (Ángela siempre presente). Insights = fusión Alertas+Oportunidades (E3):
  // basta con tener alguna de las dos. Ya no hay "Más" ni el mapa en la barra
  // (el mapa se abre desde Today, E4/E6).
  const tiene = (f) => user.features.includes(f);
  const izqNav = [
    // El de a pie ve "Mi día" en el primer slot (en lugar del Today del dueño).
    piso ? { id: "mi_dia", lk: "mnav.mi_dia", icon: ClipboardList }
         : (tiene("panel") && { id: "panel", lk: "mnav.hoy", icon: Sun }),
    (tiene("alertas") || tiene("oportunidades")) && { id: "insights", lk: "mnav.insights", icon: Sparkles },
  ].filter(Boolean);
  const derNav = [
    // C2 — LA PARADA, para quien hace calle. Va antes que "Depósito" porque el
    // chofer y el preventista no entran al galpón: su pantalla es la puerta del
    // cliente. Sale de `logistica`, que es justo lo que tienen los dos.
    // Los dos salen de `logistica`; los distingue el OFICIO, que ya está
    // partido en lib/roles.js. El que arma no sale a la calle y el que sale a
    // la calle no arma: darles el mismo destino sería volver al problema que
    // la regex partida vino a arreglar.
    tiene("logistica") && (rolId === "deposito_armado"
      ? { id: "armado", lk: "mnav.armado", icon: ClipboardList }
      : { id: "parada", lk: "mnav.parada", icon: MapPin }),
    tiene("deposito") && { id: "deposito", lk: "mnav.deposito", icon: PackageX },
    tiene("equipo") && { id: "equipo", lk: "mnav.equipo", icon: Users },
  ].filter(Boolean);

  // LA BARRA DEL OFICIO — 3 destinos y el botón de carga al centro.
  //
  // Quien avisa desde el piso (los nueve oficios con lista) tiene una barra
  // distinta: sus destinos son SU día, SU vista de oficio y Ángela, y el centro
  // deja de ser Ángela para ser el botón de carga. El motivo es de uso, no de
  // estética: lo que esta gente hace treinta veces por día es DECIR algo que
  // pasó, y eso estaba a dos toques detrás de una acción de una lista.
  //
  // Nunca cinco slots. La barra del prototipo son tres destinos + carga y ése
  // es el techo: a partir de ahí los íconos se comen entre ellos y ya no se
  // aciertan con el pulgar. Por eso el de piso pierde la solapa «Insights»
  // cuando tiene una vista de oficio — sus señales (fantasma, balanza,
  // negativo) YA le llegan como tareas en «Mi día», así que era la misma
  // información por dos puertas. Sigue alcanzable: Ángela navega ahí, y la URL
  // /insights sigue siendo válida.
  const avisa = avisaDesdeElPiso(user);
  const angelaTab = { id: "angela", lk: "mnav.angela", icon: MessageCircle };
  // El segundo destino: el de su oficio si lo tiene, y si no, Insights — así
  // nadie que sólo tenga alertas se queda con dos destinos.
  const suOficio = derNav[0] || izqNav.find((x) => x.id === "insights") || null;
  const destinos = avisa
    ? [izqNav[0], suOficio, angelaTab].filter(Boolean)
    : null;
  const nSlots = avisa ? destinos.length + 1 : izqNav.length + derNav.length + 1;

  const renderView = () => {
    switch (view) {
      case "mi_dia":
        return <MiDia user={user} onAbrirAngela={abrirAngelaCon} onTarea={abrirTarea}
                      onCerrada={onRecargar} onNavegar={navegarMobile} />;
      case "panel":
        return <Hoy data={data} oportunidades={oportunidades} onTab={setView} onGestionar={gestionarOp} />;
      // P35·E3 — "insights": fusión de Alertas + Oportunidades en filas compactas.
      case "insights":
        return <InsightsMobile onPreguntar={(t) => { setConsultaAngela(t); setView("angela"); }} onNavegar={navegarMobile} />;
      case "equipo":
        return <EquipoMobile />;
      case "cobranzas":
        // P42·1 — misma regla que en desktop: si el que mira es el dueño ve el
        // panorama; si es el preventista, su gestión de la calle.
        return <Cobranzas onPreguntar={(t) => { setConsultaAngela(t); setView("angela"); }} datos={fase?.datos} user={user} />;
      case "deposito":
        return <Deposito data={data} onPreguntar={(t) => { setConsultaAngela(t); setView("angela"); }} onNavegar={navegarMobile} />;
      case "conciliacion":
        return <Conciliacion onPreguntar={(txt) => { setConsultaAngela(txt); setView("angela"); }} onNavegar={navegarMobile} puedeMovimientos={user.features.includes("inventario")} />;
      case "administracion":
        return <Administracion data={data} onPreguntar={(t) => { setConsultaAngela(t); setView("angela"); }} />;
      // P35·E6 — el mapa en mobile es la VISTA SIMPLE read-only (sin React Flow),
      // accesible solo desde "Ver el mapa" de Today. Volver → Today.
      case "armado":
        return <Armado onCerrada={onRecargar} />;
      case "parada":
        // El transporte se filtra por el NOMBRE de la persona: el chofer no
        // tiene por qué saber cómo se escribe su camión en el export del TMS.
        return <Parada transporte={session?.usuario?.nombre || user?.nombre} />;
      case "mapa":
        return <MapaSimpleMobile onPreguntar={(t) => { setConsultaAngela(t); setView("angela"); }} onVolver={() => setView("panel")} />;
      case "aprendizaje":
        return <AprendizajeContinuo onPreguntar={(t) => { setConsultaAngela(t); setView("angela"); }} />;
      case "perfil":
        return <MiPerfil user={user} />;
      case "angela":
        return <AngelaView inputInicial={consultaAngela} user={user} onNavigate={navegarMobile} onDatosCambiaron={onRecargar} />;
      default:
        return null;
    }
  };

  // P35·E2 — tab de la barra fija. El grid da columnas iguales (sin flex-1).
  // Activo = color + peso, sin caja. Target táctil ≥44px (min-h-11).
  const TabBtn = ({ slot }) => {
    const Icon = slot.icon;
    const activo = view === slot.id;
    return (
      // Real <a href> so right-click "open in new tab" works; modified
      // clicks fall through to native browser handling.
      <Link
        to={`/${slot.id}`}
        onClick={(e) => {
          if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
          e.preventDefault();
          setView(slot.id);
        }}
        className="relative flex min-h-11 flex-col items-center justify-center gap-0.5 py-1.5"
      >
        <Icon size={21} className={activo ? "text-violeta" : "text-tinta-suave"} strokeWidth={activo ? 2.4 : 2} />
        <span className={`text-2xs font-semibold ${activo ? "text-violeta" : "text-tinta-suave"}`}>{t(slot.lk)}</span>
      </Link>
    );
  };

  // Declarative redirect (render phase, not an effect) for an invalid or
  // alias URL segment — same reasoning as DesktopApp's `redirectTo`.
  if (!view) return <Navigate to={`/${defaultView}`} replace />;

  return (
    <div className="flex min-h-[100dvh] justify-center bg-papel">
      <Toasts />
      <div className="relative flex min-h-[100dvh] w-full max-w-md flex-col bg-papel">
        <div className="sticky top-0 z-20 flex flex-col border-b border-linea/70 bg-papel/85 px-5 py-3 pt-[max(0.75rem,env(safe-area-inset-top))] backdrop-blur">
        {/* P37·AJUSTE 2 — grid de 3 columnas con LATERALES DE IGUAL PESO
            (1fr auto 1fr): el logo del cliente (columna central) queda CENTRADO
            en el viewport, sobre el mismo eje que el botón de Ángela de la barra
            inferior. No es flex+margin (los iconos desbalancearían el centro).
            El toggle EN/ES no vive acá (el idioma se hereda de la sesión). */}
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2">
          <div className="flex items-center justify-self-start">
            <img src="/logos/polpilot.png" alt="PolPilot" className="h-7 w-auto shrink-0 select-none" draggable="false" />
          </div>
          <div className="flex items-center justify-center">
            <Brand variant="mobile" />
          </div>
          <div className="flex items-center justify-end gap-2">
            {/* La bandeja también en el celular: solicitudes y avisos del dueño llegan acá */}
            <Campanita
              token={session?.token}
              esAdmin={user.es_admin}
              onVerSolicitud={user.es_admin && navIds.includes("equipo") ? () => setView("equipo") : undefined}
            />
            <button onClick={() => setView("perfil")} className="shrink-0">
              <Avatar persona={user} size={32} />
            </button>
            <button onClick={() => authStore.logout({ manual: true })} className="text-tinta-suave hover:text-tinta"><LogOut size={18} /></button>
          </div>
        </div>
        {/* Indicador "Viewing as" (solo demo con View as activo, P9·E) */}
        <div className="mt-2 empty:hidden"><VerComoChip /></div>
        </div>

        <main className="flex-1 overflow-y-auto px-5 pb-24 pt-4">
          <AnimatePresence mode="wait">
            <motion.div key={view} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.22 }} className={view === "angela" ? "h-full" : ""}>
              {/* P29·A2 — nunca una pantalla muda, tampoco en el celular */}
              <ErrorBoundary key={view} seccion={view} onInicio={() => setView(piso ? "mi_dia" : "panel")}>
                {renderView()}
              </ErrorBoundary>
            </motion.div>
          </AnimatePresence>
        </main>

        {/* P35·E2 — Barra inferior FIJA (position:fixed), simétrica, con Ángela
            al centro (botón circular). Respeta safe-area-inset-bottom; el <main>
            lleva pb-24 para que el último elemento no quede tapado. Se fueron
            "Más", el botón flotante de Ángela (redundante con el centro) y el
            mapa de la barra (se abre desde Today). El grid da columnas iguales. */}
        <nav className="fixed inset-x-0 bottom-0 z-30">
          <div
            className="mx-auto grid max-w-md items-stretch border-t border-linea bg-crema/95 px-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] pt-1.5 backdrop-blur"
            style={{ gridTemplateColumns: `repeat(${nSlots}, minmax(0, 1fr))` }}
          >
            {avisa ? (
              <>
                {destinos.slice(0, 2).map((s) => <TabBtn key={s.id} slot={s} />)}
                {/* El botón de carga. Dice el VERBO de su oficio —«Contar»,
                    «Armar», «Registrar»— porque un botón que dice lo que hace
                    se toca sin pensarlo. */}
                <button onClick={() => setHoja(true)} className="relative flex flex-col items-center gap-0.5 py-1.5">
                  <span className="grid h-9 w-9 -translate-y-1 place-items-center rounded-full bg-tinta text-crema sombra-papel">
                    <Plus size={20} />
                  </span>
                  <span className="-mt-1 text-2xs font-semibold text-tinta">{t(cargaLk(user))}</span>
                </button>
                {destinos.slice(2).map((s) => <TabBtn key={s.id} slot={s} />)}
              </>
            ) : (
              <>
                {izqNav.map((s) => <TabBtn key={s.id} slot={s} />)}
                <button onClick={() => setView("angela")} className="relative flex flex-col items-center gap-0.5 py-1.5">
                  <span className={`grid h-9 w-9 -translate-y-1 place-items-center rounded-full ${view === "angela" ? "bg-violeta" : "bg-violeta/90"} text-crema sombra-papel`}>
                    <MessageCircle size={18} />
                  </span>
                  <span className={`-mt-1 text-2xs font-semibold ${view === "angela" ? "text-violeta" : "text-tinta-suave"}`}>Ángela</span>
                </button>
                {derNav.map((s) => <TabBtn key={s.id} slot={s} />)}
              </>
            )}
          </div>
        </nav>

        {/* La hoja de carga: los avisos de SU oficio, el formulario del que
            tocó, y la voz. Viven al nivel de la app y no de una vista porque el
            botón que los abre está en la barra, que no se va nunca. */}
        {hoja && (
          <HojaDeCarga
            conVoz={!!rolDe(user)?.voz}
            onCerrar={() => setHoja(false)}
            onVoz={() => { setHoja(false); setVozAbierta(true); }}
            onAviso={(a) => { setHoja(false); setAvisoAbierto(a); }} />
        )}
        {avisoAbierto && (
          <ReporteForm tipo={avisoAbierto.tipo} aviso={avisoAbierto}
            destinoFijo={avisoAbierto.destino}
            onCerrar={() => setAvisoAbierto(null)} onListo={onRecargar} />
        )}
        {vozAbierta && (
          <VozAngela rol={muestrasDe(user)} onCerrar={() => setVozAbierta(false)}
            onListo={onRecargar}
            onPreguntar={(texto) => { setVozAbierta(false); setConsultaAngela(texto); setView("angela"); }} />
        )}
      </div>
    </div>
  );
}

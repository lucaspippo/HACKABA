import { useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { Sun, Bell, Users, MessageCircle, HandCoins, PackageX, ClipboardList, LogOut, Sparkles, Waypoints, MapPin, Plus, Search } from "lucide-react";
import Brand from "../components/Brand";
import Avatar from "../components/Avatar";
import { resaltarPorId } from "../lib/navGuiada";
import Hoy from "./Hoy";
import MiDia from "./MiDia";
import Parada from "./Parada";
import Armado from "./Armado";
import HojaDeCarga from "./HojaDeCarga";
import Buscar from "./Buscar";
import Ficha from "./Ficha";
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
import { barraDe, buscaEnMobile, muestrasDe, rolDe, tieneVistaHerramienta } from "../lib/roles";
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
  // Buscar y la ficha no son features: son la puerta y el cuarto. El recorte
  // real está en el endpoint — `buscar-global` ya filtra por lo que esta
  // persona puede ver, y la ficha va detrás de `inventario`.
  if (destino === "buscar" || destino === "ficha") return destino;
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
  // El producto abierto. Vive en estado y no en la URL porque el router mobile
  // es /:section: un deep-link a una ficha es deseable y todavía no existe —
  // queda anotado, no simulado.
  const [fichaCodigo, setFichaCodigo] = useState(null);
  // De dónde se vino, para que «volver» de la ficha vuelva a la búsqueda y no
  // al inicio: la Focus Rule también aplica al camino de vuelta.
  const [volverA, setVolverA] = useState("buscar");

  // Ejecuta una acción del oficio venga de donde venga (las acciones rápidas
  // del inicio, la vista de trabajo). Vive acá porque `voz` abre un overlay que
  // es de la app, no de una pantalla.
  const ejecutarAccion = (a) => {
    if (a.kind === "navegar") return navegarMobile(a.a);
    if (a.kind === "angela") return abrirAngelaCon(t(a.pregunta));
    if (a.kind === "voz") return setVozAbierta(true);
    if (a.kind === "reporte") return setAvisoAbierto({ tipo: a.tipo });
  };

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

  // LA BARRA — TRES DESTINOS Y EL BOTÓN DEL CENTRO. Para todos, sin excepción.
  //
  // Antes había dos barras: la del piso (tres + carga) y la de "el resto", que
  // era la vieja y que escaneaba FEATURES para llenar slots. Con eso Aldo
  // terminaba con seis ítems, y uno de ellos era «Mi ruta» — el dueño no
  // reparte. Ramón igual, por el mismo motivo: tener `logistica` no es salir a
  // la calle. **Tener el módulo no es hacer el trabajo**, y la barra es lo que
  // esta persona hace, no lo que puede ver.
  //
  // Ahora hay UNA regla:
  //
  //   slot 1 · su inicio        — «Mi día» para el piso, el panel para el resto
  //   slot 2 · su oficio        — sale del catálogo (`destino`), no de features
  //   centro · lo que más hace  — carga para el piso, la pantalla de carga para
  //                               la oficina, Ángela para el dueño (él no carga:
  //                               decide y pregunta)
  //   slot 3 · Ángela           — salvo para el dueño, que ya la tiene al centro
  //                               y en su lugar lleva Equipo
  //
  // Nunca cinco. Tres destinos + centro es el techo del prototipo: a partir de
  // ahí los íconos se comen entre ellos y ya no se aciertan con el pulgar.
  const VISTA = {
    panel: { lk: "mnav.hoy", icon: Sun },
    mi_dia: { lk: "mnav.mi_dia", icon: ClipboardList },
    insights: { lk: "mnav.insights", icon: Sparkles },
    deposito: { lk: "mnav.deposito", icon: PackageX },
    armado: { lk: "mnav.armado", icon: ClipboardList },
    parada: { lk: "mnav.parada", icon: MapPin },
    cobranzas: { lk: "mnav.cobranzas", icon: HandCoins },
    administracion: { lk: "mnav.oficina", icon: ClipboardList },
    equipo: { lk: "mnav.equipo", icon: Users },
    angela: { lk: "mnav.angela", icon: MessageCircle },
  };
  // Qué barra le toca a esta persona. La decisión vive en lib/roles.js —es de
  // oficio, no de pantalla— y ahí está pinneada contra el equipo entero.
  const { destinos: destinoIds, centro } = barraDe(user);
  const destinos = destinoIds.map((id) => ({ id, ...VISTA[id] })).filter((x) => x.lk);
  const nSlots = destinos.length + 1;

  const renderView = () => {
    switch (view) {
      case "mi_dia":
        return <MiDia user={user} onAbrirAngela={abrirAngelaCon} onTarea={abrirTarea}
                      onCerrada={onRecargar} onNavegar={navegarMobile} />;
      case "panel":
        return <Hoy data={data} oportunidades={oportunidades} onTab={setView}
                    onGestionar={gestionarOp} user={user} onAccion={ejecutarAccion} />;
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
      case "buscar":
        return <Buscar
          onProducto={(codigo) => { setFichaCodigo(codigo); setVolverA("buscar"); setView("ficha"); }}
          onCliente={(nombre) => { setConsultaAngela(t("buscar.consulta_cliente", { cliente: nombre })); setView("angela"); }}
          onPreguntar={(texto) => { setConsultaAngela(texto); setView("angela"); }}
          soloDesktop={() => toast(t("mnav.solo_desktop"))} />;
      case "ficha":
        // Sin código (una URL pegada a mano) se vuelve a la búsqueda en vez de
        // pintar una ficha vacía.
        return fichaCodigo == null
          ? <Navigate to="/buscar" replace />
          : <Ficha codigo={fichaCodigo} onVolver={() => setView(volverA)}
                   onPreguntar={(texto) => { setConsultaAngela(texto); setView("angela"); }} />;
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
            {/* La lupa, sólo para quien la usa. Los seis del piso llegan al
                dato por escaneo o desde su tarea, y una lupa que nunca se toca
                es un ícono que le come lugar a los que sí. */}
            {buscaEnMobile(user) && (
              <button onClick={() => setView("buscar")} aria-label={t("buscar.titulo")}
                className={`shrink-0 ${view === "buscar" ? "text-violeta" : "text-tinta-suave hover:text-tinta"}`}>
                <Search size={18} />
              </button>
            )}
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
            {destinos.slice(0, 2).map((x) => <TabBtn key={x.id} slot={x} />)}
            {/* EL CENTRO. Ángela mantiene su azul —es lo único que lo usa— y el
                botón de carga va en tinta: es la acción de la persona, no de la
                asistente, y confundirlos sería romper la regla de un solo
                significado por color. El rótulo dice el VERBO del oficio
                («Contar», «Armar») porque un botón que dice lo que hace se toca
                sin pensarlo. */}
            {centro.tipo === "angela" ? (
              <button onClick={() => setView("angela")} className="relative flex flex-col items-center gap-0.5 py-1.5">
                <span className={`grid h-9 w-9 -translate-y-1 place-items-center rounded-full ${view === "angela" ? "bg-violeta" : "bg-violeta/90"} text-crema sombra-papel`}>
                  <MessageCircle size={18} />
                </span>
                <span className={`-mt-1 text-2xs font-semibold ${view === "angela" ? "text-violeta" : "text-tinta-suave"}`}>Ángela</span>
              </button>
            ) : (
              <button
                onClick={() => (centro.tipo === "hoja" ? setHoja(true) : navegarMobile(centro.a))}
                className="relative flex flex-col items-center gap-0.5 py-1.5">
                <span className="grid h-9 w-9 -translate-y-1 place-items-center rounded-full bg-tinta text-crema sombra-papel">
                  <Plus size={20} />
                </span>
                <span className="-mt-1 text-2xs font-semibold text-tinta">{t(centro.lk)}</span>
              </button>
            )}
            {destinos.slice(2).map((x) => <TabBtn key={x.id} slot={x} />)}
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
        {/* `aviso` sólo cuando VIENE de la hoja: ahí trae sus campos y su
            destinatario. Una acción del catálogo con `kind: "reporte"` abre el
            formulario del TIPO, como siempre. */}
        {avisoAbierto && (
          <ReporteForm tipo={avisoAbierto.tipo}
            aviso={avisoAbierto.campos ? avisoAbierto : undefined}
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

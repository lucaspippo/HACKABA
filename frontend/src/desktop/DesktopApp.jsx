import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  LayoutDashboard, Boxes, Wallet, Banknote, Bell, Users, Upload, TrendingUp,
  HandCoins, ClipboardList, PackageX, UserCircle, Search, X, PanelRightOpen, LogOut, Sparkles, Globe, Inbox, FileText, ChevronDown, Waypoints, ShieldCheck,
} from "lucide-react";
import { api } from "../lib/api";
import { contarACorregir } from "../lib/alertas";
import AngelaMark from "../components/AngelaMark";
import ChatPanel from "../views/ChatPanel";
import ChatFullscreen from "../views/ChatFullscreen";
import { ChatRuntimeProvider, useChatDock } from "../lib/chatRuntimeProvider";
import Inicio from "./sections/Inicio";
import { InsightNodo } from "./sections/MapaNegocio";
// La sección del mapa tiene dos vistas (árbol de fuentes / cerebro de
// entidades). El switch vive en MapaSeccion; acá se monta una sola cosa.
import MapaSeccion from "./sections/MapaSeccion";
import ErrorBoundary from "../components/ErrorBoundary";
import Inventario from "./sections/Inventario";
import Saneamiento from "./sections/Saneamiento";
import Finanzas from "./sections/Finanzas";
import AlertasNegocio from "../sections/AlertasNegocio";
import OportunidadesNegocio from "../sections/OportunidadesNegocio";
import CargarDatos from "./sections/CargarDatos";
import MiPerfil from "../sections/MiPerfil";
import GestionEquipo from "../sections/GestionEquipo";
import AdminContexto from "../sections/AdminContexto";
import Cobranzas from "../sections/Cobranzas";
import Administracion from "../sections/Administracion";
import Deposito from "../sections/Deposito";
import StagingArea from "./sections/StagingArea";
import Documentos from "./sections/Documentos";
import CuentasCorrientes from "./sections/CuentasCorrientes";
import Caja from "./sections/Caja";
import Evolucion from "./sections/Evolucion";
import Auditoria from "./sections/Auditoria";
import Avatar from "../components/Avatar";
import MiDia from "../mobile/MiDia";
import { PREGUNTA_TAREA } from "../lib/piso";
import { tieneVistaHerramienta } from "../lib/roles";
import { authStore, useSession } from "../lib/auth";
import { cargarSenales, contarAlertas } from "../lib/centroAlertas";
import { useDocNuevo } from "../lib/docStore";
import { resaltarPorId } from "../lib/navGuiada";
import Campanita from "../components/Campanita";
import LangSwitch from "../components/LangSwitch";
import { VerComoChip } from "../components/VerComo";
import { useT, tRol } from "../lib/i18n";
import { toast } from "../lib/toastStore";
import Toasts from "../components/Toasts";

// Catálogo de secciones desktop. Se muestran según las features del usuario.
// Los labels viven en el diccionario i18n (lk = label key); las KEYS del catálogo
// son identificadores y no se traducen jamás.
const CATALOGO = {
  panel: { lk: "nav.panel", icon: LayoutDashboard },
  mapa: { lk: "nav.mapa", icon: Waypoints },
  inventario: { lk: "nav.inventario", icon: Boxes },
  saneamiento: { lk: "nav.saneamiento", icon: ClipboardList },
  finanzas: { lk: "nav.finanzas", icon: Wallet },
  cuentas: { lk: "nav.cuentas", icon: HandCoins },
  // Billete ≠ billetera: "Caja diaria" y "Caja y finanzas" se distinguen de un
  // vistazo en el sidebar (P9·D).
  caja: { lk: "nav.caja", icon: Banknote },
  evolucion: { lk: "nav.evolucion", icon: TrendingUp },
  alertas: { lk: "nav.alertas", icon: Bell },
  oportunidades: { lk: "nav.oportunidades", icon: Sparkles },
  equipo: { lk: "nav.equipo", icon: Users },
  cargar: { lk: "nav.cargar", icon: Upload },
  documentos: { lk: "nav.documentos", icon: FileText },
  cobranzas: { lk: "nav.cobranzas", icon: HandCoins },
  administracion: { lk: "nav.administracion", icon: ClipboardList },
  deposito: { lk: "nav.deposito", icon: PackageX },
  // Bloque F — el registro de auditoría: scope organización, sólo el dueño.
  auditoria: { lk: "nav.auditoria", icon: ShieldCheck },
  admin_contexto: { lk: "nav.admin_contexto", icon: Globe },
  perfil: { lk: "nav.perfil", icon: UserCircle },
};

// El sidebar agrupado en bloques con sentido para un dueño (no 16 ítems planos).
// Presentación pura: mismos permisos, mismo CATALOGO; sólo cambia el orden visual.
// Cada bloque es un concepto, no un cajón: "tu día" (landing), "lo que Ángela
// detectó" (requiere una decisión), "la plata", "la operación", "sistema".
// "Perfil" NO vive acá: ya se llega por el chip de cuenta en el header
// (evita el mismo destino con dos entradas). "Equipo" se sumó a Operación
// (dejar de sostener un grupo de un solo ítem).
const BLOQUES_NAV = [
  // Landing: dónde aterriza cualquiera al abrir PolPilot.
  { lk: null, ids: ["panel", "mapa"] },
  // P17·E2a — jerarquía AI-first: lo que Ángela detectó y necesita una
  // decisión, agrupado y nombrado como tal (antes mezclado sin label con el landing).
  { lk: "nav.grupo_senales", ids: ["alertas", "oportunidades", "evolucion"] },
  { lk: "nav.grupo_plata", ids: ["finanzas", "caja", "cuentas", "cobranzas"] },
  // 5 ítems supera el techo de ≤4 por grupo (carga cognitiva) — se resuelve
  // con un subdivisor visual, no con una ruta/grupo nuevo: "administracion" y
  // "equipo" son la mitad de personas/oficina del mismo concepto operativo.
  { lk: "nav.grupo_operacion", ids: ["inventario", "saneamiento", "deposito", "administracion", "equipo"], subAt: { administracion: "nav.grupo_operacion_equipo" } },
  { lk: "nav.grupo_sistema", ids: ["cargar", "documentos", "auditoria", "admin_contexto"] },
];

export default function DesktopApp(props) {
  return (
    <ChatRuntimeProvider>
      <DesktopAppInner {...props} />
    </ChatRuntimeProvider>
  );
}

function DesktopAppInner({ data, oportunidades, fase, user, onRecargar }) {
  const t = useT();
  const session = useSession();
  const { fullscreen, setFullscreen } = useChatDock();
  // P39·2 — un empleado no aterriza en el foco de la fase (eso es del dueño):
  // aterriza en SU pantalla de trabajo.
  const vistaHerramienta = tieneVistaHerramienta(user);
  const secciones = user.features.filter((f) => CATALOGO[f]);
  // La vista de trabajo del de a pie ("Mi día") es SUYA, no un módulo de la
  // matriz: en el celular aparece siempre (MobileApp la pone en el primer slot)
  // y en la compu se caía si su rol no tenía la feature "panel" — alguien de
  // depósito abría PolPilot en un escritorio y no encontraba su propio día.
  // Mismo componente y mismos permisos: MiDia sólo muestra lo que sus features
  // permiten. El dueño no se entera: él sí tiene "panel" y ve su Inicio.
  if (vistaHerramienta && !secciones.includes("panel")) secciones.unshift("panel");
  const bloques = BLOQUES_NAV
    .map((b) => ({ ...b, ids: b.ids.filter((id) => secciones.includes(id)) }))
    .filter((b) => b.ids.length > 0);
  // El sistema define el foco de la fase: el dueño aterriza donde importa hoy.
  const inicial = vistaHerramienta
    ? (secciones.includes("panel") ? "panel" : (secciones[0] || "perfil"))
    : (fase?.foco && user.features.includes(fase.foco) ? fase.foco : (secciones[0] || "perfil"));
  const [section, setSection] = useState(inicial);
  const [highlight, setHighlight] = useState(null);
  // El panel de Ángela vive abierto por defecto cuando la pantalla lo banca
  // (la referencia de diseño: Ángela siempre presente a la derecha).
  const [angelaOpen, setAngelaOpen] = useState(() => window.innerWidth >= 1280);
  const [consultaAngela, setConsultaAngela] = useState(null);
  const [busqueda, setBusqueda] = useState("");
  const [faseVisible, setFaseVisible] = useState(true);
  const [stagingCount, setStagingCount] = useState(0);
  // P28·C2 — el insight del nodo clickeado en el mapa: vive ARRIBA del chat,
  // en el panel de Ángela (la conversación entre el mapa y Ángela).
  const [mapaInsight, setMapaInsight] = useState(null);
  useEffect(() => {
    if (section !== "mapa") setMapaInsight(null);
  }, [section]);

  useEffect(() => {
    api.stagingListar().then((d) => setStagingCount(d.batches.length)).catch(() => {});
  }, []);

  // Badges del sidebar (P17·E2a): SOLO donde el número es trabajo despachable.
  // Alerts usa las MISMAS condiciones que la pantalla (lib/centroAlertas).
  const [nAlertas, setNAlertas] = useState(0);
  useEffect(() => {
    cargarSenales().then((s) => setNAlertas(contarAlertas(s))).catch(() => {});
  }, []);
  // P30·A3 — el badge cuenta lo MISMO que muestra la sección: las
  // oportunidades CAPTURABLES (las de riesgo no son oportunidad). Antes usaba
  // el shape legacy concretas/pendientes → decía 4 con 8 en pantalla.
  const nOportunidades = (oportunidades?.cards || []).filter((c) => c.naturaleza !== "riesgo").length;
  const a = data?.alertas;
  // P38·A — una sola definición de "Datos a corregir" (lib/alertas): el badge
  // cuenta EXACTAMENTE lo que muestran la tabla de stock y la sección.
  const nCorregir = contarACorregir(data);
  // P24·G2 — el badge de "Datos a corregir" suma los dos flujos: errores en el
  // sistema (nCorregir) + cargas esperando el OK (stagingCount).
  const BADGES = { alertas: nAlertas, oportunidades: nOportunidades,
                   saneamiento: nCorregir + stagingCount };
  const docNuevo = useDocNuevo();

  // P37 — Identidad del tenant ENTERA del backend (empresa + logo por tenant).
  // El frontend NO hardcodea ningún cliente: hasta que health resuelve, `marca`
  // es null (skeleton) → nunca se pinta el nombre/logo del piloto por un default.
  const [marca, setMarca] = useState(null);
  useEffect(() => {
    api.health()
      .then((h) => setMarca({ empresa: h.meta?.empresa || null, logo: h.meta?.logo || null }))
      .catch(() => setMarca({ empresa: null, logo: null }));
  }, []);
  const empresa = marca?.empresa || null;
  const clienteLogo = marca?.logo || null;
  const marcaResuelta = !!marca;

  // Ángela usa nombres "de dueño" para las secciones; acá los mapeamos a las keys reales
  // del CATALOGO para que "te llevo al inicio" no sea un callejón sin salida (inicio≠panel).
  const ALIAS_SECCION = {
    inicio: "panel", home: "panel", principal: "panel",
    "datos a corregir": "saneamiento", corregir: "saneamiento",
    finanzas: "finanzas", "caja diaria": "caja", "cuentas corrientes": "cuentas",
    logistica: "deposito", reparto: "deposito", envios: "deposito",
    // "Gestión de equipo" se unificó dentro de "Equipo" (P6): alias para
    // Ángela, la campanita y cualquier link viejo.
    gestion_equipo: "equipo", "gestion de equipo": "equipo",
  };
  // 'pendientes' no es una feature de rol: es transversal (aparece si hay datos en revisión).
  // El highlight se limpia y se re-setea con un tick de por medio: navegar dos
  // veces al MISMO ancla (mismo string de estado) también tiene que titilar (P15·E6).
  const setHighlightRobusto = (hl) => {
    setHighlight(null);
    if (hl) setTimeout(() => setHighlight(hl), 30);
  };
  const navegar = (sec, hl) => {
    let destino = ALIAS_SECCION[sec] || sec;
    // P24·G2 — "Pending data" se FUSIONÓ dentro de "Datos a corregir": las
    // rutas viejas (navegar_a, links, tests) redirigen al lugar nuevo.
    if (destino === "pendientes") {
      destino = "saneamiento";
      hl = hl || "revision";
    }
    // "panel" para el de a pie es su vista de trabajo, no el Inicio del dueño:
    // se navega igual aunque no tenga esa feature (ver `secciones`, arriba).
    if (destino && (user.features.includes(destino)
                    || (destino === "panel" && vistaHerramienta))) {
      setSection(destino);
      setHighlightRobusto(hl);
      return;
    }
    // Sección real pero sin permiso: feedback claro en vez de botón muerto (P9·C3, M7).
    if (destino && CATALOGO[destino]) toast(t("nav.sin_permiso"), "error");
    setHighlightRobusto(hl);
  };
  const irAPendientes = () => {
    api.stagingListar().then((d) => setStagingCount(d.batches.length)).catch(() => {});
    navegar("saneamiento", "revision");
  };
  const preguntar = (texto) => {
    setConsultaAngela(texto);
    setAngelaOpen(true);
  };
  // B1: abrir el panel de Ángela SIN auto-enviar ninguna pregunta — para que el
  // mensaje proactivo (angelaBus) se vea apenas se confirma una carga por foto.
  const abrirAngela = () => setAngelaOpen(true);

  // Highlight a nivel elemento: scrollea y deja el elemento TITILANDO hasta
  // que el usuario lo toca (navegación guiada de Ángela). Ver lib/navGuiada.
  useEffect(() => {
    if (!highlight) return;
    return resaltarPorId(highlight);
  }, [highlight, section]);

  return (
    <div className="flex h-[100dvh] overflow-hidden bg-papel text-tinta">
      <Toasts />
      {/* SIDEBAR */}
      <aside className="flex w-64 shrink-0 flex-col border-r border-linea bg-crema/70">
        <div className="border-b border-linea px-5 py-5">
          <img src="/logos/polpilot.png" alt="PolPilot" className="h-7 w-auto" draggable="false" />
          <div className="mt-3 flex items-center gap-2">
            <span className="text-[0.88rem] font-semibold uppercase tracking-[0.14em] text-tinta-suave">{t("nav.cliente")}</span>
            {!marcaResuelta ? (
              <span className="h-7 w-24 animate-pulse rounded bg-papel-hondo" />
            ) : clienteLogo ? (
              <img src={clienteLogo} alt={empresa || ""} className="h-8 w-auto" draggable="false" />
            ) : (
              <span className="font-display text-[0.95rem] font-bold leading-tight text-hielo">{empresa}</span>
            )}
          </div>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {bloques.map((b, bi) => (
            <div key={b.lk || "inicio"} className={bi > 0 ? "pt-2" : ""}>
              {b.lk && (
                <p className="plata px-3 pb-1 text-[0.88rem] font-semibold uppercase tracking-[0.16em] text-tinta-suave">
                  {t(b.lk)}
                </p>
              )}
              {b.ids.map((id) => {
                const c = CATALOGO[id];
                const Icon = c.icon;
                const activo = section === id;
                const subLk = b.subAt?.[id];
                return (
                  <div key={id}>
                    {subLk && (
                      <p className="px-3 pb-1 pt-2 text-[0.88rem] font-semibold uppercase tracking-[0.14em] text-tinta-suave/60">
                        {t(subLk)}
                      </p>
                    )}
                    <button
                      onClick={() => navegar(id, null)}
                      className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-[0.9rem] font-medium transition-colors ${
                        activo ? "bg-violeta-suave font-semibold text-violeta-hondo" : "text-tinta-suave hover:bg-papel-hondo/60 hover:text-tinta"
                      }`}
                    >
                      <Icon size={18} className={activo ? "text-violeta" : ""} />
                      {/* Para el de a pie ese slot no es "Inicio": es "Mi día" —
                          el mismo nombre que ya tiene en el celular. */}
                      <span className="flex-1">
                        {t(id === "panel" && vistaHerramienta ? "mnav.mi_dia" : c.lk)}
                      </span>
                      {BADGES[id] > 0 && (
                        <span className="grid h-5 min-w-5 place-items-center rounded-full bg-oro px-1 text-[0.88rem] font-bold text-crema">{BADGES[id]}</span>
                      )}
                      {id === "documentos" && docNuevo && (
                        <span className="h-2 w-2 rounded-full bg-violeta" />
                      )}
                    </button>
                  </div>
                );
              })}
            </div>
          ))}
          {/* P24·G2 — "Pending data" ya no es sección aparte: vive DENTRO de
              "Datos a corregir" (badge sumado en BADGES.saneamiento). */}
        </nav>

        <div className="space-y-1.5 border-t border-linea p-3">
          {/* La entrada genérica a Ángela vive UNA sola vez, en el header
              (botón "Ángela" arriba a la derecha) — esta tarjeta ya no la
              duplica en estado idle. Sólo aparece cuando hay algo real y
              distinto para mostrar: una decisión esperando (P15·E6). */}
          {stagingCount > 0 && (
            <button
              onClick={() => navegar("panel", "decisiones")}
              className="flex w-full items-center gap-3 rounded-xl border border-linea bg-crema px-3 py-2 text-left sombra-papel transition-colors hover:border-violeta/40"
            >
              <AngelaMark size={30} estado="esperando" />
              <div className="min-w-0 flex-1">
                <p className="text-[0.88rem] font-semibold">Ángela</p>
                <p className="flex items-center gap-1.5 truncate text-[0.88rem] text-tinta-suave">
                  <span className="inline-block h-1.5 w-1.5 rounded-full bg-oro" />
                  {t("decision.espera_ok")}
                </p>
              </div>
            </button>
          )}
          <div className="flex items-center gap-3 rounded-xl px-2 py-1.5">
            <Avatar persona={user} size={36} />
            <div className="min-w-0 flex-1">
              <p className="truncate text-[0.88rem] font-semibold">{user.nombre}</p>
              <p className="truncate text-[0.8rem] text-tinta-suave">{tRol(user.rol)}</p>
            </div>
            <button onClick={() => authStore.logout({ manual: true })} title={t("nav.salir")} className="text-tinta-suave hover:text-tinta">
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>

      {/* COLUMNA PRINCIPAL */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-4 border-b border-linea bg-papel/80 px-6 py-3 backdrop-blur">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (busqueda.trim()) {
                preguntar(busqueda.trim());
                setBusqueda("");
              }
            }}
            className="flex flex-1 items-center gap-3 rounded-full border border-linea bg-crema px-4 py-2 sombra-papel focus-within:border-violeta/40"
          >
            <Search size={17} className="shrink-0 text-tinta-suave" />
            <input
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              placeholder={t("nav.buscador")}
              className="flex-1 bg-transparent text-[0.9rem] outline-none placeholder:text-tinta-suave/80"
            />
          </form>
          <VerComoChip />
          <LangSwitch />
          <Campanita
            token={session?.token}
            esAdmin={user.es_admin}
            onVerSolicitud={() => navegar("equipo", "solicitudes")}
          />
          <button onClick={() => setAngelaOpen((v) => !v)} className="flex items-center gap-2 rounded-full bg-violeta px-3.5 py-2 text-[0.88rem] font-semibold text-crema transition-transform active:scale-95">
            <AngelaMark size={22} estado={stagingCount > 0 ? "esperando" : "idle"} /> Ángela <PanelRightOpen size={15} />
          </button>
          {/* Empresa + rol, arriba a la derecha (patrón de la referencia). Lleva al perfil,
              donde vive el selector "Ver como". */}
          <button
            onClick={() => navegar("perfil", null)}
            className="flex items-center gap-2.5 rounded-full border border-linea bg-crema py-1.5 pl-1.5 pr-3 sombra-papel transition-colors hover:border-tinta/25"
          >
            <Avatar persona={user} size={28} />
            <span className="hidden min-w-0 text-left xl:block">
              <span className="block max-w-40 truncate text-[0.8rem] font-semibold leading-tight">{empresa || ""}</span>
              <span className="block text-[0.88rem] leading-tight text-tinta-suave">{tRol(user.rol)}</span>
            </span>
            <ChevronDown size={14} className="text-tinta-suave" />
          </button>
        </header>

        <div className="flex min-h-0 flex-1">
          {fullscreen ? (
            <div className="min-w-0 flex-1 overflow-y-auto px-7 py-6">
              <ChatFullscreen
                onNavigate={navegar}
                user={user}
                onDatosCambiaron={onRecargar}
                placeholderChips={chipsPorRol(user)}
                onCollapse={() => setFullscreen(false)}
              />
            </div>
          ) : (
          <main className="min-w-0 flex-1 overflow-y-auto px-7 py-6">
            {/* Banner de fase: SOLO en el Inicio — en el resto de las secciones es
                ruido que come pantalla y su CTA no aplica (auditoría UX P5).
                P13: y solo si la fase PIDE algo (foco ≠ panel) — con todo al
                día, el saludo del Home no lleva un banner encima. */}
            {fase && fase.foco && fase.foco !== "panel" && faseVisible && user.es_admin && !user.interno && section === "panel" && (
              <div className="mb-5 flex items-start gap-3 rounded-[var(--radius-card)] border border-oro/30 bg-oro/[0.07] p-4">
                <AngelaMark size={32} />
                <div className="min-w-0 flex-1">
                  <p className="text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-oro-tinta">
                    {t("nav.fase")}: {fase.titulo}
                  </p>
                  <p className="mt-0.5 text-[0.92rem] leading-snug text-tinta">{fase.mensaje}</p>
                  {fase.foco && user.features.includes(fase.foco) && CATALOGO[fase.foco] && (
                    <button
                      onClick={() => navegar(fase.foco, null)}
                      className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-violeta px-3.5 py-1.5 text-[0.88rem] font-semibold text-crema"
                    >
                      {t("nav.ir_a")} {t(CATALOGO[fase.foco].lk)}
                    </button>
                  )}
                </div>
                <button onClick={() => setFaseVisible(false)} className="text-tinta-suave hover:text-tinta">
                  <X size={16} />
                </button>
              </div>
            )}
            <AnimatePresence mode="wait">
              <motion.div key={section} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
                {/* P29·A2 — nunca una pantalla muda: si una sección revienta,
                    estado de error honesto y navegable. key=section resetea. */}
                <ErrorBoundary key={section} seccion={section} onInicio={() => navegar("panel", null)}>
                {/* P39·2 — el "Inicio" del DUEÑO es su panel de negocio; el de un
                    empleado es SU pantalla de trabajo (tareas, acciones de su
                    oficio, chips de Ángela). Mismo slot, dos herramientas. */}
                {/* El de a pie tenía su vista encajonada en `max-w-2xl`: en una
                    pantalla de escritorio se veía como un celular estirado, con
                    dos tercios de ancho vacíos. Ahora usa el mismo contenedor que
                    el Inicio del dueño (1280px) y MiDia reparte en dos columnas
                    cuando el espacio da (container query, no viewport). */}
                {section === "panel" && (vistaHerramienta
                  ? <div className="mx-auto max-w-[1280px]"><MiDia user={user} onAbrirAngela={preguntar}
                      onTarea={(x) => { const k = PREGUNTA_TAREA[x.tipo]; if (k) preguntar(t(k)); }}
                      onCerrada={onRecargar} onNavegar={navegar} /></div>
                  : <Inicio data={data} oportunidades={oportunidades} onNavegar={navegar} onPreguntar={preguntar} />)}
                {section === "mapa" && <MapaSeccion onNavegar={navegar} onPreguntar={preguntar}
                  onInsight={(i) => { setMapaInsight(i); if (i) setAngelaOpen(true); }} />}
                {section === "inventario" && <Inventario data={data} highlight={highlight} onPreguntar={preguntar} onNavegar={navegar} />}
                {section === "saneamiento" && <Saneamiento user={user} highlight={highlight} onNavegar={navegar} onPreguntar={preguntar} onRecargar={onRecargar} onStagingCambio={setStagingCount} />}
                {section === "finanzas" && <Finanzas data={data} onPreguntar={preguntar} datos={fase?.datos} onNavegar={navegar} />}
                {section === "alertas" && <AlertasNegocio onPreguntar={preguntar} onNavegar={navegar} datos={fase?.datos} />}
                {section === "oportunidades" && <OportunidadesNegocio onPreguntar={preguntar} onNavegar={navegar} />}
                {section === "equipo" && <GestionEquipo data={data} user={user} highlight={highlight} />}
                {section === "cargar" && <CargarDatos user={user} onArchivoCargado={irAPendientes} onPreguntar={preguntar} onAbrirAngela={abrirAngela} />}
                {section === "documentos" && <Documentos onPreguntar={preguntar} />}
                {section === "cuentas" && <CuentasCorrientes onPreguntar={preguntar} />}
                {section === "caja" && <Caja />}
                {section === "cobranzas" && <Cobranzas onPreguntar={preguntar} datos={fase?.datos} user={user} />}
                {section === "administracion" && <Administracion data={data} onPreguntar={preguntar} />}
                {section === "deposito" && <Deposito data={data} onPreguntar={preguntar} />}
                {section === "evolucion" && <Evolucion data={data} onNavegar={navegar} onPreguntar={preguntar} />}
                {section === "auditoria" && <Auditoria />}
                {section === "admin_contexto" && <AdminContexto />}
                {section === "perfil" && <MiPerfil user={user} />}
                </ErrorBoundary>
              </motion.div>
            </AnimatePresence>
          </main>
          )}

          <AnimatePresence>
            {angelaOpen && !fullscreen && (
              <motion.aside
                initial={{ x: 380, opacity: 0.4 }}
                animate={{ x: 0, opacity: 1 }}
                exit={{ x: 380, opacity: 0.4 }}
                transition={{ type: "spring", stiffness: 320, damping: 34 }}
                className="flex w-[23.75rem] shrink-0 flex-col border-l border-linea bg-papel"
              >
                <div className="flex justify-end border-b border-linea px-4 py-1.5">
                  <button onClick={() => setAngelaOpen(false)} className="text-tinta-suave hover:text-tinta"><X size={18} /></button>
                </div>
                <div className="flex min-h-0 flex-1 flex-col overflow-hidden px-4 py-3">
                  {/* The map insight panel lives in the aside, OUTSIDE the
                      section's error boundary: an error there used to take
                      down the whole view (blank screen). Its own safety net,
                      keyed by insight so picking another node resets it and
                      shows the new panel. */}
                  {section === "mapa" && mapaInsight && (
                    <ErrorBoundary key={"insight:" + (mapaInsight.esMemory ? "mem"
                      : mapaInsight.esHallazgo ? "hall:" + (mapaInsight.h?.id || "")
                      : "nodo:" + (mapaInsight.id || ""))}>
                      <InsightNodo insight={mapaInsight} onNavegar={navegar}
                        onPreguntar={preguntar} onCerrar={() => setMapaInsight(null)} />
                    </ErrorBoundary>
                  )}
                  <div className="min-h-0 flex-1 overflow-hidden">
                    <ChatPanel
                      variant="dock"
                      onExpand={() => setFullscreen(true)}
                      onNavigate={navegar}
                      inputInicial={consultaAngela}
                      user={user}
                      onDatosCambiaron={onRecargar}
                      placeholderChips={chipsPorRol(user)}
                    />
                  </div>
                </div>
              </motion.aside>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

// Los chips muestran el label traducido (lk) y mandan el payload en ES
// (el motor de Ángela entiende castellano) — mismo patrón que CHIPS default.
function chipsPorRol(user) {
  if (user.features.includes("inventario"))
    return [
      { lk: "angela.chip_llevame_fantasma", enviar: "Llevame a los productos fantasma" },
      { lk: "angela.chip_manteca", enviar: "¿Cuánta plata tengo en manteca?" },
      { lk: "angela.chip_balanzas", enviar: "Mostrame las balanzas" },
      { lk: "angela.chip_riesgo", enviar: "¿Dónde está el mayor riesgo de mi inventario?" },
    ];
  if (user.features.includes("deposito"))
    return [
      { lk: "angela.chip_negativo", enviar: "Mostrame el stock negativo" },
      { lk: "angela.chip_fantasma", enviar: "¿Cuáles son mis productos fantasma?" },
    ];
  if (user.features.includes("cobranzas"))
    return [
      { lk: "angela.chip_cobrar", enviar: "¿A quién tengo que cobrar?" },
      { lk: "angela.chip_financiar", enviar: "¿Cuánto puedo financiarle a un cliente?" },
    ];
  return [
    { lk: "angela.chip_hoy", enviar: "¿Qué tengo que hacer hoy?" },
    { lk: "angela.chip_recordatorio", enviar: "Anotá un recordatorio" },
  ];
}

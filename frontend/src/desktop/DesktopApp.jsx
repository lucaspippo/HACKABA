import { useEffect, useRef, useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  LayoutDashboard, Boxes, Wallet, Banknote, Users, Upload, TrendingUp,
  HandCoins, ClipboardList, PackageX, UserCircle, Search, X, PanelRightOpen,
  Globe, FileText, Waypoints, ShieldCheck, Radar, Warehouse, Settings,
  PanelLeftClose, PanelLeftOpen, ChevronRight, MapPin, PackageSearch, Truck,
  ShoppingCart, Plug, Layers, Inbox, PackageCheck,
} from "lucide-react";
import { api } from "../lib/api";
import { contarACorregir } from "../lib/alertas";
import AngelaMark from "../components/AngelaMark";
import ChatPanel from "../views/ChatPanel";
import ChatFullscreen from "../views/ChatFullscreen";
import CommandPalette from "../components/CommandPalette";
import AccountMenu from "../components/AccountMenu";
import { ChatRuntimeProvider, useChatDock } from "../lib/chatRuntimeProvider";
import { useVista, vistaStore } from "../lib/vistaStore";
import Inicio from "./sections/Inicio";
import { InsightNodo } from "./sections/MapaNegocio";
// La sección del mapa tiene dos vistas (árbol de fuentes / cerebro de
// entidades). El switch vive en MapaSeccion; acá se monta una sola cosa.
import MapaSeccion from "./sections/MapaSeccion";
import ErrorBoundary from "../components/ErrorBoundary";
import Inventario from "./sections/Inventario";
import Saneamiento from "./sections/Saneamiento";
import Finanzas from "./sections/Finanzas";
import Prioridades from "../sections/Prioridades";
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
import Conectores from "./sections/Conectores";
import Ubicaciones from "./sections/Ubicaciones";
import Lotes from "./sections/Lotes";
import Proveedores from "./sections/Proveedores";
import OrdenesCompra from "./sections/OrdenesCompra";
import Imported from "./sections/Imported";
import MiDia from "../mobile/MiDia";
import { PREGUNTA_TAREA } from "../lib/piso";
import { tieneVistaHerramienta } from "../lib/roles";
import { authStore, useSession } from "../lib/auth";
import { useDocNuevo } from "../lib/docStore";
import { resaltarPorId } from "../lib/navGuiada";
import Campanita from "../components/Campanita";
import { VerComoChip } from "../components/VerComo";
import { useT } from "../lib/i18n";
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
  prioridades: { lk: "nav.prioridades", icon: Radar },
  equipo: { lk: "nav.equipo", icon: Users },
  cargar: { lk: "nav.cargar", icon: Upload },
  documentos: { lk: "nav.documentos", icon: FileText },
  cobranzas: { lk: "nav.cobranzas", icon: HandCoins },
  administracion: { lk: "nav.administracion", icon: ClipboardList },
  deposito: { lk: "nav.deposito", icon: PackageX },
  // Bloque F — el registro de auditoría: scope organización, sólo el dueño.
  auditoria: { lk: "nav.auditoria", icon: ShieldCheck },
  // Plan 11 — sistemas externos (CSV/BCRA/Odoo/MCP): mismo scope que auditoría.
  conectores: { lk: "nav.conectores", icon: Plug },
  staging: { lk: "nav.pendientes", icon: PackageCheck },
  admin_contexto: { lk: "nav.admin_contexto", icon: Globe },
  perfil: { lk: "nav.perfil", icon: UserCircle },
  ubicaciones: { lk: "nav.ubicaciones", icon: MapPin },
  lotes: { lk: "nav.lotes", icon: PackageSearch },
  imported: { lk: "nav.imported", icon: Layers },
  proveedores: { lk: "nav.proveedores", icon: Truck },
  ordenes_compra: { lk: "nav.ordenes_compra", icon: ShoppingCart },
};

// Grupos angostos por área reconocible (tesorería, cobranzas, inventario,
// equipo, sistema) en vez de baldes mixtos ("La plata" mezclaba tesorería con
// cobranzas; "La operación", stock con equipo/oficina). Prioridades is the
// ranked inbox (alerts + opportunities), a leaf next to Evolución — not an ERP module.
const GRUPOS_NAV = [
  { id: "panel", leaf: true },
  { id: "mapa", leaf: true },
  { id: "evolucion", leaf: true },
  { id: "prioridades", leaf: true },
  { id: "tesoreria", lk: "nav.grupo_tesoreria", icon: Wallet, ids: ["finanzas", "caja"] },
  { id: "cobrar", lk: "nav.grupo_cobrar", icon: HandCoins, ids: ["cuentas", "cobranzas"] },
  { id: "inventario", lk: "nav.grupo_inventario", icon: Warehouse, ids: ["inventario", "deposito", "ubicaciones", "lotes"] },
  { id: "ingesta", lk: "nav.grupo_ingesta", icon: Inbox, ids: ["cargar", "conectores", "staging", "imported", "saneamiento"] },
  { id: "compras", lk: "nav.grupo_compras", icon: ShoppingCart, ids: ["proveedores", "ordenes_compra"] },
  { id: "equipo", lk: "nav.grupo_equipo", icon: Users, ids: ["equipo", "administracion"] },
  { id: "sistema", lk: "nav.grupo_sistema", icon: Settings, ids: ["documentos", "auditoria", "admin_contexto"] },
];

// A qué grupo pertenece una sección hoja (null si es ella misma un grupo o no existe).
function grupoDe(seccionId) {
  for (const g of GRUPOS_NAV) if (!g.leaf && g.ids.includes(seccionId)) return g.id;
  return null;
}

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
  const { open: angelaOpen, setOpen: setAngelaOpen, fullscreen, setFullscreen } = useChatDock();
  const vista = useVista();
  const sidebarColapsado = vista.sidebarColapsado;
  // P39·2 — un empleado no aterriza en el foco de la fase (eso es del dueño):
  // aterriza en SU pantalla de trabajo.
  const vistaHerramienta = tieneVistaHerramienta(user);
  // Locations/lots/vendors/POs ride on inventario. Staging is the review
  // gate of saneamiento. Imported data is the browse step of the ingest
  // pipeline (cargar / conectores / saneamiento), not a warehouse screen.
  // Prioridades is the ranked inbox for anyone with alertas or oportunidades.
  const extraNav = [];
  if (user.features.includes("inventario")) {
    extraNav.push("ubicaciones", "lotes", "proveedores", "ordenes_compra");
  }
  if (user.features.includes("saneamiento")) extraNav.push("staging");
  if (user.features.includes("inventario") && (
      user.features.includes("cargar") || user.features.includes("conectores")
      || user.features.includes("saneamiento"))) {
    extraNav.push("imported");
  }
  if (user.features.includes("alertas") || user.features.includes("oportunidades")) {
    extraNav.push("prioridades");
  }
  const featuresEfectivas = extraNav.length
    ? [...user.features, ...extraNav]
    : user.features;
  const ALIAS_SECCION = {
    inicio: "panel", home: "panel", principal: "panel",
    "datos a corregir": "saneamiento", corregir: "saneamiento",
    finanzas: "finanzas", "caja diaria": "caja", "cuentas corrientes": "cuentas",
    logistica: "deposito", reparto: "deposito", envios: "deposito",
    gestion_equipo: "equipo", "gestion de equipo": "equipo",
    alertas: "prioridades", oportunidades: "prioridades", insights: "prioridades",
    pendientes: "staging",
  };
  const secciones = featuresEfectivas.filter((f) => CATALOGO[f]);
  // La vista de trabajo del de a pie ("Mi día") es SUYA, no un módulo de la
  // matriz: en el celular aparece siempre (MobileApp la pone en el primer slot)
  // y en la compu se caía si su rol no tenía la feature "panel" — alguien de
  // depósito abría PolPilot en un escritorio y no encontraba su propio día.
  // Mismo componente y mismos permisos: MiDia sólo muestra lo que sus features
  // permiten. El dueño no se entera: él sí tiene "panel" y ve su Inicio.
  if (vistaHerramienta && !secciones.includes("panel")) secciones.unshift("panel");
  const grupos = GRUPOS_NAV
    .map((g) => (g.leaf ? g : { ...g, ids: g.ids.filter((id) => secciones.includes(id)) }))
    .filter((g) => g.leaf ? secciones.includes(g.id) : g.ids.length > 0);
  // El sistema define el foco de la fase: el dueño aterriza donde importa hoy.
  const focoCanon = fase?.foco ? (ALIAS_SECCION[fase.foco] || fase.foco) : null;
  const inicial = vistaHerramienta
    ? (secciones.includes("panel") ? "panel" : (secciones[0] || "perfil"))
    : (focoCanon && secciones.includes(focoCanon) ? focoCanon
      : (secciones[0] || "perfil"));
  // The active section lives in the URL (/:section) instead of a useState.
  const navigate = useNavigate();
  const { section: sectionParam } = useParams();
  const resolvedSection = ALIAS_SECCION[sectionParam] || sectionParam;
  const sectionIsValid = !!resolvedSection && !!CATALOGO[resolvedSection]
    && (featuresEfectivas.includes(resolvedSection) || (resolvedSection === "panel" && vistaHerramienta));
  // Rendered declaratively via <Navigate> below rather than an imperative
  // useEffect + navigate(), which raced under StrictMode's double-effect.
  const redirectTo = !sectionIsValid ? inicial : (resolvedSection !== sectionParam ? resolvedSection : null);
  const section = sectionIsValid ? resolvedSection : inicial;
  // Acordeón exclusivo: un solo grupo abierto a la vez, sincronizado con la
  // sección activa (si Ángela o el command palette navegan a otro grupo, ese
  // pasa a ser el abierto).
  const [grupoAbierto, setGrupoAbierto] = useState(() => grupoDe(section));
  const [highlight, setHighlight] = useState(null);
  const [consultaAngela, setConsultaAngela] = useState(null);
  const [paletteOpen, setPaletteOpen] = useState(false);
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

  // Badges del sidebar: SOLO donde el número es trabajo despachable.
  // Prioridades counts the same `act` list the page shows.
  const [nPrioridades, setNPrioridades] = useState(0);
  useEffect(() => {
    api.prioridades().then((d) => setNPrioridades(d.badge || 0)).catch(() => {});
  }, []);
  // P38·A — una sola definición de "Datos a corregir" (lib/alertas): el badge
  // cuenta EXACTAMENTE lo que muestran la tabla de stock y la sección.
  const nCorregir = contarACorregir(data);
  const BADGES = { prioridades: nPrioridades,
                   saneamiento: nCorregir, staging: stagingCount };
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

  // 'pendientes' no es una feature de rol: es transversal (aparece si hay datos en revisión).
  // El highlight se limpia y se re-setea con un tick de por medio: navegar dos
  // veces al MISMO ancla (mismo string de estado) también tiene que titilar (P15·E6).
  const setHighlightRobusto = (hl) => {
    setHighlight(null);
    if (hl) setTimeout(() => setHighlight(hl), 30);
  };
  const navegar = (sec, hl) => {
    let destino = ALIAS_SECCION[sec] || sec;
    // Old "pendientes" / saneamiento?revision land on the staging step.
    if (destino === "pendientes" || (destino === "saneamiento" && hl === "revision")) {
      destino = "staging";
      hl = null;
    }
    // "panel" para el de a pie es su vista de trabajo, no el Inicio del dueño:
    // se navega igual aunque no tenga esa feature (ver `secciones`, arriba).
    if (destino && (featuresEfectivas.includes(destino)
                    || (destino === "panel" && vistaHerramienta))) {
      navigate(`/${destino}`);
      setHighlightRobusto(hl);
      return;
    }
    // Sección real pero sin permiso: feedback claro en vez de botón muerto (P9·C3, M7).
    if (destino && CATALOGO[destino]) toast(t("nav.sin_permiso"), "error");
    setHighlightRobusto(hl);
  };
  const irAPendientes = () => {
    api.stagingListar().then((d) => setStagingCount(d.batches.length)).catch(() => {});
    navegar("staging");
  };
  // El acordeón sigue a la sección activa, venga de donde venga el click
  // (sidebar, command palette, un link guiado de Ángela).
  useEffect(() => { setGrupoAbierto(grupoDe(section)); }, [section]);
  // Click en el PADRE de un grupo: si ya está abierto, sólo se cierra (no
  // navega — deja ocultar la lista sin abandonar la página); si está cerrado,
  // navega a su primer hijo y se abre, cerrando implícitamente cualquier otro
  // (un solo `grupoAbierto` a la vez == acordeón exclusivo).
  const clickGrupo = (g) => {
    if (grupoAbierto === g.id) { setGrupoAbierto(null); return; }
    navegar(g.ids[0], null);
  };
  // Ctrl+K / Cmd+K abre el command palette desde cualquier pantalla (mismo
  // patrón de shortcut global que CerebroNegocio.jsx usa con "/").
  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen(true);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);
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

  if (redirectTo) return <Navigate to={`/${redirectTo}`} replace />;

  return (
    <div className="flex h-[100dvh] overflow-hidden bg-papel text-tinta">
      <Toasts />
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        secciones={secciones}
        catalogo={CATALOGO}
        vistaHerramienta={vistaHerramienta}
        onNavegar={navegar}
        onPreguntar={preguntar}
      />
      <aside className={`flex shrink-0 flex-col border-r border-linea bg-crema/70 transition-[width] duration-200 ${sidebarColapsado ? "w-16" : "w-64"}`}>
        <div className={`flex items-center border-b border-linea py-5 ${sidebarColapsado ? "justify-center px-2" : "justify-between px-5"}`}>
          {!sidebarColapsado && (
            <div className="min-w-0">
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
          )}
          <button
            onClick={() => vistaStore.aplicar({ sidebarColapsado: !sidebarColapsado })}
            title={t(sidebarColapsado ? "nav.expandir_sidebar" : "nav.colapsar_sidebar")}
            className="shrink-0 rounded-lg p-1.5 text-tinta-suave hover:bg-papel-hondo/60 hover:text-tinta"
          >
            {sidebarColapsado ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
          </button>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {grupos.map((g) => {
            if (g.leaf) {
              const c = CATALOGO[g.id];
              const Icon = c.icon;
              const activo = section === g.id;
              return (
                <ItemNav key={g.id} icon={Icon} activo={activo} colapsado={sidebarColapsado} badge={BADGES[g.id]}
                  dot={g.id === "documentos" && docNuevo}
                  label={t(g.id === "panel" && vistaHerramienta ? "mnav.mi_dia" : c.lk)}
                  to={`/${g.id}`} onClick={() => navegar(g.id, null)} />
              );
            }
            const abierto = grupoAbierto === g.id;
            const badgeGrupo = g.ids.reduce((s, id) => s + (BADGES[id] || 0), 0);
            return (
              <div key={g.id}>
                <ItemNav icon={g.icon} activo={abierto} colapsado={sidebarColapsado} badge={badgeGrupo}
                  label={t(g.lk)} chevron={!sidebarColapsado} chevronAbierto={abierto}
                  to={`/${g.ids[0]}`} onClick={() => clickGrupo(g)} />
                <AnimatePresence initial={false}>
                  {abierto && !sidebarColapsado && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.18 }} className="overflow-hidden pl-4"
                    >
                      {g.ids.map((id) => {
                        const c = CATALOGO[id];
                        const Icon = c.icon;
                        return (
                          <ItemNav key={id} icon={Icon} activo={section === id} colapsado={false} badge={BADGES[id]}
                            dot={id === "documentos" && docNuevo} label={t(c.lk)}
                            to={`/${id}`} onClick={() => navegar(id, null)} />
                        );
                      })}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </nav>

        <div className="border-t border-linea p-3">
          {/* La entrada genérica a Ángela vive en el header — esta tarjeta ya
              no la duplica en estado idle. Sólo aparece cuando hay algo real
              y distinto para mostrar: una decisión esperando (P15·E6). */}
          {stagingCount > 0 && (
            <button
              onClick={() => navegar("panel", "decisiones")}
              title={t("decision.espera_ok")}
              className={`flex w-full items-center gap-3 rounded-xl border border-linea bg-crema text-left sombra-papel transition-colors hover:border-violeta/40 ${sidebarColapsado ? "justify-center p-2" : "px-3 py-2"}`}
            >
              <AngelaMark size={sidebarColapsado ? 26 : 30} estado="esperando" />
              {!sidebarColapsado && (
                <div className="min-w-0 flex-1">
                  <p className="text-[0.88rem] font-semibold">Ángela</p>
                  <p className="flex items-center gap-1.5 truncate text-[0.88rem] text-tinta-suave">
                    <span className="inline-block h-1.5 w-1.5 rounded-full bg-oro" />
                    {t("decision.espera_ok")}
                  </p>
                </div>
              )}
            </button>
          )}
        </div>
      </aside>

      {/* COLUMNA PRINCIPAL */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-4 border-b border-linea bg-papel/80 px-6 py-3 backdrop-blur">
          <button
            onClick={() => setPaletteOpen(true)}
            className="flex flex-1 items-center gap-3 rounded-full border border-linea bg-crema px-4 py-2 text-left sombra-papel transition-colors hover:border-violeta/40"
          >
            <Search size={17} className="shrink-0 text-tinta-suave" />
            <span className="flex-1 text-[0.9rem] text-tinta-suave/80">{t("nav.buscador")}</span>
            <kbd className="hidden shrink-0 rounded-md border border-linea px-1.5 py-0.5 text-[0.7rem] font-semibold text-tinta-suave sm:block">Ctrl K</kbd>
          </button>
          <VerComoChip />
          <Campanita
            token={session?.token}
            esAdmin={user.es_admin}
            onVerSolicitud={() => navegar("equipo", "solicitudes")}
          />
          <button onClick={() => setAngelaOpen((v) => !v)} className="flex items-center gap-2 rounded-full bg-violeta px-3.5 py-2 text-[0.88rem] font-semibold text-crema transition-transform active:scale-95">
            <AngelaMark size={22} estado={stagingCount > 0 ? "esperando" : "idle"} /> Ángela <PanelRightOpen size={15} />
          </button>
          <AccountMenu user={user} onVerPerfil={() => navegar("perfil", null)} />
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
                  {fase.foco && user.features.includes(fase.foco) && CATALOGO[ALIAS_SECCION[fase.foco] || fase.foco] && (
                    <button
                      onClick={() => navegar(fase.foco, null)}
                      className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-violeta px-3.5 py-1.5 text-[0.88rem] font-semibold text-crema"
                    >
                      {t("nav.ir_a")} {t(CATALOGO[ALIAS_SECCION[fase.foco] || fase.foco].lk)}
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
                {section === "saneamiento" && <Saneamiento user={user} highlight={highlight} onNavegar={navegar} onPreguntar={preguntar} onRecargar={onRecargar} />}
                {section === "staging" && <StagingArea onCambio={setStagingCount} onRecargar={onRecargar} onNavigate={navegar} />}
                {section === "cargar" && <CargarDatos user={user} onArchivoCargado={irAPendientes} onPreguntar={preguntar} onAbrirAngela={abrirAngela} onNavigate={navegar} />}
                {section === "finanzas" && <Finanzas data={data} onPreguntar={preguntar} datos={fase?.datos} onNavegar={navegar} />}
                {section === "prioridades" && <Prioridades onPreguntar={preguntar} onNavegar={navegar} />}
                {section === "equipo" && <GestionEquipo data={data} user={user} highlight={highlight} />}
                {section === "documentos" && <Documentos onPreguntar={preguntar} />}
                {section === "cuentas" && <CuentasCorrientes onPreguntar={preguntar} highlight={highlight} />}
                {section === "caja" && <Caja />}
                {section === "cobranzas" && <Cobranzas onPreguntar={preguntar} datos={fase?.datos} user={user} onNavegar={navegar} />}
                {section === "administracion" && <Administracion data={data} onPreguntar={preguntar} />}
                {section === "deposito" && <Deposito data={data} onPreguntar={preguntar} />}
                {section === "evolucion" && <Evolucion data={data} onNavegar={navegar} onPreguntar={preguntar} />}
                {section === "auditoria" && <Auditoria />}
                {section === "conectores" && <Conectores onNavigate={navegar} />}
                {section === "admin_contexto" && <AdminContexto />}
                {section === "perfil" && <MiPerfil user={user} />}
                {section === "ubicaciones" && <Ubicaciones />}
                {section === "lotes" && <Lotes onNavegar={navegar} />}
                {section === "imported" && <Imported highlight={highlight} onNavigate={navegar} />}
                {section === "proveedores" && <Proveedores />}
                {section === "ordenes_compra" && <OrdenesCompra />}
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

// En modo riel (colapsado) esconde el label y el badge se reduce a un
// puntito; un tooltip propio (no sólo `title`) lo compensa, porque en ese
// modo no hay texto en pantalla que lo reemplace.
function ItemNav({ icon: Icon, label, activo, colapsado, to, onClick, badge, dot, chevron, chevronAbierto }) {
  // `position: fixed` (medido con getBoundingClientRect) en vez de un
  // `absolute` normal: el <nav> del sidebar tiene overflow-y-auto, y por regla
  // de CSS eso fuerza su overflow-x a "auto" también — cualquier tooltip
  // absoluto que sobresalga del riel colapsado queda recortado. `fixed` no
  // respeta el overflow de ese ancestro (no hay transform/filter en el medio).
  const [rect, setRect] = useState(null);
  const btnRef = useRef(null);
  return (
    <div
      className="relative"
      onMouseEnter={() => colapsado && setRect(btnRef.current?.getBoundingClientRect())}
      onMouseLeave={() => setRect(null)}
    >
      <Link
        ref={btnRef}
        to={to}
        // Real <a href> so right-click "open in new tab" works; modified
        // clicks fall through to native browser handling.
        onClick={(e) => {
          if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
          e.preventDefault();
          onClick();
        }}
        className={`flex w-full items-center gap-3 rounded-xl py-2.5 text-left text-[0.9rem] font-medium transition-colors ${
          colapsado ? "justify-center px-2" : "px-3"
        } ${activo ? "bg-violeta-suave font-semibold text-violeta-hondo" : "text-tinta-suave hover:bg-papel-hondo/60 hover:text-tinta"}`}
      >
        <span className="relative shrink-0">
          <Icon size={18} className={activo ? "text-violeta" : ""} />
          {colapsado && (badge > 0 || dot) && (
            <span className="absolute -right-1 -top-1 h-2 w-2 rounded-full bg-oro" />
          )}
        </span>
        {!colapsado && (
          <>
            <span className="flex-1">{label}</span>
            {badge > 0 && (
              <span className="grid h-5 min-w-5 place-items-center rounded-full bg-oro px-1 text-[0.88rem] font-bold text-crema">{badge}</span>
            )}
            {dot && <span className="h-2 w-2 rounded-full bg-violeta" />}
            {chevron && (
              <ChevronRight size={15} className={`shrink-0 text-tinta-suave transition-transform ${chevronAbierto ? "rotate-90" : ""}`} />
            )}
          </>
        )}
      </Link>
      {rect && (
        <span
          style={{ position: "fixed", left: rect.right + 8, top: rect.top + rect.height / 2, transform: "translateY(-50%)" }}
          className="z-30 whitespace-nowrap rounded-lg bg-tinta px-2.5 py-1.5 text-[0.8rem] font-medium text-crema sombra-alta"
        >
          {label}
        </span>
      )}
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

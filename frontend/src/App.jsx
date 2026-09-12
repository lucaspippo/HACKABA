import { useEffect, useState } from "react";
import { Route, Routes, useLocation } from "react-router-dom";
import Showcase from "./components/assistant/tools/Showcase";
import AngelaMark from "./components/AngelaMark";
import Login from "./components/Login";
import MobileApp from "./mobile/MobileApp";
import DesktopApp from "./desktop/DesktopApp";
import { useIsDesktop } from "./lib/useViewport";
import { authStore, useSession } from "./lib/auth";
import { api } from "./lib/api";
import { apiUrl } from "./lib/apiUrl";
import { langStore, useT } from "./lib/i18n";
import { equipoStore } from "./lib/equipoStore";
import { vistaStore } from "./lib/vistaStore";
import { ALERTA_DEFS } from "./lib/alertas";

// Los roles sin el módulo "inventario" (depósito, reparto, mostrador…) no pueden
// pedir /api/inventario (403). Reciben este esqueleto: las secciones que muestran
// contadores (Depósito, Oficina) leen alertas.X.cantidad y encuentran ceros.
const dataSinInventario = () => ({
  meta: {},
  resumen: {},
  alertas: Object.fromEntries(
    Object.keys(ALERTA_DEFS).map((k) => [k, { cantidad: 0, plata: 0 }]),
  ),
  top_inmovilizado: [],
  grupos_disponibles: [],
});

// Un cerebro, dos superficies, login real por usuario.
export default function App() {
  const location = useLocation();
  const t = useT();
  const session = useSession();
  const isDesktop = useIsDesktop();
  const [data, setData] = useState(null);
  const [oportunidades, setOportunidades] = useState(null);
  const [fase, setFase] = useState(null);
  const [error, setError] = useState(null);
  // B8: null = todavía averiguando si el tenant tiene autologin; true = ya se
  // resolvió (entró solo o corresponde mostrar el login).
  const [autologinResuelto, setAutologinResuelto] = useState(false);

  // B8 — Entrada directa del demo (link de YC): sin sesión y con el flag del
  // tenant activo, la URL entra sola como el DUEÑO. Un logout MANUAL deja la
  // pantalla de login a la vista (el marker vive en sessionStorage).
  useEffect(() => {
    if (session?.usuario) return;
    if (sessionStorage.getItem("polpilot.logout.manual") === "1") {
      setAutologinResuelto(true);
      return;
    }
    let vivo = true;
    (async () => {
      try {
        const h = await fetch(apiUrl("/api/health")).then((r) => r.json());
        if (vivo && h.autologin) {
          const res = await fetch(apiUrl("/api/demo/autologin"), { method: "POST" });
          if (res.ok) authStore.adoptar(await res.json());
        }
      } catch { /* backend caído: el login normal lo explica */ }
      if (vivo) setAutologinResuelto(true);
    })();
    return () => { vivo = false; };
  }, [session]);

  const recargar = () =>
    Promise.all([
      session?.usuario?.features?.includes("inventario")
        ? api.inventario()
        : Promise.resolve(dataSinInventario()),
      api.oportunidades(),
      api.fase(),
    ])
      .then(([inv, op, f]) => {
        setData(inv);
        setOportunidades(op);
        setFase(f);
        setError(null);
      })
      .catch((e) => setError(e.message));

  useEffect(() => {
    if (!session?.usuario) return;
    // El idioma del usuario viene del servidor (su perfil) y manda sobre el cache local.
    langStore.syncDesdeUsuario(session.usuario);
    // Los objetivos del server (los que creó Ángela o cualquier usuario) se
    // mezclan en el tablero local de este usuario (P9·C5, M9).
    equipoStore.sincronizar();
    // P19·A — lo que Ángela recuerda de este usuario (sin_torta, margen pin,
    // orden del Home, widgets) baja del server y pisa el cache local: la
    // preferencia sobrevive logout y cambio de máquina.
    api.preferencias().then((p) => vistaStore.hidratarServer(p)).catch(() => {});
    recargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session]);

  // Backend caído: reintentar solo, cada 5s, hasta que vuelva (P15·E1). La
  // pantalla de error lo dice ("reintentando…") — nunca un Home con ceros.
  useEffect(() => {
    if (!error || !session?.usuario) return;
    const id = setInterval(recargar, 5000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [error, session]);

  // /showcase renders the tool presenters from saved fixtures. It sits BEFORE
  // the session gate on purpose: its whole value is needing no login, no
  // backend and no API key (see Showcase.tsx).
  if (location.pathname === "/showcase") return <Showcase />;

  // Sin sesión → autologin del demo si aplica (B8); si no, login.
  if (!session?.usuario) {
    if (!autologinResuelto) {
      return (
        <Centro>
          <AngelaMark size={48} pulse />
          <p className="mt-4 text-sm text-tinta-suave">{t("app.leyendo")}</p>
        </Centro>
      );
    }
    return <Login />;
  }

  if (error) {
    return (
      <Centro>
        <AngelaMark size={48} pulse />
        <p className="mt-4 max-w-xs text-center text-base text-tinta">
          {t("app.sin_conexion")}
        </p>
        <p className="mt-1 max-w-xs text-center text-sm font-medium text-tinta-suave">
          {t("app.reintentando")}
        </p>
        <p className="mt-3 max-w-xs text-center text-sm text-tinta-suave">
          {t("app.levanta_backend")} <code className="rounded bg-papel-hondo px-1">python start_demo.py</code>.
        </p>
      </Centro>
    );
  }

  if (!data) {
    return (
      <Centro>
        <AngelaMark size={48} pulse />
        <p className="mt-4 text-sm text-tinta-suave">{t("app.leyendo")}</p>
      </Centro>
    );
  }

  const user = session.usuario;
  // key por usuario: al cambiar de identidad ("View as" del demo, P9·E) el
  // árbol entero se rearma — features, secciones, chat de Ángela — CERO
  // arrastre del usuario anterior.
  // The active section lives in the URL (/:section) — deep links,
  // back/forward, and sharing a link to a specific screen work for free.
  return (
    <Routes>
      <Route
        path="/:section?"
        element={isDesktop ? (
          <DesktopApp key={user.username} data={data} oportunidades={oportunidades} fase={fase} user={user} onRecargar={recargar} />
        ) : (
          <MobileApp key={user.username} data={data} oportunidades={oportunidades} fase={fase} user={user} onRecargar={recargar} />
        )}
      />
    </Routes>
  );
}

function Centro({ children }) {
  return (
    <div className="flex min-h-[100dvh] flex-col items-center justify-center bg-papel px-6">
      {children}
    </div>
  );
}

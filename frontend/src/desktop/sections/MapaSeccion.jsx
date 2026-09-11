// "El mapa de tu negocio" tiene dos formas de mirarse, y este archivo es lo
// único que sabe que existen las dos.
//
//   Mapa    — el árbol de las 8 fuentes y sus cortes (MapaNegocio.jsx, intacto).
//   Cerebro — las entidades individuales y sus cruces (CerebroNegocio.jsx).
//
// Deliberadamente delgado: es un switch, no un contenedor con lógica. Cada
// vista carga SUS datos y mantiene SU estado. Un error en el cerebro no puede
// arrastrar al mapa — van en ErrorBoundaries separados y montados por turno.
//
// Sobre unificar las dos en una sola (el grafo denso en el centro, rodeado por
// las 8 fuentes): este archivo es el lugar donde eso pasaría. Hoy el toggle
// desmonta una y monta la otra; una versión unificada renderizaría las dos
// capas juntas acá. Nada de lo que hay adentro de cada vista lo impide.
import { useState } from "react";
import { Waypoints, Braces } from "lucide-react";
import ErrorBoundary from "../../components/ErrorBoundary";
import MapaNegocio from "./MapaNegocio";
import CerebroNegocio from "./CerebroNegocio";
import { useT } from "../../lib/i18n";

// Nota: el motor de fuerzas pesa ~300 kB y se intentó cargarlo con React.lazy
// para que solo lo pague quien abre el cerebro. No va: con Vite, el Suspense
// no resuelve nunca aunque los chunks bajen con 200 (interop del UMD de
// react-force-graph). Import estático — en una demo que se graba, 300 kB
// cuestan menos que una pantalla que se queda cargando para siempre.

const VISTAS = [
  { id: "mapa", icon: Waypoints, lk: "cerebro.tab_mapa", ay: "cerebro.tab_mapa_ay" },
  { id: "cerebro", icon: Braces, lk: "cerebro.tab_cerebro", ay: "cerebro.tab_cerebro_ay" },
];

// La elección sobrevive a salir y volver a la sección (pero no a recargar):
// misma disciplina que el resto del mapa (P32 · cache de sesión).
let _vistaElegida = "mapa";

export default function MapaSeccion({ onNavegar, onPreguntar, onInsight }) {
  const t = useT();
  const [vista, setVista] = useState(_vistaElegida);

  const cambiar = (id) => {
    if (id === vista) return;
    _vistaElegida = id;
    // el panel de Ángela es del MAPA: al irse a la otra vista se limpia solo,
    // si no queda un insight huérfano flotando en el aside.
    if (id !== "mapa") onInsight?.(null);
    setVista(id);
  };

  const activa = VISTAS.find((v) => v.id === vista);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="inline-flex rounded-full border border-linea bg-papel-hondo p-0.5">
          {VISTAS.map((v) => {
            const on = v.id === vista;
            const Icono = v.icon;
            return (
              <button key={v.id} onClick={() => cambiar(v.id)}
                aria-pressed={on}
                className={`flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-[13px] font-medium
                            transition-colors ${on
                    ? "bg-crema text-tinta shadow-[0_1px_2px_rgba(33,32,29,.08)]"
                    : "text-tinta-suave hover:text-tinta"}`}>
                <Icono className="size-3.5" />
                {t(v.lk)}
              </button>
            );
          })}
        </div>
        <span className="text-[12.5px] text-tinta-suave">{t(activa.ay)}</span>
      </div>

      {/* montadas por turno y con boundary propio: una no puede tirar a la otra */}
      {vista === "mapa" && (
        <ErrorBoundary key="vista:mapa" seccion="mapa" onInicio={() => onNavegar?.("panel", null)}>
          <MapaNegocio onNavegar={onNavegar} onPreguntar={onPreguntar} onInsight={onInsight} />
        </ErrorBoundary>
      )}
      {vista === "cerebro" && (
        <ErrorBoundary key="vista:cerebro" seccion="mapa" onInicio={() => cambiar("mapa")}>
          <CerebroNegocio onNavegar={onNavegar} onPreguntar={onPreguntar} />
        </ErrorBoundary>
      )}
    </div>
  );
}

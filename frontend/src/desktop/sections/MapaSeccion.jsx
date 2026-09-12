// "El mapa de tu negocio" now has three ways of being looked at, and this
// file is the only thing that knows all three exist.
//
//   Operación — the physical chain: where goods come from, where they are,
//               where they go (MapaOperacion.jsx). The DEFAULT view: it is
//               the one that answers "what is happening right now".
//   Fuentes   — the tree of the 8 sources and their cuts (MapaNegocio.jsx,
//               untouched).
//   Cerebro   — the individual entities and their crossings
//               (CerebroNegocio.jsx, untouched).
//
// Deliberately thin: it is a switch, not a container with logic. Each view
// loads ITS data and keeps ITS state, in separate ErrorBoundaries mounted in
// turn — an error in the brain cannot drag down the map.
//
// The door to the sources goes ON TOP and with a name of its own ("Lo que sé
// de tu negocio"). At the bottom, as «see the full source crossing», it read
// like a second operation map and nobody opened it. It is not another map:
// it is where the numbers on THIS one come from.
import { useState } from "react";
import { ArrowLeft, Braces, Route, Waypoints } from "lucide-react";
import ErrorBoundary from "../../components/ErrorBoundary";
import MapaNegocio from "./MapaNegocio";
import CerebroNegocio from "./CerebroNegocio";
import MapaOperacion from "./MapaOperacion";
import CerebroPantalla from "./CerebroPantalla";
import { useT } from "../../lib/i18n";

// The choice survives leaving and returning to the section (not a reload):
// same discipline as the rest of the map (P32 · session cache).
let _vistaElegida = "operacion";

// `highlight` is a finding id: a Home card sends here and the map must open
// ALREADY on that finding, path lit and panel open — not on a neutral map
// where you have to hunt for what to tap.
export default function MapaSeccion({ onNavegar, onPreguntar, onInsight,
                                      highlight = null }) {
  const t = useT();
  const [vista, setVista] = useState(_vistaElegida);
  // LA PANTALLA INTERMEDIA DEJÓ DE EXISTIR. «Lo que sé de tu negocio» abría una
  // vista con siete bloques compitiendo y el lienzo abajo del fold; ahora abre
  // DIRECTO el cerebro a pantalla completa, con Ángela al costado. Cerrar
  // vuelve acá, al mapa de la operación. Sin escala intermedia.
  const [pantalla, setPantalla] = useState(false);

  const ir = (id) => {
    if (id === vista) return;
    _vistaElegida = id;
    // The Ángela panel belongs to the sources map: leaving it clears the
    // insight, or an orphan floats in the aside.
    if (id !== "fuentes") onInsight?.(null);
    setVista(id);
  };

  if (vista === "operacion") {
    return (
      <div className="space-y-3">
        <div className="flex justify-end">
          <button onClick={() => setPantalla(true)}
                  className="flex min-h-[44px] items-center gap-2.5 rounded-full border
                             border-violeta/30 bg-violeta-suave/50 px-4 text-left
                             transition-colors hover:bg-violeta-suave">
            <Waypoints className="size-4 shrink-0 text-violeta" />
            <span className="min-w-0">
              <span className="block text-[13px] font-semibold leading-tight text-violeta">
                {t("mapaop.saber")}
              </span>
              <span className="block text-[11px] leading-tight text-tinta-suave">
                {t("mapaop.saber_sub")}
              </span>
            </span>
          </button>
        </div>
        <ErrorBoundary key="vista:operacion" seccion="mapa"
                       onInicio={() => onNavegar?.("panel", null)}>
          <MapaOperacion onPreguntar={onPreguntar} onNavegar={onNavegar}
                         focoInicial={highlight} />
        </ErrorBoundary>
        {pantalla && (
          <ErrorBoundary key="vista:pantalla" seccion="mapa"
                         onInicio={() => setPantalla(false)}>
            {/* cerrar vuelve acá, al mapa de la operación: es de donde se
                vino al apretar el botón. La vista «cerebro» de antes ya no se
                usa — el grafo completo es ahora el reposo de esta pantalla. */}
            <CerebroPantalla onCerrar={() => setPantalla(false)} />
          </ErrorBoundary>
        )}
      </div>
    );
  }

  const esCerebro = vista === "cerebro";
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <button onClick={() => ir("operacion")}
                className="flex min-h-[44px] items-center gap-1.5 rounded-full border
                           border-linea px-3.5 text-[13px] font-medium text-tinta-suave
                           transition-colors hover:text-tinta">
          <ArrowLeft className="size-3.5" />
          {t("mapaop.volver_operacion")}
        </button>
        <button onClick={() => ir(esCerebro ? "fuentes" : "cerebro")}
                className="flex min-h-[44px] items-center gap-1.5 text-[13px] font-medium
                           text-tinta-suave transition-colors hover:text-tinta">
          {esCerebro ? <Route className="size-4" /> : <Braces className="size-4" />}
          {esCerebro ? t("mapaop.volver_fuentes") : t("mapaop.ver_cerebro")}
        </button>
      </div>

      {vista === "fuentes" && (
        <ErrorBoundary key="vista:fuentes" seccion="mapa" onInicio={() => ir("operacion")}>
          <MapaNegocio onNavegar={onNavegar} onPreguntar={onPreguntar} onInsight={onInsight} />
        </ErrorBoundary>
      )}
      {esCerebro && (
        <ErrorBoundary key="vista:cerebro" seccion="mapa" onInicio={() => ir("operacion")}>
          <CerebroNegocio onNavegar={onNavegar} onPreguntar={onPreguntar} />
        </ErrorBoundary>
      )}
    </div>
  );
}

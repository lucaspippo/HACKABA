// EL INICIO DEL QUE TRABAJA EN EL PISO — la pantalla de la referencia.
//
// LA REGLA DE ESTA PANTALLA ES EL TAMAÑO. Entra entera en la primera vista de
// un teléfono, sin scrollear: cabecera de la app (~56px) + barra de abajo
// (~72px) dejan unos 680px, y todo lo de acá suma ~560. Por eso nada tiene el
// tamaño que "queda lindo" suelto, sino el que permite que lo de abajo también
// entre. Si se agranda un bloque, algo se cae de la pantalla.
//
// Cuatro piezas, en el orden en que las mira alguien que llega a trabajar:
//   1. la banda — cuánto le falta, de un vistazo, sin abrir nada
//   2. el detalle — qué es cada cosa y cómo viene
//   3. las acciones — lo que va a tocar con las manos ocupadas
//   4. las entregas — dónde tiene que estar después
//
// NADA ACÁ SE INVENTA: las tareas salen de `derivarTareas` (señales reales del
// sistema) y la próxima parada de la hoja de ruta. El progreso es una división
// entre dos números que ya existían, no un número de adorno.
import {
  Camera, ChevronDown, ChevronRight, FileText, ScanLine,
  StickyNote, Truck, TriangleAlert,
} from "lucide-react";
import { useT } from "../lib/i18n";

// El anillo de progreso de cada tarea. 22px de diámetro: se lee y no compite
// con el texto, que es lo que de verdad hay que leer.
function Anillo({ pct, color }) {
  const r = 9;
  const c = 2 * Math.PI * r;
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" className="shrink-0 -rotate-90">
      <circle cx="12" cy="12" r={r} fill="none" stroke="var(--color-linea)" strokeWidth="3" />
      <circle cx="12" cy="12" r={r} fill="none" stroke={color} strokeWidth="3"
              strokeLinecap="round"
              strokeDasharray={`${(c * Math.min(100, Math.max(0, pct))) / 100} ${c}`} />
    </svg>
  );
}

// 1 · LA BANDA. Una franja fina, no un bloque: dice UNA cosa —cuánto llevás—
// y deja el resto de la pantalla para lo que hay que hacer.
function Banda({ pct, onAbrir }) {
  const t = useT();
  return (
    <button onClick={onAbrir}
            className="flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-left"
            style={{ background: "linear-gradient(101deg,#e8615f 0%,#d94f62 100%)" }}>
      <span className="min-w-0 flex-1">
        <span className="block text-[15px] font-bold leading-tight text-white">
          {t("piso.mis_tareas")}
        </span>
        <span className="mt-0.5 block text-[11px] text-white/85">
          {t("piso.progreso", { pct })}
        </span>
        <span className="mt-1.5 block h-1.5 w-full overflow-hidden rounded-full bg-white/30">
          <span className="block h-full rounded-full bg-white transition-[width] duration-700"
                style={{ width: `${pct}%` }} />
        </span>
      </span>
      {/* El ícono del rubro: esto es una distribuidora, lo que se mueve son
          comprobantes. La referencia traía unas cajas de stock genéricas. */}
      <FileText size={30} className="shrink-0 text-white/90" strokeWidth={1.5} />
      <ChevronDown size={17} className="shrink-0 text-white/80" />
    </button>
  );
}

// 2 · EL DETALLE. Punto de estado a la izquierda, anillo a la derecha: el
// estado se lee por color y el avance por forma, sin leer una palabra.
const TONO = {
  hecha: { punto: "#2e9c6a", anillo: "#e8615f" },
  curso: { punto: "#de7c1a", anillo: "#e8a13a" },
  proxima: { punto: "#2a5cdf", anillo: "#2a5cdf" },
};

function Detalle({ items, onTarea }) {
  const t = useT();
  return (
    <section className="rounded-2xl border border-linea bg-crema sombra-papel">
      <h2 className="border-b border-linea px-3.5 py-2 text-[13px] font-semibold text-tinta">
        {t("piso.detalle_tareas")}
      </h2>
      <div className="px-3.5">
        {items.map((x, i) => {
          const tono = TONO[x.estado] || TONO.proxima;
          return (
            <button key={x.id} onClick={() => onTarea?.(x)}
                    className={`flex w-full items-center gap-2.5 py-2.5 text-left ${
                      i < items.length - 1 ? "border-b border-linea" : ""}`}>
              <span className="size-2.5 shrink-0 rounded-full"
                    style={{ background: tono.punto }} />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[13px] font-semibold leading-tight text-tinta">
                  {x.titulo}
                </span>
                <span className="block truncate text-[11px] leading-tight text-tinta-suave">
                  {x.detalle}
                </span>
              </span>
              <Anillo pct={x.pct} color={tono.anillo} />
            </button>
          );
        })}
      </div>
    </section>
  );
}

// 3 · LAS ACCIONES. Cinco cuadrados pastel. Es lo que se toca con una mano
// mientras la otra sostiene algo, así que el target es grande y el texto corto.
const ACCIONES = [
  { id: "escanear", Icon: ScanLine, fondo: "#eef2fd", tinta: "#2a5cdf" },
  { id: "foto", Icon: Camera, fondo: "#eaf6ef", tinta: "#2e9c6a" },
  { id: "registrar", Icon: FileText, fondo: "#fdf2e6", tinta: "#c07516" },
  { id: "problema", Icon: TriangleAlert, fondo: "#fdeeee", tinta: "#d0453f" },
  { id: "nota", Icon: StickyNote, fondo: "#f2eefc", tinta: "#6b4bc4" },
];

function Acciones({ onAccion }) {
  const t = useT();
  return (
    <section className="rounded-2xl border border-linea bg-crema px-3 py-2.5 sombra-papel">
      <h2 className="mb-2 text-[13px] font-semibold text-tinta">{t("piso.acciones_rapidas")}</h2>
      <div className="grid grid-cols-5 gap-1.5">
        {ACCIONES.map(({ id, Icon, fondo, tinta }) => (
          <button key={id} onClick={() => onAccion?.(id)}
                  className="flex flex-col items-center gap-1 active:scale-95">
            <span className="grid size-11 place-items-center rounded-xl"
                  style={{ background: fondo }}>
              <Icon size={19} style={{ color: tinta }} />
            </span>
            <span className="text-center text-[10px] leading-tight text-tinta-suave">
              {t(`piso.acc_${id}`)}
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}

// 4 · LAS ENTREGAS. El mapita es un croquis, no un mapa de verdad: decir dónde
// está el camión exigiría una posición que no tenemos, y un mapa que miente es
// peor que un dibujo que no promete nada. Los datos de al lado sí son reales.
function Entregas({ proxima, restantes, onRuta }) {
  const t = useT();
  return (
    <section className="rounded-2xl border border-linea bg-crema px-3 py-2.5 sombra-papel">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-[13px] font-semibold text-tinta">{t("piso.entregas_hoy")}</h2>
        <button onClick={onRuta}
                className="flex items-center gap-0.5 rounded-full border border-linea
                           px-2.5 py-1 text-[11px] font-semibold text-violeta">
          {t("piso.ver_ruta")} <ChevronRight size={12} />
        </button>
      </div>
      <div className="flex items-center gap-3">
        <div className="relative h-[72px] w-[46%] shrink-0 overflow-hidden rounded-xl"
             style={{ background: "#eef1f4" }}>
          <svg viewBox="0 0 120 72" className="h-full w-full">
            {/* la trama de calles, apenas sugerida */}
            <g stroke="#dadfe5" strokeWidth="5">
              <path d="M0 22 H120 M0 50 H120 M34 0 V72 M82 0 V72" />
            </g>
            {/* el recorrido */}
            <path d="M18 62 L34 50 L34 22 L82 22 L96 14" fill="none"
                  stroke="#2a5cdf" strokeWidth="2.6" strokeLinecap="round"
                  strokeDasharray="5 4" />
            <circle cx="96" cy="14" r="4" fill="#2a5cdf" />
          </svg>
          <span className="absolute bottom-1.5 left-1.5 grid size-7 place-items-center
                           rounded-full bg-violeta shadow">
            <Truck size={14} className="text-white" />
          </span>
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[11px] leading-tight text-tinta-suave">{t("piso.siguiente_parada")}</p>
          <p className="truncate text-[13px] font-semibold leading-tight text-tinta">
            {proxima || "—"}
          </p>
          {restantes != null && (
            <p className="mt-1 text-[11px] leading-tight text-tinta-suave">
              {t("piso.entregas_restantes", { n: restantes })}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}

// =============================================================================
export default function InicioPiso({ nombre, lugar, pct, tareas, proxima,
                                     restantes, onTarea, onAccion, onRuta,
                                     onAbrirTareas }) {
  const t = useT();
  return (
    <div className="space-y-2.5">
      <div className="px-0.5">
        <h1 className="font-display text-[19px] font-bold leading-tight text-tinta">
          {t("piso.hola", { nombre })}
        </h1>
        {lugar && <p className="text-[12px] leading-tight text-tinta-suave">{lugar}</p>}
      </div>

      <Banda pct={pct} onAbrir={onAbrirTareas} />
      {tareas.length > 0 && <Detalle items={tareas} onTarea={onTarea} />}
      <Acciones onAccion={onAccion} />
      {/* Sólo si hay algo que mostrar. Un «Entregas de hoy» con un guion y
          «0 entregas restantes» no es un estado vacío: es una promesa que la
          pantalla no cumple. Y cuando no hay datos casi nunca es porque no
          haya entregas — es porque este rol no tiene permiso de logística, y
          entonces el bloque directamente no le corresponde. */}
      {proxima && <Entregas proxima={proxima} restantes={restantes} onRuta={onRuta} />}
    </div>
  );
}

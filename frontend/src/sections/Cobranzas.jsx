import { useEffect, useRef, useState } from "react";
import {
  Lock, HandCoins, Gauge, Send, Check, Clock, X, Pencil, Users, AlertTriangle,
} from "lucide-react";
import AngelaSays from "../components/AngelaSays";
import AngelaMark from "../components/AngelaMark";
import Cargando from "../components/Cargando";
import { useApiMutation, useApiQuery } from "../lib/query";
import { peso, pesoCorto, num, fecha as fmtFecha } from "../lib/format";
import { toast } from "../lib/toastStore";
import { useT } from "../lib/i18n";

// COBRANZA AGÉNTICA — a quién cobrar primero, y que Ángela lo redacte.
//
// Sin cuentas cargadas sigue siendo el placeholder honesto de siempre. Con
// cuentas, esto es la vista real: el orden, el mensaje listo, y el estado de
// cada gestión.
//
// La diferencia con una lista de morosos: una lista se ordena por saldo y el
// dueño igual tiene que pensar. Acá el orden ya incorpora cuánto se corrió cada
// cliente de SU propia costumbre — por eso Doña Elsa, que debe menos, va antes
// que San Martín. Esa es la cuenta que el dueño hace de memoria.
//
// Ángela redacta y PROPONE; nada sale sin que alguien toque "Mandar".
//
// P42·1 — LA MISMA PANTALLA, DOS ALTURAS. Cobranzas dejó de ser sólo del
// preventista: el dueño también la tiene, porque la cobranza es SU estrategia
// (a quién apretar, en qué orden, cuánta liquidez entra) y la ejecución es de
// la calle. No son dos pantallas: es la misma lista mirada desde arriba.
//   · preventista → sus clientes, el mensaje, la gestión de hoy.
//   · dueño       → el panorama: dónde está concentrada la exposición, cuánto
//                   hay sin tocar, quién está trabajando cada cuenta.
// El orden, los montos y la liquidez son los MISMOS números para los dos: el
// backend calcula una vez (core/cobranza.py) y acá sólo cambia qué se destaca.
export default function Cobranzas({ onPreguntar, datos, user, onNavegar }) {
  const t = useT();
  const hayCuentas = !!datos?.cuentas;
  const esDueno = !!user?.es_admin;
  const [abierto, setAbierto] = useState(null);   // propuesta desplegada
  const { data: d, isLoading, refetch } = useApiQuery("cobranza", [], { enabled: hayCuentas });
  const recargar = () => refetch();

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-2xl font-bold">{t("cobranzas.titulo")}</h1>
        <p className="mt-1 text-sm text-tinta-suave">
          {t(esDueno ? "cobranzas.subtitulo_dueno" : "cobranzas.subtitulo")}
        </p>
      </header>

      <AngelaSays>
        {t(hayCuentas
          ? (esDueno ? "cobranzas.angela_intro_dueno" : "cobranzas.angela_intro_ok")
          : "cobranzas.angela_intro")}
      </AngelaSays>

      {hayCuentas && isLoading && <Cargando />}

      {hayCuentas && d && d.disponible && (
        <>
          {/* la liquidez: lo que entra si se cobra esto */}
          <div className="grid gap-3 sm:grid-cols-3">
            <Tile valor={pesoCorto(d.entra_si_cobras)} lk="cobranzas.tile_entra" tono="text-salvia" />
            <Tile valor={num(d.items.length)} lk="cobranzas.tile_cuentas" tono="text-tinta" />
            <Tile valor={pesoCorto(d.prometido)} lk="cobranzas.tile_prometido"
              tono={d.promesas_vencidas ? "text-rojo" : "text-hielo"}
              nota={d.promesas_vencidas
                ? t("cobranzas.promesas_vencidas", { n: num(d.promesas_vencidas) }) : null} />
          </div>

          {esDueno && d.panorama?.disponible && <Panorama p={d.panorama} t={t} />}

          <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
            <div className="border-b border-linea px-4 py-3">
              <p className="font-display text-lg font-bold leading-tight">
                {t(esDueno ? "cobranzas.orden_titulo_dueno" : "cobranzas.orden_titulo")}
              </p>
              <p className="text-sm text-tinta-suave">{t("cobranzas.orden_sub")}</p>
            </div>

            {d.items.map((c, i) => (
              <Fila key={c.id} c={c} pos={i + 1} t={t} esDueno={esDueno}
                abierto={abierto === c.id}
                onAbrir={() => setAbierto(abierto === c.id ? null : c.id)}
                onHecho={() => { setAbierto(null); recargar(); }}
                onPreguntar={onPreguntar} onNavegar={onNavegar} />
            ))}

            <p className="border-t border-linea px-4 py-2.5 text-xs leading-snug text-tinta-suave">
              {t("cobranzas.nota_orden")}
            </p>
          </div>
        </>
      )}

      {hayCuentas && d && !d.disponible && (
        <p className="rounded-[var(--radius-card)] border border-salvia/30 bg-salvia/[0.06] p-6
                      text-center text-sm text-tinta">
          {t("cobranzas.sin_morosos")}
        </p>
      )}

      {!hayCuentas && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Bloque icon={HandCoins} titulo={t("cobranzas.bloque_cobros")} falta={t("cobranzas.bloque_cobros_falta")} />
          <Bloque icon={Gauge} titulo={t("cobranzas.bloque_limite")} falta={t("cobranzas.bloque_limite_falta")} />
        </div>
      )}

      <div className="rounded-[var(--radius-card)] border border-dashed border-linea bg-papel-hondo/40 p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-tinta-suave">{t("cobranzas.como_funciona")}</p>
        <ul className="mt-2 space-y-1.5 text-sm text-tinta">
          <li>• {t("cobranzas.punto_1")}</li>
          <li>• {t("cobranzas.punto_2")}</li>
          <li>• {t("cobranzas.punto_3")}</li>
        </ul>
      </div>
    </div>
  );
}

const ESTADO_CLS = {
  pendiente: "bg-papel-hondo text-tinta-suave",
  recordado: "bg-hielo/15 text-hielo",
  promesa: "bg-oro/20 text-oro-tinta",
  pagado: "bg-salvia/20 text-salvia",
  sin_respuesta: "bg-rojo/15 text-rojo",
};

// EL PANORAMA DEL DUEÑO. Tres preguntas que el preventista no se hace y el
// dueño no puede dejar de hacerse: ¿está concentrada la deuda?, ¿cuánta plata
// está sin que nadie la toque?, ¿quién está trabajando cada cuenta?
// Todo sale de `panorama` (core/cobranza.py): derivado de la misma lista, cero
// fuente nueva. Acá no se suma nada.
function Panorama({ p, t }) {
  // Contra el desfasaje de versiones (frontend nuevo + backend viejo, que en
  // dev pasa con cada hot-reload): un campo que todavía no vino no puede
  // tumbar la sección entera. Sin esto, un deploy a medias deja Cobranzas en
  // el estado de error en vez de mostrar la lista, que es lo que importa.
  const nombres = p.concentracion_nombres || [];
  const trabajan = p.quien_trabaja || [];
  return (
    <div className="grid gap-3 lg:grid-cols-3">
      {/* 1 · concentración: si tres nombres explican la mitad, la estrategia
             no es "cobrar mejor", es hablar con esos tres. */}
      <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-tinta-suave">
          {t("cobranzas.pan_concentracion")}
        </p>
        <p className="plata mt-1.5 text-2xl font-medium leading-none text-tinta">
          {num(p.concentracion_share)}%
        </p>
        <p className="mt-1.5 text-sm leading-snug text-tinta">
          {t(p.concentracion_n === 1
             ? "cobranzas.pan_concentracion_uno"
             : "cobranzas.pan_concentracion_det", {
            n: num(p.concentracion_n),
            monto: pesoCorto(p.concentracion_saldo),
            nombres: nombres.join(", "),
          })}
        </p>
      </div>

      {/* 2 · lo que nadie tocó: la única cifra accionable hoy mismo */}
      <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-tinta-suave">
          {t("cobranzas.pan_sin_tocar")}
        </p>
        <p className={`plata mt-1.5 text-2xl font-medium leading-none ${p.sin_tocar ? "text-rojo" : "text-salvia"}`}>
          {pesoCorto(p.sin_tocar_saldo)}
        </p>
        <p className="mt-1.5 text-sm leading-snug text-tinta">
          {t("cobranzas.pan_sin_tocar_det", {
            n: num(p.sin_tocar), gest: num(p.en_gestion), monto: pesoCorto(p.en_gestion_saldo),
          })}
        </p>
        {p.exceso_dias_promedio > 0 && (
          <p className="mt-1.5 inline-flex items-center gap-1 text-xs text-oro-tinta">
            <AlertTriangle size={12} />
            {t("cobranzas.pan_exceso_promedio", { dias: num(p.exceso_dias_promedio) })}
          </p>
        )}
      </div>

      {/* 3 · quién la está trabajando: sale del actor auditado en cada gestión */}
      <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-tinta-suave">
          {t("cobranzas.pan_quien")}
        </p>
        {trabajan.length === 0 ? (
          <p className="mt-1.5 text-sm leading-snug text-tinta-suave">
            {t("cobranzas.pan_quien_nadie")}
          </p>
        ) : (
          <ul className="mt-2 space-y-1.5">
            {trabajan.map((f) => (
              <li key={f.actor} className="flex items-center gap-2 text-sm">
                <Users size={13} className="shrink-0 text-tinta-suave" />
                <span className="min-w-0 flex-1 truncate text-tinta">{f.actor}</span>
                <span className="shrink-0 text-xs text-tinta-suave">
                  {t("cobranzas.pan_quien_cuentas", { n: num(f.cuentas) })}
                </span>
                <span className="plata shrink-0 font-medium text-tinta">{pesoCorto(f.saldo)}</span>
              </li>
            ))}
          </ul>
        )}
        {p.cobrado > 0 && (
          <p className="mt-2 text-xs text-salvia">
            {t("cobranzas.pan_cobrado", { n: num(p.cobrado), monto: pesoCorto(p.cobrado_saldo) })}
          </p>
        )}
      </div>
    </div>
  );
}

function Fila({ c, pos, t, esDueno, abierto, onAbrir, onHecho, onPreguntar, onNavegar }) {
  const [texto, setTexto] = useState("");
  const [editando, setEditando] = useState(false);
  const [sugerencia, setSugerencia] = useState(null);
  const seeded = useRef(false);
  const { data: propData, isPending: propPending, isError: propError } = useApiQuery(
    "cobranzaPropuesta", [c.id], { enabled: abierto },
  );
  const registrarMut = useApiMutation("cobranzaRegistrar");
  const enviando = registrarMut.isPending;
  const prop = !abierto ? null : (propPending && !propData ? null : propError ? false : (propData ?? null));

  useEffect(() => {
    if (propData?.mensaje == null || seeded.current) return;
    setTexto(propData.mensaje);
    seeded.current = true;
  }, [propData]);

  const registrar = async (estado, extra = {}) => {
    try {
      const r = await registrarMut.mutateAsync([c.id, estado, { mensaje: texto, ...extra }]);
      // Lo que sigue después de perseguir a un cliente es mandarle el estado
      // de cuenta. Se OFRECE con la frase que arma el backend; el papel no se
      // genera solo (core/carpeta.sugerencia no escribe nada).
      if (r?.sugerencia?.texto) setSugerencia(r.sugerencia);
      toast(t(`cobranzas.ok_${estado}`, { cliente: c.cliente }));
      if (!r?.sugerencia?.texto) onHecho();
    } catch {
      toast(t("cobranzas.err"));
    }
  };

  const est = c.gestion.estado;

  return (
    <div className="border-b border-linea/60 last:border-0">
      {/* div en vez de button: "ver cuenta" necesita ser un botón real y
          anidado, y HTML no permite <button> dentro de <button>. */}
      <div role="button" tabIndex={0} onClick={onAbrir}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onAbrir(); } }}
        className="flex w-full cursor-pointer items-center gap-3 px-4 py-3 text-left hover:bg-papel-hondo/40">
        <span className="plata w-5 shrink-0 text-sm font-semibold text-tinta-suave">{pos}</span>
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-1.5">
            <span className="block text-base font-semibold">{c.cliente}</span>
            {onNavegar && (
              <button
                onClick={(e) => { e.stopPropagation(); onNavegar("cuentas", `cliente-${c.id}`); }}
                className="shrink-0 text-xs font-semibold text-hielo hover:underline"
              >
                {t("cobranzas.ver_cuenta")}
              </button>
            )}
          </span>
          {/* el par que produce el orden, dicho como lo diría una persona */}
          <span className="block text-sm text-tinta-suave">
            {t("cobranzas.fuera_de_lo_suyo", {
              dias: num(c.exceso_dias), prom: num(c.promedio_pago_dias),
            })}
            {/* al dueño le importa además quién la está trabajando: sale del
                actor que quedó auditado al registrar la gestión. */}
            {esDueno && c.gestion.actor && (
              <span className="text-tinta-suave/80">
                {" · "}{t("cobranzas.la_trabaja", { quien: c.gestion.actor })}
              </span>
            )}
          </span>
        </span>
        <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${ESTADO_CLS[est]}`}>
          {t(`cobranzas.estado_${est}`)}
        </span>
        <span className="plata w-32 shrink-0 text-right text-base font-medium">{peso(c.saldo)}</span>
      </div>

      {abierto && (
        <div className="border-t border-linea/60 bg-papel-hondo/30 px-4 py-4">
          {prop === null && <Cargando />}
          {prop === false && <p className="text-sm text-rojo">{t("cobranzas.err")}</p>}
          {prop && (
            <div className="space-y-3">
              <div className="flex items-start gap-2.5">
                <AngelaMark size={26} />
                <p className="text-sm leading-snug text-tinta">
                  {t("cobranzas.propone", {
                    cliente: c.cliente, saldo: peso(c.saldo), dias: num(c.dias_sin_pagar),
                  })}
                </p>
              </div>

              {/* el mensaje es EDITABLE antes de mandarse: el dueño conoce al cliente */}
              {editando ? (
                <textarea value={texto} onChange={(e) => setTexto(e.target.value)} rows={5}
                  className="w-full rounded-xl border border-linea bg-crema px-3.5 py-2.5
                             text-sm leading-snug text-tinta" />
              ) : (
                <p className="whitespace-pre-line rounded-xl border border-linea bg-crema px-3.5 py-2.5
                              text-sm leading-snug text-tinta">{texto}</p>
              )}

              <div className="flex flex-wrap gap-2">
                <button onClick={() => registrar("recordado")} disabled={enviando}
                  className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2
                             text-sm font-semibold text-crema disabled:opacity-50">
                  <Send size={14} /> {t("cobranzas.mandar")}
                </button>
                <button onClick={() => setEditando((v) => !v)}
                  className="inline-flex items-center gap-1.5 rounded-full border border-linea bg-crema
                             px-4 py-2 text-sm font-semibold text-tinta-suave">
                  <Pencil size={14} /> {t(editando ? "cobranzas.listo_editar" : "cobranzas.editar")}
                </button>
                <button onClick={() => onPreguntar?.(t("cobranzas.otro_tono_prompt", { cliente: c.cliente }))}
                  className="rounded-full border border-linea bg-crema px-4 py-2 text-sm
                             font-semibold text-tinta-suave">
                  {t("cobranzas.otro_tono")}
                </button>
              </div>

              {/* el seguimiento: qué pasó después */}
              <div className="flex flex-wrap items-center gap-2 border-t border-linea pt-3">
                <span className="text-xs uppercase tracking-wide text-tinta-suave">
                  {t("cobranzas.que_paso")}
                </span>
                <Chip icon={Clock} onClick={() => {
                  const f = window.prompt(t("cobranzas.promesa_pregunta"));
                  if (f) registrar("promesa", { promesa_fecha: f });
                }}>{t("cobranzas.estado_promesa")}</Chip>
                <Chip icon={Check} onClick={() => registrar("pagado")}>
                  {t("cobranzas.estado_pagado")}
                </Chip>
                <Chip icon={X} onClick={() => registrar("sin_respuesta")}>
                  {t("cobranzas.estado_sin_respuesta")}
                </Chip>
              {/* Proponer → aprobar, aplicado a los papeles: recién gestionada
                  la cobranza, lo que sigue es mandarle el estado de cuenta.
                  Se OFRECE; el papel no se genera solo. */}
              {sugerencia && (
                <div className="mt-2 flex flex-wrap items-center gap-2 rounded-xl border border-violeta/25 bg-violeta/[0.05] px-3 py-2">
                  <AngelaMark size={16} />
                  <span className="min-w-0 flex-1 text-sm text-tinta">{sugerencia.texto}</span>
                  <button onClick={() => { onNavegar?.("documentos", sugerencia.pedido); setSugerencia(null); onHecho(); }}
                    className="rounded-full bg-violeta px-3.5 py-1.5 text-sm font-semibold text-crema">
                    {t("cobranzas.sug_si")}
                  </button>
                  <button onClick={() => { setSugerencia(null); onHecho(); }}
                    className="rounded-full border border-linea px-3.5 py-1.5 text-sm font-semibold text-tinta-suave hover:text-tinta">
                    {t("cobranzas.sug_no")}
                  </button>
                </div>
              )}
              </div>

              {c.gestion.promesa_fecha && (
                <p className="text-sm text-oro-tinta">
                  {t("cobranzas.prometio", { fecha: fmtFecha(c.gestion.promesa_fecha) })}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Chip({ icon: Icon, onClick, children }) {
  return (
    <button onClick={onClick}
      className="inline-flex items-center gap-1.5 rounded-full border border-linea bg-crema px-3 py-1.5
                 text-sm font-medium text-tinta-suave hover:text-tinta">
      <Icon size={13} /> {children}
    </button>
  );
}

function Tile({ valor, lk, tono, nota }) {
  const t = useT();
  return (
    <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-3.5 sombra-papel">
      <p className={`plata text-xl font-medium leading-none ${tono}`}>{valor}</p>
      <p className="mt-1 text-xs text-tinta-suave">{t(lk)}</p>
      {nota && <p className="mt-0.5 text-xs font-semibold text-rojo">{nota}</p>}
    </div>
  );
}

function Bloque({ icon: Icon, titulo, falta }) {
  const t = useT();
  return (
    <div className="rounded-[var(--radius-card)] border border-dashed border-linea bg-papel-hondo/40 p-5">
      <div className="flex items-center gap-2 text-tinta-suave">
        <Lock size={15} />
        <Icon size={16} />
      </div>
      <p className="mt-2 font-display text-base font-bold leading-tight">{titulo}</p>
      <p className="mt-1 text-sm text-tinta-suave">{t("cobranzas.falta", { que: falta })}</p>
    </div>
  );
}

import { useEffect, useMemo, useState } from "react";
import {
  ShieldCheck, Search, ChevronDown, Undo2, Lock, HandCoins, Boxes, Database,
  KeyRound, UserCircle, MessageCircle, Wrench, CircleUser, Bot, X, Link2,
} from "lucide-react";
import AngelaSays from "../../components/AngelaSays";
import Cargando from "../../components/Cargando";
import { api } from "../../lib/api";
import { peso, num } from "../../lib/format";
import { fechaRelativa } from "../../components/ActividadFeed";
import { toast } from "../../lib/toastStore";
import { useT, useLang } from "../../lib/i18n";

// BLOQUE F · EL REGISTRO. Quién decidió qué, cuándo, y qué pasó después.
//
// Nada de esto es información nueva: PolPilot viene auditando cada acción desde
// el primer día (core/audit.py), y todos los bloques escriben en el mismo riel.
// Lo que faltaba era poder LEERLO. Esta pantalla es la lectura.
//
// Por qué importa más que una feature: un dueño de PyME no le da autonomía a un
// software porque el software se lo pida bien. Se la da cuando puede auditar lo
// que hizo. El registro no es un extra de compliance — es la condición para que
// Ángela pueda hacer más el mes que viene.
//
// Todos los números salen del evento tal como quedó guardado. Si un monto no se
// escribió cuando pasó, acá no aparece: un registro que estima no es un registro.

const ICONO_CLASE = {
  plata: { Icon: HandCoins, tono: "text-salvia", bg: "bg-salvia/12" },
  stock: { Icon: Boxes, tono: "text-hielo", bg: "bg-hielo/12" },
  datos: { Icon: Database, tono: "text-violeta", bg: "bg-violeta/10" },
  permisos: { Icon: KeyRound, tono: "text-oro-tinta", bg: "bg-oro/15" },
  perfil: { Icon: UserCircle, tono: "text-tinta-suave", bg: "bg-papel-hondo" },
  consulta: { Icon: MessageCircle, tono: "text-tinta-suave", bg: "bg-papel-hondo" },
  tecnico: { Icon: Wrench, tono: "text-tinta-suave", bg: "bg-papel-hondo" },
  otros: { Icon: Wrench, tono: "text-tinta-suave", bg: "bg-papel-hondo" },
};
// El orden de los chips: primero lo que se defiende ante alguien.
const ORDEN_CLASES = ["plata", "stock", "datos", "permisos", "perfil", "consulta"];

export default function Auditoria() {
  const t = useT();
  const lang = useLang();
  const [d, setD] = useState(null);          // null = cargando, false = error
  const [aut, setAut] = useState(null);
  const [clase, setClase] = useState(null);
  const [actor, setActor] = useState("");
  const [q, setQ] = useState("");
  const [sujeto, setSujeto] = useState(null); // hilo abierto
  const [hilo, setHilo] = useState(null);     // { sujeto, eventos } | null

  const recargar = () =>
    api.auditoria({ clase, actor, q }).then(setD).catch(() => setD(false));

  // El registro se repide al cambiar el filtro; el idioma también, porque los
  // textos vienen traducidos del backend (mismo criterio que el resto del P31).
  useEffect(() => { setD(null); recargar(); }, [clase, actor, q, lang]);
  useEffect(() => { api.autonomia().then(setAut).catch(() => setAut(false)); }, [lang]);
  // El hilo abierto también: si no, al cambiar de idioma la pantalla queda
  // mitad en uno y mitad en el otro (P31 — el bug bilingüe que ya cazamos una vez).
  useEffect(() => {
    if (!sujeto) { setHilo(null); return; }
    api.auditoriaHilo(sujeto).then(setHilo).catch(() => { setSujeto(null); toast(t("audit.error")); });
  }, [sujeto, lang]);

  const r = d?.resumen;
  const filtrando = !!(clase || actor || q);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-2xl font-bold">{t("audit.titulo")}</h1>
        <p className="mt-1 text-[0.9rem] text-tinta-suave">{t("audit.subtitulo")}</p>
      </header>

      <AngelaSays>{t("audit.angela")}</AngelaSays>

      {d === false && <p className="text-[0.9rem] text-rojo">{t("audit.error")}</p>}

      {/* LA FRANJA DE CONFIANZA. El tercer número es el que importa: de todo lo
          que tocó plata, stock o permisos, cuánto se ejecutó sin un sí humano.
          Tiene que decir 0, y tiene que poder verificarse acá abajo. */}
      {r && (
        <div className="grid gap-3 sm:grid-cols-3">
          <Tile valor={num(r.total)} label={t("audit.tile_total")} tono="text-tinta" />
          <Tile valor={num(r.aprobadas)} label={t("audit.tile_aprobadas")} tono="text-salvia" />
          <Tile
            valor={num(r.sensibles_sin_aprobacion)}
            label={t("audit.tile_sin_ok", { n: num(r.sensibles) })}
            tono={r.sensibles_sin_aprobacion ? "text-rojo" : "text-salvia"}
            icono={r.sensibles_sin_aprobacion ? null : ShieldCheck}
          />
        </div>
      )}

      {/* QUÉ PUEDE HACER ÁNGELA SOLA — la perilla, con los candados a la vista. */}
      {aut && <PanelAutonomia aut={aut} onCambio={(x) => { setAut(x); recargar(); }} />}

      {/* --- filtros ------------------------------------------------------- */}
      <div className="space-y-2.5">
        <div className="flex flex-wrap gap-1.5">
          {ORDEN_CLASES.filter((c) => (r?.por_clase?.[c] || 0) > 0).map((c) => {
            const { Icon } = ICONO_CLASE[c];
            const on = clase === c;
            return (
              <button key={c} onClick={() => setClase(on ? null : c)}
                className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[0.78rem] font-semibold transition-colors ${
                  on ? "border-violeta bg-violeta/[0.06] text-violeta"
                     : "border-linea text-tinta-suave hover:text-tinta"}`}>
                <Icon size={12} /> {t(`audit.clase_${c}`)}
                <span className="text-tinta-suave/70">{num(r.por_clase[c])}</span>
              </button>
            );
          })}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="flex items-center gap-2 rounded-full border border-linea bg-crema px-3 py-1.5">
            <Search size={13} className="text-tinta-suave" />
            <input value={q} onChange={(e) => setQ(e.target.value)}
              placeholder={t("audit.buscar")} aria-label={t("audit.buscar")}
              className="w-52 bg-transparent text-[0.82rem] text-tinta outline-none" />
          </label>
          {(r?.actores || []).length > 1 && (
            <select value={actor} onChange={(e) => setActor(e.target.value)}
              aria-label={t("audit.quien")}
              className="rounded-full border border-linea bg-crema px-3 py-1.5 text-[0.82rem] text-tinta">
              <option value="">{t("audit.todos")}</option>
              {r.actores.map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
          )}
          {filtrando && (
            <button onClick={() => { setClase(null); setActor(""); setQ(""); }}
              className="inline-flex items-center gap-1 text-[0.8rem] font-semibold text-tinta-suave hover:text-tinta">
              <X size={12} /> {t("audit.limpiar")}
            </button>
          )}
        </div>
      </div>

      {/* --- el registro ---------------------------------------------------- */}
      {d === null && <Cargando />}
      {d && (
        <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
          <div className="flex items-baseline justify-between gap-3 border-b border-linea px-4 py-3">
            <p className="font-display text-[1.05rem] font-bold leading-tight">
              {t("audit.lista_titulo")}
            </p>
            <p className="text-[0.78rem] text-tinta-suave">
              {t("audit.mostrando", { n: num(d.mostrados), total: num(d.total_filtrado) })}
              {/* lo que se deja fuera, DICHO: un registro que esconde filas en
                  silencio deja de servir para lo único que sirve. */}
              {!clase && r?.sin_efecto_ocultos > 0 && (
                <> · {t("audit.ocultos", { n: num(r.sin_efecto_ocultos) })}</>
              )}
            </p>
          </div>
          {d.eventos.length === 0 ? (
            <p className="px-4 py-8 text-center text-[0.88rem] text-tinta-suave">
              {t("audit.sin_resultados")}
            </p>
          ) : (
            <Dias eventos={d.eventos} hoyISO={r?.hoy} t={t} onHilo={setSujeto} />
          )}
        </div>
      )}

      {hilo && <Hilo hilo={hilo} hoyISO={r?.hoy} t={t} onCerrar={() => setSujeto(null)} />}

      <p className="rounded-[var(--radius-card)] border border-dashed border-linea bg-papel-hondo/40 p-4
                    text-[0.82rem] leading-snug text-tinta-suave">
        {t("audit.nota_pie")}
      </p>
    </div>
  );
}

// La etiqueta del día. `fechaRelativa` (la del feed del Home) colapsa a "hoy"
// todo lo que no sea pasado, porque ese feed nunca muestra eventos posteriores
// a la fecha congelada del tenant. Acá sí los hay: el registro es TODO, sin
// recortes de fecha. Un registro donde seis días distintos dicen "hoy" no es un
// registro — así que fuera de la ventana relativa se muestra la fecha, seca.
function etiquetaDia(dia, hoyISO, t) {
  if (!dia) return "";
  if (hoyISO && dia > hoyISO) return dia;   // posterior a la fecha del tenant
  return fechaRelativa(dia, hoyISO, t);
}

// Agrupado por día, como el feed del Home: un registro sin días es una lista.
function Dias({ eventos, hoyISO, t, onHilo }) {
  const grupos = useMemo(() => {
    const g = [];
    for (const e of eventos) {
      let x = g.find((y) => y.dia === e.dia);
      if (!x) { x = { dia: e.dia, items: [] }; g.push(x); }
      x.items.push(e);
    }
    return g;
  }, [eventos]);

  return grupos.map((g) => (
    <div key={g.dia}>
      <p className="border-b border-linea/60 bg-papel-hondo/40 px-4 py-1.5 text-[0.7rem]
                    font-semibold uppercase tracking-[0.12em] text-tinta-suave">
        {etiquetaDia(g.dia, hoyISO, t)}
      </p>
      {g.items.map((e) => <FilaAudit key={e.id} e={e} t={t} onHilo={onHilo} />)}
    </div>
  ));
}

function FilaAudit({ e, t, onHilo }) {
  const [abierto, setAbierto] = useState(false);
  const { Icon, tono, bg } = ICONO_CLASE[e.clase] || ICONO_CLASE.otros;
  return (
    <div className="border-b border-linea/60 last:border-0">
      <button onClick={() => setAbierto((v) => !v)}
        className="flex w-full items-start gap-3 px-4 py-2.5 text-left hover:bg-papel-hondo/40">
        <span className={`mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full ${bg}`}>
          <Icon size={14} className={tono} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-[0.9rem] leading-snug text-tinta">
            {e.texto}
            {e.sujeto && <span className="text-tinta-suave"> · {e.sujeto}</span>}
          </span>
          {/* QUIÉN PUSO EL SÍ. Es la línea entera del bloque F: sin esto, el
              registro dice qué pasó pero no que alguien lo decidió. */}
          <span className="mt-0.5 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[0.76rem]">
            <Gate e={e} t={t} />
            {e.impacto != null && (
              <span className="plata font-medium text-tinta">{peso(e.impacto)}</span>
            )}
            {e.reversible && (
              <span className="inline-flex items-center gap-1 text-salvia">
                <Undo2 size={11} /> {t("audit.reversible")}
              </span>
            )}
          </span>
        </span>
        <span className="shrink-0 pt-0.5 text-[0.74rem] text-tinta-suave">
          {(e.cuando || "").slice(11, 16)}
        </span>
        <ChevronDown size={15}
          className={`mt-0.5 shrink-0 text-tinta-suave transition-transform ${abierto ? "rotate-180" : ""}`} />
      </button>

      {abierto && (
        <div className="space-y-2 border-t border-linea/60 bg-papel-hondo/30 px-4 py-3 pl-14">
          <p className="text-[0.74rem] uppercase tracking-wide text-tinta-suave">
            {t("audit.det_cuando")} <span className="normal-case text-tinta">{e.cuando}</span>
          </p>
          <Lado titulo={t("audit.det_antes")} v={e.antes} vacio={t("audit.det_nada")} />
          <Lado titulo={t("audit.det_despues")} v={e.despues} vacio={t("audit.det_nada")} />
          {e.en_hilo > 1 && (
            <button onClick={() => onHilo(e.sujeto)}
              className="inline-flex items-center gap-1.5 rounded-full border border-linea bg-crema
                         px-3 py-1.5 text-[0.8rem] font-semibold text-tinta-suave hover:text-tinta">
              <Link2 size={12} /> {t("audit.ver_hilo", { n: num(e.en_hilo), sujeto: e.sujeto })}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// El sello de cómo se ejecutó. "aprobacion" lleva NOMBRE: es lo que se defiende
// ante un contador, un socio o uno mismo dentro de seis meses.
function Gate({ e, t }) {
  if (e.gate === "aprobacion")
    return (
      <span className="inline-flex items-center gap-1 text-salvia">
        <ShieldCheck size={11} /> {t("audit.gate_aprobo", { quien: e.aprobado_por })}
      </span>
    );
  if (e.gate === "propia")
    return (
      <span className="inline-flex items-center gap-1 text-tinta-suave">
        <CircleUser size={11} /> {t("audit.gate_propia", { quien: e.actor })}
      </span>
    );
  if (e.gate === "sistema")
    return (
      <span className="inline-flex items-center gap-1 text-hielo">
        <Bot size={11} /> {t("audit.gate_sistema")}
      </span>
    );
  // preguntarle algo a Ángela no es una acción suya: no tocó nada
  if (e.gate === "sin_efecto")
    return (
      <span className="inline-flex items-center gap-1 text-tinta-suave">
        <MessageCircle size={11} /> {t("audit.gate_sin_efecto")}
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1 text-oro-tinta">
      <Wrench size={11} /> {t("audit.gate_desconocido", { quien: e.actor })}
    </span>
  );
}

function Lado({ titulo, v, vacio }) {
  const pares = v && typeof v === "object" ? Object.entries(v) : [];
  return (
    <div className="text-[0.8rem]">
      <span className="text-tinta-suave">{titulo}: </span>
      {pares.length === 0 ? (
        <span className="text-tinta-suave/70">{vacio}</span>
      ) : (
        <span className="text-tinta">
          {pares.map(([k, val], i) => (
            <span key={k}>
              {i > 0 && " · "}
              <span className="text-tinta-suave">{k.replace(/_/g, " ")}: </span>
              {typeof val === "object" ? JSON.stringify(val) : String(val)}
            </span>
          ))}
        </span>
      )}
    </div>
  );
}

// EL HILO — "y después qué pasó", de corrido. La misma gestión leída como una
// historia: se mandó el recordatorio, prometió el viernes, pagó.
function Hilo({ hilo, hoyISO, t, onCerrar }) {
  return (
    <div className="rounded-[var(--radius-card)] border border-violeta/30 bg-crema p-4 sombra-papel">
      <div className="mb-3 flex items-center justify-between gap-3">
        <p className="font-display text-[1.02rem] font-bold leading-tight">
          {t("audit.hilo_titulo", { sujeto: hilo.sujeto })}
        </p>
        <button onClick={onCerrar} className="text-tinta-suave hover:text-tinta"><X size={16} /></button>
      </div>
      <ol className="space-y-2.5 border-l-2 border-linea pl-4">
        {hilo.eventos.map((e) => (
          <li key={e.id} className="relative">
            <span className="absolute -left-[1.42rem] top-1.5 h-2 w-2 rounded-full bg-violeta" />
            <p className="text-[0.88rem] leading-snug text-tinta">{e.texto}</p>
            <p className="text-[0.76rem] text-tinta-suave">
              {etiquetaDia(e.dia, hoyISO, t)} · {e.actor}
              {e.impacto != null && <span className="plata"> · {peso(e.impacto)}</span>}
            </p>
          </li>
        ))}
      </ol>
    </div>
  );
}

// LA PERILLA. Tres clases con candado y el porqué escrito; una sola graduable.
// El candado no es un default conservador que mañana movemos: es la promesa.
function PanelAutonomia({ aut, onCambio }) {
  const t = useT();
  const [abierto, setAbierto] = useState(false);
  const [guardando, setGuardando] = useState(null);

  const cambiar = async (clase, nivel) => {
    setGuardando(clase);
    try {
      await api.autonomiaSet(clase, nivel);
      onCambio(await api.autonomia());
      toast(t("audit.aut_guardado"));
    } catch {
      toast(t("audit.error"));
    } finally { setGuardando(null); }
  };

  return (
    <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
      <button onClick={() => setAbierto((v) => !v)}
        className="flex w-full items-center gap-3 text-left">
        <ShieldCheck size={17} className="shrink-0 text-violeta" />
        <span className="min-w-0 flex-1">
          <span className="block font-display text-[1.02rem] font-bold leading-tight">
            {t("audit.aut_titulo")}
          </span>
          <span className="block text-[0.82rem] text-tinta-suave">{t("audit.aut_sub")}</span>
        </span>
        <ChevronDown size={16} className={`shrink-0 text-tinta-suave transition-transform ${abierto ? "rotate-180" : ""}`} />
      </button>

      {abierto && (
        <div className="mt-3.5 space-y-3 border-t border-linea pt-3.5">
          {aut.clases.map((c) => (
            <div key={c.clase} className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <p className="flex items-center gap-1.5 text-[0.9rem] font-semibold text-tinta">
                  {!c.graduable && <Lock size={12} className="shrink-0 text-tinta-suave" />}
                  {c.label}
                </p>
                {c.motivo && <p className="text-[0.8rem] leading-snug text-tinta-suave">{c.motivo}</p>}
              </div>
              {c.graduable ? (
                <div className="flex shrink-0 gap-1.5">
                  {aut.niveles.map((n) => (
                    <button key={n.id} disabled={guardando === c.clase}
                      onClick={() => c.nivel !== n.id && cambiar(c.clase, n.id)}
                      title={n.detalle}
                      className={`rounded-full border px-3 py-1.5 text-[0.78rem] font-semibold transition-colors disabled:opacity-50 ${
                        c.nivel === n.id ? "border-violeta bg-violeta text-crema"
                                         : "border-linea bg-crema text-tinta-suave hover:text-tinta"}`}>
                      {n.label}
                    </button>
                  ))}
                </div>
              ) : (
                <span className="shrink-0 rounded-full bg-papel-hondo px-3 py-1.5 text-[0.78rem]
                                 font-semibold text-tinta-suave">{c.nivel_label}</span>
              )}
            </div>
          ))}

          {/* LO QUE YA HACE SOLA, dicho de frente. Esconderlo sería exactamente
              el tipo de cosa que este registro existe para no hacer. */}
          <div className="flex items-start gap-2 rounded-xl border border-hielo/25 bg-hielo/[0.05] px-3 py-2.5">
            <Bot size={14} className="mt-0.5 shrink-0 text-hielo" />
            <p className="text-[0.82rem] leading-snug text-tinta">{aut.ya_hace_sola.texto}</p>
          </div>
          <p className="text-[0.8rem] leading-snug text-tinta-suave">{aut.proximo_paso}</p>
        </div>
      )}
    </div>
  );
}

function Tile({ valor, label, tono, icono: Icon }) {
  return (
    <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-3.5 sombra-papel">
      <p className={`plata flex items-center gap-1.5 text-xl font-medium leading-none ${tono}`}>
        {Icon && <Icon size={17} />}{valor}
      </p>
      <p className="mt-1 text-[0.76rem] leading-snug text-tinta-suave">{label}</p>
    </div>
  );
}

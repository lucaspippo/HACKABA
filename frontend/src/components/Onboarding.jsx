import { useEffect, useState } from "react";
import { MapPin, Truck, ClipboardList, BookOpen, Users, ChevronDown, ArrowRight,
         MessageCircle } from "lucide-react";
import AngelaMark from "./AngelaMark";
import { antiguedadTexto } from "./BadgeNuevo";
import { api } from "../lib/api";
import { useT, useLang, tRol, tDato } from "../lib/i18n";

// P·onboarding — DONDE ÁNGELA LE ENSEÑA EL LABURO AL QUE RECIÉN ENTRÓ.
//
// El dolor real: el que entra tarda semanas en ser útil porque lo que hay que
// saber (dónde va cada cosa, cada cuánto llega cada proveedor, qué se hace con
// una factura, qué reglas puso el dueño) vive en la cabeza del que lleva años.
// Y la rotación en trabajo físico es alta: ese costo se paga seguido.
//
// Esta pantalla no es un tutorial de PolPilot: es el manual DE ESTE NEGOCIO.
// Cada tema muestra el DATO REAL (las 21 ubicaciones que existen, los 6
// proveedores con sus días, las reglas que le aplican a esta persona) y, al
// lado, las preguntas para que se lo cuente Ángela en su idioma. Las preguntas
// se arman con nombres REALES del dataset — así ninguna sugerencia lleva a un
// "eso no lo tengo".
//
// Todo sale de /api/onboarding, que ya viene recortado por las features de
// quien pregunta. Acá no se decide qué puede ver nadie: se muestra lo que llegó.

const ICONO = { ubicaciones: MapPin, reposicion: Truck, procesos: ClipboardList,
                reglas: BookOpen, contactos: Users };

// El orden de los procesos en pantalla = el orden en que se los cruza en el día.
const PROC_ORDEN = ["recepcion", "factura", "faltante", "conteo", "ubicar", "preguntar"];

function Chip({ texto, onPreguntar }) {
  return (
    <button
      onClick={() => onPreguntar?.(texto)}
      className="flex w-full items-center gap-2 rounded-xl border border-linea bg-crema px-3 py-2 text-left transition-colors hover:border-violeta/40 active:bg-papel-hondo/40"
    >
      <MessageCircle size={14} className="shrink-0 text-violeta" />
      <span className="min-w-0 flex-1 text-[0.85rem] leading-snug text-tinta">{texto}</span>
      <ArrowRight size={14} className="shrink-0 text-tinta-suave" />
    </button>
  );
}

function Tema({ id, titulo, sub, preguntas, children, abierto, onToggle, onPreguntar }) {
  const t = useT();
  const Icon = ICONO[id] || ClipboardList;
  const [datos, setDatos] = useState(false);
  return (
    <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
      <button onClick={onToggle} className="flex w-full items-center gap-3 px-4 py-3 text-left">
        <Icon size={18} className="shrink-0 text-violeta" />
        <span className="min-w-0 flex-1">
          <span className="block text-[0.94rem] font-semibold leading-snug text-tinta">{titulo}</span>
          {sub && <span className="block text-[0.78rem] leading-snug text-tinta-suave">{sub}</span>}
        </span>
        <ChevronDown size={16} className={`shrink-0 text-tinta-suave transition-transform ${abierto ? "rotate-180" : ""}`} />
      </button>
      {abierto && (
        <div className="space-y-2 border-t border-linea px-4 py-3">
          {preguntas.map((q) => <Chip key={q} texto={q} onPreguntar={onPreguntar} />)}
          {children && (
            <>
              <button onClick={() => setDatos((v) => !v)}
                className="text-[0.78rem] font-semibold text-tinta-suave underline decoration-linea underline-offset-2 hover:text-tinta">
                {datos ? t("onb.ocultar_datos") : t("onb.ver_datos")}
              </button>
              {datos && <div className="pt-1">{children}</div>}
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default function Onboarding({ onPreguntar }) {
  const t = useT();
  const lang = useLang();
  const [g, setG] = useState(null);
  const [abierto, setAbierto] = useState("ubicaciones");
  useEffect(() => { api.onboarding().then(setG).catch(() => setG(false)); }, []);

  if (!g) return null;   // sin guía (o error): la vista de trabajo queda igual que siempre

  const { persona, ubicaciones, reposicion, procesos, reglas, contactos } = g;
  const ant = antiguedadTexto(persona?.antiguedad);
  const preguntar = (texto) => onPreguntar?.(texto);

  // Las preguntas de ejemplo se arman con entidades REALES del dataset: el
  // producto que de verdad está en la cámara de frío, el proveedor que de
  // verdad repone en 3 días. Una sugerencia que Ángela no pueda contestar es
  // peor que no sugerir nada.
  const ejemploFrio = (ubicaciones?.ubicaciones || [])
    .find((u) => (ubicaciones.frio || []).includes(u.ubicacion))?.ejemplos?.[0];
  const ejemploSeco = (ubicaciones?.ubicaciones || [])
    .find((u) => !(ubicaciones.frio || []).includes(u.ubicacion))?.ejemplos?.[0];
  const provMasRapido = reposicion?.proveedores?.[0]?.proveedor;
  const provs = reposicion?.proveedores || [];

  const temas = [];
  if (ubicaciones?.hay_datos) {
    temas.push({
      id: "ubicaciones",
      titulo: t("onb.t_ubicaciones"),
      sub: t("onb.t_ubicaciones_sub", { ubicaciones: ubicaciones.total, lotes: ubicaciones.lotes,
                                        frio: (ubicaciones.frio || []).length }),
      preguntas: [
        ejemploFrio && t("onb.q_donde", { producto: ejemploFrio }),
        t("onb.q_frio"),
        t("onb.q_donde_dejo"),
        t("onb.q_vence_pronto"),
      ].filter(Boolean),
      contenido: (
        <ul className="divide-y divide-linea/70 text-[0.84rem]">
          {ubicaciones.ubicaciones.map((u) => (
            <li key={u.ubicacion} className="flex items-baseline justify-between gap-3 py-1.5">
              <span className="min-w-0 flex-1">
                <span className="block font-medium text-tinta">{u.ubicacion}</span>
                <span className="block truncate text-[0.76rem] text-tinta-suave">{u.ejemplos.join(" · ")}</span>
              </span>
              <span className="shrink-0 text-[0.76rem] text-tinta-suave">{t("onb.ubi_lotes", { n: u.lotes })}</span>
            </li>
          ))}
        </ul>
      ),
    });
  }
  if (reposicion?.hay_datos) {
    temas.push({
      id: "reposicion",
      titulo: t("onb.t_reposicion"),
      sub: t("onb.t_reposicion_sub", { n: provs.length, min: provs[0]?.dias_reposicion,
                                       max: provs[provs.length - 1]?.dias_reposicion }),
      preguntas: [
        provMasRapido && t("onb.q_cada_cuanto_prov", { proveedor: provMasRapido }),
        ejemploSeco && t("onb.q_cada_cuanto_prod", { producto: ejemploSeco }),
        t("onb.q_tarda_mas"),
      ].filter(Boolean),
      contenido: (
        <>
          <ul className="divide-y divide-linea/70 text-[0.84rem]">
            {provs.map((p) => (
              <li key={p.proveedor} className="flex items-baseline justify-between gap-3 py-1.5">
                <span className="min-w-0 flex-1">
                  <span className="block font-medium text-tinta">{p.proveedor}</span>
                  {p.nota && <span className="block text-[0.76rem] leading-snug text-tinta-suave">{p.nota}</span>}
                </span>
                <span className="shrink-0 text-[0.76rem] font-semibold text-tinta-suave">
                  {t("onb.rep_dias", { n: p.dias_reposicion })}
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-[0.76rem] text-tinta-suave">{t("onb.rep_default", { n: reposicion.dias_default })}</p>
        </>
      ),
    });
  }
  if (procesos?.length) {
    const orden = [...procesos].sort((a, b) => PROC_ORDEN.indexOf(a.id) - PROC_ORDEN.indexOf(b.id));
    temas.push({
      id: "procesos",
      titulo: t("onb.t_procesos"),
      sub: t("onb.t_procesos_sub", { n: orden.length }),
      preguntas: [t("onb.q_camion"), t("onb.q_factura"), t("onb.q_faltante"), t("onb.q_conteo")],
      contenido: (
        <div className="space-y-3">
          {orden.map((p) => (
            <div key={p.id}>
              <p className="text-[0.84rem] font-semibold text-tinta">{t(`onb.proc_${p.id}`)}</p>
              <ol className="mt-1 list-decimal space-y-0.5 pl-5 text-[0.82rem] leading-snug text-tinta-suave">
                {(lang === "en" ? p.pasos_en : p.pasos).map((paso, i) => <li key={i}>{paso}</li>)}
              </ol>
            </div>
          ))}
        </div>
      ),
    });
  }
  if (reglas?.length) {
    temas.push({
      id: "reglas",
      titulo: t("onb.t_reglas"),
      sub: t("onb.t_reglas_sub", { n: reglas.length }),
      preguntas: [t("onb.q_reglas"), t("onb.q_regla_frio"), t("onb.q_no_quebrar")],
      contenido: (
        <>
          <ul className="space-y-1.5 text-[0.84rem] leading-snug text-tinta">
            {reglas.map((r) => (
              <li key={r.id} className="flex gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-violeta/60" />
                <span>{lang === "en" && r.texto_en ? r.texto_en : r.texto}</span>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-[0.76rem] text-tinta-suave">{t("onb.reglas_pie")}</p>
        </>
      ),
    });
  }
  if (contactos?.length) {
    temas.push({
      id: "contactos",
      titulo: t("onb.t_contactos"),
      sub: t("onb.t_contactos_sub"),
      preguntas: [t("onb.q_aviso_falta"), t("onb.q_quien_aprueba")],
      contenido: (
        <ul className="divide-y divide-linea/70 text-[0.84rem]">
          {contactos.map((c) => (
            <li key={c.username} className="py-1.5">
              <span className="font-medium text-tinta">{c.nombre}</span>
              <span className="text-tinta-suave"> · {tRol(c.rol)}</span>
              <span className="block text-[0.76rem] leading-snug text-tinta-suave">{t(`onb.para_${c.para}`)}</span>
            </li>
          ))}
        </ul>
      ),
    });
  }

  return (
    <section className="space-y-3">
      {/* El título vive ACÁ y no en «Mi día»: mientras la guía carga, el bloque
          entero no existe — nunca un encabezado solo colgando (P32). */}
      <h2 className="font-display text-[1.05rem] font-bold">{t("onb.titulo")}</h2>

      {/* La bienvenida: quién sos, hace cuánto entraste y qué podés preguntar.
          El puesto y el referente salen de SU ficha, no de un texto genérico. */}
      <div className="rounded-[var(--radius-card)] border border-violeta/25 bg-violeta/[0.05] p-4">
        <div className="flex items-start gap-2.5">
          <AngelaMark size={30} estado="esperando" />
          <div className="min-w-0">
            <p className="font-display text-[1.02rem] font-bold leading-tight">
              {t("onb.saludo", { nombre: persona?.nombre, ant })}
            </p>
            <p className="mt-1 text-[0.85rem] leading-snug text-tinta-suave">{t("onb.intro")}</p>
            {persona?.puesto && (
              <p className="mt-1.5 text-[0.78rem] text-tinta-suave">
                {t("onb.puesto", {
                  sector: tDato(persona.puesto.sector, persona.puesto.sector_en),
                  turno: tDato(persona.puesto.turno, persona.puesto.turno_en) })}
                {persona.puesto.mentor && (
                  <> · {t("onb.mentor", { nombre: persona.puesto.mentor.nombre,
                                          rol: tRol(persona.puesto.mentor.rol) })}</>
                )}
              </p>
            )}
          </div>
        </div>
      </div>
      {/* Para escribir libre está la consulta rápida de «Mi día», que este
          empleado tiene igual que todos: acá no se duplica la misma caja. */}

      {temas.map((tm) => (
        <Tema key={tm.id} id={tm.id} titulo={tm.titulo} sub={tm.sub} preguntas={tm.preguntas}
          abierto={abierto === tm.id} onToggle={() => setAbierto(abierto === tm.id ? null : tm.id)}
          onPreguntar={preguntar}>
          {tm.contenido}
        </Tema>
      ))}
    </section>
  );
}

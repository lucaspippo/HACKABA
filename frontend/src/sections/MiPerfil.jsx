import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Camera, Pencil, Send, Clock, XCircle, Mic, MicOff, Globe, Target } from "lucide-react";
import AngelaMark from "../components/AngelaMark";
import LangSwitch from "../components/LangSwitch";
import { api } from "../lib/api";
import { useSession, authStore } from "../lib/auth";
import { equipoStore, useEquipo, ESTADO_LABEL } from "../lib/equipoStore";
import { useT, tRol, tDato } from "../lib/i18n";

// El perfil autoadministrado: Ángela te hace PREGUNTAS por bloques y con eso
// arma tu descripción real (y sugiere los módulos que te faltan con fundamento).
// Editar la propia descripción y foto es personalización de vista (sin aprobación).

// Las preguntas de Ángela. Se componen en UNA descripción con etiquetas fijas,
// así el backend no cambia y lo escrito se puede volver a separar en bloques.
// OJO: "etiqueta" es el marcador del FORMATO GUARDADO — lo que se escribe SIEMPRE
// se guarda con el marcador en castellano (es el dato, y `sugerir_modulos`
// matchea sobre él). `etiqueta_en` sólo existe para poder LEER la versión
// traducida que trae el seed (`descripcion_en`): mismo texto, marcador en
// inglés. Lo que se muestra como título son los keys lket/lkq/lkph con t().
export const BLOQUES = [
  { id: "funcion", etiqueta: "Mi función", etiqueta_en: "My role", lket: "miperfil.bloque_funcion_et", lkq: "miperfil.bloque_funcion_q", lkph: "miperfil.bloque_funcion_ph" },
  { id: "tareas", etiqueta: "Me encargo de", etiqueta_en: "I take care of", lket: "miperfil.bloque_tareas_et", lkq: "miperfil.bloque_tareas_q", lkph: "miperfil.bloque_tareas_ph" },
  { id: "mira", etiqueta: "Todos los días miro", etiqueta_en: "Every day I look at", lket: "miperfil.bloque_mira_et", lkq: "miperfil.bloque_mira_q", lkph: "miperfil.bloque_mira_ph" },
  { id: "decide", etiqueta: "Decido sobre", etiqueta_en: "I decide on", lket: "miperfil.bloque_decide_et", lkq: "miperfil.bloque_decide_q", lkph: "miperfil.bloque_decide_ph" },
];

// Todos los marcadores que se saben leer, en los dos idiomas.
const MARCADORES = BLOQUES.flatMap((b) => [b.etiqueta, b.etiqueta_en]);

/** ¿Este texto viene con el formato de bloques (en cualquiera de los dos
 *  idiomas)? Si no, es una descripción libre y se muestra de corrido. */
export function tieneBloques(texto) {
  return new RegExp(`(?:${MARCADORES.join("|")}):\\s*`).test(texto || "");
}

export function componerDescripcion(bloques) {
  return BLOQUES
    .filter((b) => (bloques[b.id] || "").trim())
    .map((b) => `${b.etiqueta}: ${bloques[b.id].trim().replace(/\.?$/, ".")}`)
    .join(" ");
}

export function partirDescripcion(texto) {
  const out = { funcion: "", tareas: "", mira: "", decide: "" };
  if (!texto) return out;
  // si el texto tiene las etiquetas, lo separamos; si no, todo va a "función"
  if (!tieneBloques(texto)) return { ...out, funcion: texto };
  for (const b of BLOQUES) {
    const m = texto.match(new RegExp(
      `(?:${b.etiqueta}|${b.etiqueta_en}):\\s*([^]*?)(?=(?:${MARCADORES.join("|")}):|$)`));
    if (m) out[b.id] = m[1].trim().replace(/\.$/, "");
  }
  return out;
}

export default function MiPerfil({ user }) {
  const t = useT();
  const session = useSession();
  const token = session?.token;
  const esMiPerfil = session?.usuario?.username === user?.username;

  // `descripcion` es SIEMPRE el castellano: es lo que se edita y lo que se
  // guarda. `descripcionEn` es la traducción del seed, sólo para mostrar. Al
  // reescribir el perfil, el backend deja de mandar la traducción (son sus
  // palabras) y las dos vistas muestran lo mismo.
  const [descripcion, setDescripcion] = useState(user?.descripcion || "");
  const [descripcionEn, setDescripcionEn] = useState(user?.descripcion_en || "");
  const [bloques, setBloques] = useState(() => partirDescripcion(user?.descripcion || ""));
  const [bloqueActivo, setBloqueActivo] = useState("funcion");
  const bloqueActivoRef = useRef("funcion");
  const [editando, setEditando] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [sugerencias, setSugerencias] = useState([]);
  const [solicitudes, setSolicitudes] = useState([]);
  const [pedibles, setPedibles] = useState([]);   // todo lo que PUEDE pedir
  const [pidiendo, setPidiendo] = useState(null); // módulo elegido, esperando el porqué
  const [porque, setPorque] = useState("");
  const [fotoVersion, setFotoVersion] = useState(0);
  const [tieneFoto, setTieneFoto] = useState(!!user?.foto);
  const [aviso, setAviso] = useState(null);
  const fileRef = useRef(null);

  // Dictado por voz (Web Speech API del navegador): el empleado le CUENTA su rol
  // y Ángela arma el perfil. Transcripción local, nada de audio al backend.
  const [grabando, setGrabando] = useState(false);
  const recRef = useRef(null);
  const SR = typeof window !== "undefined" && (window.SpeechRecognition || window.webkitSpeechRecognition);

  const toggleDictado = () => {
    if (grabando) {
      recRef.current?.stop();
      return;
    }
    const rec = new SR();
    rec.lang = "es-AR";
    rec.continuous = true;
    rec.interimResults = false;
    rec.onresult = (e) => {
      const texto = Array.from(e.results).slice(e.resultIndex).map((r) => r[0].transcript).join(" ");
      // lo dictado cae en el bloque que estás completando
      const id = bloqueActivoRef.current;
      setBloques((b) => ({ ...b, [id]: (b[id] ? b[id].trimEnd() + " " : "") + texto.trim() }));
    };
    rec.onend = () => setGrabando(false);
    rec.onerror = () => { setGrabando(false); setAviso(t("miperfil.voz_error")); };
    recRef.current = rec;
    setEditando(true);
    setGrabando(true);
    rec.start();
  };

  const cargar = () => {
    if (!user) return;
    api.perfil(user.username).then((p) => {
      setSugerencias(p.sugerencias || []);
      setSolicitudes(p.solicitudes || []);
      setPedibles(p.pedibles || []);
      setTieneFoto(!!p.foto);
      if (!editando) {
        setDescripcion(p.descripcion || "");
        setDescripcionEn(p.descripcion_en || "");
      }
    }).catch(() => {});
  };

  useEffect(() => {
    cargar();
    // Si el dueño aprobó algo desde la última visita, esto trae las features nuevas.
    authStore.refresh();
  }, [user?.username]);

  // Lo que me toca del tablero del equipo: match por nombre del responsable
  // (insensible a acentos — "Ramón"/"Ramon" son la misma persona).
  const equipo = useEquipo();
  const _norm = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
  const misObjetivos = (equipo.objetivos || []).filter((o) => _norm(o.responsable) === _norm(user?.nombre));
  const misRecordatorios = (equipo.recordatorios || []).filter((r) => _norm(r.responsable) === _norm(user?.nombre));

  if (!user) return null;

  // Lo que se MUESTRA: la traducción si la hay y la pantalla está en inglés; si
  // no, el castellano. Lo que se EDITA sigue siendo `descripcion` (el original).
  const vista = tDato(descripcion, descripcionEn);
  const bloquesVista = partirDescripcion(vista);

  const guardarDescripcion = async () => {
    const compuesta = componerDescripcion(bloques);
    if (!compuesta.trim() || !token) return;
    setGuardando(true);
    try {
      const r = await api.perfilDescripcion(user.username, token, compuesta);
      setDescripcion(compuesta);
      setSugerencias(r.sugerencias || []);
      setEditando(false);
      setAviso(r.sugerencias?.length
        ? t("miperfil.guardado_sugerencias")
        : t("miperfil.guardado"));
    } catch {
      setAviso(t("miperfil.guardar_error"));
    } finally {
      setGuardando(false);
    }
  };

  const subirFoto = (e) => {
    const file = e.target.files?.[0];
    if (!file || !token) return;
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        await api.perfilFoto(user.username, token, reader.result);
        setTieneFoto(true);
        setFotoVersion((v) => v + 1);
      } catch {
        setAviso(t("miperfil.foto_error"));
      }
    };
    reader.readAsDataURL(file);
  };

  // P39·1.2 — pedir acceso es del EMPLEADO: elige el módulo que necesita para
  // trabajar y escribe por qué. El pedido cae en «Solicitudes» del dueño (y le
  // suena la campanita); si lo aprueba, queda tildado en «Quién ve qué».
  const solicitarModulo = async (modulo, motivo = "") => {
    if (!token) return;
    try {
      await api.solicitar(token, [modulo], motivo);
      setAviso(t("miperfil.solicitud_enviada"));
      setPidiendo(null);
      setPorque("");
      cargar();
    } catch {
      setAviso(t("miperfil.solicitud_error"));
    }
  };

  const ESTADO = {
    pendiente: { icon: Clock, color: "text-oro", lk: "miperfil.estado_pendiente" },
    aprobada: { icon: CheckCircle2, color: "text-salvia", lk: "miperfil.estado_aprobada" },
    rechazada: { icon: XCircle, color: "text-rojo", lk: "miperfil.estado_rechazada" },
  };

  return (
    <div className="space-y-6">
      <header className="flex items-center gap-4">
        <div className="relative">
          {tieneFoto ? (
            <img
              src={`/api/perfil/${user.username}/foto?v=${fotoVersion}`}
              alt={user.nombre}
              className="h-14 w-14 rounded-full object-cover"
            />
          ) : (
            <span className="grid h-14 w-14 shrink-0 place-items-center rounded-full text-xl font-bold text-crema" style={{ background: user.color }}>
              {user.nombre[0]}
            </span>
          )}
          {esMiPerfil && (
            <>
              <button
                onClick={() => fileRef.current?.click()}
                title={t("miperfil.cambiar_foto")}
                className="absolute -bottom-1 -right-1 grid h-6 w-6 place-items-center rounded-full border border-linea bg-crema text-tinta-suave hover:text-tinta"
              >
                <Camera size={13} />
              </button>
              <input ref={fileRef} type="file" accept="image/png,image/jpeg" className="hidden" onChange={subirFoto} />
            </>
          )}
        </div>
        <div>
          <h1 className="font-display text-2xl font-bold leading-none">{user.nombre}</h1>
          <p className="mt-1 text-[0.9rem] text-tinta-suave">{tRol(user.rol)}</p>
        </div>
      </header>

      {aviso && (
        <p className="rounded-xl border border-oro/30 bg-oro/[0.07] px-3.5 py-2 text-[0.86rem] text-tinta">{aviso}</p>
      )}

      {/* Descripción editable (personalización de vista: sin aprobación, queda auditada) */}
      <section className="rounded-[var(--radius-card)] border border-linea bg-crema p-5 sombra-papel">
        <div className="flex items-center justify-between">
          <p className="text-[0.72rem] font-semibold uppercase tracking-[0.14em] text-tinta-suave">
            {t("miperfil.que_haces")}
          </p>
          {esMiPerfil && !editando && (
            <button onClick={() => setEditando(true)} className="inline-flex items-center gap-1 text-[0.8rem] font-semibold text-tinta">
              <Pencil size={13} /> {t("miperfil.editar")}
            </button>
          )}
        </div>
        {editando ? (
          <div className="mt-3 space-y-3">
            <div className="flex items-start gap-2.5">
              <AngelaMark size={24} />
              <p className="text-[0.86rem] leading-snug text-tinta-suave">
                {t("miperfil.intro_preguntas")}
              </p>
            </div>
            {BLOQUES.map((b) => (
              <div key={b.id}>
                <label htmlFor={`bloque-${b.id}`} className="mb-1 flex items-center gap-2 text-[0.84rem] font-semibold">
                  {t(b.lkq)}
                  {grabando && bloqueActivo === b.id && (
                    <span className="inline-flex items-center gap-1 text-[0.72rem] font-medium text-rojo"><Mic size={11} /> {t("miperfil.dictando_aca")}</span>
                  )}
                </label>
                <textarea
                  id={`bloque-${b.id}`}
                  value={bloques[b.id]}
                  onChange={(e) => setBloques((v) => ({ ...v, [b.id]: e.target.value }))}
                  onFocus={() => { setBloqueActivo(b.id); bloqueActivoRef.current = b.id; }}
                  rows={2}
                  className={`w-full rounded-xl border bg-papel p-3 text-[0.92rem] leading-relaxed outline-none focus:border-tinta/40 ${
                    grabando && bloqueActivo === b.id ? "border-rojo/40" : "border-linea"}`}
                  placeholder={t(b.lkph)}
                />
              </div>
            ))}
            <div className="flex flex-wrap items-center gap-2">
              <button onClick={guardarDescripcion} disabled={guardando} className="rounded-full bg-tinta px-4 py-1.5 text-[0.84rem] font-semibold text-crema disabled:opacity-50">
                {guardando ? t("miperfil.guardando") : t("miperfil.guardar")}
              </button>
              {SR && (
                <button onClick={toggleDictado}
                  className={`inline-flex items-center gap-1.5 rounded-full border px-4 py-1.5 text-[0.84rem] font-semibold ${
                    grabando ? "border-rojo bg-rojo/10 text-rojo animate-pulse" : "border-linea text-tinta-suave hover:text-tinta"}`}>
                  {grabando ? <><MicOff size={14} /> {t("miperfil.voz_parar")}</> : <><Mic size={14} /> {t("miperfil.voz_contar")}</>}
                </button>
              )}
              <button onClick={() => { recRef.current?.stop(); setEditando(false); setBloques(partirDescripcion(descripcion)); }} className="rounded-full border border-linea px-4 py-1.5 text-[0.84rem] font-semibold text-tinta-suave">
                {t("miperfil.cancelar")}
              </button>
              {grabando && <span className="text-[0.8rem] text-rojo">{t("miperfil.escuchando")}</span>}
            </div>
          </div>
        ) : vista && tieneBloques(vista) ? (
          <dl className="mt-2 space-y-2">
            {BLOQUES.filter((b) => bloquesVista[b.id]).map((b) => (
              <div key={b.id}>
                <dt className="text-[0.76rem] font-semibold text-tinta-suave">{t(b.lket)}</dt>
                <dd className="text-[0.92rem] leading-relaxed">{bloquesVista[b.id]}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="mt-2 text-[0.95rem] leading-relaxed text-tinta">{vista}</p>
        )}
      </section>

      {/* Lo mío en el tablero: objetivos y recordatorios donde YO soy responsable
          (match por nombre, insensible a acentos — el tablero completo vive en Equipo) */}
      {esMiPerfil && (misObjetivos.length > 0 || misRecordatorios.length > 0) && (
        <section>
          <h2 className="mb-3 flex items-center gap-2 font-display text-[1.1rem] font-bold">
            <Target size={18} className="text-tinta-suave" /> {t("miperfil.mio_titulo")}
          </h2>
          {misObjetivos.length > 0 && (
            <div className="space-y-2.5">
              {misObjetivos.map((o) => (
                <div key={o.id} className="flex items-center gap-3 rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
                  <div className="min-w-0 flex-1">
                    <p className="font-display text-[0.98rem] font-bold leading-tight">{t(o.nombre)}</p>
                    <p className="mt-0.5 text-[0.8rem] text-tinta-suave">{t(o.fecha)}</p>
                  </div>
                  <button
                    onClick={() => equipoStore.cicloEstado(o.id)}
                    className={`shrink-0 rounded-full px-3 py-1 text-[0.76rem] font-semibold ${
                      o.estado === "listo" ? "bg-salvia/15 text-salvia" : o.estado === "en_proceso" ? "bg-oro/15 text-oro-tinta" : "bg-papel-hondo text-tinta-suave"
                    }`}
                  >
                    {t(ESTADO_LABEL[o.estado])}
                  </button>
                </div>
              ))}
            </div>
          )}
          {misRecordatorios.length > 0 && (
            <div className="mt-2.5 overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema">
              {misRecordatorios.map((r) => (
                <button key={r.id} onClick={() => equipoStore.toggleRecordatorio(r.id)}
                  className="flex w-full items-center gap-3 border-b border-linea px-4 py-2.5 text-left last:border-0">
                  <span className={`grid h-5 w-5 shrink-0 place-items-center rounded-full border ${r.hecho ? "border-salvia bg-salvia text-crema" : "border-tinta-suave/40"}`}>
                    {r.hecho && <CheckCircle2 size={13} />}
                  </span>
                  <span className={`flex-1 text-[0.88rem] ${r.hecho ? "text-tinta-suave line-through" : "text-tinta"}`}>{t(r.texto)}</span>
                </button>
              ))}
            </div>
          )}
        </section>
      )}

      {/* P39·1.2 — PEDIR ACCESO: el canal del empleado hacia «Solicitudes» del
          dueño. Ángela sugiere lo que matchea con su descripción, pero el
          empleado puede pedir CUALQUIER módulo que le falte — él sabe qué
          necesita para trabajar. Siempre con el porqué en sus palabras; nada
          se habilita solo. */}
      {esMiPerfil && (sugerencias.length > 0 || pedibles.length > 0) && (
        <section>
          <div className="mb-1 flex items-center gap-2">
            <AngelaMark size={26} />
            <h2 className="font-display text-[1.1rem] font-bold">{t("miperfil.pedir_titulo")}</h2>
          </div>
          <p className="mb-3 text-[0.86rem] leading-snug text-tinta-suave">{t("miperfil.pedir_sub")}</p>

          {sugerencias.length > 0 && (
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {sugerencias.map((s) => (
                <div key={s.modulo} className="rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
                  <p className="font-display text-[0.98rem] font-bold">{s.label}</p>
                  <p className="mt-1 text-[0.84rem] leading-snug text-tinta-suave">{s.motivo}</p>
                  <button onClick={() => { setPidiendo(s); setPorque(""); }}
                    className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-tinta px-3.5 py-1.5 text-[0.82rem] font-semibold text-crema">
                    <Send size={13} /> {t("miperfil.solicitar")}
                  </button>
                </div>
              ))}
            </div>
          )}

          {pedibles.length > 0 && (
            <div className="mt-3">
              <p className="mb-2 text-[0.8rem] font-semibold uppercase tracking-wide text-tinta-suave">
                {sugerencias.length > 0 ? t("miperfil.pedir_otro") : t("miperfil.pedir_cual")}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {pedibles.map((m) => (
                  <button key={m.modulo} onClick={() => { setPidiendo(m); setPorque(""); }}
                    className={`rounded-full border px-3 py-1.5 text-[0.8rem] font-semibold transition-colors ${
                      pidiendo?.modulo === m.modulo
                        ? "border-tinta bg-tinta text-crema"
                        : "border-linea text-tinta-suave hover:border-tinta/40 hover:text-tinta"}`}>
                    {m.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {pidiendo && (
            <div className="mt-3 rounded-[var(--radius-card)] border border-tinta/20 bg-papel-hondo/40 p-4">
              <p className="text-[0.9rem] font-semibold text-tinta">
                {t("miperfil.pedir_para_que", { modulo: pidiendo.label })}
              </p>
              <textarea
                value={porque} onChange={(e) => setPorque(e.target.value)} rows={2} autoFocus
                placeholder={t("miperfil.pedir_ph")}
                className="mt-2 w-full rounded-xl border border-linea bg-crema p-3 text-[0.88rem] leading-snug outline-none focus:border-tinta/40"
              />
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <button onClick={() => solicitarModulo(pidiendo.modulo, porque)} disabled={!porque.trim()}
                  className="inline-flex items-center gap-1.5 rounded-full bg-tinta px-4 py-1.5 text-[0.84rem] font-semibold text-crema disabled:opacity-40">
                  <Send size={13} /> {t("miperfil.pedir_enviar")}
                </button>
                <button onClick={() => { setPidiendo(null); setPorque(""); }}
                  className="rounded-full border border-linea px-4 py-1.5 text-[0.84rem] font-semibold text-tinta-suave hover:text-tinta">
                  {t("miperfil.pedir_cancelar")}
                </button>
                <span className="text-[0.78rem] text-tinta-suave">{t("miperfil.pedir_nota")}</span>
              </div>
            </div>
          )}
        </section>
      )}

      {/* Mis solicitudes: estado + respuesta del dueño */}
      {esMiPerfil && solicitudes.length > 0 && (
        <section>
          <h2 className="mb-2 font-display text-[1.05rem] font-bold">{t("miperfil.tus_solicitudes")}</h2>
          <div className="space-y-2">
            {solicitudes.map((s) => {
              const e = ESTADO[s.estado] || ESTADO.pendiente;
              const Icon = e.icon;
              return (
                <div key={s.id} className="flex items-start gap-2.5 rounded-xl border border-linea bg-crema px-3.5 py-2.5">
                  <Icon size={16} className={`mt-0.5 shrink-0 ${e.color}`} />
                  <div className="min-w-0">
                    <p className="text-[0.88rem] font-medium">{s.label} · <span className={e.color}>{t(e.lk)}</span></p>
                    {s.motivo_dueno && <p className="text-[0.8rem] text-tinta-suave">{t("miperfil.el_dueno", { motivo: s.motivo_dueno })}</p>}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Módulos activos */}
      <section>
        <h2 className="mb-3 font-display text-[1.1rem] font-bold">{t("miperfil.incluye")}</h2>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {Object.entries(user.modulos_labels || {})
            .filter(([id]) => id !== "angela")
            .map(([id, label]) => (
              <div key={id} className="flex items-center gap-2.5 rounded-xl border border-linea bg-crema px-3.5 py-2.5">
                <CheckCircle2 size={16} className="text-salvia" />
                <span className="text-[0.9rem] font-medium">{label}</span>
              </div>
            ))}
        </div>
        <p className="mt-3 text-[0.82rem] text-tinta-suave">
          {t("miperfil.usas_en", {
            lista: user.superficies?.map((s) => t(s === "desktop" ? "miperfil.superficie_desktop" : "miperfil.superficie_mobile")).join(` ${t("miperfil.y")} `),
          })}
        </p>
      </section>

      {/* P19·A — transparencia total: lo que Ángela recuerda de CÓMO te gusta
          ver el negocio, listado y borrable una por una. Nada de memoria oculta. */}
      {esMiPerfil && <PreferenciasAngela />}

      {/* Idioma (scope usuario: se persiste en el perfil, en el servidor —
          mañana WhatsApp le habla a cada uno en su idioma leyendo lo mismo) */}
      {esMiPerfil && (
        <section>
          <h2 className="mb-3 font-display text-[1.1rem] font-bold">{t("perfil.idioma_titulo")}</h2>
          <div className="flex items-center gap-3 rounded-xl border border-linea bg-crema px-3.5 py-3">
            <Globe size={16} className="shrink-0 text-hielo" />
            <p className="flex-1 text-[0.85rem] text-tinta-suave">{t("perfil.idioma_nota")}</p>
            <LangSwitch />
          </div>
        </section>
      )}

      {/* P24·F2 — el switcher de usuarios se mudó a Equipo: Mi perfil queda
          con lo propio (foto, bloques, idioma, preferencias). */}
    </div>
  );
}

// P19·A — "Lo que Ángela recuerda de vos": las preferencias de vista aplicadas
// por la interfaz + las notas libres, cada una con su X. Borrar acá borra en el
// SERVIDOR (la fuente de verdad) y la vista vuelve al default en el momento.
function PreferenciasAngela() {
  const t = useT();
  const [prefs, setPrefs] = useState(null);
  // P24·D6 — las reglas de aviso (umbrales/programados) viven acá también:
  // visibles y borrables junto a las preferencias. Transparencia total.
  const [reglas, setReglas] = useState([]);
  const cargarReglas = () =>
    api.recordatorios()
      .then((r) => setReglas((r.recordatorios || []).filter((x) => x.condicion && x.estado !== "hecho")))
      .catch(() => {});
  useEffect(() => {
    api.preferencias().then(setPrefs).catch(() => setPrefs({ vista: {}, notas: {} }));
    cargarReglas();
  }, []);
  if (!prefs) return null;

  // Cada preferencia del catálogo se describe en lenguaje de dueño.
  const items = [];
  const v = prefs.vista || {};
  if (v.sin_torta) items.push({ clave: "sin_torta", texto: t("miperfil.pref_sin_torta") });
  if (v.margen_pin_umbral != null) items.push({ clave: "margen_pin_umbral", texto: t("miperfil.pref_margen_pin", { umbral: v.margen_pin_umbral }) });
  if (v.orden_home) items.push({ clave: "orden_home", texto: t("miperfil.pref_orden_home") });
  const nWidgets = Object.values(v.widgets || {}).reduce((a, l) => a + l.length, 0);
  if (nWidgets > 0) items.push({ clave: "widgets", texto: t("miperfil.pref_widgets", { n: nWidgets }) });
  for (const [k, val] of Object.entries(prefs.notas || {})) {
    items.push({ clave: k, texto: `${k}: ${val}`, nota: true });
  }

  const borrar = async (clave) => {
    try {
      const r = await api.preferenciaBorrar(clave);
      setPrefs({ vista: r.vista, notas: r.notas });
      // La vista local vuelve al default de esa preferencia en el momento.
      const { vistaStore } = await import("../lib/vistaStore");
      vistaStore.hidratarServer({ vista: r.vista });
    } catch { /* si falla queda como estaba; el server manda */ }
  };

  return (
    <section>
      <h2 className="mb-1 font-display text-[1.1rem] font-bold">{t("miperfil.prefs_titulo")}</h2>
      <p className="mb-3 text-[0.84rem] text-tinta-suave">{t("miperfil.prefs_sub")}</p>
      {items.length === 0 && reglas.length === 0 ? (
        <p className="rounded-xl border border-linea bg-crema px-3.5 py-3 text-[0.85rem] text-tinta-suave">
          {t("miperfil.prefs_vacio")}
        </p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-linea bg-crema">
          {items.map((it) => (
            <div key={it.clave} className="flex items-center gap-3 border-b border-linea/70 px-3.5 py-2.5 last:border-0">
              <AngelaMark size={20} />
              <p className="min-w-0 flex-1 text-[0.86rem] text-tinta">{it.texto}</p>
              <button onClick={() => borrar(it.clave)} aria-label={t("miperfil.pref_borrar")}
                className="grid h-8 w-8 shrink-0 place-items-center rounded-full text-tinta-suave hover:bg-rojo/10 hover:text-rojo">
                <XCircle size={16} />
              </button>
            </div>
          ))}
          {/* P24·D6 — las reglas de aviso: "avisame si…" / "recordame los lunes…" */}
          {reglas.map((r) => (
            <div key={r.id} className="flex items-center gap-3 border-b border-linea/70 px-3.5 py-2.5 last:border-0">
              <AngelaMark size={20} estado="esperando" />
              <div className="min-w-0 flex-1">
                <p className="text-[0.86rem] text-tinta">{r.texto}</p>
                <p className="text-[0.72rem] text-tinta-suave">{t("miperfil.regla_aviso")}</p>
              </div>
              <button
                onClick={() => api.recordatorioCompletar(r.id).then(cargarReglas).catch(() => {})}
                aria-label={t("miperfil.pref_borrar")}
                className="grid h-8 w-8 shrink-0 place-items-center rounded-full text-tinta-suave hover:bg-rojo/10 hover:text-rojo">
                <XCircle size={16} />
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

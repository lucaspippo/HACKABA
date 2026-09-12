import { useEffect, useMemo, useState } from "react";
import { Users, Monitor, Smartphone, Check, Send, X, Inbox, MessageSquare, Pencil, ChevronDown, Target, Activity, Clock, Eye, ArrowUpDown } from "lucide-react";
import AngelaSays from "../components/AngelaSays";
import AngelaMark from "../components/AngelaMark";
import ObjetivosPanel from "./ObjetivosPanel";
import Avatar from "../components/Avatar";
import BadgeNuevo, { antiguedadTexto } from "../components/BadgeNuevo";
import { VerComoSelector, cambiarA } from "../components/VerComo";
import { api } from "../lib/api";
import { apiUrl } from "../lib/apiUrl";
import { toast } from "../lib/toastStore";
import { useSession } from "../lib/auth";
import { equipoStore, useEquipo, ESTADO_LABEL } from "../lib/equipoStore";
import { num } from "../lib/format";
import { useT, t, useLang, tRol, tDato } from "../lib/i18n";

// EQUIPO, unificado: antes eran dos apartados ("Mi equipo" y "Gestión de
// equipo") que confundían. Ahora es UNO: todos ven el tablero del equipo
// (objetivos, recordatorios); el dueño además gestiona — solicitudes, matriz
// de módulos, perfiles con edición de descripciones y avisos de Ángela.

// El logo de WhatsApp (inline: sin assets externos) para el canal futuro.
function LogoWhatsApp({ size = 18 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="#25D366" aria-hidden="true">
      <path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2Zm0 18.2a8.2 8.2 0 0 1-4.2-1.1l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2Zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8s-.4-.1-.6.1-.7.8-.8 1-.3.2-.5.1a6.7 6.7 0 0 1-2-1.2 7.4 7.4 0 0 1-1.4-1.7c-.1-.2 0-.4.1-.5l.4-.5a1.7 1.7 0 0 0 .3-.4.5.5 0 0 0 0-.4c0-.1-.6-1.4-.8-1.9s-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 2.9 2.9 0 0 0-.9 2.2 5 5 0 0 0 1 2.7 11.4 11.4 0 0 0 4.4 3.9 14.8 14.8 0 0 0 1.5.5 3.6 3.6 0 0 0 1.6.1 2.7 2.7 0 0 0 1.7-1.2 2.1 2.1 0 0 0 .2-1.2c-.1-.1-.2-.2-.4-.3Z" />
    </svg>
  );
}

// P39·1.2 — Solicitudes ES el canal: el empleado pide desde su perfil el módulo
// que necesita para trabajar (con el porqué en sus palabras), acá el dueño
// aprueba o rechaza, y aprobar TILDA la celda de esa persona en «Quién ve qué»
// (mismo sistema de permisos de siempre — perfiles.resolver_solicitud escribe
// features_habilitadas, que es exactamente lo que lee la matriz).
function Solicitudes({ token, onCambio, onVerMatriz, vacioVisible = false }) {
  const t = useT();
  // P32·1 — null = cargando (nada aún), [] = confirmado vacío: el mensaje
  // "no hay solicitudes" no puede aparecer antes de que llegue la respuesta.
  const [items, setItems] = useState(null);
  const [motivos, setMotivos] = useState({});

  const cargar = () => {
    api.solicitudes(token, "pendiente").then((d) => setItems(d.solicitudes)).catch(() => {});
  };
  useEffect(cargar, [token]);

  const resolver = async (s, aprobar) => {
    try {
      await api.solicitudResolver(s.id, token, aprobar, motivos[s.id] || "");
      // Aprobar = tildar esa celda en «Quién ve qué». El toast lo dice para que
      // el dueño sepa dónde quedó (y no lo tenga que ir a buscar).
      toast(aprobar
        ? t("equipo.toast_aprobada_matriz", { nombre: s.nombre, label: s.label })
        : t("equipo.toast_rechazada", { nombre: s.nombre }));
      cargar();
      onCambio?.();
    } catch {
      toast(t("equipo.toast_error_resolver"), "error");
    }
  };

  if (items === null) return null;           // cargando: sin flash de vacío

  // El copy del canal va SIEMPRE (con o sin pendientes): explica qué es esta
  // pestaña y a dónde impacta aprobar.
  const Explica = () => (
    <p className="mb-3 text-[0.86rem] leading-snug text-tinta-suave">
      {t("equipo.solicitudes_explica")}{" "}
      {onVerMatriz && (
        <button onClick={onVerMatriz} className="font-semibold text-tinta underline decoration-linea underline-offset-2 hover:decoration-tinta">
          {t("equipo.solicitudes_ir_matriz")}
        </button>
      )}
    </p>
  );

  if (items.length === 0) {
    return vacioVisible ? (
      <section data-nav-id="solicitudes">
        <h2 className="mb-1 flex items-center gap-2 font-display text-[1.15rem] font-bold">
          <Inbox size={18} className="text-tinta-suave" /> {t("equipo.solicitudes_titulo")}
        </h2>
        <Explica />
        <p className="rounded-[var(--radius-card)] border border-linea bg-papel-hondo/40 p-5 text-[0.9rem] text-tinta-suave">
          {t("equipo.solicitudes_vacio")}
        </p>
      </section>
    ) : null;
  }
  return (
    <section data-nav-id="solicitudes">
      <h2 className="mb-1 flex items-center gap-2 font-display text-[1.15rem] font-bold">
        <Inbox size={18} className="text-tinta-suave" /> {t("equipo.solicitudes_titulo")}
        <span className="grid h-5 min-w-5 place-items-center rounded-full bg-oro px-1.5 text-[0.7rem] font-bold text-crema">{items.length}</span>
      </h2>
      <Explica />
      <div className="space-y-3">
        {items.map((s) => (
          <div key={s.id} className="rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
            <p className="text-[0.9rem]">
              <span className="font-semibold">{s.nombre}</span> {t("equipo.pide")} <span className="font-semibold">{s.label}</span>.
            </p>
            {/* Lo que ESCRIBIÓ el empleado: el porqué en sus palabras (P39·1.2) */}
            {s.motivo_empleado && (
              <p className="mt-1.5 rounded-xl bg-papel-hondo/60 p-2.5 text-[0.86rem] italic leading-snug text-tinta">
                "{s.motivo_empleado}"
              </p>
            )}
            {/* P41·3.2 — se fue "Ángela recomendó esto": el pedido lo hace el
                EMPLEADO y el dueño decide. Si no escribió un porqué propio, se
                muestra el contexto del matcheo, pero sin firmarlo Ángela. */}
            {!s.motivo_empleado && s.motivo_angela && (
              <p className="mt-1.5 rounded-xl bg-papel-hondo/60 p-2.5 text-[0.86rem] italic leading-snug text-tinta">
                "{s.motivo_angela}"
              </p>
            )}
            <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-linea pt-3">
              <button onClick={() => resolver(s, true)} className="inline-flex items-center gap-1.5 rounded-full bg-tinta px-4 py-1.5 text-[0.84rem] font-semibold text-crema">
                <Check size={14} /> {t("equipo.aprobar")}
              </button>
              <button onClick={() => resolver(s, false)} className="inline-flex items-center gap-1.5 rounded-full border border-linea px-4 py-1.5 text-[0.84rem] font-semibold text-tinta-suave hover:text-tinta">
                <X size={14} /> {t("equipo.rechazar")}
              </button>
              <input
                value={motivos[s.id] || ""}
                onChange={(e) => setMotivos((m) => ({ ...m, [s.id]: e.target.value }))}
                placeholder={t("equipo.motivo_ph")}
                className="min-w-52 flex-1 rounded-full border border-linea bg-papel px-3.5 py-1.5 text-[0.82rem] outline-none focus:border-tinta/40"
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// La matriz: cada empleado × cada módulo. El dueño habilita/deshabilita directo.
function MatrizModulos({ token }) {
  const t = useT();
  const [matriz, setMatriz] = useState([]);
  const [modulos, setModulos] = useState({});

  const cargar = () => {
    api.adminMatriz(token).then((d) => { setMatriz(d.matriz); setModulos(d.modulos); }).catch(() => {});
  };
  useEffect(cargar, [token]);

  const toggle = async (username, modulo, actual) => {
    try {
      const r = await api.adminFeature(token, username, modulo, !actual);
      toast(t(r.habilitado ? "equipo.toast_habilitaste" : "equipo.toast_sacaste", { modulo: modulos[modulo] || modulo, usuario: username }));
      cargar();
    } catch {
      toast(t("equipo.toast_error_modulo"), "error");
    }
  };

  // Columnas: módulos operativos (sin los de fábrica que no tiene sentido tocar).
  const columnas = Object.keys(modulos).filter((m) => !["angela", "perfil", "admin_contexto"].includes(m));
  if (matriz.length === 0) return null;

  return (
    <section data-nav-id="matriz">
      <h2 className="mb-1 font-display text-[1.15rem] font-bold">{t("equipo.matriz_titulo")}</h2>
      <p className="mb-3 text-[0.84rem] text-tinta-suave">
        {t("equipo.matriz_sub")}
      </p>
      <div className="overflow-x-auto rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
        <table className="w-full text-[0.82rem]">
          <thead>
            <tr className="border-b border-linea text-left">
              <th className="sticky left-0 bg-crema px-3 py-2 font-semibold">{t("equipo.matriz_empleado")}</th>
              {/* P24·E1 — headers LEGIBLES: envuelven en dos líneas (nada de
                  "…" para adivinar); el tooltip queda de refuerzo */}
              {columnas.map((m) => (
                <th key={m} className="px-1.5 py-2 text-center align-bottom font-semibold text-tinta-suave" title={modulos[m]}>
                  <span className="block w-16 whitespace-normal break-words text-[0.64rem] leading-tight">{modulos[m]}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matriz.map((f) => (
              <tr key={f.username} className="border-b border-linea/60 last:border-0">
                <td className="sticky left-0 bg-crema px-3 py-2 font-semibold">{f.nombre}</td>
                {columnas.map((m) => (
                  <td key={m} className="px-2 py-1.5 text-center">
                    <button
                      onClick={() => toggle(f.username, m, f.modulos[m])}
                      disabled={f.es_admin}
                      title={f.es_admin ? t("equipo.dueno_ve_todo") : t(f.modulos[m] ? "equipo.title_sacar" : "equipo.title_habilitar", { modulo: modulos[m] })}
                      className={`h-5 w-5 rounded-md border transition-colors ${
                        f.modulos[m] ? "border-salvia bg-salvia/80" : "border-linea bg-papel hover:border-tinta-suave"
                      } ${f.es_admin ? "cursor-not-allowed opacity-40" : ""}`}
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

// Avisos que Ángela propone mandar al equipo, derivados de lo detectado.
// El responsable sale de los PERFILES REALES del tenant (nada hardcodeado):
// datos/precios → quien tenga rol de administración; stock físico → depósito.
function proponerNotificaciones(data, perfiles) {
  if (!data || perfiles.length === 0) return [];
  const buscar = (palabras) =>
    perfiles.find((p) => !p.es_admin && palabras.some((w) => (p.rol || "").toLowerCase().includes(w)));
  const admin = buscar(["administra", "caja", "oficina"]) || perfiles.find((p) => !p.es_admin);
  const depo = buscar(["depós", "depos", "stock", "logíst", "logist"]) || admin;
  if (!admin) return [];

  const a = data.alertas;
  const props = [];
  if (a.balanza.cantidad > 0)
    props.push({ id: "balanza", responsable: admin.nombre, username: admin.username,
      mensaje: t("equipo.prop_balanza_msj", { nombre: admin.nombre, n: a.balanza.cantidad }),
      tarea: t("equipo.prop_balanza_tarea", { n: a.balanza.cantidad }) });
  if (a.negativos.cantidad > 0)
    props.push({ id: "negativos", responsable: depo.nombre, username: depo.username,
      mensaje: t("equipo.prop_negativos_msj", { nombre: depo.nombre, n: a.negativos.cantidad }),
      tarea: t("equipo.prop_negativos_tarea", { n: a.negativos.cantidad }) });
  if (a.sin_pvp.cantidad > 0)
    props.push({ id: "sin_pvp", responsable: admin.nombre, username: admin.username,
      mensaje: t("equipo.prop_sinpvp_msj", { nombre: admin.nombre, n: a.sin_pvp.cantidad }),
      tarea: t("equipo.prop_sinpvp_tarea", { n: a.sin_pvp.cantidad }) });
  return props;
}

// Tablero del equipo: objetivos + recordatorios (lo que era "Mi equipo",
// sin el organigrama hardcodeado del piloto). Lo ven todos los que tienen equipo.
function TableroEquipo() {
  const t = useT();
  const equipo = useEquipo();
  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
      <div>
        <h2 className="mb-3 font-display text-[1.15rem] font-bold">{t("equipo.objetivos_titulo")}</h2>
        <div className="space-y-2.5">
          {equipo.objetivos.length === 0 && (
            <p className="rounded-[var(--radius-card)] border border-dashed border-linea p-4 text-[0.86rem] text-tinta-suave">
              {t("equipo.objetivos_vacio")}
            </p>
          )}
          {equipo.objetivos.map((o) => (
            <div key={o.id} className="rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
              <p className="font-display text-[0.98rem] font-bold leading-tight">{t(o.nombre)}</p>
              <div className="mt-2 flex items-center justify-between">
                <span className="text-[0.8rem] text-tinta-suave">{o.responsable} · {t(o.fecha)}</span>
                <button
                  onClick={() => equipoStore.cicloEstado(o.id)}
                  className={`rounded-full px-3 py-1 text-[0.76rem] font-semibold ${
                    o.estado === "listo" ? "bg-salvia/15 text-salvia" : o.estado === "en_proceso" ? "bg-oro/15 text-oro-tinta" : "bg-papel-hondo text-tinta-suave"
                  }`}
                >
                  {t(ESTADO_LABEL[o.estado])}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-5">
        <div>
          <h2 className="mb-3 font-display text-[1.15rem] font-bold">{t("equipo.recordatorios_titulo")}</h2>
          <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema">
            {equipo.recordatorios.length === 0 && (
              <p className="p-4 text-[0.86rem] text-tinta-suave">{t("equipo.recordatorios_vacio")}</p>
            )}
            {equipo.recordatorios.map((r) => (
              <button key={r.id} onClick={() => equipoStore.toggleRecordatorio(r.id)} className="flex w-full items-center gap-3 border-b border-linea px-4 py-2.5 text-left last:border-0">
                <span className={`grid h-5 w-5 shrink-0 place-items-center rounded-full border ${r.hecho ? "border-salvia bg-salvia text-crema" : "border-tinta-suave/40"}`}>
                  {r.hecho && <Check size={13} />}
                </span>
                <span className={`flex-1 text-[0.88rem] ${r.hecho ? "text-tinta-suave line-through" : "text-tinta"}`}>{t(r.texto)}</span>
                <span className="shrink-0 text-[0.74rem] font-semibold text-tinta-suave">{r.responsable}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-[var(--radius-card)] border border-dashed border-linea bg-papel-hondo/40 p-4">
          <div className="flex items-center gap-2 text-tinta-suave">
            <MessageSquare size={16} />
            <p className="text-[0.9rem] font-semibold">{t("equipo.novedades_titulo")}</p>
          </div>
          <p className="mt-1.5 text-[0.84rem] leading-snug text-tinta-suave">
            {t("equipo.novedades_detalle")}
          </p>
        </div>
      </div>
    </div>
  );
}

// P29·B1 — LA FICHA de la persona: al abrirla, sus objetivos con avance, su
// actividad reciente REAL (consultas a Ángela por tema, cargas, correcciones)
// y lo que tiene pendiente (recordatorios sin hacer + solicitudes esperando).
// Todo derivado de datos que YA existen (equipoStore + /api/equipo-actividad
// + /api/solicitudes) — cero métricas inventadas.
function FichaPersona({ p, ficha }) {
  const t = useT();
  const { objetivos, pendientes, actividad, solicitudes } = ficha;
  const Bloque = ({ icon: Icon, titulo, children }) => (
    <div className="min-w-0">
      <p className="mb-1.5 flex items-center gap-1.5 text-[0.72rem] font-semibold uppercase tracking-wide text-tinta-suave">
        <Icon size={13} /> {titulo}
      </p>
      {children}
    </div>
  );
  const Vacio = ({ texto }) => <p className="text-[0.82rem] text-tinta-suave">{texto}</p>;
  return (
    <div className="mt-3 grid grid-cols-1 gap-4 border-t border-linea pt-3 sm:grid-cols-3">
      <Bloque icon={Target} titulo={t("equipo.ficha_objetivos")}>
        {objetivos.length === 0 ? <Vacio texto={t("equipo.ficha_sin_objetivos")} /> : (
          <div className="space-y-1.5">
            {objetivos.map((o) => (
              <div key={o.id} className="text-[0.84rem] leading-snug">
                <span className="text-tinta">{t(o.nombre)}</span>
                <span className={`ml-1.5 rounded-full px-2 py-0.5 text-[0.68rem] font-semibold ${
                  o.estado === "listo" ? "bg-salvia/15 text-salvia" : o.estado === "en_proceso" ? "bg-oro/15 text-oro-tinta" : "bg-papel-hondo text-tinta-suave"
                }`}>{t(ESTADO_LABEL[o.estado])}</span>
              </div>
            ))}
          </div>
        )}
      </Bloque>
      <Bloque icon={Activity} titulo={t("equipo.ficha_actividad")}>
        {!actividad || (actividad.consultas + actividad.cargas + actividad.correcciones) === 0
          ? <Vacio texto={t("equipo.ficha_sin_actividad")} />
          : (
            <div className="space-y-1 text-[0.84rem] leading-snug text-tinta">
              <p>{[
                actividad.consultas > 0 && t(actividad.consultas === 1 ? "equipo.act_consultas_1" : "equipo.act_consultas", { n: actividad.consultas }),
                actividad.cargas > 0 && t(actividad.cargas === 1 ? "equipo.act_cargas_1" : "equipo.act_cargas", { n: actividad.cargas }),
                actividad.correcciones > 0 && t(actividad.correcciones === 1 ? "equipo.act_correcciones_1" : "equipo.act_correcciones", { n: actividad.correcciones }),
              ].filter(Boolean).join(" · ")}</p>
              {actividad.temas_top?.length > 0 && (
                <p className="text-[0.78rem] text-tinta-suave">
                  {t("equipo.act_temas", { temas: actividad.temas_top.map(([k]) => k.replaceAll("_", " ")).join(", ") })}
                </p>
              )}
            </div>
          )}
      </Bloque>
      <Bloque icon={Clock} titulo={t("equipo.ficha_pendiente")}>
        {pendientes.length === 0 && solicitudes.length === 0 ? <Vacio texto={t("equipo.ficha_al_dia")} /> : (
          <div className="space-y-1 text-[0.84rem] leading-snug">
            {solicitudes.map((s) => (
              <p key={`s${s.id}`} className="text-oro-tinta">{t("equipo.ficha_solicitud", { label: s.label })}</p>
            ))}
            {pendientes.map((r) => (
              <p key={r.id} className="text-tinta">{t(r.texto)}</p>
            ))}
          </div>
        )}
      </Bloque>
    </div>
  );
}

// Card de perfil con edición de la descripción POR EL DUEÑO (gestión completa).
function PerfilCard({ p, token, onGuardado, ficha }) {
  const t = useT();
  const [editando, setEditando] = useState(false);
  const [texto, setTexto] = useState(p.descripcion || "");
  const [guardando, setGuardando] = useState(false);
  const [abierta, setAbierta] = useState(false);

  const guardar = async () => {
    setGuardando(true);
    try {
      await api.perfilDescripcion(p.username, token, texto);
      toast(t("equipo.toast_desc_guardada", { nombre: p.nombre }));
      setEditando(false);
      onGuardado?.();
    } catch {
      toast(t("equipo.toast_desc_error"), "error");
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-5 sombra-papel">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <Avatar persona={p} size={44} />
          <div>
            <p className="font-display text-[1.05rem] font-bold leading-tight">
              {p.nombre} {p.es_admin && <span className="ml-1 rounded-full bg-tinta/[0.08] px-2 py-0.5 text-[0.66rem] font-semibold uppercase text-tinta">{t("equipo.badge_admin")}</span>}
            </p>
            <p className="text-[0.8rem] text-tinta-suave">{t("equipo.usuario_meta", { rol: tRol(p.rol), username: p.username })}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-tinta-suave">
          {p.superficies?.includes("desktop") && <Monitor size={16} />}
          {p.superficies?.includes("mobile") && <Smartphone size={16} />}
          {!editando && (
            <button onClick={() => { setTexto(p.descripcion || ""); setEditando(true); }}
              title={t("equipo.title_editar_desc", { nombre: p.nombre })}
              className="inline-flex items-center gap-1 rounded-full border border-linea px-2.5 py-1 text-[0.76rem] font-semibold hover:text-tinta">
              <Pencil size={12} /> {t("equipo.editar")}
            </button>
          )}
          {ficha && (
            <button onClick={() => setAbierta((v) => !v)}
              className="inline-flex items-center gap-1 rounded-full border border-linea px-2.5 py-1 text-[0.76rem] font-semibold hover:text-tinta">
              {t("equipo.ficha_ver")} <ChevronDown size={12} className={`transition-transform ${abierta ? "rotate-180" : ""}`} />
            </button>
          )}
        </div>
      </div>

      {editando ? (
        <div className="mt-3 space-y-2">
          <textarea
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            rows={3}
            className="w-full rounded-xl border border-linea bg-papel p-3 text-[0.88rem] leading-snug outline-none focus:border-tinta/40"
          />
          <div className="flex gap-2">
            <button onClick={guardar} disabled={guardando} className="rounded-full bg-tinta px-4 py-1.5 text-[0.82rem] font-semibold text-crema disabled:opacity-50">
              {guardando ? t("equipo.guardando") : t("equipo.guardar")}
            </button>
            <button onClick={() => setEditando(false)} className="rounded-full border border-linea px-4 py-1.5 text-[0.82rem] font-semibold text-tinta-suave">
              {t("equipo.cancelar")}
            </button>
          </div>
        </div>
      ) : (
        <p className="mt-3 rounded-xl bg-papel-hondo/50 p-3 text-[0.86rem] leading-snug text-tinta">
          {/* se MUESTRA en el idioma del que mira; se EDITA el original */}
          <span className="font-semibold text-tinta-suave">{t("equipo.se_describio")}</span>
          {tDato(p.descripcion, p.descripcion_en)}
        </p>
      )}

      <div className="mt-3 flex flex-wrap gap-1.5">
        {Object.entries(p.modulos_labels || {})
          .filter(([id]) => id !== "angela")
          .map(([id, label]) => (
            <span key={id} className="rounded-full bg-papel-hondo px-2.5 py-0.5 text-[0.74rem] font-semibold text-tinta-suave">
              {label}
            </span>
          ))}
      </div>

      {abierta && ficha && <FichaPersona p={p} ficha={ficha} />}
    </div>
  );
}

// P41·3 — DOS pestañas, no cuatro. Antes las MISMAS 13 personas se listaban
// tres veces (el tablero, "lo que pasó" y la matriz) y "Ver como" era una cuarta
// lista. Ahora: "Equipo" = UNA lista, con todo lo de cada persona al expandir
// (incluido Ver como); "Permisos" = la matriz + los pedidos que la alimentan.
// "Objetivos" es su propia pestaña, separada del roster: propuestas y
// tablero no compiten con la lista de gente por la misma pantalla.
const TABS = [
  { id: "equipo", lk: "equipo.tab_equipo" },
  { id: "objetivos", lk: "equipo.tab_objetivos" },
  { id: "permisos", lk: "equipo.tab_permisos" },
];

// P34·3 — los TEMAS de consulta a Ángela son slugs de tools; se mapean a una
// categoría legible (cobranzas, caja, inventario…). El que no está en el mapa
// cae a su forma humanizada — jamás se inventa.
const TEMA_CAT = {
  cuentas_corrientes: "cobranzas", mensaje_cobro: "cobranzas", scoring_credito: "cobranzas",
  scoring_venta: "cobranzas", cuenta_estado: "cobranzas",
  estado_caja: "caja", caja_movimiento: "caja", caja_cerrar: "caja",
  plata_en: "inventario", analisis_rotacion: "inventario", buscar_productos: "inventario",
  plata_parada: "inventario", inventario: "inventario", stock: "inventario",
  consultar_deposito: "deposito", deposito: "deposito",
  lista_precios: "precios", precio: "precios",
  resumen_negocio: "panorama", kpis: "panorama",
  estacionalidad: "evolucion", consultar_serie: "evolucion", evolucion: "evolucion",
  pagos: "pagos", finanzas: "pagos",
};
function temaLabel(slug, t) {
  const cat = TEMA_CAT[slug];
  return cat ? t(`equipo.tema_${cat}`) : slug.replaceAll("_", " ");
}

// P39·1.3 — "Qué resolvió esta semana": los slugs que graba la auditoría, con
// las palabras del oficio. El que no está mapeado cae a su forma humanizada con
// el conteo — jamás se inventa una tarea que el sistema no registró.
const RESUELTO_LK = {
  cargar_remito: "equipo.hizo_remito",
  cargar_factura: "equipo.hizo_factura",
  cargar_recibo: "equipo.hizo_recibo",
  cargar_orden_compra: "equipo.hizo_oc",
  integrar_staging: "equipo.hizo_staging",
  crear_apartado: "equipo.hizo_apartado",
  aplicar_lista_precios: "equipo.hizo_lista",
  corregir_precio_perdida: "equipo.hizo_precio",
  sanear_fantasma: "equipo.hizo_fantasma",
  sanear_fantasma_custom: "equipo.hizo_fantasma",
  sanear_negativo: "equipo.hizo_negativo",
  sanear_balanza: "equipo.hizo_balanza",
  sanear_costo_viejo: "equipo.hizo_costo",
  validacion_montos_ventas: "equipo.hizo_validacion",
  preparar_orden_compra: "equipo.hizo_orden_armada",
  reportar_faltante: "equipo.hizo_faltante",
  marcar_conteo: "equipo.hizo_conteo",
  confirmar_entrega: "equipo.hizo_entrega",
  cerrar_tarea_piso: "equipo.hizo_tarea",
  pedir_reposicion: "equipo.hizo_reposicion",
};
function resueltoLabel(slug, n, t) {
  const lk = RESUELTO_LK[slug];
  if (!lk) return `${num(n)} × ${slug.replaceAll("_", " ")}`;
  return t(n === 1 ? `${lk}_1` : lk, { n: num(n) });
}

// El chip de estado: verdad de recencia (nunca inventada).
function estadoDe(a) {
  if (a.dias_desde == null) return { lk: "equipo.est_sin", cls: "bg-papel-hondo text-tinta-suave" };
  if (a.dias_desde <= 7) return { lk: "equipo.est_semana", cls: "bg-salvia/12 text-salvia", n: a.dias_desde };
  return { lk: "equipo.est_hace", cls: "bg-oro/12 text-oro-tinta", n: a.dias_desde };
}

// El detalle expandido de una persona: SOLO lo que el sistema registra.
function DetallePersona({ a, perfil, objetivos, solicitud, onVerComo, onVerPerfil, token, onGuardado }) {
  const t = useT();
  const [aviso, setAviso] = useState("");
  const [objetivo, setObjetivo] = useState("");
  // P41·3.1 — la descripción "en sus palabras" vivía en OTRA lista (el tablero
  // de perfiles). Ahora está acá, con todo lo demás de la persona, y el dueño la
  // edita sin cambiar de pestaña.
  const [editando, setEditando] = useState(false);
  const [texto, setTexto] = useState(perfil?.descripcion || "");
  const [guardando, setGuardando] = useState(false);
  const guardarDesc = async () => {
    setGuardando(true);
    try {
      await api.perfilDescripcion(a.username, token, texto);
      toast(t("equipo.toast_desc_guardada", { nombre: a.nombre }));
      setEditando(false);
      onGuardado?.();
    } catch {
      toast(t("equipo.toast_desc_error"), "error");
    } finally { setGuardando(false); }
  };
  const modulos = Object.entries(perfil?.modulos_labels || {}).filter(([id]) => id !== "angela");
  const Bloque = ({ titulo, children }) => (
    <div className="min-w-0">
      <p className="mb-1 text-[0.68rem] font-semibold uppercase tracking-wide text-tinta-suave">{titulo}</p>
      {children}
    </div>
  );
  const Vacio = ({ tx }) => <p className="text-[0.82rem] text-tinta-suave">{tx}</p>;
  const mandarAviso = () => {
    if (!aviso.trim()) return;
    api.notificacionAvisar(a.username, t("equipo.aviso_titulo"), aviso.trim())
      .then(() => { toast(t("equipo.toast_enviado", { nombre: a.nombre })); setAviso(""); })
      .catch(() => toast(t("equipo.toast_enviar_error"), "error"));
  };
  // P41·4 — asignar deja de ser sólo local: crea una tarea PERSISTIDA para esa
  // persona, que la ve en su vista de trabajo y la marca hecha desde el celular.
  // El objetivo del tablero se sigue agregando (es la vista del dueño).
  const asignar = async () => {
    const texto = objetivo.trim();
    if (!texto) return;
    equipoStore.addObjetivo(texto, a.nombre, t("oportunidades.este_mes"));
    setObjetivo("");
    try {
      await api.recordatorioCrear(texto, a.username);
      toast(t("equipo.toast_tarea_asignada", { quien: a.nombre }));
    } catch {
      // el objetivo quedó en el tablero, pero la tarea no llegó: se dice.
      toast(t("equipo.toast_tarea_error", { quien: a.nombre }), "error");
    }
  };
  return (
    <div className="border-t border-linea bg-papel/40 px-4 py-4">
      {/* 0 · Quién es, en sus palabras (P41·3.1) */}
      {perfil?.descripcion && !editando && (
        <div className="mb-3 rounded-xl bg-papel-hondo/50 p-3">
          <div className="flex items-start justify-between gap-2">
            <p className="text-[0.84rem] leading-snug text-tinta">
              {/* se MUESTRA en el idioma del que mira; se EDITA el original */}
              <span className="font-semibold text-tinta-suave">{t("equipo.se_describio")}</span>
              {tDato(perfil.descripcion, perfil.descripcion_en)}
            </p>
            {token && (
              <button onClick={() => { setTexto(perfil.descripcion || ""); setEditando(true); }}
                title={t("equipo.title_editar_desc", { nombre: a.nombre })}
                className="inline-flex shrink-0 items-center gap-1 rounded-full border border-linea px-2.5 py-1 text-[0.72rem] font-semibold text-tinta-suave hover:text-tinta">
                <Pencil size={11} /> {t("equipo.editar")}
              </button>
            )}
          </div>
        </div>
      )}
      {editando && (
        <div className="mb-3 space-y-2">
          <textarea value={texto} onChange={(e) => setTexto(e.target.value)} rows={3}
            className="w-full rounded-xl border border-linea bg-crema p-3 text-[0.86rem] leading-snug outline-none focus:border-tinta/40" />
          <div className="flex gap-2">
            <button onClick={guardarDesc} disabled={guardando}
              className="rounded-full bg-tinta px-4 py-1.5 text-[0.82rem] font-semibold text-crema disabled:opacity-50">
              {guardando ? t("equipo.guardando") : t("equipo.guardar")}
            </button>
            <button onClick={() => setEditando(false)}
              className="rounded-full border border-linea px-4 py-1.5 text-[0.82rem] font-semibold text-tinta-suave">
              {t("equipo.cancelar")}
            </button>
          </div>
        </div>
      )}

      {/* P·onboarding — la ficha laboral de la persona: cuánto hace que está,
          dónde y con quién. Sólo se muestra lo que su perfil declara. */}
      {(perfil?.antiguedad || perfil?.puesto) && (
        <p className="mb-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-[0.8rem] text-tinta-suave">
          <BadgeNuevo persona={perfil} />
          {perfil?.antiguedad && !perfil.antiguedad.nuevo && (
            <span>{t("equipo.det_antiguedad", { ant: antiguedadTexto(perfil.antiguedad) })}</span>
          )}
          {perfil?.puesto && (
            <span>{t("onb.puesto", {
              sector: tDato(perfil.puesto.sector, perfil.puesto.sector_en),
              turno: tDato(perfil.puesto.turno, perfil.puesto.turno_en) })}</span>
          )}
          {perfil?.puesto?.mentor && (
            <span>{t("onb.mentor", { nombre: perfil.puesto.mentor.nombre,
                                     rol: tRol(perfil.puesto.mentor.rol) })}</span>
          )}
        </p>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {/* 1 · Qué le consulta a Ángela (TEMAS, jamás texto de conversación) */}
        <Bloque titulo={t("equipo.det_consulta")}>
          {a.consultas > 0 ? (
            <div className="space-y-0.5 text-[0.84rem] text-tinta">
              <p>{t(a.consultas === 1 ? "equipo.act_consultas_1" : "equipo.act_consultas", { n: a.consultas })}</p>
              {a.temas_top?.length > 0 && (
                <p className="text-[0.8rem] text-tinta-suave">{t("equipo.det_temas")} {a.temas_top.map(([k, n]) => `${temaLabel(k, t)} (${num(n)})`).join(" · ")}</p>
              )}
            </div>
          ) : <Vacio tx={t("equipo.det_sin_consultas")} />}
        </Bloque>

        {/* P39·1.3 — Qué RESOLVIÓ esta semana, en concreto y con nombre propio:
            "cargó 3 remitos por foto", "corrigió 2 productos en negativo".
            Sale de la auditoría de los últimos 7 días, agrupada por acción. */}
        <Bloque titulo={t("equipo.det_resolvio")}>
          {a.resueltos?.length > 0 ? (
            <ul className="space-y-0.5 text-[0.84rem] leading-snug text-tinta">
              {a.resueltos.map(([slug, n]) => (
                <li key={slug} className="flex items-start gap-1.5">
                  <Check size={13} className="mt-1 shrink-0 text-salvia" />
                  <span>{resueltoLabel(slug, n, t)}</span>
                </li>
              ))}
            </ul>
          ) : <Vacio tx={t("equipo.det_sin_resueltos")} />}
        </Bloque>

        {/* 2 · Qué hizo en el negocio (cargas, correcciones, con recencia) */}
        <Bloque titulo={t("equipo.det_hizo")}>
          {(a.cargas + a.correcciones) > 0 ? (
            <div className="space-y-0.5 text-[0.84rem] text-tinta">
              {a.cargas > 0 && <p>{t(a.cargas === 1 ? "equipo.act_cargas_1" : "equipo.act_cargas", { n: a.cargas })}</p>}
              {a.correcciones > 0 && <p>{t(a.correcciones === 1 ? "equipo.act_correcciones_1" : "equipo.act_correcciones", { n: a.correcciones })}</p>}
              {a.dias_desde != null && <p className="text-[0.8rem] text-tinta-suave">{a.dias_desde === 0 ? t("equipo.det_ultima_hoy") : t("equipo.det_ultima_hace", { n: num(a.dias_desde) })}</p>}
            </div>
          ) : <Vacio tx={t("equipo.det_sin_acciones")} />}
        </Bloque>

        {/* 3 · Objetivos */}
        <Bloque titulo={t("equipo.ficha_objetivos")}>
          {objetivos.length === 0 ? <Vacio tx={t("equipo.ficha_sin_objetivos")} /> : (
            <div className="space-y-1">
              {objetivos.map((o) => (
                <div key={o.id} className="text-[0.84rem] leading-snug">
                  <span className="text-tinta">{t(o.nombre)}</span>
                  <span className={`ml-1.5 rounded-full px-2 py-0.5 text-[0.66rem] font-semibold ${o.estado === "listo" ? "bg-salvia/15 text-salvia" : o.estado === "en_proceso" ? "bg-oro/15 text-oro-tinta" : "bg-papel-hondo text-tinta-suave"}`}>{t(ESTADO_LABEL[o.estado])}</span>
                </div>
              ))}
            </div>
          )}
        </Bloque>

        {/* 4 · Qué tiene habilitado (los módulos de su rol). La navegación real
            (qué secciones abre, frecuencia) todavía NO se registra — honesto. */}
        <Bloque titulo={t("equipo.det_modulos")}>
          <div className="flex flex-wrap gap-1">
            {modulos.map(([id, label]) => (
              <span key={id} className="rounded-full bg-papel-hondo px-2 py-0.5 text-[0.72rem] font-semibold text-tinta-suave">{label}</span>
            ))}
          </div>
        </Bloque>

        {/* 5 · Lo que Ángela detectó (solicitud de módulo con su porqué) */}
        {solicitud && (
          <Bloque titulo={t("equipo.det_angela")}>
            <p className="text-[0.84rem] leading-snug text-tinta">{t("equipo.det_solicitud", { modulo: solicitud.label })}</p>
            {solicitud.motivo_angela && <p className="mt-0.5 text-[0.8rem] text-tinta-suave">{solicitud.motivo_angela}</p>}
          </Bloque>
        )}
      </div>

      {/* P39·1.3 — el canal que falta, declarado por persona (no inventado):
          cuando se conecte el grupo, lo de ESTA persona aterriza acá. */}
      <div className="mt-3 flex items-start gap-2.5 rounded-xl border border-dashed border-linea bg-papel-hondo/40 px-3 py-2.5">
        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-crema"><LogoWhatsApp size={14} /></span>
        <p className="text-[0.8rem] leading-snug text-tinta-suave">
          {t("equipo.det_whatsapp", { nombre: a.nombre })}
        </p>
      </div>

      {/* 6 · Acciones del dueño desde acá */}
      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-linea pt-3">
        <div className="flex items-center gap-1.5">
          <input value={objetivo} onChange={(e) => setObjetivo(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && asignar()}
            placeholder={t("equipo.det_ph_objetivo")}
            className="w-44 rounded-full border border-linea bg-crema px-3 py-1.5 text-[0.8rem] outline-none focus:border-tinta/40" />
          <button onClick={asignar} className="inline-flex items-center gap-1 rounded-full border border-linea px-3 py-1.5 text-[0.8rem] font-semibold text-tinta-suave hover:text-tinta"><Target size={13} /> {t("equipo.det_asignar")}</button>
        </div>
        <div className="flex items-center gap-1.5">
          <input value={aviso} onChange={(e) => setAviso(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && mandarAviso()}
            placeholder={t("equipo.det_ph_aviso")}
            className="w-44 rounded-full border border-linea bg-crema px-3 py-1.5 text-[0.8rem] outline-none focus:border-tinta/40" />
          <button onClick={mandarAviso} className="inline-flex items-center gap-1 rounded-full border border-linea px-3 py-1.5 text-[0.8rem] font-semibold text-tinta-suave hover:text-tinta"><Send size={13} /> {t("equipo.det_avisar")}</button>
        </div>
        <button onClick={() => onVerComo(a.username)} className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-3.5 py-1.5 text-[0.8rem] font-semibold text-crema"><Eye size={13} /> {t("equipo.det_vercomo")}</button>
        {onVerPerfil && (
          <button onClick={() => onVerPerfil(a.username)} className="inline-flex items-center gap-1.5 rounded-full border border-linea px-3.5 py-1.5 text-[0.8rem] font-semibold text-tinta-suave hover:text-tinta">{t("equipo.det_perfil")}</button>
        )}
      </div>
    </div>
  );
}

// P24·E4 → P34·3 — "Lo que pasó con tu equipo": PANEL DE GESTIÓN. Resumen real
// arriba + una fila por CADA empleado (los inactivos también), expandible al
// detalle real de esa persona. Es un AGREGADOR de la auditoría: cero actividad
// inventada, cero conversaciones expuestas. WhatsApp = futuro declarado.
export function ActividadEquipo({ token, perfiles, equipo, solicitudes, onVerPerfil, onGuardado }) {
  const t = useT();
  const [datos, setDatos] = useState(null);
  const [abierto, setAbierto] = useState(null);
  const [orden, setOrden] = useState("actividad");  // actividad | nombre
  useEffect(() => {
    api.equipoActividad().then(setDatos).catch(() => setDatos({ actividad: [], resumen: null, objetivos: [] }));
  }, [token]);
  if (!datos) return (
    <div className="space-y-2.5">
      {Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-14 animate-pulse rounded-[var(--radius-card)] border border-linea/60 bg-papel-hondo/50" />)}
    </div>
  );
  const perfilDe = (u) => perfiles?.find((p) => p.username === u);
  const objetivosDe = (nombre) => (equipo?.objetivos || []).filter((o) => o.responsable === nombre);
  const solicitudDe = (a) => (solicitudes || []).find((s) => s.usuario === a.username || s.nombre === a.nombre);
  const filas = [...(datos.actividad || [])];
  if (orden === "nombre") filas.sort((x, y) => x.nombre.localeCompare(y.nombre));
  // (el backend ya ordena por actividad desc)
  const r = datos.resumen;

  return (
    <section className="space-y-4">
      {/* 2.C — resumen agregado real del equipo */}
      {r && (
        <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
          {[
            { v: `${num(r.activos_semana)}/${num(r.personas)}`, l: t("equipo.res_activos") },
            { v: num(r.acciones_total), l: t("equipo.res_acciones") },
            // P36·E4 — los objetivos ya no viven acá (tenían el "0·0" de los
            // manuales): ahora son el panel de objetivos MEDIDOS de Ángela.
            { v: r.tema_top ? temaLabel(r.tema_top, t) : "—", l: t("equipo.res_tema") },
          ].map((x) => (
            <div key={x.l} className="rounded-[var(--radius-card)] border border-linea bg-crema px-3.5 py-2.5 sombra-papel">
              <p className="plata text-lg font-medium leading-none">{x.v}</p>
              <p className="mt-1 text-[0.7rem] leading-snug text-tinta-suave">{x.l}</p>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between gap-2">
        <p className="text-[0.86rem] text-tinta-suave">{t("equipo.actividad_sub")}</p>
        <button onClick={() => setOrden(orden === "actividad" ? "nombre" : "actividad")}
          className="inline-flex items-center gap-1 rounded-full border border-linea px-3 py-1 text-[0.76rem] font-semibold text-tinta-suave hover:text-tinta">
          <ArrowUpDown size={12} /> {orden === "actividad" ? t("equipo.orden_actividad") : t("equipo.orden_nombre")}
        </button>
      </div>

      {/* 2.A — una fila compacta por CADA empleado (los inactivos también) */}
      <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
        {filas.map((a) => {
          const est = estadoDe(a);
          const abierta = abierto === a.username;
          const perfil = perfilDe(a.username);
          return (
            <div key={a.username} className="border-b border-linea/70 last:border-0">
              <button onClick={() => setAbierto(abierta ? null : a.username)}
                className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-papel-hondo/30">
                <Avatar persona={perfil || { nombre: a.nombre }} size={36} />
                <div className="min-w-0 flex-1">
                  {/* P·onboarding — el que recién entró, marcado en la lista:
                      no se lee igual alguien con 9 años que alguien con 1 semana. */}
                  <p className="flex items-center gap-1.5 truncate text-[0.9rem] font-semibold text-tinta">
                    <span className="truncate">{a.nombre} <span className="font-normal text-tinta-suave">· {tRol(a.rol)}</span></span>
                    <BadgeNuevo persona={perfil} compacto />
                  </p>
                  <p className="truncate text-[0.78rem] text-tinta-suave">
                    {(() => {
                      const objs = a.objetivos_en_curso + a.objetivos_listos;
                      const partes = [
                        a.consultas > 0 && t(a.consultas === 1 ? "equipo.mini_consultas_1" : "equipo.mini_consultas", { n: num(a.consultas) }),
                        a.acciones > 0 && t(a.acciones === 1 ? "equipo.mini_acciones_1" : "equipo.mini_acciones", { n: num(a.acciones) }),
                        objs > 0 && t(objs === 1 ? "equipo.mini_objetivos_1" : "equipo.mini_objetivos", { n: num(objs) }),
                      ].filter(Boolean);
                      return partes.length ? partes.join(" · ") : t("equipo.mini_sin");
                    })()}
                  </p>
                </div>
                <span className={`hidden shrink-0 rounded-full px-2.5 py-0.5 text-[0.7rem] font-semibold sm:inline ${est.cls}`}>
                  {est.n != null ? t(est.lk, { n: num(est.n) }) : t(est.lk)}
                </span>
                <ChevronDown size={16} className={`shrink-0 text-tinta-suave transition-transform ${abierta ? "rotate-180" : ""}`} />
              </button>
              {abierta && (
                <DetallePersona a={a} perfil={perfil} objetivos={objetivosDe(a.nombre)}
                  solicitud={solicitudDe(a)} onVerComo={(u) => cambiarA(u, t)} onVerPerfil={onVerPerfil}
                  token={token} onGuardado={onGuardado} />
              )}
            </div>
          );
        })}
      </div>

      {/* WhatsApp: SOLO logo + futuro declarado (qué sumaría cuando exista) */}
      <div className="flex items-start gap-3 rounded-[var(--radius-card)] border border-dashed border-linea bg-papel-hondo/40 p-4">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-crema"><LogoWhatsApp /></span>
        <div>
          <p className="text-[0.86rem] font-semibold text-tinta">{t("equipo.act_whatsapp_futuro")}</p>
          <p className="mt-0.5 text-[0.82rem] leading-snug text-tinta-suave">{t("equipo.act_whatsapp_detalle")}</p>
        </div>
      </div>
    </section>
  );
}

export default function GestionEquipo({ data, user, highlight }) {
  const t = useT();
  const lang = useLang(); // las propuestas memorizadas se rearman al cambiar el idioma
  const session = useSession();
  const esAdmin = !!user?.es_admin;
  const [tab, setTab] = useState("equipo");
  const [perfiles, setPerfiles] = useState([]);
  const [pendientes, setPendientes] = useState(0);
  const [error, setError] = useState(null);
  const [enviados, setEnviados] = useState({});
  const [cancelados, setCancelados] = useState({});
  // P29·B1 — los insumos de la FICHA por persona (mismas fuentes que las tabs)
  const equipo = useEquipo();
  const [actividad, setActividad] = useState([]);
  const [solicitudesList, setSolicitudesList] = useState([]);

  // Si Ángela navega con highlight (solicitudes/matriz), abrimos esa pestaña.
  useEffect(() => {
    if (highlight === "solicitudes" || highlight === "matriz") setTab("permisos");
  }, [highlight]);

  const cargarPerfiles = () => {
    if (!session?.token || !esAdmin) return;
    fetch(apiUrl(`/api/perfiles?token=${encodeURIComponent(session.token)}`))
      .then((r) => (r.ok ? r.json() : Promise.reject(r)))
      .then((d) => setPerfiles(d.perfiles))
      .catch(() => setError(t("equipo.error_perfiles")));
    api.solicitudes(session.token, "pendiente")
      .then((d) => { setPendientes(d.solicitudes.length); setSolicitudesList(d.solicitudes); })
      .catch(() => {});
    api.equipoActividad().then((d) => setActividad(d.actividad || [])).catch(() => {});
  };
  useEffect(cargarPerfiles, [session, esAdmin]);

  // La ficha de cada persona: objetivos con avance, actividad real, pendientes.
  const fichaDe = (p) => ({
    objetivos: equipo.objetivos.filter((o) => o.responsable === p.nombre),
    pendientes: equipo.recordatorios.filter((r) => !r.hecho && r.responsable === p.nombre),
    actividad: actividad.find((a) => a.username === p.username) || null,
    solicitudes: solicitudesList.filter((s) => s.username === p.username || s.nombre === p.nombre),
  });

  const propuestas = useMemo(() => proponerNotificaciones(data, perfiles), [data, perfiles, lang]);

  const aprobar = async (p) => {
    try {
      // Va por el sistema de notificaciones REAL: le llega a SU campanita.
      await api.notificacionAvisar(p.username, t("equipo.aviso_titulo"), p.mensaje);
      equipoStore.addRecordatorio(p.tarea, p.responsable);
      setEnviados((s) => ({ ...s, [p.id]: true }));
      toast(t("equipo.toast_enviado", { nombre: p.responsable }));
    } catch {
      toast(t("equipo.toast_enviar_error"), "error");
    }
  };

  return (
    <div className="space-y-6">
      <header className="flex items-center gap-2">
        <Users size={24} className="text-tinta-suave" />
        <div>
          <h1 className="font-display text-2xl font-bold leading-none">{t("equipo.titulo")}</h1>
          <p className="mt-1 text-[0.9rem] text-tinta-suave">
            {esAdmin ? t("equipo.sub_admin") : t("equipo.sub_empleado")}
          </p>
        </div>
      </header>

      {/* Los empleados ven el tablero; el dueño además gestiona por pestañas */}
      {!esAdmin ? (
        <>
          {/* P36·E4 — los objetivos que Ángela mide (el empleado ve los suyos) */}
          <ObjetivosPanel />
          <TableroEquipo />
          <AngelaSays>
            {t("equipo.angela_empleado")}
          </AngelaSays>
        </>
      ) : (
        <>
          <div className="flex gap-1.5 border-b border-linea">
            {TABS.map((tb) => (
              <button
                key={tb.id}
                onClick={() => setTab(tb.id)}
                className={`relative -mb-px rounded-t-xl border px-4 py-2 text-[0.86rem] font-semibold transition-colors ${
                  tab === tb.id ? "border-linea border-b-crema bg-crema text-tinta" : "border-transparent text-tinta-suave hover:text-tinta"
                }`}
              >
                {t(tb.lk)}
                {tb.id === "permisos" && pendientes > 0 && (
                  <span className="ml-1.5 inline-grid h-4.5 min-w-4.5 place-items-center rounded-full bg-oro px-1 text-[0.66rem] font-bold text-crema">{pendientes}</span>
                )}
                {tb.id === "objetivos" && propuestas.filter((p) => !cancelados[p.id]).length > 0 && (
                  <span className="ml-1.5 inline-grid h-4.5 min-w-4.5 place-items-center rounded-full bg-oro px-1 text-[0.66rem] font-bold text-crema">
                    {propuestas.filter((p) => !cancelados[p.id]).length}
                  </span>
                )}
              </button>
            ))}
          </div>

          {error && <p className="text-[0.9rem] text-rojo">{error}</p>}

          {/* P41·3.2 — PERMISOS: la matriz arriba (funciona bien, no se toca) y
              abajo los pedidos que la alimentan. El pedido nace del EMPLEADO. */}
          {tab === "permisos" && session?.token && (
            <>
              <MatrizModulos token={session.token} />
              <div className="mt-6">
                <Solicitudes token={session.token} onCambio={cargarPerfiles} vacioVisible />
              </div>
              {/* Futuro declarado, no feature inventada: el canal WhatsApp */}
              <div className="mt-4 flex items-start gap-3 rounded-[var(--radius-card)] border border-dashed border-linea bg-papel-hondo/40 p-4">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-crema"><LogoWhatsApp /></span>
                <div>
                  <p className="text-[0.92rem] font-semibold text-tinta">{t("equipo.mob_conecta_wsp")}</p>
                  <p className="mt-1 text-[0.86rem] leading-snug text-tinta-suave">{t("equipo.mob_novedades_detalle")}</p>
                </div>
              </div>
            </>
          )}

          {/* P41·3.1 — EQUIPO: UNA sola lista de las 13 personas. Al expandir
              una, todo lo suyo junto (descripción, qué resolvió, objetivos,
              módulos) y las acciones — incluido "Ver como", que dejó de ser una
              lista aparte. */}
          {tab === "equipo" && session?.token && (
            <ActividadEquipo token={session.token} perfiles={perfiles} equipo={equipo}
              solicitudes={solicitudesList} onGuardado={cargarPerfiles}
              onVerPerfil={(u) => cambiarA(u, t)} />
          )}

          {tab === "objetivos" && (
            <>
              {/* P36·E4 — los objetivos que Ángela mide sola (el dueño ve todos) */}
              <ObjetivosPanel />

              {/* P41·3.4 — los "heads-up" de Ángela, AGRUPADOS. Antes eran 3
                  tarjetas grandes apiladas que se leían como spam. Ahora es UN
                  bloque con una fila compacta por aviso: quién, qué le diría, y
                  Enviar/Cancelar al lado. Sigue decidiendo el dueño — nada sale
                  solo (por eso no hay push: hay un botón). */}
              {propuestas.filter((p) => !cancelados[p.id]).length > 0 && (
                <section className="rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
                  <div className="flex items-center gap-2 border-b border-linea px-4 py-2.5">
                    <AngelaMark size={22} />
                    <h2 className="font-display text-[0.98rem] font-bold">{t("equipo.propone_titulo")}</h2>
                    <span className="grid h-5 min-w-5 place-items-center rounded-full bg-papel-hondo px-1.5 text-[0.7rem] font-bold text-tinta-suave">
                      {num(propuestas.filter((p) => !cancelados[p.id]).length)}
                    </span>
                    <span className="ml-auto text-[0.76rem] text-tinta-suave">{t("equipo.vos_decidis")}</span>
                  </div>
                  <div>
                    {propuestas.filter((p) => !cancelados[p.id]).map((p) => {
                      const enviado = enviados[p.id];
                      return (
                        <div key={p.id} className="flex flex-wrap items-center gap-x-3 gap-y-1.5 border-b border-linea/70 px-4 py-2.5 last:border-0">
                          <span className="text-[0.78rem] font-semibold uppercase tracking-wide text-tinta-suave">
                            {t("equipo.para", { nombre: p.responsable })}
                          </span>
                          <p className="min-w-0 flex-1 basis-64 text-[0.86rem] italic leading-snug text-tinta">"{p.mensaje}"</p>
                          {enviado ? (
                            <span className="inline-flex shrink-0 items-center gap-1.5 text-[0.82rem] font-semibold text-salvia">
                              <Check size={14} /> {t("equipo.enviado_tarea", { nombre: p.responsable })}
                            </span>
                          ) : (
                            <span className="flex shrink-0 items-center gap-1.5">
                              <button onClick={() => aprobar(p)} className="inline-flex items-center gap-1.5 rounded-full bg-tinta px-3.5 py-1.5 text-[0.8rem] font-semibold text-crema">
                                <Send size={13} /> {t("equipo.enviar_a", { nombre: p.responsable })}
                              </button>
                              <button onClick={() => setCancelados((s) => ({ ...s, [p.id]: true }))} title={t("equipo.cancelar")}
                                className="grid h-7 w-7 place-items-center rounded-full border border-linea text-tinta-suave hover:text-tinta">
                                <X size={13} />
                              </button>
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </section>
              )}

              <TableroEquipo />

              <AngelaSays>
                {t("equipo.angela_admin")}
              </AngelaSays>
            </>
          )}
        </>
      )}
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import { Send, Camera, Mic, FileText, Paperclip, ChevronRight, Check, XCircle } from "lucide-react";
import AngelaMark from "../components/AngelaMark";
import FacturaFlow from "../components/FacturaFlow";
import VozAngela from "../components/VozAngela";
import { textoFeed } from "../components/ActividadFeed";
import { fecha } from "../lib/format";
import { api } from "../lib/api";
import { angelaBus } from "../lib/angelaBus";
import { authStore } from "../lib/auth";
import { rolDe } from "../lib/roles";
import { equipoStore } from "../lib/equipoStore";
import { vistaStore } from "../lib/vistaStore";
import { useT, useLang } from "../lib/i18n";

// Chips: lk es lo que se MUESTRA (traducido); "enviar" es el payload que va al
// backend y queda en ES (el motor de Ángela entiende castellano). Los chips que
// llegan por props como strings simples se muestran y envían tal cual.
const CHIPS = [
  { lk: "angela.chip_manteca", enviar: "¿Cuánta plata tengo en manteca?" },
  { lk: "angela.chip_fantasma", enviar: "¿Cuáles son mis productos fantasma?" },
  { lk: "angela.chip_anota", enviar: "Anotá que Vanesa revise los precios de balanza" },
  { lk: "angela.chip_riesgo", enviar: "¿Dónde está el mayor riesgo de mi inventario?" },
];

// Chat de Ángela, compartido entre mobile (pantalla completa) y desktop (panel).
// onNavigate: si se pasa (desktop), Ángela puede llevar al usuario a una sección.
export default function AngelaView({
  saludoInicial,
  onNavigate,
  placeholderChips = CHIPS,
  inputInicial,
  user,
  onDatosCambiaron,
}) {
  const t = useT();
  const [mensajes, setMensajes] = useState([
    {
      role: "assistant",
      content: saludoInicial || t("angela.saludo_default"),
    },
  ]);
  const [input, setInput] = useState("");
  const [vozAbierta, setVozAbierta] = useState(false);
  const [pensando, setPensando] = useState(false);
  // P19·D — mientras el checklist del plan se revela, la esfera está "ejecutando"
  const [ejecutando, setEjecutando] = useState(false);
  const [modo, setModo] = useState(null);
  const [fotoAbierta, setFotoAbierta] = useState(false);
  const [feed, setFeed] = useState([]);
  const finRef = useRef(null);
  const ultimaConsulta = useRef(null);

  // "Lo último que hice": la auditoría real del tenant, para que el panel
  // recién abierto muestre trabajo hecho, no una hoja en blanco.
  useEffect(() => {
    api.actividad().then((a) => setFeed((a.feed || []).slice(0, 3))).catch(() => {});
  }, []);

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensajes, pensando]);

  // P31·4 — el saludo inicial sigue el idioma: si la conversación TODAVÍA no
  // empezó (solo está el saludo), al cambiar EN/ES se re-traduce. Una vez que
  // el usuario escribe, el transcript queda como está (no se reescribe).
  const lang = useLang();
  useEffect(() => {
    setMensajes((m) => (m.length === 1 && m[0].role === "assistant"
      ? [{ role: "assistant", content: saludoInicial || t("angela.saludo_default") }]
      : m));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang]);

  // B1: los mensajes PROACTIVOS de Ángela (p. ej. el análisis al confirmarse una
  // carga por foto) entran al transcript como mensajes de ella, sin pregunta del
  // usuario. Si el panel estaba cerrado, quedaron en cola y se drenan al montar;
  // como quedan en `mensajes`, viajan en el historial de la próxima consulta.
  useEffect(() => {
    const alTranscript = (p) =>
      setMensajes((m) => [...m, { role: "assistant", content: p.content }]);
    angelaBus.drain().forEach(alTranscript);
    return angelaBus.subscribe(alTranscript);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Cuando se entra con una consulta (buscador global, "que lo gestione Ángela",
  // banner de fase), Ángela la responde sola: pregunta → estás ahí.
  useEffect(() => {
    if (inputInicial && inputInicial !== ultimaConsulta.current) {
      ultimaConsulta.current = inputInicial;
      enviar(inputInicial);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inputInicial]);

  const aplicarAcciones = (acciones = []) => {
    if (!acciones.length) return;
    equipoStore.aplicarAcciones(acciones); // recordatorios / objetivos
    for (const a of acciones) {
      if (a.type === "modify_view" && a.cambios) vistaStore.aplicar(a.cambios);
      if (a.type === "create_widget" && a.widget) vistaStore.agregarWidget(a.section, a.widget);
      if (a.type === "crear_pestana" && a.pestana) vistaStore.agregarPestana(a.pestana);
      // P19·A — Ángela recordó una preferencia: la vista se adapta EN EL
      // MOMENTO (el server ya la persistió; esto es el espejo local).
      if (a.type === "preferencia" && a.vista) vistaStore.hidratarServer({ vista: a.vista });
      // P19·B — el Home se reordena en el momento (server ya persistido).
      if (a.type === "orden_home") vistaStore.aplicar({ ordenHome: a.orden });
      // P24·B — el documento se ENTREGA en el chat (card de descarga); ya no
      // se navega a un preview. El render+listado pasa en la card (DocCard).
    }
    if (acciones.some((a) => a.type === "saneado")) onDatosCambiaron?.();
    // Si hay varios navigate en la misma respuesta (p.ej. el auto-navigate de
    // una tool + un navegar_a puntual), gana el ÚLTIMO: es la intención más
    // específica de Ángela (ej. "cliente-<id>" pisa al grupo "morosos").
    const nav = [...acciones].reverse().find((a) => a.type === "navigate");
    if (nav && onNavigate) onNavigate(nav.section, nav.highlight);
  };

  const enviar = async (texto) => {
    const msg = (texto ?? input).trim();
    if (!msg || pensando) return;
    setInput("");
    const historial = mensajes.map((m) => ({ role: m.role, content: m.content }));
    setMensajes((m) => [...m, { role: "user", content: msg }]);
    setPensando(true);
    try {
      // El token identifica al usuario en el backend; el rol/nombre reales salen
      // de ahí (el body ya no decide la identidad). Ver /api/angela.
      const r = await api.angela(msg, historial, { token: authStore.getSnapshot()?.token });
      setModo(r.modo);
      // P19·D — si la respuesta trae un plan ejecutado, el checklist viaja CON
      // el mensaje (los pasos ya corrieron en el server, en ese orden; acá se
      // revelan uno a uno para que el trabajo se VEA).
      const plan = (r.acciones || []).find((a) => a.type === "plan_progreso");
      // P24·B — el documento generado viaja CON el mensaje como card de descarga
      const docAccion = (r.acciones || []).find((a) => a.type === "documento");
      setMensajes((m) => [...m, {
        role: "assistant", content: r.respuesta, opciones: r.opciones || [],
        plan: plan ? { pasos: plan.pasos, resumen: plan.resumen } : undefined,
        documento: docAccion?.documento,
        escribir: true, // typewriter: solo los mensajes recién llegados
      }]);
      aplicarAcciones(r.acciones);
      if (plan) onDatosCambiaron?.(); // el plan tocó datos: refetch como un saneado
    } catch {
      setMensajes((m) => [
        ...m,
        { role: "assistant", content: t("angela.error_conexion") },
      ]);
    } finally {
      setPensando(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center gap-3 pb-3 pt-1">
        <AngelaMark size={40} pulse={pensando} estado={ejecutando ? "ejecutando" : undefined} />
        <div>
          <h1 className="font-display text-xl font-bold leading-none">Ángela</h1>
          <p className="mt-0.5 flex items-center gap-1.5 text-[0.78rem] text-tinta-suave">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-salvia" />
            {modo === "simulado"
              ? t("angela.modo_datos")
              : t("angela.socia")}
          </p>
        </div>
      </header>

      <div className="flex-1 space-y-3 overflow-y-auto pb-2">
        {mensajes.map((m, i) =>
          m.role === "assistant" ? (
            <div key={i} className="flex gap-2.5">
              <AngelaMark size={28} />
              <div className="max-w-[88%]">
                <div className="whitespace-pre-line rounded-2xl rounded-tl-md border border-linea bg-crema px-3.5 py-2.5 text-[0.95rem] leading-snug text-tinta sombra-papel">
                  <TextoAngela texto={m.content} animar={!!m.escribir && i === mensajes.length - 1} />
                  {m.plan && <PlanChecklist plan={m.plan} onEjecutando={setEjecutando} />}
                  {m.documento && <DocCard documento={m.documento} t={t} />}
                </div>
                {m.opciones?.length > 0 && (
                  <div className="mt-2 flex flex-col gap-1.5">
                    {m.opciones.map((op, k) => (
                      <button
                        key={k}
                        onClick={() => enviar(op.enviar)}
                        disabled={pensando}
                        className="rounded-xl border border-violeta/30 bg-crema px-3 py-2 text-left text-[0.86rem] font-semibold text-violeta transition-colors hover:bg-violeta hover:text-crema disabled:opacity-50"
                      >
                        {op.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div key={i} className="flex justify-end">
              <div className="max-w-[85%] whitespace-pre-line rounded-2xl rounded-tr-md bg-tinta px-3.5 py-2.5 text-[0.95rem] leading-snug text-crema">
                {m.content}
              </div>
            </div>
          )
        )}
        {pensando && (
          <div className="flex gap-2.5">
            <AngelaMark size={28} />
            <div className="rounded-2xl rounded-tl-md border border-linea bg-crema px-4 py-3 sombra-papel">
              <span className="flex gap-1">
                {[0, 1, 2].map((d) => (
                  <span
                    key={d}
                    className="h-1.5 w-1.5 animate-bounce rounded-full bg-tinta-suave"
                    style={{ animationDelay: `${d * 0.15}s` }}
                  />
                ))}
              </span>
            </div>
          </div>
        )}
        <div ref={finRef} />
      </div>

      {mensajes.length <= 1 && (
        <div className="pb-3">
          {/* Lo último que Ángela hizo — auditoría real, no decoración */}
          {feed.length > 0 && (
            <div className="mb-3 space-y-1.5">
              <p className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-tinta-suave">{t("angela.ultimo")}</p>
              {feed.map((e, i) => (
                <div key={i} className="flex items-start gap-2.5 rounded-xl border border-linea bg-crema px-3 py-2 sombra-papel">
                  <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${e.tipo === "staging" ? "bg-salvia" : "bg-oro"}`} />
                  <span className="min-w-0 flex-1 text-[0.8rem] leading-snug text-tinta">{textoFeed(e, t)}</span>
                  <span className="shrink-0 text-[0.7rem] text-tinta-suave">{fecha(e.cuando)}</span>
                </div>
              ))}
            </div>
          )}
          {/* Acciones reales del agente (nada de features inventadas) */}
          <div className="mb-3 space-y-1.5">
            {authStore.tiene("cargar") && (
              <button
                onClick={() => setFotoAbierta(true)}
                className="flex w-full items-center gap-3 rounded-xl border border-linea bg-crema px-3 py-2.5 text-left sombra-papel transition-colors hover:border-violeta/40"
              >
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-violeta-suave text-violeta"><Paperclip size={16} /></span>
                <span className="min-w-0 flex-1">
                  <span className="block text-[0.85rem] font-semibold leading-tight">{t("angela.accion_foto")}</span>
                  <span className="block text-[0.74rem] text-tinta-suave">{t("angela.accion_foto_sub")}</span>
                </span>
                <ChevronRight size={15} className="text-tinta-suave" />
              </button>
            )}
            {onNavigate && authStore.tiene("documentos") && (
              <button
                onClick={() => onNavigate("documentos")}
                className="flex w-full items-center gap-3 rounded-xl border border-linea bg-crema px-3 py-2.5 text-left sombra-papel transition-colors hover:border-violeta/40"
              >
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-violeta-suave text-violeta"><FileText size={16} /></span>
                <span className="min-w-0 flex-1">
                  <span className="block text-[0.85rem] font-semibold leading-tight">{t("angela.accion_doc")}</span>
                  <span className="block text-[0.74rem] text-tinta-suave">{t("angela.accion_doc_sub")}</span>
                </span>
                <ChevronRight size={15} className="text-tinta-suave" />
              </button>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {placeholderChips.map((c) => (
              <button
                key={typeof c === "string" ? c : c.lk}
                onClick={() => enviar(typeof c === "string" ? c : c.enviar)}
                className="rounded-full border border-linea bg-crema px-3 py-1.5 text-left text-[0.82rem] font-medium text-tinta-suave transition-colors hover:border-violeta/40 hover:text-tinta"
              >
                {typeof c === "string" ? c : t(c.lk)}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* P10: la camarita — foto del comprobante desde el chat (la promesa
          "snap a photo and tell her to load it"). Solo roles con `cargar`. */}
      {fotoAbierta && (
        <FacturaFlow
          onCerrar={() => setFotoAbierta(false)}
          onCargado={() => onDatosCambiaron?.()}
          onPreguntar={(texto) => { setFotoAbierta(false); enviar(texto); }}
        />
      )}

      {/* P43·C1 — la voz, EN el chat. Estaba sólo en la sección Depósito, así
          que el que abría el chat para hablarle a Ángela se encontraba con un
          teclado. Es el MISMO componente del Bloque C (audio → Web Speech →
          validadores deterministas → propuesta que un humano aprueba): acá sólo
          se monta desde otro lado. Si la nota de voz resulta ser una consulta y
          no un reporte, cae al chat por `onPreguntar` y sigue la conversación. */}
      {vozAbierta && (
        <VozAngela
          rol={rolDe(user)?.id}
          onCerrar={() => setVozAbierta(false)}
          onListo={() => onDatosCambiaron?.()}
          onPreguntar={(texto) => { setVozAbierta(false); enviar(texto); }}
        />
      )}

      <div className="flex items-center gap-2 rounded-full border border-linea bg-crema p-1.5 pl-4 sombra-papel">
        {authStore.tiene("cargar") && (
          <button
            onClick={() => setFotoAbierta(true)}
            title={t("foto.titulo")}
            className="grid h-11 w-11 shrink-0 place-items-center rounded-full text-tinta-suave transition-colors hover:text-violeta"
          >
            <Camera size={20} />
          </button>
        )}
        {/* P44·A2 — el micrófono del chat es de TODOS. Hablarle a Ángela en vez
            de tipearle no es una capacidad de depósito: el dueño manejando también
            prefiere preguntar en voz alta. Sin gate de rol a propósito; el que
            reporta desde el piso además lo tiene en su vista de trabajo (ver
            lib/roles.reportaPorVoz). Si el navegador no escucha, VozAngela ya cae
            a sus frases preparadas — no hace falta esconder el botón. */}
        <button
          onClick={() => setVozAbierta(true)}
          title={t("voz.titulo")}
          aria-label={t("voz.titulo")}
          className="grid h-11 w-11 shrink-0 place-items-center rounded-full text-tinta-suave transition-colors hover:text-violeta"
        >
          <Mic size={20} />
        </button>
        {/* P24·F3 — un pedido a la vez: mientras Ángela trabaja, el input se
            deshabilita con estado visible. La navegación por la app sigue libre;
            lo que se serializa es el chat (doble-click ya no la vuelve loca). */}
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && enviar()}
          disabled={pensando || ejecutando}
          placeholder={pensando || ejecutando ? t("angela.ph_trabajando") : t("angela.ph_input")}
          className="flex-1 bg-transparent text-[0.95rem] outline-none placeholder:text-tinta-suave/70 disabled:opacity-60"
        />
        <button
          onClick={() => enviar()}
          disabled={!input.trim() || pensando}
          className="grid h-11 w-11 place-items-center rounded-full bg-violeta text-crema transition-transform active:scale-90 disabled:opacity-40"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}

// P19·D — typewriter: la respuesta aparece escribiéndose (percepción de que
// Ángela está trabajando, sin tocar el backend). Solo anima el mensaje recién
// llegado; el historial se muestra entero.
function TextoAngela({ texto, animar }) {
  const [visible, setVisible] = useState(animar ? 0 : texto.length);
  useEffect(() => {
    if (!animar) return;
    setVisible(0);
    const id = setInterval(() => {
      setVisible((v) => {
        if (v >= texto.length) { clearInterval(id); return v; }
        return v + 3;
      });
    }, 14);
    return () => clearInterval(id);
  }, [texto, animar]);
  return <>{texto.slice(0, visible)}</>;
}

// P24·B — la entrega del documento EN el chat: al montar, el PDF se renderiza
// UNA vez en el server (con eso queda listado en Documentos, "pedido por" y
// todo); el botón descarga ese binario. Sin preview dentro de PolPilot: la
// única acción es DESCARGAR (el preview en pantalla descalzaba números).
function DocCard({ documento, t }) {
  const [estado, setEstado] = useState("generando"); // generando|listo|error
  const blobRef = useRef(null);
  useEffect(() => {
    let vivo = true;
    api.documentoPdf(documento)
      .then((b) => { if (vivo) { blobRef.current = b; setEstado("listo"); } })
      .catch(() => { if (vivo) setEstado("error"); });
    return () => { vivo = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const bajar = () => {
    if (!blobRef.current) return;
    const url = URL.createObjectURL(blobRef.current);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${documento.tipo || "documento"}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  };
  return (
    <div className="mt-2.5 flex items-center gap-3 rounded-xl border border-linea bg-papel px-3 py-2.5">
      <FileText size={18} className="shrink-0 text-violeta" />
      <div className="min-w-0 flex-1">
        <p className="truncate text-[0.88rem] font-semibold text-tinta">{documento.titulo}</p>
        <p className="text-[0.74rem] text-tinta-suave">{documento.subtitulo || documento.fecha || ""}</p>
      </div>
      {estado === "generando" && (
        <span className="shrink-0 text-[0.78rem] text-tinta-suave">{t("angela.doc_generando")}</span>
      )}
      {estado === "listo" && (
        <button onClick={bajar}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-violeta px-3.5 py-1.5 text-[0.8rem] font-semibold text-crema">
          {t("angela.doc_descargar")}
        </button>
      )}
      {estado === "error" && (
        <span className="shrink-0 text-[0.78rem] font-semibold text-rojo">{t("angela.doc_error")}</span>
      )}
    </div>
  );
}

// P19·D — el checklist del plan: los pasos YA corrieron en el server (en este
// orden, cada uno con su backup); acá se revelan uno a uno con su checkmark
// para que el trabajo se vea. Mientras revela, la esfera pasa a "ejecutando".
function PlanChecklist({ plan, onEjecutando }) {
  const [visibles, setVisibles] = useState(0);
  const pasos = plan.pasos || [];
  useEffect(() => {
    onEjecutando?.(true);
    let k = 0;
    const id = setInterval(() => {
      k += 1;
      setVisibles(k);
      if (k >= pasos.length) {
        clearInterval(id);
        onEjecutando?.(false);
      }
    }, 550);
    return () => { clearInterval(id); onEjecutando?.(false); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return (
    <div className="mt-2.5 space-y-1.5 border-t border-linea/70 pt-2.5">
      {pasos.slice(0, visibles).map((p, i) => (
        <div key={i} className="flex items-start gap-2 text-[0.88rem]">
          {p.ok ? (
            <Check size={15} className="mt-0.5 shrink-0 text-salvia" />
          ) : (
            <XCircle size={15} className="mt-0.5 shrink-0 text-rojo" />
          )}
          <span className={p.ok ? "text-tinta" : "text-rojo-hondo"}>
            {p.titulo}
            {p.detalle && <span className="text-tinta-suave"> — {p.detalle}</span>}
            {p.error && <span className="text-rojo-hondo"> — {p.error}</span>}
          </span>
        </div>
      ))}
      {visibles < pasos.length && (
        <p className="plata text-[0.78rem] font-semibold text-tinta-suave">
          {visibles}/{pasos.length}…
        </p>
      )}
    </div>
  );
}

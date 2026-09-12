// LA VOZ DEL PISO — el empleado habla, Ángela propone, un humano aprueba.
//
// El de depósito tiene una caja rota en la mano y el chofer está en la calle:
// ninguno de los dos va a tipear. Acá dictan.
//
// CÓMO TRANSCRIBE, y por qué así: la Web Speech API corre EN EL NAVEGADOR —
// el reconocimiento es real, gratis, sin backend nuevo y sin una segunda API
// key (la API de Anthropic no acepta audio ni transcribe). Donde no existe
// (Safari/iOS es irregular) o no hay red, quedan las frases preparadas del
// demo, que recorren exactamente la misma tubería.
//
// LO QUE ESTE COMPONENTE NO HACE: decidir. Manda el texto al backend, muestra
// lo que Ángela entendió, y hasta que una persona no toca "Confirmar" no se
// escribe nada. Si el backend marcó algo como bloqueado —una cantidad que no
// cierra, dos productos que matchean igual— el botón no se habilita. Eso NO
// cambió acá: lo único que se volvió conversacional es la rama `consulta`
// (una pregunta no escribe nada, nunca necesitó ese freno).
//
// THE CONVERSATIONAL PART: a question ("¿cuánto stock de aceite queda?")
// hands off to VoiceCallScreen — a full voice-call screen built on
// assistant-ui's own RealtimeVoiceAdapter (useVoiceState/useVoiceControls/
// useVoiceVolume), backed here by lib/voice/webSpeechVoiceAdapter.ts (Web
// Speech recognize/ask/speak, chained). Same shared component and adapter
// shape core/voz_viva.py's GPT-Live-1 flow uses (VozVivaRecepcion.jsx) —
// one state machine for "a live voice session with Ángela", two different
// things behind it.
import { useEffect, useRef, useState } from "react";
import { Mic, Square, X, Check, AlertTriangle } from "lucide-react";
import AngelaMark from "./AngelaMark";
import { useApiQuery, useApiMutation } from "../lib/query";
import { useT } from "../lib/i18n";
import { VoiceCallScreen } from "./voice/VoiceCallScreen";
import { createWebSpeechVoiceAdapter, isWebSpeechVoiceSupported } from "../lib/voice/webSpeechVoiceAdapter";

const Reconocimiento = typeof window !== "undefined"
  ? (window.SpeechRecognition || window.webkitSpeechRecognition)
  : null;

export default function VozAngela({ onCerrar, onListo, onPreguntar, rol }) {
  const t = useT();
  // listo|escuchando|pensando|propuesta|hecho
  const [paso, setPaso] = useState("listo");
  const [texto, setTexto] = useState("");
  const [prop, setProp] = useState(null);
  const [elegido, setElegido] = useState(null);
  const [cantidad, setCantidad] = useState("");
  const [error, setError] = useState(null);
  const rec = useRef(null);
  // La llamada conversacional (rama `consulta`): mientras esté activa,
  // VoiceCallScreen se hace cargo por completo — ver render() más abajo.
  const [call, setCall] = useState(null);   // { adapter, transcript } | null
  const muestrasQ = useApiQuery("vozMuestras");
  const escucharMut = useApiMutation("vozEscuchar");
  const confirmarMut = useApiMutation("vozConfirmar");
  const muestras = muestrasQ.data?.muestras || [];

  useEffect(() => {
    return () => { try { rec.current?.stop(); } catch { /* ya estaba parado */ } };
  }, []);

  const interpretar = async (frase) => {
    setPaso("pensando");
    setError(null);
    try {
      const r = await escucharMut.mutateAsync([frase]);
      if (!r.ok) { setError(r.motivo); setPaso("listo"); return; }
      if (r.intencion === "consulta") { startCall(frase); return; }
      setProp(r);
      setElegido(r.elegido ?? null);
      setCantidad(r.datos?.cantidad ?? "");
      setPaso("propuesta");
    } catch {
      setError(t("voz.err_red"));
      setPaso("listo");
    }
  };

  const appendToCall = (item) =>
    setCall((prev) => prev && {
      ...prev,
      transcript: [...prev.transcript, { id: `${prev.transcript.length}`, ...item }],
    });

  const startCall = (initialQuestion) => {
    if (!isWebSpeechVoiceSupported()) {
      // sin reconocimiento/síntesis en este navegador: la pregunta se
      // responde en el chat de texto, como siempre pudo.
      onPreguntar?.(initialQuestion);
      onCerrar?.();
      return;
    }
    const adapter = createWebSpeechVoiceAdapter({
      channel: "voz",
      initialQuestion,
      onTranscript: appendToCall,
    });
    setCall({ adapter, transcript: [{ id: "u0", role: "user", text: initialQuestion }] });
  };

  const endCall = () => {
    setCall(null);
    setPaso("listo");
  };

  const endCallWithError = () => {
    setCall(null);
    setError(t("voz.err_respuesta"));
    setPaso("listo");
  };

  const escuchar = () => {
    if (!Reconocimiento) { setError(t("voz.sin_soporte")); return; }
    setError(null);
    setTexto("");
    const r = new Reconocimiento();
    r.lang = "es-AR";              // el criollo del piso, no un español neutro
    r.interimResults = true;       // se ve escribir mientras habla: da confianza
    r.continuous = false;
    r.onresult = (e) => {
      const frase = Array.from(e.results).map((x) => x[0].transcript).join("");
      setTexto(frase);
      if (e.results[e.results.length - 1].isFinal) interpretar(frase);
    };
    r.onerror = (e) => {
      setError(e.error === "not-allowed" ? t("voz.sin_permiso") : t("voz.err_audio"));
      setPaso("listo");
    };
    r.onend = () => setPaso((p) => (p === "escuchando" ? "listo" : p));
    rec.current = r;
    setPaso("escuchando");
    r.start();
  };

  const confirmar = async () => {
    setPaso("pensando");
    try {
      await confirmarMut.mutateAsync([prop.intencion, {
        ...prop.datos,
        codigo: elegido,
        cantidad: cantidad === "" ? null : Number(cantidad),
      }, prop.transcripcion]);
      setPaso("hecho");
      onListo?.();
    } catch {
      setError(t("voz.err_red"));
      setPaso("propuesta");
    }
  };

  // El backend manda lo que un humano tiene que resolver; sin eso no se escribe.
  // Cada freno se levanta de UNA forma concreta:
  //   producto → eligiendo uno de los candidatos
  //   cantidad → escribiendo un número DISTINTO del que se frenó
  // (aceptar el mismo número sería el humano haciendo clic sin mirar, que es
  // justo lo que el freno viene a evitar)
  const frenos = prop?.bloqueado || [];
  const frenoCantidad = frenos.some((b) => b.campo === "cantidad");
  const frenoProducto = frenos.some((b) => b.campo === "producto");
  const cantidadCorregida = Number(cantidad) > 0
    && String(cantidad) !== String(prop?.datos?.cantidad ?? "");
  const puedeConfirmar = Boolean(
    prop && prop.intencion !== "consulta"
    && (!frenoProducto || elegido)
    && (!frenoCantidad || cantidadCorregida));

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-tinta/30 sm:items-center"
      onClick={onCerrar}>
      <div onClick={(e) => e.stopPropagation()}
        className="flex max-h-[92dvh] w-full max-w-lg flex-col overflow-hidden rounded-t-[var(--radius-card)]
                   border border-linea bg-papel sombra-alta sm:rounded-[var(--radius-card)]">
        <div className="flex items-center justify-between border-b border-linea bg-crema px-5 py-3">
          <h2 className="flex items-center gap-2 font-display text-lg font-bold">
            <Mic size={18} className="text-violeta" /> {t("voz.titulo")}
          </h2>
          <button onClick={onCerrar} aria-label={t("common.cerrar")} className="text-tinta-suave hover:text-tinta">
            <X size={18} />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-5">
          {call && (
            <VoiceCallScreen voice={call.adapter} transcript={call.transcript}
              onEnd={endCall} onError={endCallWithError} />
          )}

          {/* ---------------------------------------------- hablar */}
          {!call && (paso === "listo" || paso === "escuchando") && (
            <div className="space-y-4">
              <p className="text-sm leading-snug text-tinta-suave">{t("voz.ayuda")}</p>
              <button onClick={paso === "escuchando" ? () => rec.current?.stop() : escuchar}
                className={`flex w-full items-center justify-center gap-2.5 rounded-full px-5 py-4
                            text-base font-semibold text-crema transition-colors ${
                  paso === "escuchando" ? "bg-rojo" : "bg-violeta hover:bg-violeta-hondo"}`}>
                {paso === "escuchando"
                  ? <><Square size={18} /> {t("voz.parar")}</>
                  : <><Mic size={18} /> {t("voz.hablar")}</>}
              </button>
              {paso === "escuchando" && (
                <p className="rounded-xl border border-violeta/30 bg-violeta-suave px-3.5 py-2.5
                              text-base italic text-tinta">
                  {texto || t("voz.escuchando")}
                </p>
              )}
              {/* el plan B honesto: sin Web Speech o sin red, la misma tubería */}
              {muestras.length > 0 && paso === "listo" && (
                <div>
                  <p className="text-xs uppercase tracking-wide text-tinta-suave">
                    {t("voz.muestras")}
                  </p>
                  <div className="mt-1.5 space-y-1">
                    {muestras.filter((m) => !rol || m.rol === rol || !m.rol).map((m) => (
                      <button key={m.id} onClick={() => { setTexto(m.texto); interpretar(m.texto); }}
                        className="block w-full rounded-xl border border-linea bg-crema px-3.5 py-2.5
                                   text-left hover:bg-papel-hondo/60">
                        {/* el título se traduce acá; la frase dictada es dato */}
                        <span className="block text-sm font-semibold text-tinta">
                          {t(`vozmuestra.${m.id}`)}
                        </span>
                        <span className="block text-sm italic leading-snug text-tinta-suave">
                          «{m.texto}»
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {error && (
                <p className="rounded-xl border border-oro/30 bg-oro/[0.08] px-3.5 py-2 text-sm">
                  {error}
                </p>
              )}
            </div>
          )}

          {!call && paso === "pensando" && (
            <div className="flex items-center justify-center gap-3 py-10">
              <AngelaMark size={30} estado="ejecutando" />
              <p className="text-sm text-tinta-suave">{t("voz.pensando")}</p>
            </div>
          )}

          {/* ------------------------------------------- la propuesta */}
          {!call && paso === "propuesta" && prop && (
            <div className="space-y-4">
              <p className="rounded-xl bg-papel-hondo px-3.5 py-2.5 text-sm italic text-tinta-suave">
                «{prop.transcripcion}»
              </p>

              <div className="flex items-start gap-2.5">
                <AngelaMark size={26} />
                <p className="text-base leading-snug text-tinta">
                  {t(`voz.entendi_${prop.intencion}`)}
                </p>
              </div>

              {/* el producto: se elige, no se adivina */}
              {prop.candidatos?.length > 0 && (
                <div>
                  <p className="text-xs uppercase tracking-wide text-tinta-suave">
                    {t("voz.f_producto")}
                  </p>
                  <div className="mt-1 space-y-1">
                    {prop.candidatos.map((c) => (
                      <button key={c.codigo} onClick={() => setElegido(c.codigo)}
                        className={`flex w-full items-center gap-2 rounded-xl border px-3 py-2 text-left
                                    text-sm ${elegido === c.codigo
                            ? "border-violeta bg-violeta-suave font-semibold text-tinta"
                            : "border-linea bg-crema text-tinta-suave hover:bg-papel-hondo/60"}`}>
                        <span className="min-w-0 flex-1 truncate">{c.descripcion}</span>
                        {elegido === c.codigo && <Check size={15} className="shrink-0 text-violeta" />}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex items-center gap-3">
                <label className="text-xs uppercase tracking-wide text-tinta-suave">
                  {t("voz.f_cantidad")}
                </label>
                <input value={cantidad} inputMode="decimal"
                  onChange={(e) => setCantidad(e.target.value)}
                  className="plata w-24 rounded-lg border border-linea bg-crema px-2.5 py-1.5
                             text-right text-base" />
              </div>

              {/* lo que el CÓDIGO frenó: se dice y se explica */}
              {frenos.map((b, i) => (
                <p key={i} className="flex gap-2 rounded-xl border border-oro/40 bg-oro/[0.09]
                                      px-3.5 py-2.5 text-sm leading-snug text-tinta">
                  <AlertTriangle size={15} className="mt-0.5 shrink-0 text-oro-tinta" />
                  {b.detalle}
                </p>
              ))}

              <div className="flex flex-wrap gap-2 pt-1">
                <button onClick={confirmar} disabled={!puedeConfirmar}
                  className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2.5
                             text-sm font-semibold text-crema disabled:opacity-40">
                  <Check size={15} /> {t("voz.confirmar")}
                </button>
                <button onClick={() => { setProp(null); setPaso("listo"); }}
                  className="rounded-full border border-linea bg-crema px-4 py-2.5
                             text-sm font-semibold text-tinta-suave">
                  {t("voz.otra_vez")}
                </button>
              </div>
            </div>
          )}

          {!call && paso === "hecho" && (
            <div className="space-y-4 py-4 text-center">
              <span className="mx-auto grid h-11 w-11 place-items-center rounded-full bg-salvia text-crema">
                <Check size={20} />
              </span>
              <p className="text-base text-tinta">{t("voz.anotado")}</p>
              <button onClick={onCerrar}
                className="rounded-full border border-linea bg-crema px-4 py-2.5 text-sm
                           font-semibold text-tinta-suave">
                {t("voz.cerrar")}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

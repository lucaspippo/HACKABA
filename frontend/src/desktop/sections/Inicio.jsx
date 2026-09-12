import { useEffect, useRef } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { useAui, useAuiState } from "@assistant-ui/react";
import ChatPanel from "../../views/ChatPanel";
import { useApiQuery } from "../../lib/query";
import { authStore, useSession } from "../../lib/auth";
import { pesoCorto } from "../../lib/format";
import { useT, useLang } from "../../lib/i18n";
import { estiloAccion } from "../../lib/prioridadAccion";

const MAX_PRIORIDADES = 3;

function primerNombre(nombre) {
  if (!nombre) return "";
  return String(nombre).trim().split(/\s+/)[0] || "";
}

function HomeLanding({ onNavegar }) {
  const t = useT();
  const lang = useLang();
  const aui = useAui();
  const session = useSession();
  const nombre = primerNombre(session?.usuario?.nombre);
  const puedePrioridades = authStore.tiene("alertas") || authStore.tiene("oportunidades");

  const prioQ = useApiQuery("prioridades", [], { enabled: puedePrioridades });
  const prio = prioQ.data;
  const prioError = prioQ.isError;
  const identityRef = useRef({ token: session?.token, lang });

  useEffect(() => {
    if (!puedePrioridades) return;
    if (identityRef.current.token === session?.token && identityRef.current.lang === lang) return;
    identityRef.current = { token: session?.token, lang };
    prioQ.refetch();
  }, [puedePrioridades, session?.token, lang, prioQ.refetch]);

  const pendientes = (prio?.act || []).filter((item) => !item.action_taken);
  const hoy = pendientes.slice(0, MAX_PRIORIDADES);
  const cargando = puedePrioridades && !prio && !prioError;

  const preguntar = (texto) => {
    if (!texto) return;
    aui.thread.append(texto);
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex flex-1 flex-col items-center justify-center">
        <motion.h1
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: [0.23, 1, 0.32, 1] }}
          className="max-w-3xl text-balance text-center font-display text-[2.35rem] font-bold leading-[1.15] tracking-tight text-tinta motion-reduce:transition-none sm:text-5xl"
        >
          {nombre ? t("inicio.hero_hoy", { nombre }) : t("inicio.hero_hoy_anon")}
        </motion.h1>
      </div>

      {(cargando || hoy.length > 0) && (
        <div className="mb-2 flex w-full flex-col items-stretch gap-2.5">
          {cargando
            ? [0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="skeleton mx-auto h-11 rounded-full"
                  style={{ width: `${92 - i * 10}%` }}
                />
              ))
            : hoy.map((item) => {
                const estilo = estiloAccion(item);
                const Icon = estilo.icon;
                const cifra =
                  item.monto != null && item.monto > 0
                    ? pesoCorto(item.monto)
                    : item.cifra_texto || null;
                const pregunta =
                  item.accion_chat ||
                  t("inicio.prio_preguntar", { titulo: item.titulo });
                return (
                  <button
                    key={item.id}
                    type="button"
                    title={item.resumen || item.titulo}
                    onClick={() => preguntar(pregunta)}
                    className="flex w-full items-center gap-3 rounded-full border border-linea bg-crema/95 px-3.5 py-2 text-left sombra-papel transition-colors hover:border-tinta/25 hover:bg-crema"
                  >
                    <span
                      className={`grid size-8 shrink-0 place-items-center rounded-full ${estilo.cls}`}
                    >
                      <Icon size={15} />
                    </span>
                    <span className="min-w-0 flex-1 truncate text-sm font-semibold text-tinta">
                      {item.titulo}
                    </span>
                    {cifra && (
                      <span className="plata shrink-0 text-sm font-medium text-tinta">
                        {cifra}
                      </span>
                    )}
                  </button>
                );
              })}
          {!cargando && pendientes.length > MAX_PRIORIDADES && (
            <button
              type="button"
              onClick={() => onNavegar("prioridades")}
              className="mt-1 inline-flex items-center justify-center gap-1 self-center text-sm font-semibold text-tinta-suave transition-colors hover:text-tinta"
            >
              {t("inicio.ver_prioridades")} <ArrowRight size={13} />
            </button>
          )}
        </div>
      )}
    </div>
  );
}

const WASH_FADE = { duration: 0.35, ease: "easeOut" };

export default function Inicio({ onNavegar, onDatosCambiaron }) {
  const isEmpty = useAuiState((s) => s.thread.isEmpty);
  const reduceMotion = useReducedMotion();

  return (
    <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden px-8 pb-6">
      <AnimatePresence>
        {isEmpty && (
          <motion.div
            key="inicio-wash"
            aria-hidden
            className="inicio-wash"
            initial={reduceMotion ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={reduceMotion ? { opacity: 1 } : { opacity: 0 }}
            transition={WASH_FADE}
          />
        )}
      </AnimatePresence>
      <div className="relative z-10 flex min-h-0 flex-1 flex-col">
        <ChatPanel
          variant="home"
          emptyState={<HomeLanding onNavegar={onNavegar} />}
          onNavigate={onNavegar}
          onDatosCambiaron={onDatosCambiaron}
        />
      </div>
    </div>
  );
}

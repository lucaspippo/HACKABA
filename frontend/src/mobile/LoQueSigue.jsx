import { ArrowRight, Sparkles } from "lucide-react";
import AngelaMark from "../components/AngelaMark";
import { pesoCorto } from "../lib/format";
import { useT } from "../lib/i18n";

// LO QUE SIGUE — el bloque donde la imagen de referencia pone «Próxima entrega».
//
// El dueño no entrega nada, así que ahí no puede ir una entrega. Lo que va es
// lo que le corresponda a cada uno, y la regla es la misma en todos: **lo
// próximo que esta persona va a tener enfrente.**
//
//   · el chofer      → su próxima parada
//   · el que arma    → el próximo pedido a armar
//   · el dueño       → el hallazgo de más peso del día
//
// Adentro, la banda de la imagen: una franja al pie, en azul Ángela porque es
// suya y ése es el único caso en que el azul corresponde (DESIGN.md, One
// Meaning Rule).
//
// LA BANDA TIENE DOS MODOS, Y NO ES UN CAPRICHO. Dice «PolPilot recomienda»
// sólo cuando hay una recomendación DE VERDAD —`insight.recommendation.detail`,
// que Ángela escribió— y en ese caso muestra ese texto. Cuando no la hay,
// muestra la misma franja pero rotulada como lo que es: preguntarle. Poner
// «PolPilot recomienda» arriba del prompt que se le MANDA a Ángela sería
// ponerle en la boca un consejo que no dio — y en este dataset hoy ninguna card
// de oportunidades trae `recommendation.detail`, así que sería siempre.

export default function LoQueSigue({ titulo, icono: Icono, principal, detalle,
                                     monto, recomienda, pregunta, onRecomienda,
                                     onAbrir, verLk }) {
  const t = useT();
  if (!principal) return null;

  return (
    <section>
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <h2 className="font-display text-lg font-bold">{titulo}</h2>
        {onAbrir && verLk && (
          <button onClick={onAbrir} className="text-sm font-semibold text-tinta-suave">
            {t(verLk)}
          </button>
        )}
      </div>

      <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
        <div className="flex items-start gap-3 px-4 py-3.5">
          {Icono && (
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-papel-hondo text-tinta">
              <Icono size={18} strokeWidth={1.9} />
            </span>
          )}
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold leading-snug text-tinta">{principal}</p>
            {detalle?.length > 0 && (
              <p className="mt-0.5 flex flex-wrap gap-x-3 text-xs leading-snug text-tinta-suave">
                {detalle.filter(Boolean).map((d, i) => <span key={i}>{d}</span>)}
              </p>
            )}
          </div>
          {monto ? (
            <span className="plata shrink-0 text-sm font-medium text-tinta">{pesoCorto(monto)}</span>
          ) : null}
        </div>

        {/* La banda de la recomendación. Es de Ángela y se ve que es de ella:
            su marca, su azul, su texto. Nunca se ejecuta sola — abre el chat
            con la propuesta escrita y la persona decide. */}
        {(recomienda || pregunta) && (
          <button onClick={onRecomienda}
            className="flex w-full items-start gap-2.5 border-t border-violeta/20 bg-violeta/[0.06] px-4 py-3 text-left active:scale-[0.99]">
            <AngelaMark size={24} estado="esperando" />
            <span className="min-w-0 flex-1">
              <span className="block text-2xs font-semibold uppercase tracking-wide text-violeta">
                {recomienda ? t("sigue.recomienda") : t("sigue.preguntarle")}
              </span>
              <span className="block text-sm leading-snug text-tinta">
                {recomienda || pregunta}
              </span>
            </span>
            <ArrowRight size={15} className="mt-0.5 shrink-0 text-violeta" />
          </button>
        )}
      </div>
    </section>
  );
}

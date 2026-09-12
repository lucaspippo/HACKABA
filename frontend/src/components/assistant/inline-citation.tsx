"use client";

import type { ReactNode } from "react";
import { Popover } from "@base-ui/react/popover";
import { cn } from "@/lib/utils";
import { floating, mono } from "./surfaces";

export interface Source {
  domain: string;
  title: string;
  snippet: string;
  detail?: string;
}

// El blanco del toque es más grande que el ícono: 15×13px medidos en
// producción es un objetivo que se falla con el dedo, y en el
// escenario se toca con el dedo o con el mouse apurado.
//
// Shared with the loading placeholder so the chip keeps this exact geometry
// when the piece arrives and it turns into a real trigger: the sentence must
// not reflow under the reader mid-read.
const CHIP =
  "mx-0.5 inline-flex h-[18px] min-w-[18px] translate-y-[-2px] items-center justify-center rounded-[5px] px-1 align-middle font-mono text-xs font-medium tabular-nums transition-colors";

/**
 * Una cita al lado de una frase de Ángela: se toca y se ve de dónde salió.
 *
 * ABRE CON CLIC, Y ESO NO ES UN DETALLE.
 *
 * Esto usaba `PreviewCard`, que es un HOVER card: no tiene manejador de clic.
 * Medido en el navegador contra el deploy, con la respuesta del demo abierta:
 * al pasar el mouse por encima el panel aparecía —existía en el DOM, entero
 * dentro de la pantalla, en (1110,169) de 205×266— y al hacer CLIC no pasaba
 * absolutamente nada. Con el dedo, donde no hay hover, nunca pasaba nada.
 *
 * Y este es el momento del pitch donde se prueba que la regla se aprendió y no
 * se inventó. Una cita que sólo se abre si el mouse se queda quieto encima es
 * una cita decorativa.
 *
 * `Popover` es el primitivo que corresponde: abre con clic (y con Enter y con
 * Espacio, porque el trigger es un botón de verdad), cierra con Escape o
 * tocando afuera, y reposiciona solo cuando no entra —que es lo que pasa en el
 * panel angosto del grafo, de 300px. El hover se mantiene como atajo opcional,
 * con retardo, pero ya no es la única forma de abrirlo.
 *
 * El estado abierto se lee del atributo `data-popup-open` que pone Base UI, no
 * de un `useState` nuestro: un `open` controlado sin `triggerId` es justamente
 * la otra forma de que esto no se vea.
 */
export function Citation({
  label,
  ariaLabel,
  source,
  tone = "neutral",
  loading = false,
  onOpen,
  openLabel,
}: {
  label: ReactNode;
  ariaLabel?: string;
  source?: Source;
  tone?: "neutral" | "knowledge";
  loading?: boolean;
  onOpen?: () => void;
  openLabel?: string;
}) {
  // While the piece is still in flight there is nothing to preview, so the
  // chip is deliberately NOT a button: a control that opens an empty panel
  // reads as broken, and a screen reader would announce it as available.
  if (loading || !source) {
    return (
      <span
        role="status"
        aria-busy="true"
        aria-label={ariaLabel}
        className={cn(
          CHIP,
          tone === "knowledge"
            ? "bg-oro/10 text-oro-tinta/40"
            : "bg-foreground/[0.04] text-foreground/25",
        )}
      >
        {label}
      </span>
    );
  }

  return (
    <Popover.Root>
      <Popover.Trigger
        openOnHover
        delay={140}
        closeDelay={120}
        render={<button type="button" aria-label={ariaLabel} />}
        className={cn(
          CHIP,
          "cursor-pointer",
          tone === "knowledge"
            ? "bg-oro/15 text-oro-tinta hover:bg-oro/30 data-[popup-open]:bg-oro-tinta data-[popup-open]:text-crema"
            : "bg-foreground/[0.06] text-foreground/45 hover:text-foreground/90 data-[popup-open]:bg-foreground data-[popup-open]:text-background",
        )}
      >
        {label}
      </Popover.Trigger>
      <Popover.Portal>
        {/* EL z-index VA ACA, EN EL POSITIONER, Y NO EN EL POPUP.
            El Popup es `position: static`, asi que su `z-50` no hacia
            absolutamente nada: z-index solo tiene efecto sobre un elemento
            posicionado. El que se posiciona es el Positioner, y venia con
            `z-index: auto`.
            Como el popup se portalea al <body>, queda de HERMANO de la
            pantalla del grafo, que es `fixed inset-0 z-[140]`. Con z auto
            pierde: el panel se abria, existia, estaba «visible» con opacidad
            1 y en la posicion correcta, y se dibujaba DEBAJO de toda la
            pantalla. Medido con elementFromPoint en el centro del panel: el
            elemento de arriba era un <dt> de la tarjeta de herramienta, no el
            panel. Por eso no se veia ni con clic ni con hover.
            200 > 140, y por encima tambien del panel de la seccion. */}
        <Popover.Positioner side="top" sideOffset={8} collisionPadding={12}
                            className="z-[200]">
          <Popover.Popup
            className={cn(
              floating,
              // EN PIXELES, NO EN rem: la app lleva la raiz a 12.8px, asi que
              // `w-64` (16rem) daba 204,8px —medido— y el panel quedaba mas
              // angosto que el panel del chat, con astillas de la tarjeta de
              // atras asomando a los dos costados. Se lee amontonado.
              "w-[300px] max-w-[calc(100vw-24px)] origin-(--transform-origin) rounded-2xl p-3.5 outline-none",
              // La SOMBRA no es decoracion: sin ella el panel tiene el mismo
              // fondo que la pagina y se lee como una tarjeta mas del hilo, no
              // como algo que se abrio encima.
              "shadow-[0_14px_38px_-10px_rgba(33,32,29,.3)]",
              "transition-[opacity,scale] duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none",
              "data-[starting-style]:scale-[0.97] data-[starting-style]:opacity-0",
              "data-[ending-style]:scale-[0.97] data-[ending-style]:opacity-0",
            )}
          >
            <div className="flex items-center gap-1.5">
              <span className="bg-foreground/[0.06] text-foreground/45 flex size-4 items-center justify-center rounded text-xs font-medium">
                {source.domain[0]?.toUpperCase()}
              </span>
              <span className={cn(mono, "text-foreground/40")}>{source.domain}</span>
            </div>
            <p className="mt-2 text-lg leading-snug font-medium">{source.title}</p>
            <p className="text-foreground/50 mt-1 text-lg leading-relaxed">
              {source.snippet}
            </p>
            {source.detail && (
              <p className="text-foreground/40 mt-1 text-sm leading-relaxed">
                {source.detail}
              </p>
            )}
            {/* The hand-off to the full memory panel. It is a second, explicit
                step and NOT the chip's own click: the click already opens this
                preview, and that is the interaction the touch fix above bought.
                Closing first matters — otherwise the preview stays floating
                over the panel it just opened. */}
            {onOpen && openLabel && (
              <Popover.Close
                render={<button type="button" />}
                onClick={onOpen}
                className={cn(
                  "mt-2.5 flex w-full cursor-pointer items-center justify-between gap-2 rounded-lg px-2 py-1.5 text-left text-sm font-medium transition-colors",
                  "text-oro-tinta bg-oro/10 hover:bg-oro/20",
                )}
              >
                {openLabel}
                <span aria-hidden>→</span>
              </Popover.Close>
            )}
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  );
}

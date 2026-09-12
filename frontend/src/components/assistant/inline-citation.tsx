"use client";

import type { ReactNode } from "react";
import { Popover } from "@base-ui/react/popover";
import { cn } from "@/lib/utils";

/** The rule itself leads: `heading` is what Ángela cited, not a source label. */
export interface Source {
  heading: string;
  meta?: string;
  detail?: string;
}

// El blanco del toque es más grande que el ícono: 15×13px medidos en
// producción es un objetivo que se falla con el dedo, y en el
// escenario se toca con el dedo o con el mouse apurado.
//
// Shared with the loading placeholder so the chip keeps this exact geometry
// when the piece arrives and it turns into a real trigger: the sentence must
// not reflow under the reader mid-read.
const CHIP = cn(
  "mx-0.5 inline-flex h-5 min-w-5 translate-y-px items-center justify-center rounded-full px-1 align-middle ring-1 transition-colors",
  "outline-none focus-visible:ring-2 focus-visible:ring-violeta",
);

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
          "cursor-default",
          tone === "knowledge"
            ? "bg-crema text-oro-tinta/40 ring-oro/20"
            : "bg-crema text-tinta-suave/40 ring-linea",
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
            ? "bg-crema text-oro-tinta ring-oro/45 hover:bg-oro/15 hover:ring-oro/70 data-[popup-open]:bg-oro/20 data-[popup-open]:ring-oro"
            : "bg-crema text-tinta-suave ring-linea hover:text-tinta data-[popup-open]:bg-tinta data-[popup-open]:text-crema data-[popup-open]:ring-tinta",
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
              // EN PIXELES, NO EN rem: la app lleva la raiz a 12.8px, asi que
              // `w-64` (16rem) daba 204,8px —medido— y el panel quedaba mas
              // angosto que el panel del chat, con astillas de la tarjeta de
              // atras asomando a los dos costados. Se lee amontonado.
              "w-[280px] max-w-[calc(100vw-24px)] origin-(--transform-origin) rounded-xl px-3.5 py-2.5 outline-none",
              // Dark surface, as in polpilot-app: the preview has to read as
              // something that opened ON TOP of the thread, not as one more
              // card in it. On this ground the shadow alone was not enough.
              "bg-tinta text-crema sombra-alta",
              "transition-[opacity,scale] duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none",
              "data-[starting-style]:scale-[0.97] data-[starting-style]:opacity-0",
              "data-[ending-style]:scale-[0.97] data-[ending-style]:opacity-0",
            )}
          >
            {/* A square turned 45° reads the same from either side, so the
                arrow needs no per-side flip — Base UI only has to place it. */}
            <Popover.Arrow>
              <span className="block size-2 rotate-45 bg-tinta" />
            </Popover.Arrow>
            <p className="text-sm leading-snug font-semibold text-crema">
              {source.heading}
            </p>
            {source.meta && (
              <p className="mt-1.5 text-xs leading-snug text-crema/75">{source.meta}</p>
            )}
            {source.detail && (
              <p className="mt-1 text-xs leading-snug text-crema/65">{source.detail}</p>
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
                  "mt-2.5 flex w-full cursor-pointer items-center justify-between gap-2 rounded-lg px-2 py-1.5 text-left text-xs font-medium transition-colors",
                  "bg-crema/10 text-crema/80 hover:bg-crema/20 hover:text-crema",
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

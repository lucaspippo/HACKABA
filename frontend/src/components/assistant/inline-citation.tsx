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
}: {
  label: ReactNode;
  ariaLabel?: string;
  source: Source;
  tone?: "neutral" | "knowledge";
}) {
  return (
    <Popover.Root>
      <Popover.Trigger
        openOnHover
        delay={140}
        closeDelay={120}
        render={<button type="button" aria-label={ariaLabel} />}
        className={cn(
          // El blanco del toque es más grande que el ícono: 15×13px medidos en
          // producción es un objetivo que se falla con el dedo, y en el
          // escenario se toca con el dedo o con el mouse apurado.
          "mx-0.5 inline-flex h-[18px] min-w-[18px] translate-y-[-2px] cursor-pointer items-center justify-center rounded-[5px] px-1 align-middle font-mono text-xs font-medium tabular-nums transition-colors",
          tone === "knowledge"
            ? "bg-oro/15 text-oro-tinta hover:bg-oro/30 data-[popup-open]:bg-oro-tinta data-[popup-open]:text-crema"
            : "bg-foreground/[0.06] text-foreground/45 hover:text-foreground/90 data-[popup-open]:bg-foreground data-[popup-open]:text-background",
        )}
      >
        {label}
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Positioner side="top" sideOffset={8} collisionPadding={12}>
          <Popover.Popup
            className={cn(
              floating,
              "z-50 w-64 max-w-[min(16rem,calc(100vw-24px))] origin-(--transform-origin) rounded-2xl p-3.5 outline-none",
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
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  );
}

"use client";

import type { ComponentProps } from "react";
import { BrainIcon, CheckIcon, ClockIcon, XIcon } from "lucide-react";
import { cn } from "@/lib/utils";

// A proposal is a decision the user still owes us, so it wears `oro`; once
// taken it wears `salvia` (kept) or stays `oro` muted (queued for someone
// else's review). Same two meanings those tokens carry everywhere else.
//
// These sit OUTSIDE the message bubble (AssistantMessage), on the page —
// crema + ring, never a wash on crema. StatusPill's pairing: ring + dot.
export type MemoryChange = "proposed" | "saved" | "pending" | "existing";

export interface MemoryChip {
  id: string;
  text: string;
  change: MemoryChange;
  // Present only when the model suggested a real effect: "id" here is a
  // client-side key, not a server id — nothing is saved yet on either branch.
  narrativeAlternative?: { id: string; text: string };
}

export interface MemoryChipsLabels {
  memory: string;
  remembered: (n: number) => string;
  save: (text: string) => string;
  dismiss: (text: string) => string;
  keep: string;
  discard: string;
  saved: string;
  pending: string;
  applyRuleLabel: string;
  contextOnlyLabel: string;
  saveAsRule?: (text: string) => string;
  saveAsContext?: (text: string) => string;
}

const TONE: Record<MemoryChange, string> = {
  proposed: "text-oro-tinta ring-oro/35",
  saved: "text-salvia ring-salvia/30",
  pending: "text-oro-tinta ring-oro/25",
  existing: "text-tinta-suave ring-linea",
};

const DOT: Record<MemoryChange, string> = {
  proposed: "bg-oro",
  saved: "bg-salvia",
  pending: "bg-oro",
  existing: "bg-tinta-suave/50",
};

const actionButton =
  "inline-flex h-8 shrink-0 items-center justify-center rounded-xl px-2.5 text-xs font-semibold outline-none transition-colors focus-visible:ring-2 focus-visible:ring-violeta/40";

export function MemoryChips({
  chips,
  labels,
  onSave,
  onDismiss,
  className,
  ...props
}: Omit<
  ComponentProps<"div">,
  "children" | "chips" | "labels" | "onSave" | "onDismiss"
> & {
  chips: readonly MemoryChip[];
  labels: MemoryChipsLabels;
  onSave?: (id: string) => void;
  onDismiss?: (id: string) => void;
}) {
  const kept = chips.filter((chip) => chip.change === "saved").length;

  return (
    <div
      data-slot="memory-chips"
      className={cn("relative z-10 flex w-full flex-col gap-2", className)}
      {...props}
    >
      <div className="flex items-center gap-1.5">
        <BrainIcon className="size-3.5 text-oro-tinta" />
        <span className="text-xs font-semibold text-oro-tinta">
          {kept > 0 ? labels.remembered(kept) : labels.memory}
        </span>
      </div>

      <div className="flex flex-col gap-2">
        {chips.map((chip) => (
          <div
            key={chip.id}
            className={cn(
              "flex w-full flex-col gap-2 rounded-xl bg-crema px-3 py-2.5 ring-1 sombra-papel",
              TONE[chip.change],
            )}
          >
            <div className="flex items-start gap-2">
              <span
                aria-hidden
                className={cn("mt-1.5 size-2 shrink-0 rounded-full", DOT[chip.change])}
              />
              <p className="min-w-0 flex-1 text-sm font-semibold leading-snug">
                {chip.text}
              </p>
              {chip.change === "saved" && (
                <CheckIcon aria-label={labels.saved} className="mt-0.5 size-3.5 shrink-0" />
              )}
              {chip.change === "pending" && (
                <ClockIcon aria-label={labels.pending} className="mt-0.5 size-3.5 shrink-0" />
              )}
            </div>

            {chip.change === "proposed" && (
              <div className="flex flex-wrap items-center gap-1.5 pl-4">
                {chip.narrativeAlternative ? (
                  <>
                    <button
                      type="button"
                      aria-label={labels.saveAsRule?.(chip.text) ?? labels.save(chip.text)}
                      onClick={() => onSave?.(chip.id)}
                      className={cn(actionButton, "bg-tinta text-crema hover:bg-tinta/90")}
                    >
                      {labels.applyRuleLabel}
                    </button>
                    <button
                      type="button"
                      aria-label={labels.saveAsContext?.(chip.text) ?? labels.save(chip.text)}
                      onClick={() => onSave?.(chip.narrativeAlternative!.id)}
                      className={cn(
                        actionButton,
                        "bg-papel text-tinta ring-1 ring-linea hover:bg-papel-hondo",
                      )}
                    >
                      {labels.contextOnlyLabel}
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    aria-label={labels.save(chip.text)}
                    onClick={() => onSave?.(chip.id)}
                    className={cn(actionButton, "bg-tinta text-crema hover:bg-tinta/90")}
                  >
                    <CheckIcon className="mr-1 size-3" />
                    {labels.keep}
                  </button>
                )}
                <button
                  type="button"
                  aria-label={labels.dismiss(chip.text)}
                  onClick={() => onDismiss?.(chip.id)}
                  className={cn(
                    actionButton,
                    "gap-1 text-tinta-suave ring-1 ring-linea hover:bg-papel-hondo hover:text-tinta",
                  )}
                >
                  <XIcon className="size-3" />
                  {labels.discard}
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

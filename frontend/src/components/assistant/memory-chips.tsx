"use client";

import type { ComponentProps } from "react";
import { BrainIcon, CheckIcon, ClockIcon, XIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { field, ghostButton, mono } from "./surfaces";

// A proposal is a decision the user still owes us, so it wears `oro`; once
// taken it wears `salvia` (kept) or stays `oro` muted (queued for someone
// else's review). Same two meanings those tokens carry everywhere else.
export type MemoryChange = "proposed" | "saved" | "pending" | "existing";

export interface MemoryChip {
  id: string;
  text: string;
  change: MemoryChange;
}

export interface MemoryChipsLabels {
  memory: string;
  remembered: (n: number) => string;
  save: (text: string) => string;
  dismiss: (text: string) => string;
  saved: string;
  pending: string;
}

const TONE: Record<MemoryChange, string> = {
  proposed: "bg-oro/10 text-oro-tinta",
  saved: "bg-salvia/10 text-salvia",
  pending: "bg-oro/[0.07] text-oro-tinta/80",
  existing: "",
};

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
      className={cn("flex w-full max-w-sm flex-col gap-2", className)}
      {...props}
    >
      <div className="flex items-center gap-1.5">
        <BrainIcon className="size-3.5 text-oro-tinta/50" />
        <span className={cn(mono, "text-foreground/35")}>
          {kept > 0 ? labels.remembered(kept) : labels.memory}
        </span>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {chips.map((chip) => (
          <span
            key={chip.id}
            className={cn(
              "fade-in zoom-in-95 animate-in fill-mode-both group flex max-w-full items-center gap-1 rounded-full py-1 pr-1 pl-2.5 text-xs duration-300",
              chip.change === "existing"
                ? cn(field, "text-foreground/55")
                : TONE[chip.change],
            )}
          >
            <span className="min-w-0 truncate">{chip.text}</span>

            {chip.change === "proposed" && (
              <>
                <button
                  type="button"
                  aria-label={labels.save(chip.text)}
                  onClick={() => onSave?.(chip.id)}
                  className={cn(ghostButton, "size-4 shrink-0")}
                >
                  <CheckIcon className="size-2.5" />
                </button>
                <button
                  type="button"
                  aria-label={labels.dismiss(chip.text)}
                  onClick={() => onDismiss?.(chip.id)}
                  className={cn(ghostButton, "size-4 shrink-0")}
                >
                  <XIcon className="size-2.5" />
                </button>
              </>
            )}

            {chip.change === "saved" && (
              <CheckIcon aria-label={labels.saved} className="size-2.5 shrink-0" />
            )}
            {chip.change === "pending" && (
              <ClockIcon aria-label={labels.pending} className="size-2.5 shrink-0" />
            )}
          </span>
        ))}
      </div>
    </div>
  );
}

"use client";

import type { ComponentProps } from "react";
import { PauseIcon, PlayIcon, Volume2Icon } from "lucide-react";
import { cn } from "@/lib/utils";
import { field, ghostButton, mono, paper } from "../../lib/surfaces";
import { announced, pct } from "../../lib/range";

export interface ReadAloudLabels {
  play: string;
  pause: string;
  progress: string;
  speed: (rate: number) => string;
}

export function ReadAloud({
  words,
  spokenIndex,
  playing,
  rate,
  elapsed,
  labels,
  onToggle,
  onRateChange,
  className,
  ...props
}: Omit<
  ComponentProps<"div">,
  | "children"
  | "words"
  | "spokenIndex"
  | "playing"
  | "rate"
  | "elapsed"
  | "labels"
  | "onToggle"
  | "onRateChange"
> & {
  words: readonly string[];
  spokenIndex: number;
  playing: boolean;
  rate: number;
  elapsed: string;
  labels: ReadAloudLabels;
  onToggle?: () => void;
  onRateChange?: () => void;
}) {
  const progress = pct(spokenIndex, words.length);

  return (
    <div
      data-slot="read-aloud"
      className={cn(
        paper,
        "flex w-full max-w-sm flex-col gap-3 rounded-2xl p-3.5",
        className,
      )}

      {...props}
    >
      <p className="text-[13.5px] leading-relaxed">
        {words.map((word, i) => (
          <span
            key={`${i}-${word}`}
            className={cn(
              "transition-colors duration-200 motion-reduce:transition-none",
              i < spokenIndex
                ? "text-foreground/40"
                : i === spokenIndex
                  ? "rounded bg-violeta/10 text-foreground/95"
                  : "text-foreground/70",
            )}
          >
            {word}{" "}
          </span>
        ))}
      </p>

      <div className="flex items-center gap-2.5">
        <button
          type="button"
          aria-label={playing ? labels.pause : labels.play}
          onClick={onToggle}
          className={cn(ghostButton, "bg-foreground/6 size-8 shrink-0")}
        >
          {playing ? (
            <PauseIcon className="size-3.5" />
          ) : (
            <PlayIcon className="size-3.5 translate-x-px" />
          )}
        </button>

        <span
          role="progressbar"
          aria-label={labels.progress}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={announced(progress)}
          aria-valuetext={elapsed}
          className="bg-foreground/8 h-0.75 min-w-0 flex-1 overflow-hidden rounded-full"
        >
          <span
            className="block h-full rounded-full bg-violeta transition-[width] duration-200 ease-linear motion-reduce:transition-none"
            style={{ width: `${progress}%` }}
          />
        </span>

        <span className={cn(mono, "text-foreground/35 shrink-0 tabular-nums")}>
          {elapsed}
        </span>

        <button
          type="button"
          aria-label={labels.speed(rate)}
          onClick={onRateChange}
          className={cn(
            field,
            mono,
            "text-foreground/55 hover:text-foreground/90 shrink-0 rounded-full px-2 py-1 tabular-nums transition-colors",
          )}
        >
          {rate}×
        </button>

        <Volume2Icon className="text-foreground/25 size-3.5 shrink-0" />
      </div>
    </div>
  );
}

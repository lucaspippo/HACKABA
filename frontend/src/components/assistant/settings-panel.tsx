"use client";

import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

// The registry ships this with model / system-prompt / temperature controls
// too. None of them apply here: the model comes from config.modelo_para() and
// the prompt is assembled server-side in angela.py, neither of which a user
// picks. Left commented rather than deleted so re-adding one is a diff, not a
// re-download.
//
// import { field, mono, paper } from "./surfaces";
// import { clamp } from "./range";

export interface SettingToggle {
  key: string;
  label: string;
  detail: string;
  on: boolean;
}

export function SettingsPanel({
  toggles,
  onToggle,
  className,
  ...props
}: Omit<ComponentProps<"div">, "children" | "toggles" | "onToggle"> & {
  toggles: readonly SettingToggle[];
  onToggle?: (key: string) => void;
}) {
  return (
    <div
      data-slot="settings-panel"
      className={cn("flex w-full flex-col gap-2.5", className)}
      {...props}
    >
      {toggles.map((toggle) => (
        <div key={toggle.key} className="flex items-center gap-3">
          <span className="flex min-w-0 flex-1 flex-col">
            <span className="text-[13px]">{toggle.label}</span>
            <span className="text-foreground/35 text-xs">{toggle.detail}</span>
          </span>
          <button
            type="button"
            role="switch"
            aria-checked={toggle.on}
            aria-label={toggle.label}
            onClick={() => onToggle?.(toggle.key)}
            className={cn(
              "flex h-5 w-9 shrink-0 items-center rounded-full p-0.5 transition-colors duration-200 outline-none focus-visible:ring-2 focus-visible:ring-violeta/40",
              toggle.on ? "bg-violeta" : "bg-foreground/15",
            )}
          >
            <span
              className={cn(
                "bg-background size-4 rounded-full transition-transform duration-200 motion-reduce:transition-none",
                toggle.on && "translate-x-4",
              )}
            />
          </button>
        </div>
      ))}
    </div>
  );
}

import { GripVertical } from "lucide-react";
import type { PointerEvent } from "react";
import { cn } from "@/lib/utils";

type Props = {
  label: string;
  dragging: boolean;
  onPointerDown: (event: PointerEvent<HTMLDivElement>) => void;
};

export default function ResizeHandle({ label, dragging, onPointerDown }: Props) {
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={label}
      onPointerDown={onPointerDown}
      className={cn(
        "group/resize absolute inset-y-0 left-0 z-20 flex w-3 -translate-x-1/2 cursor-col-resize touch-none items-center justify-center",
        dragging && "is-dragging",
      )}
    >
      <span
        aria-hidden
        className={cn(
          "absolute inset-y-2 w-0.5 rounded-full bg-violeta/0 transition-colors",
          "group-hover/resize:bg-violeta/70",
          dragging && "bg-violeta",
        )}
      />
      <span
        aria-hidden
        className={cn(
          "relative grid size-5 place-items-center rounded-full border border-linea bg-crema text-tinta-suave sombra-papel",
          "opacity-0 transition-opacity group-hover/resize:opacity-100",
          dragging && "opacity-100 text-violeta",
        )}
      >
        <GripVertical size={12} />
      </span>
    </div>
  );
}

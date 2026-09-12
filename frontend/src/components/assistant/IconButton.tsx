import { useRef, useState } from "react";
import type { KeyboardEvent, MutableRefObject, ReactNode } from "react";

const SHAPES = {
  toolbar: "size-8 hover:bg-crema hover:text-tinta",
  composer: "size-11 hover:text-violeta",
};

const BASE =
  "grid shrink-0 place-items-center rounded-full text-tinta-suave outline-none transition-colors focus-visible:ring-2 focus-visible:ring-violeta";

type Props = {
  label: string;
  onClick: () => void;
  children: ReactNode;
  shape?: keyof typeof SHAPES;
  placement?: "top" | "bottom";
  className?: string;
  buttonRef?: MutableRefObject<HTMLButtonElement | null>;
};

export default function IconButton({
  label,
  onClick,
  children,
  shape = "toolbar",
  placement = "bottom",
  className = "",
  buttonRef,
}: Props) {
  const ref = useRef<HTMLButtonElement | null>(null);
  const [anchor, setAnchor] = useState<DOMRect | null>(null);

  const attach = (node: HTMLButtonElement | null) => {
    ref.current = node;
    if (buttonRef) buttonRef.current = node;
  };

  const reveal = () => setAnchor(ref.current?.getBoundingClientRect() ?? null);
  const dismiss = () => setAnchor(null);

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key !== "Escape" || !anchor) return;
    event.stopPropagation();
    dismiss();
  };

  return (
    <>
      <button
        ref={attach}
        type="button"
        aria-label={label}
        onClick={onClick}
        onMouseEnter={reveal}
        onMouseLeave={dismiss}
        onFocus={reveal}
        onBlur={dismiss}
        onKeyDown={onKeyDown}
        className={`${BASE} ${SHAPES[shape]} ${className}`}
      >
        {children}
      </button>
      {anchor && (
        <span
          data-testid="icon-button-tooltip"
          aria-hidden="true"
          style={{
            position: "fixed",
            left: anchor.left + anchor.width / 2,
            top: placement === "top" ? anchor.top - 8 : anchor.bottom + 8,
            transform: placement === "top" ? "translate(-50%, -100%)" : "translateX(-50%)",
          }}
          className="z-50 whitespace-nowrap rounded-lg bg-tinta px-2.5 py-1.5 text-sm font-medium text-crema sombra-alta"
        >
          {label}
        </span>
      )}
    </>
  );
}

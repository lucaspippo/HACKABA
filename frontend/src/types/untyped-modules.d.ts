// Chat-layer TS imports of not-yet-typed JSX/JS modules. `strict` implies
// noImplicitAny, so every module a .tsx file imports needs a declaration.
// Delete each entry as its module is converted to TS (ResultTable and
// MiniChart in Phase 3).
import type { ReactNode } from "react";

declare module "*/ResultTable" {
  const C: (props: { rows: unknown[]; limit?: number }) => ReactNode;
  export default C;
}
declare module "*/MiniChart" {
  const C: (props: { points: unknown[]; format?: string }) => ReactNode;
  export default C;
}
declare module "*/AngelaMark" {
  const C: (props: {
    size?: number; pulse?: boolean; estado?: string;
  }) => ReactNode;
  export default C;
}
declare module "*/PlanChecklist" {
  const C: (props: {
    plan: { pasos?: unknown[]; resumen?: string };
    onExecutingChange?: (running: boolean) => void;
  }) => ReactNode;
  export default C;
}
declare module "*/DocCard" {
  const C: (props: { documento: unknown; t: (k: string) => string }) => ReactNode;
  export default C;
}
declare module "*/MemoryChips" {
  const C: (props: {
    chips: Array<{ id: string; pid: string; text: string; change: string }>;
    onForget: (chip: { id: string; pid: string }) => void;
  }) => ReactNode;
  export default C;
}
declare module "*/lib/format" {
  export function peso(n: number): string;
  export function num(n: number): string;
  export function fecha(d: unknown): string;
}
declare module "*/lib/i18n" {
  export function t(key: string, params?: Record<string, unknown>): string;
  export function useT(): (key: string, params?: Record<string, unknown>) => string;
}
declare module "*/lib/toastStore" {
  export function toast(message: string, kind?: string): void;
}
declare module "*/lib/api" {
  export const api: Record<string, (...args: never[]) => Promise<unknown>>;
}
declare module "*/lib/auth" {
  export const authStore: {
    getSnapshot(): { token?: string; usuario?: Record<string, unknown> } | null;
    logout(options?: { manual?: boolean }): void;
    tiene(feature: string): boolean;
    refresh(): Promise<void>;
  };
}

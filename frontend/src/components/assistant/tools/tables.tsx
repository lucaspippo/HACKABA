import { useState } from "react";
import { ChevronUp, ChevronDown } from "lucide-react";
import type { ToolPresenter, ToolRenderProps } from "./types";
import { toolLabels } from "./labels";
import { Tile } from "./kpi";
import { peso, num } from "../../../lib/format";
import { t } from "../../../lib/i18n";

/**
 * Phase 3 (design doc): ResultTable promoted to a real presenter for
 * cuentas_corrientes / listar_grupo / top_inmovilizado — sortable,
 * right-aligned numerics, unit-aware. The generic Fallback already tables
 * `items`-shaped results, but cuentas_corrientes' no-cliente-arg shape
 * (`{totales, clientes, morosos, alertas}`) has no top-level array, so it
 * fell through Fallback to an empty GenericResult — this presenter is a
 * real fix, not just polish, for that one.
 */

export type Column = { key: string; label: string; money?: boolean };

export function sortRows(rows: Record<string, unknown>[], key: string, dir: 1 | -1) {
  return [...rows].sort((a, b) => {
    const av = a[key];
    const bv = b[key];
    if (typeof av === "number" && typeof bv === "number") return (av - bv) * dir;
    return String(av ?? "").localeCompare(String(bv ?? "")) * dir;
  });
}

function formatVal(v: unknown, money?: boolean) {
  if (v == null) return "—";
  if (typeof v === "number") return money ? peso(v) : num(v);
  if (typeof v === "boolean") return v ? t("common.si") : t("common.no");
  return String(v);
}

function SortableTable({
  rows,
  columns,
  initialSort,
  limit = 10,
}: {
  rows: Record<string, unknown>[];
  columns: Column[];
  initialSort?: string;
  limit?: number;
}) {
  const [sort, setSort] = useState<{ key: string; dir: 1 | -1 }>({
    key: initialSort || columns[0].key,
    dir: -1,
  });
  if (rows.length === 0) return null;
  const sorted = sortRows(rows, sort.key, sort.dir);
  const toggle = (key: string) =>
    setSort((s) => (s.key === key ? { key, dir: (s.dir * -1) as 1 | -1 } : { key, dir: -1 }));

  return (
    <div className="mt-1.5 overflow-x-auto rounded-xl border border-linea">
      <table className="w-full text-left text-[0.78rem]">
        <thead>
          <tr className="border-b border-linea bg-papel/60">
            {columns.map((c) => (
              <th key={c.key} className="p-0">
                <button
                  onClick={() => toggle(c.key)}
                  className="flex w-full items-center gap-1 whitespace-nowrap px-2.5 py-1.5 font-semibold text-tinta-suave hover:text-tinta"
                >
                  {c.label}
                  {sort.key === c.key &&
                    (sort.dir === 1 ? <ChevronUp size={11} /> : <ChevronDown size={11} />)}
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.slice(0, limit).map((r, i) => (
            <tr key={i} className={i % 2 ? "bg-crema/40" : ""}>
              {columns.map((c) => (
                <td key={c.key} className="whitespace-nowrap px-2.5 py-1.5 tabular-nums text-tinta">
                  {formatVal(r[c.key], c.money)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > limit && (
        <p className="border-t border-linea px-2.5 py-1 text-[0.72rem] text-tinta-suave">
          {t("toolui.tabla.mas", { n: String(rows.length - limit) })}
        </p>
      )}
    </div>
  );
}

type ClienteRow = Record<string, unknown> & {
  nombre?: string;
  saldo?: number;
  en_mora?: boolean;
  dias_sin_pagar?: number;
  disponible?: number;
};

type CuentasResult = {
  error?: string;
  encontrado?: boolean;
  cliente?: string;
  // shape when a `cliente` arg was given and matched — the enriched client itself.
  nombre?: string;
  saldo?: number;
  en_mora?: boolean;
  dias_sin_pagar?: number;
  disponible?: number;
  // shape when no `cliente` arg was given — the full ledger.
  totales?: {
    total_adeudado?: number;
    clientes_con_deuda?: number;
    total_morosos?: number;
    cantidad_morosos?: number;
  };
  clientes?: ClienteRow[];
};

export function CuentasCorrientes({ result }: ToolRenderProps) {
  const r = result as CuentasResult;
  if (!r || r.error) return null;

  if (r.encontrado === false) {
    return (
      <p className="mt-1 text-[0.82rem] text-tinta-suave">
        {t("toolui.cuentas.no_encontrado", { cliente: r.cliente ?? "" })}
      </p>
    );
  }

  if (Array.isArray(r.clientes)) {
    const tot = r.totales || {};
    const columns: Column[] = [
      { key: "nombre", label: t("toolui.cuentas.col_cliente") },
      { key: "saldo", label: t("toolui.cuentas.col_saldo"), money: true },
      { key: "dias_sin_pagar", label: t("toolui.cuentas.col_dias") },
    ];
    return (
      <div className="mt-1.5">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Tile label={t("toolui.cuentas.total_adeudado")} value={peso(tot.total_adeudado || 0)} />
          <Tile label={t("toolui.cuentas.clientes_con_deuda")} value={num(tot.clientes_con_deuda || 0)} />
          <Tile
            label={t("toolui.cuentas.total_morosos")}
            value={peso(tot.total_morosos || 0)}
            tono={tot.total_morosos ? "text-rojo" : undefined}
          />
          <Tile label={t("toolui.cuentas.cantidad_morosos")} value={num(tot.cantidad_morosos || 0)} />
        </div>
        <SortableTable rows={r.clientes} columns={columns} initialSort="saldo" />
      </div>
    );
  }

  if (r.nombre) {
    return (
      <div className="mt-1.5 grid grid-cols-2 gap-2 sm:grid-cols-3">
        <Tile
          label={t("toolui.cuentas.col_saldo")}
          value={peso(r.saldo || 0)}
          tono={r.en_mora ? "text-rojo" : undefined}
        />
        {r.disponible != null && <Tile label={t("toolui.cuentas.disponible")} value={peso(r.disponible)} />}
        {r.dias_sin_pagar != null && (
          <Tile label={t("toolui.cuentas.col_dias")} value={num(r.dias_sin_pagar)} />
        )}
      </div>
    );
  }

  return null;
}

type ItemsResult = {
  items?: Record<string, unknown>[];
  total_inmovilizado_listado?: number;
  error?: string;
};

export function ItemsTable({ result }: ToolRenderProps) {
  const r = result as ItemsResult;
  if (!r || !Array.isArray(r.items) || r.items.length === 0) return null;
  const columns: Column[] = [
    { key: "descripcion", label: t("toolui.items.col_desc") },
    { key: "stock", label: t("toolui.items.col_stock") },
    { key: "costo_iva", label: t("toolui.items.col_costo"), money: true },
    { key: "inmovilizado", label: t("toolui.items.col_inmovilizado"), money: true },
  ];
  return (
    <div className="mt-1.5">
      {r.total_inmovilizado_listado != null && (
        <p className="text-[0.82rem] text-tinta">
          {t("toolui.items.total")}: <b className="plata">{peso(r.total_inmovilizado_listado)}</b>
        </p>
      )}
      <SortableTable rows={r.items} columns={columns} initialSort="inmovilizado" />
    </div>
  );
}

export const cuentasCorrientesPresenter: ToolPresenter = {
  labels: toolLabels("cuentas_corrientes"),
  render: CuentasCorrientes,
};
export const listarGrupoPresenter: ToolPresenter = { labels: toolLabels("listar_grupo"), render: ItemsTable };
export const topInmovilizadoPresenter: ToolPresenter = {
  labels: toolLabels("top_inmovilizado"),
  render: ItemsTable,
};

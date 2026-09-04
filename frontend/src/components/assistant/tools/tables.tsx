import { useState } from "react";
import { ChevronUp, ChevronDown } from "lucide-react";
import type { ToolPresenter, ToolRenderProps } from "./types";
import { toolLabels } from "./labels";
import { Tile } from "./kpi";
import { toolErrorMessage, ToolErrorText } from "./toolError";
import { peso, num } from "../../../lib/format";
import { t } from "../../../lib/i18n";

/**
 * cuentas_corrientes' no-cliente-arg shape (`{totales, clientes, morosos,
 * alertas}`) has no top-level array, so it previously fell through Fallback
 * to an empty GenericResult.
 */

export type Column = { key: string; label: string; money?: boolean; numeric?: boolean };

export function sortRows(rows: Record<string, unknown>[], key: string, dir: 1 | -1) {
  return [...rows].sort((a, b) => {
    const left = a[key];
    const right = b[key];
    if (typeof left === "number" && typeof right === "number") return (left - right) * dir;
    return String(left ?? "").localeCompare(String(right ?? "")) * dir;
  });
}

function formatValue(value: unknown, money?: boolean) {
  if (value == null) return "—";
  if (typeof value === "number") return money ? peso(value) : num(value);
  if (typeof value === "boolean") return value ? t("common.si") : t("common.no");
  return String(value);
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
            {columns.map((column) => {
              const alignRight = column.money || column.numeric;
              return (
                <th key={column.key} className="p-0">
                  <button
                    onClick={() => toggle(column.key)}
                    className={`flex w-full items-center gap-1 whitespace-nowrap px-2.5 py-1.5 font-semibold text-tinta-suave hover:text-tinta ${
                      alignRight ? "justify-end" : ""
                    }`}
                  >
                    {column.label}
                    {sort.key === column.key &&
                      (sort.dir === 1 ? <ChevronUp size={11} /> : <ChevronDown size={11} />)}
                  </button>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sorted.slice(0, limit).map((row, i) => (
            <tr key={i} className={i % 2 ? "bg-crema/40" : ""}>
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={`whitespace-nowrap px-2.5 py-1.5 tabular-nums text-tinta ${
                    column.money || column.numeric ? "text-right" : ""
                  }`}
                >
                  {formatValue(row[column.key], column.money)}
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

// Field names below mirror cuentas_corrientes' JSON response
// (backend/core/cuentas.py) verbatim — not identifiers of ours to translate.
type CustomerRow = Record<string, unknown> & {
  nombre?: string;
  saldo?: number;
  en_mora?: boolean;
  dias_sin_pagar?: number;
  disponible?: number;
};

type AccountsReceivableResult = {
  encontrado?: boolean;
  cliente?: string;
  // single matched customer (a `cliente` arg was given) vs. the full ledger below.
  nombre?: string;
  saldo?: number;
  en_mora?: boolean;
  dias_sin_pagar?: number;
  disponible?: number;
  totales?: {
    total_adeudado?: number;
    clientes_con_deuda?: number;
    total_morosos?: number;
    cantidad_morosos?: number;
  };
  clientes?: CustomerRow[];
};

export function AccountsReceivable({ result }: ToolRenderProps) {
  const err = toolErrorMessage(result);
  if (err) return <ToolErrorText message={err} />;
  const data = result as AccountsReceivableResult;
  if (!data) return null;

  if (data.encontrado === false) {
    return (
      <p className="mt-1 text-[0.82rem] text-tinta-suave">
        {t("toolui.cuentas.no_encontrado", { cliente: data.cliente ?? "" })}
      </p>
    );
  }

  if (Array.isArray(data.clientes)) {
    const totals = data.totales || {};
    const columns: Column[] = [
      { key: "nombre", label: t("toolui.cuentas.col_cliente") },
      { key: "saldo", label: t("toolui.cuentas.col_saldo"), money: true },
      { key: "dias_sin_pagar", label: t("toolui.cuentas.col_dias"), numeric: true },
    ];
    return (
      <div className="mt-1.5">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Tile label={t("toolui.cuentas.total_adeudado")} value={peso(totals.total_adeudado || 0)} />
          <Tile label={t("toolui.cuentas.clientes_con_deuda")} value={num(totals.clientes_con_deuda || 0)} />
          <Tile
            label={t("toolui.cuentas.total_morosos")}
            value={peso(totals.total_morosos || 0)}
            tone={totals.total_morosos ? "text-rojo" : undefined}
          />
          <Tile label={t("toolui.cuentas.cantidad_morosos")} value={num(totals.cantidad_morosos || 0)} />
        </div>
        <SortableTable rows={data.clientes} columns={columns} initialSort="saldo" />
      </div>
    );
  }

  if (data.nombre) {
    return (
      <div className="mt-1.5 grid grid-cols-2 gap-2 sm:grid-cols-3">
        <Tile
          label={t("toolui.cuentas.col_saldo")}
          value={peso(data.saldo || 0)}
          tone={data.en_mora ? "text-rojo" : undefined}
        />
        {data.disponible != null && <Tile label={t("toolui.cuentas.disponible")} value={peso(data.disponible)} />}
        {data.dias_sin_pagar != null && (
          <Tile label={t("toolui.cuentas.col_dias")} value={num(data.dias_sin_pagar)} />
        )}
      </div>
    );
  }

  return null;
}

type ItemGroupResult = {
  items?: Record<string, unknown>[];
  total_inmovilizado_listado?: number;
};

export function ItemGroupTable({ result }: ToolRenderProps) {
  const err = toolErrorMessage(result);
  if (err) return <ToolErrorText message={err} />;
  const data = result as ItemGroupResult;
  if (!data || !Array.isArray(data.items) || data.items.length === 0) return null;
  const columns: Column[] = [
    { key: "descripcion", label: t("toolui.items.col_desc") },
    { key: "stock", label: t("toolui.items.col_stock"), numeric: true },
    { key: "costo_iva", label: t("toolui.items.col_costo"), money: true },
    { key: "inmovilizado", label: t("toolui.items.col_inmovilizado"), money: true },
  ];
  return (
    <div className="mt-1.5">
      {data.total_inmovilizado_listado != null && (
        <p className="text-[0.82rem] text-tinta">
          {t("toolui.items.total")}: <b className="plata">{peso(data.total_inmovilizado_listado)}</b>
        </p>
      )}
      <SortableTable rows={data.items} columns={columns} initialSort="inmovilizado" />
    </div>
  );
}

export const accountsReceivablePresenter: ToolPresenter = {
  labels: toolLabels("cuentas_corrientes"),
  render: AccountsReceivable,
};
export const itemGroupPresenter: ToolPresenter = { labels: toolLabels("listar_grupo"), render: ItemGroupTable };
export const topTiedUpCapitalPresenter: ToolPresenter = {
  labels: toolLabels("top_inmovilizado"),
  render: ItemGroupTable,
};

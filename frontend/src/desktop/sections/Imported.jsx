import { useEffect, useMemo, useState } from "react";
import { Layers } from "lucide-react";
import Cargando from "../../components/Cargando";
import TablaCRUD from "../../components/TablaCRUD";
import { api } from "../../lib/api";
import { fecha, num, peso } from "../../lib/format";
import { useT } from "../../lib/i18n";
import IngestPipeline from "./IngestPipeline";

const TABS = [
  { id: "products", lk: "imported.tab_products" },
  { id: "sales", lk: "imported.tab_sales" },
  { id: "receipts", lk: "imported.tab_receipts" },
  { id: "movements", lk: "imported.tab_movements" },
];
const ROW_CAP = 1000;

function SourceBadge({ source, t }) {
  const odoo = source === "odoo";
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-[0.72rem] font-semibold ${
      odoo ? "bg-violeta/12 text-violeta" : "bg-papel-hondo text-tinta-suave"}`}>
      {t(odoo ? "imported.source_odoo_badge" : "imported.source_csv_badge")}
    </span>
  );
}

function searchHaystack(row) {
  return Object.values(row).filter((v) => v != null && v !== "").join(" ").toLowerCase();
}

export default function Imported({ highlight, onNavigate }) {
  const t = useT();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("products");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [query, setQuery] = useState("");

  useEffect(() => {
    api.imported().then(setData).catch(setError);
  }, []);

  useEffect(() => {
    if (TABS.some((item) => item.id === highlight)) setTab(highlight);
  }, [highlight]);

  useEffect(() => { setQuery(""); }, [tab]);

  const columns = useMemo(() => {
    const sourceCol = {
      key: "source", label: t("imported.col_source"), sortable: true,
      render: (row) => <SourceBadge source={row.source} t={t} />,
    };
    if (tab === "products") {
      return [
        { key: "sku", label: t("imported.col_sku"), sortable: true, plata: true,
          render: (p) => p.sku || p.code || "—" },
        { key: "description", label: t("imported.col_product"), sortable: true,
          render: (p) => <span className="font-medium text-tinta">{p.description || "—"}</span> },
        { key: "stock", label: t("imported.col_stock"), sortable: true, align: "right", plata: true,
          render: (p) => num(p.stock || 0) },
        { key: "free_qty", label: t("imported.col_free"), sortable: true, align: "right", plata: true,
          render: (p) => (p.free_qty == null ? "—" : num(p.free_qty)) },
        { key: "cost", label: t("imported.col_cost"), sortable: true, align: "right", plata: true,
          render: (p) => (p.cost == null ? "—" : peso(p.cost)) },
        { key: "list_price", label: t("imported.col_list_price"), sortable: true, align: "right", plata: true,
          render: (p) => (p.list_price == null ? "—" : peso(p.list_price)) },
        sourceCol,
      ];
    }
    if (tab === "sales") {
      return [
        { key: "date", label: t("imported.col_date"), sortable: true, plata: true,
          render: (row) => (row.date ? fecha(row.date) : "—") },
        { key: "product", label: t("imported.col_product"), sortable: true,
          render: (row) => <span className="font-medium text-tinta">{row.product || "—"}</span> },
        { key: "code", label: t("imported.col_sku"), sortable: true, plata: true,
          render: (row) => row.code || "—" },
        { key: "quantity", label: t("imported.col_qty"), sortable: true, align: "right", plata: true,
          render: (row) => num(row.quantity || 0) },
        { key: "price", label: t("imported.col_price"), sortable: true, align: "right", plata: true,
          render: (row) => (row.price == null ? "—" : peso(row.price)) },
        sourceCol,
      ];
    }
    if (tab === "receipts") {
      return [
        { key: "date", label: t("imported.col_date"), sortable: true, plata: true,
          render: (row) => (row.date ? fecha(row.date) : "—") },
        { key: "product", label: t("imported.col_product"), sortable: true,
          render: (row) => <span className="font-medium text-tinta">{row.product || "—"}</span> },
        { key: "vendor", label: t("imported.col_vendor"), sortable: true,
          render: (row) => row.vendor || "—" },
        { key: "quantity", label: t("imported.col_qty"), sortable: true, align: "right", plata: true,
          render: (row) => num(row.quantity || 0) },
        { key: "warehouse", label: t("imported.col_warehouse"), sortable: true, plata: true,
          render: (row) => row.warehouse || "—" },
        { key: "po_number", label: t("imported.col_po"), sortable: true, plata: true,
          render: (row) => row.po_number || row.origin || "—" },
        sourceCol,
      ];
    }
    return [
      { key: "product", label: t("imported.col_product"), sortable: true,
        render: (row) => <span className="font-medium text-tinta">{row.product || "—"}</span> },
      { key: "location", label: t("imported.col_location"), sortable: true,
        render: (row) => row.location || "—" },
      { key: "lot", label: t("imported.col_lot"), plata: true, render: (row) => row.lot || "—" },
      { key: "expiry", label: t("imported.col_expiry"), sortable: true, plata: true,
        render: (row) => (row.expiry ? fecha(row.expiry) : "—") },
      { key: "quantity", label: t("imported.col_qty"), sortable: true, align: "right", plata: true,
        render: (row) => num(row.quantity || 0) },
      { key: "in_date", label: t("imported.col_received"), sortable: true, plata: true,
        render: (row) => (row.in_date ? fecha(row.in_date) : "—") },
      { key: "counted_qty", label: t("imported.col_counted"), sortable: true, align: "right", plata: true,
        render: (row) => (row.counted_qty == null ? "—" : num(row.counted_qty)) },
      sourceCol,
    ];
  }, [tab, t]);

  if (!data) return <div className="pt-2"><Cargando error={error} /></div>;

  const tabRows = data[tab] || [];
  const bySource = sourceFilter === "odoo"
    ? tabRows.filter((row) => row.source === "odoo")
    : tabRows;
  const needle = query.trim().toLowerCase();
  const filtered = needle ? bySource.filter((row) => searchHaystack(row).includes(needle)) : bySource;
  const visible = filtered.slice(0, ROW_CAP);
  const emptyKey = {
    products: "imported.empty_products",
    sales: "imported.empty_sales",
    receipts: "imported.empty_receipts",
    movements: "imported.empty_movements",
  }[tab];

  const countFor = (id) => {
    const rows = data[id] || [];
    return sourceFilter === "odoo" ? rows.filter((row) => row.source === "odoo").length : rows.length;
  };

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Layers size={24} className="text-tinta-suave" />
          <div>
            <h1 className="font-display text-2xl font-bold leading-none">{t("imported.title")}</h1>
            <p className="mt-1 text-[0.9rem] text-tinta-suave">{t("imported.subtitle")}</p>
            <div className="mt-3">
              <IngestPipeline current="imported" onNavigate={onNavigate} />
            </div>
          </div>
        </div>
      </header>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-1 border-b border-linea">
          {TABS.map((item) => (
            <button key={item.id} type="button" onClick={() => setTab(item.id)}
              className={`px-3 py-1.5 text-[0.82rem] font-semibold border-b-2 -mb-px ${
                tab === item.id ? "border-violeta text-violeta" : "border-transparent text-tinta-suave hover:text-tinta"}`}>
              {t(item.lk)}
              <span className="ml-1.5 font-normal text-tinta-suave">{countFor(item.id)}</span>
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1">
          {[
            { id: "all", lk: "imported.source_all" },
            { id: "odoo", lk: "imported.source_odoo" },
          ].map((item) => (
            <button key={item.id} type="button" onClick={() => setSourceFilter(item.id)}
              className={`rounded-full px-3 py-1 text-[0.76rem] font-semibold ${
                sourceFilter === item.id ? "bg-violeta text-crema" : "bg-papel-hondo text-tinta-suave hover:text-tinta"}`}>
              {t(item.lk)}
            </button>
          ))}
        </div>
      </div>

      {filtered.length > ROW_CAP && (
        <p className="text-[0.82rem] text-tinta-suave">
          {t("imported.truncated", { n: ROW_CAP, total: filtered.length })}
        </p>
      )}

      <TablaCRUD
        key={tab}
        idDe={(row) => row._key}
        columnas={columns}
        filas={visible}
        q={query}
        onQ={setQuery}
        buscarPlaceholder={t("imported.search")}
        vacio={t(emptyKey)}
      />
    </div>
  );
}

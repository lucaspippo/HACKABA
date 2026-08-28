import { useEffect, useMemo, useState } from "react";
import { Layers, Truck, Warehouse } from "lucide-react";
import Cargando from "../../components/Cargando";
import TablaCRUD, { SourceBadge } from "../../components/TablaCRUD";
import { FacetSelect, FilterDivider, FilterRail, SourceChips, uniqueValues } from "../../components/FilterRail";
import DateRangePicker from "../../components/DateRangePicker";
import CellLink, { qLink } from "../../components/CellLink";
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

function searchHaystack(row) {
  return Object.values(row).filter((v) => v != null && v !== "").join(" ").toLowerCase();
}

function inDateRange(iso, from, to) {
  if (!iso) return !(from || to);
  const d = String(iso).slice(0, 10);
  if (from && d < from) return false;
  if (to && d > to) return false;
  return true;
}

export default function Imported({ highlight, onNavigate }) {
  const t = useT();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("products");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [vendor, setVendor] = useState("");
  const [warehouse, setWarehouse] = useState("");

  useEffect(() => {
    api.imported().then(setData).catch(setError);
  }, []);

  useEffect(() => {
    if (TABS.some((item) => item.id === highlight)) setTab(highlight);
  }, [highlight]);

  useEffect(() => { setQuery(""); setDateFrom(""); setDateTo(""); setVendor(""); setWarehouse(""); }, [tab]);

  const columns = useMemo(() => {
    const sourceCol = {
      key: "source", label: t("imported.col_source"), sortable: true, groupable: true,
      groupLabel: (k) => t(k === "odoo" ? "crud.source_odoo" : k === "manual" ? "crud.source_manual" : "crud.source_csv"),
      render: (row) => <SourceBadge source={row.source} t={t} />,
    };
    if (tab === "products") {
      return [
        { key: "sku", label: t("imported.col_sku"), sortable: true, plata: true,
          render: (p) => p.sku || p.code || "—" },
        { key: "description", label: t("imported.col_product"), sortable: true, groupable: true,
          render: (p) => (
            <CellLink to={qLink("productos", p.description || p.sku)}>
              <span className="font-medium">{p.description || "—"}</span>
            </CellLink>
          ) },
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
        { key: "product", label: t("imported.col_product"), sortable: true, groupable: true,
          render: (row) => (
            <CellLink to={qLink("productos", row.product)}>
              <span className="font-medium">{row.product || "—"}</span>
            </CellLink>
          ) },
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
        { key: "product", label: t("imported.col_product"), sortable: true, groupable: true,
          render: (row) => (
            <CellLink to={qLink("productos", row.product)}>
              <span className="font-medium">{row.product || "—"}</span>
            </CellLink>
          ) },
        { key: "vendor", label: t("imported.col_vendor"), sortable: true, groupable: true,
          render: (row) => <CellLink to={qLink("proveedores", row.vendor)}>{row.vendor || "—"}</CellLink> },
        { key: "quantity", label: t("imported.col_qty"), sortable: true, align: "right", plata: true,
          render: (row) => num(row.quantity || 0) },
        { key: "warehouse", label: t("imported.col_warehouse"), sortable: true, groupable: true,
          render: (row) => <CellLink to={qLink("ubicaciones", row.warehouse)}>{row.warehouse || "—"}</CellLink> },
        { key: "po_number", label: t("imported.col_po"), sortable: true, plata: true, groupable: true,
          render: (row) => {
            const po = row.po_number || row.origin;
            return <CellLink to={qLink("ordenes_compra", po)}>{po || "—"}</CellLink>;
          } },
        sourceCol,
      ];
    }
    return [
      { key: "product", label: t("imported.col_product"), sortable: true, groupable: true,
        render: (row) => (
          <CellLink to={qLink("productos", row.product)}>
            <span className="font-medium">{row.product || "—"}</span>
          </CellLink>
        ) },
      { key: "location", label: t("imported.col_location"), sortable: true, groupable: true,
        render: (row) => <CellLink to={qLink("ubicaciones", row.location)}>{row.location || "—"}</CellLink> },
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
  const bySource = sourceFilter === "all"
    ? tabRows
    : tabRows.filter((row) => (row.source || "csv") === sourceFilter);
  const dateField = tab === "movements" ? "in_date" : "date";
  const dated = (tab === "sales" || tab === "receipts" || tab === "movements")
    ? bySource.filter((row) => inDateRange(row[dateField], dateFrom, dateTo))
    : bySource;
  const faceted = dated.filter((row) => {
    if (vendor && row.vendor !== vendor) return false;
    if (warehouse && row.warehouse !== warehouse) return false;
    return true;
  });
  const needle = query.trim().toLowerCase();
  const filtered = needle ? faceted.filter((row) => searchHaystack(row).includes(needle)) : faceted;
  const vendors = tab === "receipts" ? uniqueValues(bySource, "vendor") : [];
  const warehouses = tab === "receipts" ? uniqueValues(bySource, "warehouse") : [];
  const hasFilters = !!(query || dateFrom || dateTo || vendor || warehouse || sourceFilter !== "all");
  const clearFilters = () => {
    setQuery(""); setDateFrom(""); setDateTo(""); setVendor(""); setWarehouse(""); setSourceFilter("all");
  };
  const visible = filtered.slice(0, ROW_CAP);
  const emptyKey = {
    products: "imported.empty_products",
    sales: "imported.empty_sales",
    receipts: "imported.empty_receipts",
    movements: "imported.empty_movements",
  }[tab];

  const countFor = (id) => {
    const rows = data[id] || [];
    return sourceFilter === "all" ? rows.length
      : rows.filter((row) => (row.source || "csv") === sourceFilter).length;
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
          <SourceChips value={sourceFilter} onChange={setSourceFilter} t={t} />
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
        onLimpiar={hasFilters ? clearFilters : undefined}
        filtros={(tab === "sales" || tab === "receipts" || tab === "movements") ? (
          <FilterRail onClear={hasFilters ? clearFilters : undefined} clearLabel={t("crud.limpiar_filtros")}>
            <DateRangePicker from={dateFrom} to={dateTo} onChange={(a, b) => { setDateFrom(a); setDateTo(b); }} />
            {tab === "receipts" && (
              <>
                <FilterDivider />
                <FacetSelect icon={Truck} label={t("recepciones.facet_proveedor")}
                  value={vendor} options={vendors} onChange={setVendor} />
                <FacetSelect icon={Warehouse} label={t("recepciones.facet_deposito")}
                  value={warehouse} options={warehouses} onChange={setWarehouse} />
              </>
            )}
          </FilterRail>
        ) : undefined}
      />
    </div>
  );
}

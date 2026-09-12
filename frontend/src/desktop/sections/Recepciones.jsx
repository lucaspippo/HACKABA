import { useCallback, useState } from "react";
import { PackagePlus, Pencil, Trash2, X, Truck, Warehouse, ShoppingCart } from "lucide-react";
import Cargando from "../../components/Cargando";
import TablaCRUD, { SourceBadge, SourceChips } from "../../components/TablaCRUD";
import { FilterChip, FilterDivider, FilterRail, FacetSelect } from "../../components/FilterRail";
import DateRangePicker from "../../components/DateRangePicker";
import CellLink, { qLink } from "../../components/CellLink";
import { api } from "../../lib/api";
import { toast } from "../../lib/toastStore";
import { fecha, num } from "../../lib/format";
import { usePagedList } from "../../lib/usePagedList";
import { useT } from "../../lib/i18n";

export default function Recepciones() {
  const t = useT();
  const [modal, setModal] = useState(null);
  const [exportando, setExportando] = useState(false);
  const fetcher = useCallback((p) => api.receipts(p), []);
  const page = usePagedList(fetcher);

  const eliminar = async (id) => {
    try {
      await api.receiptEliminar(id);
      toast(t("recepciones.eliminada"));
      page.reload();
    } catch {
      toast(t("recepciones.error"), "error");
    }
  };

  const exportar = async () => {
    setExportando(true);
    try { await api.receiptsExport(page.query()); }
    catch { toast(t("crud.export_error"), "error"); }
    finally { setExportando(false); }
  };

  if (page.loading && page.items.length === 0) {
    return <div className="pt-2"><Cargando error={page.error} /></div>;
  }

  return (
    <div className="space-y-6">
      <header className="flex items-center gap-2">
        <PackagePlus size={24} className="text-tinta-suave" />
        <div>
          <h1 className="font-display text-2xl font-bold leading-none">{t("recepciones.titulo")}</h1>
          <p className="mt-1 text-[0.9rem] text-tinta-suave">{t("recepciones.subtitulo")}</p>
        </div>
      </header>

      <TablaCRUD
        titulo={t("recepciones.tabla")}
        conteo={t("crud.conteo", { a: num(page.items.length), b: num(page.total) })}
        columnas={[
          { key: "fecha", label: t("imported.col_date"), sortable: true, plata: true, groupable: true,
            render: (r) => (r.fecha ? fecha(r.fecha) : "—") },
          { key: "producto", label: t("imported.col_product"), sortable: true, groupable: true,
            render: (r) => (
              <CellLink to={qLink("productos", r.producto)}>
                <span className="font-medium">{r.producto || "—"}</span>
              </CellLink>
            ) },
          { key: "proveedor", label: t("imported.col_vendor"), sortable: true, groupable: true,
            render: (r) => <CellLink to={qLink("proveedores", r.proveedor)}>{r.proveedor || "—"}</CellLink> },
          { key: "cantidad", label: t("imported.col_qty"), sortable: true, align: "right", plata: true,
            render: (r) => num(r.cantidad || 0) },
          { key: "deposito", label: t("imported.col_warehouse"), sortable: true, groupable: true,
            render: (r) => <CellLink to={qLink("ubicaciones", r.deposito)}>{r.deposito || "—"}</CellLink> },
          { key: "po_number", label: t("imported.col_po"), sortable: true, plata: true, groupable: true,
            render: (r) => {
              const po = r.po_number || r.origen;
              return <CellLink to={qLink("ordenes_compra", po)}>{po || "—"}</CellLink>;
            } },
          { key: "source", label: t("imported.col_source"), sortable: true, groupable: true,
            groupLabel: (k) => t(k === "odoo" ? "crud.source_odoo" : k === "manual" ? "crud.source_manual" : "crud.source_csv"),
            render: (r) => <SourceBadge source={r.source} t={t} /> },
        ]}
        filas={page.items}
        q={page.q}
        onQ={page.setQ}
        buscarPlaceholder={t("recepciones.buscar")}
        vacio={t("recepciones.vacio")}
        onCrear={() => setModal("nuevo")}
        crearLabel={t("recepciones.nueva")}
        onExport={exportar}
        exportando={exportando}
        onSort={page.toggleSort}
        orden={page.sort}
        onLoadMore={page.loadMore}
        hasMore={page.hasMore}
        cargandoMas={page.loadingMore}
        onLimpiar={page.hasActiveFilters ? page.clearFilters : undefined}
        filtros={(
          <FilterRail onClear={page.hasActiveFilters ? page.clearFilters : undefined} clearLabel={t("crud.limpiar_filtros")}>
            <SourceChips value={page.source} onChange={page.setSource} t={t} />
            <FilterDivider />
            <DateRangePicker from={page.dateFrom} to={page.dateTo} onChange={page.setDateRange} />
            <FacetSelect icon={Truck} label={t("recepciones.facet_proveedor")}
              value={page.filters.proveedor || ""}
              options={page.facets.proveedor}
              onChange={(v) => page.setFilter("proveedor", v)} />
            <FacetSelect icon={Warehouse} label={t("recepciones.facet_deposito")}
              value={page.filters.deposito || ""}
              options={page.facets.deposito}
              onChange={(v) => page.setFilter("deposito", v)} />
            <FilterChip icon={ShoppingCart} active={!!page.filters.sin_po} onClick={() => page.setFilter("sin_po", page.filters.sin_po ? "" : "1")}>
              {t("recepciones.filtro_sin_oc")}
            </FilterChip>
          </FilterRail>
        )}
        acciones={(r) => (
          <div className="flex items-center justify-end gap-2">
            <button type="button" onClick={() => setModal(r)} className="text-tinta-suave hover:text-tinta"><Pencil size={14} /></button>
            <button type="button" onClick={() => eliminar(r.id)} className="text-tinta-suave hover:text-rojo"><Trash2 size={14} /></button>
          </div>
        )}
      />

      {modal && (
        <ModalRecepcion
          inicial={modal === "nuevo" ? null : modal}
          onClose={() => setModal(null)}
          onGuardado={() => { setModal(null); page.reload(); }}
        />
      )}
    </div>
  );
}

const CAMPOS = [
  ["fecha", "imported.col_date", "date"],
  ["producto", "imported.col_product", "text"],
  ["codigo", "imported.col_sku", "number"],
  ["proveedor", "imported.col_vendor", "text"],
  ["cantidad", "imported.col_qty", "number"],
  ["deposito", "imported.col_warehouse", "text"],
  ["po_number", "imported.col_po", "text"],
];

function ModalRecepcion({ inicial, onClose, onGuardado }) {
  const t = useT();
  const [form, setForm] = useState({
    fecha: inicial?.fecha || "", producto: inicial?.producto || "",
    codigo: inicial?.codigo ?? "", proveedor: inicial?.proveedor || "",
    cantidad: inicial?.cantidad ?? "", deposito: inicial?.deposito || "",
    po_number: inicial?.po_number || "",
  });
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);

  const guardar = async () => {
    setGuardando(true);
    setError(null);
    const payload = {
      ...form,
      codigo: form.codigo === "" ? null : Number(form.codigo),
      cantidad: Number(form.cantidad) || 0,
    };
    try {
      if (inicial) await api.receiptActualizar(inicial.id, payload);
      else await api.receiptCrear(payload);
      toast(t(inicial ? "recepciones.actualizada" : "recepciones.creada"));
      onGuardado();
    } catch (e) {
      setError(e.criollo || t("recepciones.error"));
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-tinta/40 p-4" onClick={onClose}>
      <div className="max-h-[85vh] w-full max-w-md overflow-y-auto rounded-[var(--radius-card)] border border-linea bg-crema p-6 sombra-alta" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between">
          <h2 className="font-display text-xl font-bold">{t(inicial ? "recepciones.editar" : "recepciones.nueva")}</h2>
          <button type="button" onClick={onClose} className="text-tinta-suave hover:text-tinta"><X size={20} /></button>
        </div>
        {CAMPOS.map(([campo, lk, tipo]) => (
          <div key={campo}>
            <label className="mt-3 block text-[0.82rem] font-semibold text-tinta-suave">{t(lk)}</label>
            <input type={tipo} value={form[campo]} onChange={(e) => setForm({ ...form, [campo]: e.target.value })}
              autoFocus={campo === "producto"}
              className="mt-1 w-full rounded-xl border border-linea bg-papel px-3.5 py-2.5 text-[0.9rem] outline-none focus:border-tinta/40" />
          </div>
        ))}
        {error && <p className="mt-2 text-[0.82rem] text-rojo-hondo">{error}</p>}
        <div className="mt-5 flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-full border border-linea px-4 py-2 text-[0.85rem] font-semibold text-tinta-suave">
            {t("inventario.form_cancelar")}
          </button>
          <button type="button" onClick={guardar} disabled={!form.producto.trim() || guardando}
            className="rounded-full bg-violeta px-4 py-2 text-[0.85rem] font-semibold text-crema disabled:opacity-50">
            {t("inventario.form_guardar")}
          </button>
        </div>
      </div>
    </div>
  );
}

import { useCallback, useState } from "react";
import { TrendingUp, Pencil, Trash2, X } from "lucide-react";
import Cargando from "../../components/Cargando";
import TablaCRUD, { SourceBadge, SourceChips } from "../../components/TablaCRUD";
import { FilterDivider, FilterRail } from "../../components/FilterRail";
import DateRangePicker from "../../components/DateRangePicker";
import CellLink, { qLink } from "../../components/CellLink";
import { api } from "../../lib/api";
import { toast } from "../../lib/toastStore";
import { fecha, num, peso } from "../../lib/format";
import { usePagedList } from "../../lib/usePagedList";
import { useT } from "../../lib/i18n";

export default function Ventas() {
  const t = useT();
  const [modal, setModal] = useState(null);
  const [exportando, setExportando] = useState(false);
  const fetcher = useCallback((p) => api.sales(p), []);
  const page = usePagedList(fetcher);

  const eliminar = async (id) => {
    try {
      await api.saleEliminar(id);
      toast(t("ventas_crud.eliminada"));
      page.reload();
    } catch {
      toast(t("ventas_crud.error"), "error");
    }
  };

  const exportar = async () => {
    setExportando(true);
    try { await api.salesExport(page.query()); }
    catch { toast(t("crud.export_error"), "error"); }
    finally { setExportando(false); }
  };

  if (page.loading && page.items.length === 0) {
    return <div className="pt-2"><Cargando error={page.error} /></div>;
  }

  return (
    <div className="space-y-6">
      <header className="flex items-center gap-2">
        <TrendingUp size={24} className="text-tinta-suave" />
        <div>
          <h1 className="font-display text-2xl font-bold leading-none">{t("ventas_crud.titulo")}</h1>
          <p className="mt-1 text-[0.9rem] text-tinta-suave">{t("ventas_crud.subtitulo")}</p>
        </div>
      </header>

      <TablaCRUD
        titulo={t("ventas_crud.tabla")}
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
          { key: "codigo", label: t("imported.col_sku"), sortable: true, plata: true,
            render: (r) => <CellLink to={qLink("productos", r.codigo)}>{r.codigo ?? "—"}</CellLink> },
          { key: "cantidad", label: t("imported.col_qty"), sortable: true, align: "right", plata: true,
            render: (r) => num(r.cantidad || 0) },
          { key: "precio", label: t("imported.col_price"), sortable: true, align: "right", plata: true,
            render: (r) => (r.precio == null ? "—" : peso(r.precio)) },
          { key: "source", label: t("imported.col_source"), sortable: true, groupable: true,
            groupLabel: (k) => t(k === "odoo" ? "crud.source_odoo" : k === "manual" ? "crud.source_manual" : "crud.source_csv"),
            render: (r) => <SourceBadge source={r.source} t={t} /> },
        ]}
        filas={page.items}
        q={page.q}
        onQ={page.setQ}
        buscarPlaceholder={t("ventas_crud.buscar")}
        vacio={t("ventas_crud.vacio")}
        onCrear={() => setModal("nuevo")}
        crearLabel={t("ventas_crud.nueva")}
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
          </FilterRail>
        )}
        acciones={(r) => (
          <div className="flex items-center justify-end gap-2">
            <button type="button" onClick={() => setModal(r)} aria-label={t("common.editar")} className="text-tinta-suave hover:text-tinta"><Pencil size={14} /></button>
            <button type="button" onClick={() => eliminar(r.id)} aria-label={t("common.eliminar")} className="text-tinta-suave hover:text-rojo"><Trash2 size={14} /></button>
          </div>
        )}
      />

      {modal && (
        <ModalVenta
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
  ["cantidad", "imported.col_qty", "number"],
  ["precio", "imported.col_price", "number"],
];

function ModalVenta({ inicial, onClose, onGuardado }) {
  const t = useT();
  const [form, setForm] = useState({
    fecha: inicial?.fecha || "", producto: inicial?.producto || "",
    codigo: inicial?.codigo ?? "", cantidad: inicial?.cantidad ?? "", precio: inicial?.precio ?? "",
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
      precio: form.precio === "" ? null : Number(form.precio),
    };
    try {
      if (inicial) await api.saleActualizar(inicial.id, payload);
      else await api.saleCrear(payload);
      toast(t(inicial ? "ventas_crud.actualizada" : "ventas_crud.creada"));
      onGuardado();
    } catch (e) {
      setError(e.criollo || t("ventas_crud.error"));
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-tinta/40 p-4" onClick={onClose}>
      <div className="max-h-[85vh] w-full max-w-md overflow-y-auto rounded-[var(--radius-card)] border border-linea bg-crema p-6 sombra-alta" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between">
          <h2 className="font-display text-xl font-bold">{t(inicial ? "ventas_crud.editar" : "ventas_crud.nueva")}</h2>
          <button type="button" onClick={onClose} aria-label={t("common.cerrar")} className="text-tinta-suave hover:text-tinta"><X size={20} /></button>
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

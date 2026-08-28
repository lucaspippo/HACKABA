import { useCallback, useState } from "react";
import { PackageSearch, Pencil, Trash2, X } from "lucide-react";
import Cargando from "../../components/Cargando";
import TablaCRUD, { SourceBadge, SourceChips } from "../../components/TablaCRUD";
import { api } from "../../lib/api";
import { toast } from "../../lib/toastStore";
import { fecha, num } from "../../lib/format";
import { usePagedList } from "../../lib/usePagedList";
import { useT } from "../../lib/i18n";

export default function Movimientos({ onNavegar }) {
  const t = useT();
  const [modal, setModal] = useState(null);
  const [exportando, setExportando] = useState(false);
  const fetcher = useCallback((p) => api.movimientos(p), []);
  const page = usePagedList(fetcher);

  const eliminar = async (id) => {
    try {
      await api.loteEliminar(id);
      toast(t("movimientos.eliminado"));
      page.reload();
    } catch {
      toast(t("movimientos.error"), "error");
    }
  };

  const exportar = async () => {
    setExportando(true);
    try { await api.movimientosExport(page.query()); }
    catch { toast(t("crud.export_error"), "error"); }
    finally { setExportando(false); }
  };

  if (page.loading && page.items.length === 0) {
    return <div className="pt-2"><Cargando error={page.error} /></div>;
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <PackageSearch size={24} className="text-tinta-suave" />
          <div>
            <h1 className="font-display text-2xl font-bold leading-none">{t("movimientos.titulo")}</h1>
            <p className="mt-1 text-[0.9rem] text-tinta-suave">{t("movimientos.subtitulo")}</p>
          </div>
        </div>
        {onNavegar && (
          <button type="button" onClick={() => onNavegar("deposito")} className="text-[0.84rem] font-semibold text-hielo">
            {t("lotes.ver_vencimientos")}
          </button>
        )}
      </header>

      <TablaCRUD
        titulo={t("movimientos.tabla")}
        conteo={t("crud.conteo", { a: num(page.items.length), b: num(page.total) })}
        columnas={[
          { key: "producto", label: t("lotes.col_producto"), sortable: true,
            render: (l) => <span className="font-medium text-tinta">{l.producto}</span> },
          { key: "ubicacion", label: t("lotes.col_ubicacion"), sortable: true,
            render: (l) => l.ubicacion || "—" },
          { key: "lote", label: t("lotes.col_lote"), plata: true, render: (l) => l.lote || "—" },
          { key: "vencimiento", label: t("lotes.col_vencimiento"), sortable: true, plata: true,
            render: (l) => (l.vencimiento ? fecha(l.vencimiento) : "—") },
          { key: "cantidad", label: t("lotes.col_cantidad"), sortable: true, align: "right", plata: true,
            render: (l) => num(l.cantidad || 0) },
          { key: "in_date", label: t("imported.col_received"), sortable: true, plata: true,
            render: (l) => (l.in_date ? fecha(l.in_date) : "—") },
          { key: "counted_qty", label: t("imported.col_counted"), sortable: true, align: "right", plata: true,
            render: (l) => (l.counted_qty == null ? "—" : num(l.counted_qty)) },
          { key: "source", label: t("imported.col_source"), sortable: true,
            render: (l) => <SourceBadge source={l.source} t={t} /> },
        ]}
        filas={page.items}
        q={page.q}
        onQ={page.setQ}
        buscarPlaceholder={t("movimientos.buscar")}
        vacio={t("movimientos.vacio")}
        onCrear={() => setModal("nuevo")}
        crearLabel={t("movimientos.nuevo")}
        onExport={exportar}
        exportando={exportando}
        onSort={page.toggleSort}
        orden={page.sort}
        onLoadMore={page.loadMore}
        hasMore={page.hasMore}
        cargandoMas={page.loadingMore}
        filtros={<SourceChips value={page.source} onChange={page.setSource} t={t} />}
        acciones={(l) => (
          <div className="flex items-center justify-end gap-2">
            <button type="button" onClick={() => setModal(l)} className="text-tinta-suave hover:text-tinta"><Pencil size={14} /></button>
            <button type="button" onClick={() => eliminar(l.id)} className="text-tinta-suave hover:text-rojo"><Trash2 size={14} /></button>
          </div>
        )}
      />

      {modal && (
        <ModalMovimiento
          inicial={modal === "nuevo" ? null : modal}
          onClose={() => setModal(null)}
          onGuardado={() => { setModal(null); page.reload(); }}
        />
      )}
    </div>
  );
}

const CAMPOS = [
  ["producto", "lotes.col_producto", "text"],
  ["ubicacion", "lotes.col_ubicacion", "text"],
  ["lote", "lotes.col_lote", "text"],
  ["vencimiento", "lotes.col_vencimiento", "date"],
  ["cantidad", "lotes.col_cantidad", "number"],
  ["in_date", "imported.col_received", "date"],
  ["counted_qty", "imported.col_counted", "number"],
];

function ModalMovimiento({ inicial, onClose, onGuardado }) {
  const t = useT();
  const [form, setForm] = useState({
    producto: inicial?.producto || "", ubicacion: inicial?.ubicacion || "",
    lote: inicial?.lote || "", vencimiento: inicial?.vencimiento || "",
    cantidad: inicial?.cantidad ?? "", in_date: inicial?.in_date || "",
    counted_qty: inicial?.counted_qty ?? "",
  });
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);

  const guardar = async () => {
    setGuardando(true);
    setError(null);
    const payload = {
      ...form,
      cantidad: Number(form.cantidad) || 0,
      counted_qty: form.counted_qty === "" ? null : Number(form.counted_qty),
    };
    try {
      if (inicial) await api.loteActualizar(inicial.id, payload);
      else await api.loteCrear(payload);
      toast(t(inicial ? "movimientos.actualizado" : "movimientos.creado"));
      onGuardado();
    } catch (e) {
      setError(e.criollo || t("movimientos.error"));
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-tinta/40 p-4" onClick={onClose}>
      <div className="max-h-[85vh] w-full max-w-md overflow-y-auto rounded-[var(--radius-card)] border border-linea bg-crema p-6 sombra-alta" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between">
          <h2 className="font-display text-xl font-bold">{t(inicial ? "movimientos.editar" : "movimientos.nuevo")}</h2>
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
          <button type="button" onClick={guardar} disabled={!form.producto.trim() || !form.ubicacion.trim() || guardando}
            className="rounded-full bg-violeta px-4 py-2 text-[0.85rem] font-semibold text-crema disabled:opacity-50">
            {t("inventario.form_guardar")}
          </button>
        </div>
      </div>
    </div>
  );
}

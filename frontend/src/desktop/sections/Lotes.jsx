import { useState } from "react";
import { PackageSearch, Plus, X, Pencil, Trash2 } from "lucide-react";
import Cargando from "../../components/Cargando";
import TablaCRUD from "../../components/TablaCRUD";
import { toast } from "../../lib/toastStore";
import { num, fecha } from "../../lib/format";
import { useT } from "../../lib/i18n";
import { useApiMutation, useApiQuery } from "../../lib/query";

export default function Lotes({ onNavegar }) {
  const t = useT();
  const { data, error } = useApiQuery("lotes");
  const loteEliminar = useApiMutation("loteEliminar");
  const items = data?.lotes;
  const [modal, setModal] = useState(null);
  const [q, setQ] = useState("");

  const eliminar = async (id) => {
    try {
      await loteEliminar.mutateAsync(id);
      toast(t("lotes.eliminado"));
    } catch {
      toast(t("lotes.error"), "error");
    }
  };

  if (items == null) return <div className="pt-2"><Cargando error={error} /></div>;

  const qn = q.trim().toLowerCase();
  const filtrados = qn
    ? items.filter((l) => `${l.producto} ${l.ubicacion} ${l.lote}`.toLowerCase().includes(qn))
    : items;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <PackageSearch size={24} className="text-tinta-suave" />
          <div>
            <h1 className="font-display text-2xl font-bold leading-none">{t("lotes.titulo")}</h1>
            <p className="mt-1 text-sm text-tinta-suave">{t("lotes.subtitulo")}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {onNavegar && (
            <button onClick={() => onNavegar("deposito")} className="text-sm font-semibold text-hielo">
              {t("lotes.ver_vencimientos")}
            </button>
          )}
          <button onClick={() => setModal("nuevo")}
            className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-sm font-semibold text-crema">
            <Plus size={15} /> {t("lotes.nuevo")}
          </button>
        </div>
      </header>

      <TablaCRUD
        columnas={[
          { key: "producto", label: t("lotes.col_producto"), sortable: true,
            render: (l) => <span className="font-medium text-tinta">{l.producto}</span> },
          { key: "ubicacion", label: t("lotes.col_ubicacion"), sortable: true,
            render: (l) => <span className="text-tinta-suave">{l.ubicacion}</span> },
          { key: "lote", label: t("lotes.col_lote"), plata: true, render: (l) => l.lote || "—" },
          { key: "vencimiento", label: t("lotes.col_vencimiento"), sortable: true, plata: true,
            render: (l) => (l.vencimiento ? fecha(l.vencimiento) : "—") },
          { key: "cantidad", label: t("lotes.col_cantidad"), sortable: true, align: "right", plata: true,
            render: (l) => num(l.cantidad || 0) },
        ]}
        filas={filtrados}
        q={q}
        onQ={setQ}
        buscarPlaceholder={t("lotes.buscar")}
        vacio={t("lotes.vacio")}
        acciones={(l) => (
          <div className="flex items-center justify-end gap-2">
            <button onClick={() => setModal(l)} aria-label={t("common.editar")} className="text-tinta-suave hover:text-tinta"><Pencil size={14} /></button>
            <button onClick={() => eliminar(l.id)} aria-label={t("common.eliminar")} className="text-tinta-suave hover:text-rojo"><Trash2 size={14} /></button>
          </div>
        )}
      />

      {modal && (
        <ModalLote
          inicial={modal === "nuevo" ? null : modal}
          onClose={() => setModal(null)}
          onGuardado={() => { setModal(null); }}
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
];

function ModalLote({ inicial, onClose, onGuardado }) {
  const t = useT();
  const loteCrear = useApiMutation("loteCrear");
  const loteActualizar = useApiMutation("loteActualizar");
  const [form, setForm] = useState({
    producto: inicial?.producto || "", ubicacion: inicial?.ubicacion || "",
    lote: inicial?.lote || "", vencimiento: inicial?.vencimiento || "",
    cantidad: inicial?.cantidad ?? "",
  });
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);

  const guardar = async () => {
    setGuardando(true);
    setError(null);
    const payload = { ...form, cantidad: Number(form.cantidad) || 0 };
    try {
      if (inicial) await loteActualizar.mutateAsync([inicial.id, payload]);
      else await loteCrear.mutateAsync(payload);
      toast(t(inicial ? "lotes.actualizado" : "lotes.creado"));
      onGuardado();
    } catch (e) {
      setError(e.criollo || t("lotes.error"));
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-tinta/40 p-4" onClick={onClose}>
      <div className="max-h-[85vh] w-full max-w-md overflow-y-auto rounded-[var(--radius-card)] border border-linea bg-crema p-6 sombra-alta" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between">
          <h2 className="font-display text-xl font-bold">{t(inicial ? "lotes.editar" : "lotes.nuevo")}</h2>
          <button onClick={onClose} aria-label={t("common.cerrar")} className="text-tinta-suave hover:text-tinta"><X size={20} /></button>
        </div>
        {CAMPOS.map(([campo, lk, tipo]) => (
          <div key={campo}>
            <label className="mt-3 block text-sm font-semibold text-tinta-suave">{t(lk)}</label>
            <input type={tipo} value={form[campo]} onChange={(e) => setForm({ ...form, [campo]: e.target.value })}
              autoFocus={campo === "producto"}
              className="mt-1 w-full rounded-xl border border-linea bg-papel px-3.5 py-2.5 text-sm outline-none focus:border-tinta/40" />
          </div>
        ))}
        {error && <p className="mt-2 text-sm text-rojo-hondo">{error}</p>}
        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-full border border-linea px-4 py-2 text-sm font-semibold text-tinta-suave">
            {t("lotes.cancelar")}
          </button>
          <button onClick={guardar} disabled={!form.producto.trim() || !form.ubicacion.trim() || guardando}
            className="rounded-full bg-violeta px-4 py-2 text-sm font-semibold text-crema disabled:opacity-50">
            {t("lotes.guardar")}
          </button>
        </div>
      </div>
    </div>
  );
}

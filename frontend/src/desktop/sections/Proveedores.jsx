import { useEffect, useState } from "react";
import { Truck, Plus, X, Pencil, Trash2 } from "lucide-react";
import Cargando from "../../components/Cargando";
import TablaCRUD from "../../components/TablaCRUD";
import { api } from "../../lib/api";
import { toast } from "../../lib/toastStore";
import { useT } from "../../lib/i18n";

function qDeHighlight(highlight) {
  if (!highlight) return "";
  return highlight.startsWith("q:") ? highlight.slice(2) : highlight;
}

export default function Proveedores({ highlight }) {
  const t = useT();
  const [items, setItems] = useState(null);
  const [error, setError] = useState(null);
  const [modal, setModal] = useState(null);
  const [q, setQ] = useState(() => qDeHighlight(highlight));

  useEffect(() => {
    const n = qDeHighlight(highlight);
    if (n) setQ(n);
  }, [highlight]);

  const cargar = () => api.proveedores().then((d) => setItems(d.proveedores)).catch(setError);
  useEffect(() => { cargar(); }, []);

  const eliminar = async (id) => {
    try {
      await api.proveedorEliminar(id);
      toast(t("proveedores.eliminado"));
      cargar();
    } catch {
      toast(t("proveedores.error"), "error");
    }
  };

  if (!items) return <div className="pt-2"><Cargando error={error} /></div>;

  const qn = q.trim().toLowerCase();
  const filtrados = qn
    ? items.filter((p) => `${p.nombre} ${p.contacto} ${p.telefono} ${p.email}`.toLowerCase().includes(qn))
    : items;

  const columnas = [
    { key: "nombre", label: t("proveedores.nombre"), sortable: true,
      render: (p) => <span className="font-medium text-tinta">{p.nombre}</span> },
    { key: "contacto", label: t("proveedores.contacto"), render: (p) => p.contacto || "—" },
    { key: "telefono", label: t("proveedores.telefono"), render: (p) => p.telefono || "—" },
    { key: "email", label: t("proveedores.email"), render: (p) => p.email || "—" },
  ];

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Truck size={24} className="text-tinta-suave" />
          <div>
            <h1 className="font-display text-2xl font-bold leading-none">{t("proveedores.titulo")}</h1>
            <p className="mt-1 text-[0.9rem] text-tinta-suave">{t("proveedores.subtitulo")}</p>
          </div>
        </div>
        <button onClick={() => setModal("nuevo")}
          className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-[0.85rem] font-semibold text-crema">
          <Plus size={15} /> {t("proveedores.nuevo")}
        </button>
      </header>

      <TablaCRUD
        columnas={columnas}
        filas={filtrados}
        q={q}
        onQ={setQ}
        buscarPlaceholder={t("proveedores.buscar")}
        vacio={t("proveedores.vacio")}
        acciones={(p) => (
          <div className="flex items-center justify-end gap-2">
            <button onClick={() => setModal(p)} className="text-tinta-suave hover:text-tinta"><Pencil size={14} /></button>
            <button onClick={() => eliminar(p.id)} className="text-tinta-suave hover:text-rojo"><Trash2 size={14} /></button>
          </div>
        )}
      />

      {modal && (
        <ModalProveedor
          inicial={modal === "nuevo" ? null : modal}
          onClose={() => setModal(null)}
          onGuardado={() => { setModal(null); cargar(); }}
        />
      )}
    </div>
  );
}

const CAMPOS = [
  ["nombre", "proveedores.nombre", "proveedores.nombre_ph"],
  ["contacto", "proveedores.contacto", "proveedores.contacto_ph"],
  ["telefono", "proveedores.telefono", "proveedores.telefono_ph"],
  ["email", "proveedores.email", "proveedores.email_ph"],
  ["notas", "proveedores.notas", "proveedores.notas_ph"],
];

function ModalProveedor({ inicial, onClose, onGuardado }) {
  const t = useT();
  const [form, setForm] = useState({
    nombre: inicial?.nombre || "", contacto: inicial?.contacto || "",
    telefono: inicial?.telefono || "", email: inicial?.email || "", notas: inicial?.notas || "",
  });
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);

  const guardar = async () => {
    setGuardando(true);
    setError(null);
    try {
      if (inicial) await api.proveedorActualizar(inicial.id, form);
      else await api.proveedorCrear(form);
      toast(t(inicial ? "proveedores.actualizado" : "proveedores.creado"));
      onGuardado();
    } catch (e) {
      setError(e.criollo || t("proveedores.error"));
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-tinta/40 p-4" onClick={onClose}>
      <div className="max-h-[85vh] w-full max-w-md overflow-y-auto rounded-[var(--radius-card)] border border-linea bg-crema p-6 sombra-alta" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between">
          <h2 className="font-display text-xl font-bold">{t(inicial ? "proveedores.editar" : "proveedores.nuevo")}</h2>
          <button onClick={onClose} className="text-tinta-suave hover:text-tinta"><X size={20} /></button>
        </div>
        {CAMPOS.map(([campo, lk, phk]) => (
          <div key={campo}>
            <label className="mt-3 block text-[0.82rem] font-semibold text-tinta-suave">{t(lk)}</label>
            <input value={form[campo]} onChange={(e) => setForm({ ...form, [campo]: e.target.value })}
              autoFocus={campo === "nombre"} placeholder={t(phk)}
              className="mt-1 w-full rounded-xl border border-linea bg-papel px-3.5 py-2.5 text-[0.9rem] outline-none focus:border-tinta/40" />
          </div>
        ))}
        {error && <p className="mt-2 text-[0.82rem] text-rojo-hondo">{error}</p>}
        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-full border border-linea px-4 py-2 text-[0.85rem] font-semibold text-tinta-suave">
            {t("proveedores.cancelar")}
          </button>
          <button onClick={guardar} disabled={!form.nombre.trim() || guardando}
            className="rounded-full bg-violeta px-4 py-2 text-[0.85rem] font-semibold text-crema disabled:opacity-50">
            {t("proveedores.guardar")}
          </button>
        </div>
      </div>
    </div>
  );
}

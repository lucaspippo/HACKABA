import { useEffect, useState } from "react";
import { MapPin, X, Pencil, Trash2 } from "lucide-react";
import Cargando from "../../components/Cargando";
import TablaCRUD from "../../components/TablaCRUD";
import CellLink, { paramLink } from "../../components/CellLink";
import { api } from "../../lib/api";
import { toast } from "../../lib/toastStore";
import { useT } from "../../lib/i18n";
import { useQuerySeed } from "../../lib/usePagedList";

export default function Ubicaciones() {
  const t = useT();
  const [items, setItems] = useState(null);
  const [error, setError] = useState(null);
  const [modal, setModal] = useState(null); // null | "nueva" | {id,...}
  const seed = useQuerySeed();
  const [q, setQ] = useState(seed);

  const cargar = () => api.ubicaciones().then((d) => setItems(d.ubicaciones)).catch(setError);
  useEffect(() => { cargar(); }, []);
  useEffect(() => { if (seed) setQ(seed); }, [seed]);

  const eliminar = async (id) => {
    try {
      await api.ubicacionEliminar(id);
      toast(t("ubicaciones.eliminada"));
      cargar();
    } catch {
      toast(t("ubicaciones.error"), "error");
    }
  };

  if (!items) return <div className="pt-2"><Cargando error={error} /></div>;

  const qn = q.trim().toLowerCase();
  const filtradas = qn ? items.filter((u) => `${u.nombre} ${u.nota || ""}`.toLowerCase().includes(qn)) : items;

  const columnas = [
    { key: "nombre", label: t("ubicaciones.nombre"), sortable: true,
      render: (u) => (
        <span className="flex items-center gap-2 font-medium text-tinta">
          <MapPin size={14} className="shrink-0 text-tinta-suave" />
          <CellLink to={paramLink("movimientos", "ubicacion", u.nombre)}>{u.nombre}</CellLink>
        </span>
      ) },
    { key: "nota", label: t("ubicaciones.nota"), render: (u) => u.nota || "—" },
  ];

  return (
    <div className="space-y-6">
      <header className="flex items-center gap-2">
        <MapPin size={24} className="text-tinta-suave" />
        <div>
          <h1 className="font-display text-2xl font-bold leading-none">{t("ubicaciones.titulo")}</h1>
          <p className="mt-1 text-[0.9rem] text-tinta-suave">{t("ubicaciones.subtitulo")}</p>
        </div>
      </header>

      <TablaCRUD
        titulo={t("ubicaciones.titulo")}
        columnas={columnas}
        filas={filtradas}
        q={q}
        onQ={setQ}
        buscarPlaceholder={t("ubicaciones.buscar")}
        vacio={t("ubicaciones.vacio")}
        onCrear={() => setModal("nueva")}
        crearLabel={t("ubicaciones.nueva")}
        onLimpiar={q ? () => setQ("") : undefined}
        acciones={(u) => (
          <div className="flex items-center justify-end gap-2">
            <button type="button" onClick={() => setModal(u)} className="text-tinta-suave hover:text-tinta"><Pencil size={14} /></button>
            <button type="button" onClick={() => eliminar(u.id)} className="text-tinta-suave hover:text-rojo"><Trash2 size={14} /></button>
          </div>
        )}
      />

      {modal && (
        <ModalUbicacion
          inicial={modal === "nueva" ? null : modal}
          onClose={() => setModal(null)}
          onGuardado={() => { setModal(null); cargar(); }}
        />
      )}
    </div>
  );
}

function ModalUbicacion({ inicial, onClose, onGuardado }) {
  const t = useT();
  const [nombre, setNombre] = useState(inicial?.nombre || "");
  const [nota, setNota] = useState(inicial?.nota || "");
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);

  const guardar = async () => {
    setGuardando(true);
    setError(null);
    try {
      if (inicial) await api.ubicacionActualizar(inicial.id, { nombre, nota });
      else await api.ubicacionCrear({ nombre, nota });
      toast(t(inicial ? "ubicaciones.actualizada" : "ubicaciones.creada"));
      onGuardado();
    } catch (e) {
      setError(e.criollo || t("ubicaciones.error"));
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-tinta/40 p-4" onClick={onClose}>
      <div className="w-full max-w-md rounded-[var(--radius-card)] border border-linea bg-crema p-6 sombra-alta" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between">
          <h2 className="font-display text-xl font-bold">{t(inicial ? "ubicaciones.editar" : "ubicaciones.nueva")}</h2>
          <button onClick={onClose} className="text-tinta-suave hover:text-tinta"><X size={20} /></button>
        </div>
        <label className="mt-4 block text-[0.82rem] font-semibold text-tinta-suave">{t("ubicaciones.nombre")}</label>
        <input value={nombre} onChange={(e) => setNombre(e.target.value)} autoFocus
          placeholder={t("ubicaciones.nombre_ph")}
          className="mt-1 w-full rounded-xl border border-linea bg-papel px-3.5 py-2.5 text-[0.9rem] outline-none focus:border-tinta/40" />
        <label className="mt-3 block text-[0.82rem] font-semibold text-tinta-suave">{t("ubicaciones.nota")}</label>
        <input value={nota} onChange={(e) => setNota(e.target.value)}
          placeholder={t("ubicaciones.nota_ph")}
          className="mt-1 w-full rounded-xl border border-linea bg-papel px-3.5 py-2.5 text-[0.9rem] outline-none focus:border-tinta/40" />
        {error && <p className="mt-2 text-[0.82rem] text-rojo-hondo">{error}</p>}
        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-full border border-linea px-4 py-2 text-[0.85rem] font-semibold text-tinta-suave">
            {t("ubicaciones.cancelar")}
          </button>
          <button onClick={guardar} disabled={!nombre.trim() || guardando}
            className="rounded-full bg-violeta px-4 py-2 text-[0.85rem] font-semibold text-crema disabled:opacity-50">
            {t("ubicaciones.guardar")}
          </button>
        </div>
      </div>
    </div>
  );
}

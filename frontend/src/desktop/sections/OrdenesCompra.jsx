import { useEffect, useState } from "react";
import { ClipboardList, X, Trash2, FileText, CircleDot, PackageCheck, Ban } from "lucide-react";
import Cargando from "../../components/Cargando";
import TablaCRUD from "../../components/TablaCRUD";
import { FilterChip, FilterDivider, FilterRail } from "../../components/FilterRail";
import DateRangePicker from "../../components/DateRangePicker";
import CellLink, { paramLink, qLink } from "../../components/CellLink";
import { useApiMutation, useApiQuery } from "../../lib/query";
import { toast } from "../../lib/toastStore";
import { fecha } from "../../lib/format";
import { useT } from "../../lib/i18n";
import { useQuerySeed } from "../../lib/usePagedList";

function qDeHighlight(highlight) {
  if (!highlight) return "";
  return highlight.startsWith("q:") ? highlight.slice(2) : highlight;
}

const ESTADO_CLS = {
  borrador: "bg-oro/15 text-oro-tinta",
  aprobada: "bg-hielo/12 text-hielo",
  recibida: "bg-salvia/15 text-salvia",
  cancelada: "bg-papel-hondo text-tinta-suave",
};

const ESTADO_ICON = {
  borrador: FileText,
  aprobada: CircleDot,
  recibida: PackageCheck,
  cancelada: Ban,
};

export default function OrdenesCompra({ highlight }) {
  const t = useT();
  const { data, error } = useApiQuery("ordenesPreparadas");
  const items = data?.ordenes;
  const setStatus = useApiMutation("ordenCompraEstado");
  const [modal, setModal] = useState(false);
  const seed = useQuerySeed();
  const [q, setQ] = useState(() => qDeHighlight(highlight) || seed);
  const [estado, setEstado] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  useEffect(() => {
    const n = qDeHighlight(highlight);
    if (n) setQ(n);
  }, [highlight]);

  useEffect(() => { if (seed) setQ(seed); }, [seed]);

  const cambiarEstado = async (numero, estado) => {
    try {
      await setStatus.mutateAsync([numero, estado]);
    } catch {
      toast(t("ordenes.error"), "error");
    }
  };

  if (!items) return <div className="pt-2"><Cargando error={error} /></div>;

  const qn = q.trim().toLowerCase();
  const filtradas = (qn
    ? items.filter((o) => `${o.numero} ${o.proveedor || ""}`.toLowerCase().includes(qn))
    : items
  ).filter((o) => {
    if (estado && o.estado !== estado) return false;
    if (dateFrom && (o.fecha || "") < dateFrom) return false;
    if (dateTo && (o.fecha || "") > dateTo) return false;
    return true;
  });

  const estadoCounts = {};
  for (const o of items) estadoCounts[o.estado] = (estadoCounts[o.estado] || 0) + 1;
  const estadosPresentes = ["borrador", "aprobada", "recibida", "cancelada"].filter((k) => estadoCounts[k]);

  const hasFilters = !!(q || estado || dateFrom || dateTo);
  const clearFilters = () => { setQ(""); setEstado(""); setDateFrom(""); setDateTo(""); };

  const resumenItems = (o) => {
    const its = o.items || [];
    if (its.length === 0) return "—";
    const primero = its[0].producto;
    return its.length > 1 ? `${primero} (+${its.length - 1})` : primero;
  };

  return (
    <div className="space-y-6">
      <header className="flex items-center gap-2">
        <ClipboardList size={24} className="text-tinta-suave" />
        <div>
          <h1 className="font-display text-2xl font-bold leading-none">{t("ordenes.titulo")}</h1>
          <p className="mt-1 text-sm text-tinta-suave">{t("ordenes.subtitulo")}</p>
        </div>
      </header>

      <TablaCRUD
        idDe={(o) => o.numero}
        titulo={t("ordenes.titulo")}
        columnas={[
          { key: "numero", label: t("ordenes.col_numero"), sortable: true,
            render: (o) => (
              <CellLink to={paramLink("recepciones", "po_number", o.numero)}>
                <span className="plata font-semibold">{o.numero}</span>
              </CellLink>
            ) },
          { key: "estado", label: t("ordenes.col_estado"), sortable: true, groupable: true,
            groupLabel: (k) => t(`ordenes.estado_${k}`),
            render: (o) => (
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${ESTADO_CLS[o.estado] || ESTADO_CLS.borrador}`}>
                {t(`ordenes.estado_${o.estado}`)}
              </span>
            ) },
          { key: "proveedor", label: t("ordenes.proveedor"), sortable: true, groupable: true,
            render: (o) => <CellLink to={qLink("proveedores", o.proveedor)}>{o.proveedor || "—"}</CellLink> },
          { key: "fecha", label: t("ordenes.fecha"), sortable: true, plata: true,
            render: (o) => fecha(o.fecha) },
          { key: "ubicacion_entrega", label: t("ordenes.ubicacion_entrega"), groupable: true,
            render: (o) => <CellLink to={qLink("ubicaciones", o.ubicacion_entrega)}>{o.ubicacion_entrega || "—"}</CellLink> },
          { key: "items", label: t("ordenes.items"), render: resumenItems },
        ]}
        filas={filtradas}
        q={q}
        onQ={setQ}
        buscarPlaceholder={t("ordenes.buscar")}
        vacio={qn ? t("ordenes.vacio_filtro") : t("ordenes.vacio")}
        onCrear={() => setModal(true)}
        crearLabel={t("ordenes.nueva")}
        onLimpiar={hasFilters ? clearFilters : undefined}
        filtros={(
          <FilterRail onClear={hasFilters ? clearFilters : undefined} clearLabel={t("crud.limpiar_filtros")}>
            {estadosPresentes.map((k) => {
              const Icon = ESTADO_ICON[k];
              return (
                <FilterChip key={k} icon={Icon} active={estado === k}
                  tone={k === "cancelada" ? "ink" : k === "borrador" ? "attention" : "ink"}
                  onClick={() => setEstado(estado === k ? "" : k)}>
                  {t(`ordenes.estado_${k}`)}
                </FilterChip>
              );
            })}
            <FilterDivider />
            <DateRangePicker from={dateFrom} to={dateTo} onChange={(a, b) => { setDateFrom(a); setDateTo(b); }} />
          </FilterRail>
        )}
        acciones={(o) => (
          <div className="flex justify-end gap-1.5">
            {o.estado === "borrador" && (
              <>
                <button onClick={() => cambiarEstado(o.numero, "aprobada")}
                  className="rounded-full border border-linea px-3 py-1 text-xs font-semibold text-tinta-suave hover:text-tinta">
                  {t("ordenes.aprobar")}
                </button>
                <button onClick={() => cambiarEstado(o.numero, "cancelada")}
                  className="rounded-full border border-linea px-3 py-1 text-xs font-semibold text-tinta-suave hover:text-rojo">
                  {t("ordenes.cancelar_orden")}
                </button>
              </>
            )}
            {o.estado === "aprobada" && (
              <button onClick={() => cambiarEstado(o.numero, "recibida")}
                className="rounded-full border border-linea px-3 py-1 text-xs font-semibold text-tinta-suave hover:text-tinta">
                {t("ordenes.marcar_recibida")}
              </button>
            )}
          </div>
        )}
      />

      {modal && (
        <ModalOrden onClose={() => setModal(false)} onGuardado={() => setModal(false)} />
      )}
    </div>
  );
}

function ModalOrden({ onClose, onGuardado }) {
  const t = useT();
  const { data: vendorData } = useApiQuery("proveedores");
  const { data: locationData } = useApiQuery("ubicaciones");
  const createOrder = useApiMutation("ordenCompraCrear");
  const proveedores = vendorData?.proveedores ?? [];
  const ubicaciones = locationData?.ubicaciones ?? [];
  const [proveedor, setProveedor] = useState("");
  const [ubicacion, setUbicacion] = useState("");
  const [fechaOrden, setFechaOrden] = useState("");
  const [motivo, setMotivo] = useState("");
  const [items, setItems] = useState([{ producto: "", cantidad: "" }]);
  const [error, setError] = useState(null);

  const cambiarItem = (i, campo, valor) =>
    setItems((prev) => prev.map((it, idx) => (idx === i ? { ...it, [campo]: valor } : it)));
  const agregarItem = () => setItems((prev) => [...prev, { producto: "", cantidad: "" }]);
  const quitarItem = (i) => setItems((prev) => prev.filter((_, idx) => idx !== i));

  const guardar = async () => {
    setError(null);
    const validos = items
      .filter((it) => it.producto.trim())
      .map((it) => ({ producto: it.producto, cantidad: Number(it.cantidad) || 0 }));
    try {
      await createOrder.mutateAsync([{
        proveedor, ubicacion, fecha: fechaOrden, motivo, items: validos,
      }]);
      toast(t("ordenes.creada"));
      onGuardado();
    } catch (e) {
      setError(e.criollo || t("ordenes.error"));
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-tinta/40 p-4" onClick={onClose}>
      <div className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-[var(--radius-card)] border border-linea bg-crema p-6 sombra-alta" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between">
          <h2 className="font-display text-xl font-bold">{t("ordenes.nueva")}</h2>
          <button onClick={onClose} aria-label={t("common.cerrar")} className="text-tinta-suave hover:text-tinta"><X size={20} /></button>
        </div>

        <label className="mt-4 block text-sm font-semibold text-tinta-suave">{t("ordenes.proveedor")}</label>
        <input value={proveedor} onChange={(e) => setProveedor(e.target.value)} list="proveedores-dl"
          placeholder={t("ordenes.proveedor_ph")}
          className="mt-1 w-full rounded-xl border border-linea bg-papel px-3.5 py-2.5 text-sm outline-none focus:border-tinta/40" />
        <datalist id="proveedores-dl">
          {proveedores.map((p) => <option key={p.id} value={p.nombre} />)}
        </datalist>

        <label className="mt-3 block text-sm font-semibold text-tinta-suave">{t("ordenes.ubicacion_entrega")}</label>
        <input value={ubicacion} onChange={(e) => setUbicacion(e.target.value)} list="ubicaciones-dl"
          placeholder={t("ordenes.ubicacion_ph")}
          className="mt-1 w-full rounded-xl border border-linea bg-papel px-3.5 py-2.5 text-sm outline-none focus:border-tinta/40" />
        <datalist id="ubicaciones-dl">
          {ubicaciones.map((u) => <option key={u.id} value={u.nombre} />)}
        </datalist>

        <label className="mt-3 block text-sm font-semibold text-tinta-suave">{t("ordenes.fecha")}</label>
        <input type="date" value={fechaOrden} onChange={(e) => setFechaOrden(e.target.value)}
          className="mt-1 w-full rounded-xl border border-linea bg-papel px-3.5 py-2.5 text-sm outline-none focus:border-tinta/40" />

        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm font-semibold text-tinta-suave">{t("ordenes.items")}</p>
          <button onClick={agregarItem} className="text-sm font-semibold text-violeta">{t("ordenes.agregar_item")}</button>
        </div>
        <div className="mt-1.5 space-y-2">
          {items.map((it, i) => (
            <div key={i} className="flex items-center gap-2">
              <input value={it.producto} onChange={(e) => cambiarItem(i, "producto", e.target.value)}
                placeholder={t("ordenes.item_producto_ph")}
                className="min-w-0 flex-1 rounded-xl border border-linea bg-papel px-3 py-2 text-sm outline-none focus:border-tinta/40" />
              <input type="number" value={it.cantidad} onChange={(e) => cambiarItem(i, "cantidad", e.target.value)}
                placeholder={t("ordenes.item_cantidad_ph")}
                className="w-24 rounded-xl border border-linea bg-papel px-3 py-2 text-sm outline-none focus:border-tinta/40" />
              {items.length > 1 && (
                <button onClick={() => quitarItem(i)} aria-label={t("common.eliminar")} className="text-tinta-suave hover:text-rojo"><Trash2 size={15} /></button>
              )}
            </div>
          ))}
        </div>

        <label className="mt-3 block text-sm font-semibold text-tinta-suave">{t("ordenes.motivo")}</label>
        <input value={motivo} onChange={(e) => setMotivo(e.target.value)}
          className="mt-1 w-full rounded-xl border border-linea bg-papel px-3.5 py-2.5 text-sm outline-none focus:border-tinta/40" />

        {error && <p className="mt-2 text-sm text-rojo-hondo">{error}</p>}
        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-full border border-linea px-4 py-2 text-sm font-semibold text-tinta-suave">
            {t("ordenes.cancelar")}
          </button>
          <button onClick={guardar}
            disabled={!proveedor.trim() || !items.some((it) => it.producto.trim()) || createOrder.isPending}
            className="rounded-full bg-violeta px-4 py-2 text-sm font-semibold text-crema disabled:opacity-50">
            {t("ordenes.crear")}
          </button>
        </div>
      </div>
    </div>
  );
}

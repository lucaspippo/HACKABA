import { useCallback, useEffect, useState } from "react";
import { Boxes, Pencil, Trash2, X } from "lucide-react";
import Cargando from "../../components/Cargando";
import TablaCRUD, { SourceBadge, SourceChips } from "../../components/TablaCRUD";
import { api } from "../../lib/api";
import { toast } from "../../lib/toastStore";
import { num, peso } from "../../lib/format";
import { usePagedList } from "../../lib/usePagedList";
import { useT } from "../../lib/i18n";

const ERRORES_DATO = ["fantasma", "negativo", "sin_precio", "balanza", "costo_viejo"];
const ESTADO_CAL = {
  ok: { lk: "inventario.estado_ok", cls: "bg-salvia/15 text-salvia" },
  fantasma: { lk: "inventario.estado_fantasma", cls: "bg-rojo/12 text-rojo" },
  negativo: { lk: "inventario.estado_negativo", cls: "bg-rojo/12 text-rojo" },
  sin_precio: { lk: "inventario.estado_sin_precio", cls: "bg-oro/20 text-oro-tinta" },
  balanza: { lk: "inventario.estado_balanza", cls: "bg-oro/20 text-oro-tinta" },
  costo_viejo: { lk: "inventario.estado_costo_viejo", cls: "bg-oro/20 text-oro-tinta" },
};

export default function Productos({ data, highlight }) {
  const t = useT();
  const [filtro, setFiltro] = useState("todos");
  const [errSel, setErrSel] = useState("todos");
  const [modal, setModal] = useState(null);
  const [exportando, setExportando] = useState(false);

  useEffect(() => {
    if (!highlight) return;
    if (highlight === "balanza" || highlight === "balanzas") setFiltro("balanza");
    else if (highlight === "a_corregir") setFiltro("a_corregir");
    else if (["fantasma", "negativo", "sin_precio", "balanza", "costo_viejo"].includes(highlight)) {
      setFiltro("a_corregir");
      setErrSel(highlight);
    }
  }, [highlight]);

  const fetcher = useCallback(
    (p) => api.productos({
      ...p,
      filtro: filtro === "todos" ? "" : filtro,
      err: filtro === "a_corregir" && errSel !== "todos" ? errSel : "",
    }),
    [filtro, errSel],
  );
  const page = usePagedList(fetcher);

  const alertas = data?.alertas || {};
  const nACorregir = ["fantasmas", "negativos", "sin_pvp", "balanza"]
    .reduce((a, k) => a + (alertas[k]?.cantidad || 0), 0);

  const eliminar = async (codigo) => {
    try {
      await api.articuloEliminar(codigo);
      toast(t("productos.eliminado"));
      page.reload();
    } catch {
      toast(t("productos.error"), "error");
    }
  };

  const exportar = async () => {
    setExportando(true);
    try {
      await api.productosExport({
        ...page.query(),
        filtro: filtro === "todos" ? "" : filtro,
        err: filtro === "a_corregir" && errSel !== "todos" ? errSel : "",
      });
    } catch {
      toast(t("crud.export_error"), "error");
    } finally {
      setExportando(false);
    }
  };

  if (page.loading && page.items.length === 0) {
    return <div className="pt-2"><Cargando error={page.error} /></div>;
  }

  const chips = [
    { id: "todos", label: t("inventario.filtro_todos") },
    { id: "ok", label: t("inventario.filtro_activos") },
    { id: "balanza", label: t("inventario.filtro_balanza") },
    { id: "a_corregir", label: t("inventario.filtro_a_corregir", { n: num(nACorregir) }) },
  ];

  return (
    <div className="space-y-6">
      <header className="flex items-center gap-2">
        <Boxes size={24} className="text-tinta-suave" />
        <div>
          <h1 className="font-display text-2xl font-bold leading-none">{t("productos.titulo")}</h1>
          <p className="mt-1 text-[0.9rem] text-tinta-suave">{t("productos.subtitulo")}</p>
        </div>
      </header>

      <TablaCRUD
        titulo={t("inventario.tabla_titulo")}
        conteo={t("inventario.tabla_conteo", { a: num(page.items.length), b: num(page.total) })}
        columnas={[
          { key: "descripcion", label: t("inventario.col_producto"), sortable: true,
            render: (p) => (
              <span>
                <span className="font-medium text-tinta">{p.descripcion}</span>
                <span className="mt-0.5 block text-[0.78rem] text-tinta-suave">{t("inventario.cod", { codigo: p.codigo })}</span>
              </span>
            ) },
          { key: "sku", label: t("imported.col_sku"), sortable: true, plata: true,
            render: (p) => p.sku || "—" },
          { key: "stock", label: t("inventario.col_stock"), sortable: true, align: "right", plata: true,
            render: (p) => {
              const pipe = [
                (Number(p.incoming_qty) || 0) !== 0 && t("inventario.pipeline_inc", { n: num(p.incoming_qty) }),
                (Number(p.outgoing_qty) || 0) !== 0 && t("inventario.pipeline_out", { n: num(p.outgoing_qty) }),
              ].filter(Boolean).join(" · ");
              return (
                <span>
                  {num(Math.round(p.stock || 0))}
                  {pipe ? <span className="mt-0.5 block text-[0.78rem] font-normal text-tinta-suave">{pipe}</span> : null}
                </span>
              );
            } },
          { key: "costo_iva", label: t("inventario.col_costo"), sortable: true, align: "right", plata: true,
            render: (p) => (
              <span>
                {p.costo_iva ? peso(p.costo_iva) : "—"}
                {p.source === "odoo" && p.costo_iva > 0 && (
                  <span className="mt-0.5 block text-[0.78rem] font-normal text-tinta-suave">{t("inventario.col_costo_odoo")}</span>
                )}
              </span>
            ) },
          { key: "pvp", label: t("inventario.col_pvp"), sortable: true, align: "right", plata: true,
            render: (p) => {
              if (p.pricing_status === "needs_pricing") {
                return <span className="text-rojo">{t("imported.pricing_needs")}</span>;
              }
              return (
                <span>
                  {p.pvp ? peso(p.pvp) : "—"}
                  {p.pricing_status === "wholesale_only" && (
                    <span className="mt-0.5 block text-[0.78rem] font-normal text-tinta-suave">
                      {t("imported.pricing_wholesale")}
                    </span>
                  )}
                </span>
              );
            } },
          { key: "margen_venta_pct", label: t("inventario.col_margen"), sortable: true, align: "right", plata: true,
            render: (p) => (p.margen_venta_pct == null ? "—" : (
              <span>
                {num(p.margen_venta_pct)}%
                {p.margen_pesos != null && (
                  <span className="mt-0.5 block text-[0.78rem] font-normal text-tinta-suave">{peso(p.margen_pesos)}</span>
                )}
              </span>
            )) },
          { key: "estado_calidad", label: t("inventario.col_estado"), sortable: true,
            render: (p) => {
              const e = ESTADO_CAL[p.estado_calidad] || ESTADO_CAL.ok;
              return <span className={`rounded-full px-2.5 py-0.5 text-[0.72rem] font-semibold ${e.cls}`}>{t(e.lk)}</span>;
            } },
          { key: "source", label: t("imported.col_source"), sortable: true,
            render: (p) => <SourceBadge source={p.source} t={t} /> },
        ]}
        filas={page.items}
        idDe={(p) => p.codigo}
        q={page.q}
        onQ={page.setQ}
        buscarPlaceholder={t("inventario.tabla_buscar")}
        vacio={t("productos.vacio")}
        onCrear={() => setModal("nuevo")}
        crearLabel={t("inventario.nuevo_producto")}
        onExport={exportar}
        exportando={exportando}
        onSort={page.toggleSort}
        orden={page.sort}
        onLoadMore={page.loadMore}
        hasMore={page.hasMore}
        cargandoMas={page.loadingMore}
        cargando={page.loading}
        filtros={(
          <>
            {chips.map((c) => (
              <button key={c.id} type="button" onClick={() => { setFiltro(c.id); setErrSel("todos"); }}
                className={`rounded-full px-3 py-1 text-[0.82rem] font-semibold ${
                  filtro === c.id
                    ? c.id === "a_corregir" ? "bg-rojo text-crema" : "bg-tinta text-crema"
                    : c.id === "a_corregir" && nACorregir > 0
                      ? "border border-rojo/35 text-rojo" : "border border-linea text-tinta-suave"}`}>
                {c.label}
              </button>
            ))}
            <span className="mx-1 h-4 w-px bg-linea" />
            <SourceChips value={page.source} onChange={page.setSource} t={t} />
            {filtro === "a_corregir" && ERRORES_DATO.map((e) => (
              <button key={e} type="button" onClick={() => setErrSel(e)}
                className={`rounded-full px-3 py-1 text-[0.82rem] font-semibold ${
                  errSel === e ? "bg-rojo text-crema" : "border border-rojo/30 text-rojo"}`}>
                {t(ESTADO_CAL[e].lk)}
              </button>
            ))}
          </>
        )}
        acciones={(p) => (
          <div className="flex items-center justify-end gap-2">
            <button type="button" onClick={() => setModal(p)} className="text-tinta-suave hover:text-tinta"><Pencil size={14} /></button>
            <button type="button" onClick={() => eliminar(p.codigo)} className="text-tinta-suave hover:text-rojo"><Trash2 size={14} /></button>
          </div>
        )}
      />

      {modal && (
        <ModalArticulo
          inicial={modal === "nuevo" ? null : modal}
          onClose={() => setModal(null)}
          onGuardado={() => { setModal(null); page.reload(); }}
        />
      )}
    </div>
  );
}

const CAMPOS_ARTICULO = [
  ["codigo", "inventario.form_codigo", "number"],
  ["descripcion", "inventario.form_descripcion", "text"],
  ["tipo", "inventario.form_categoria", "text"],
  ["proveedor", "inventario.form_proveedor", "text"],
  ["stock", "inventario.form_stock", "number"],
  ["costo_iva", "inventario.form_costo", "number"],
  ["pvp", "inventario.form_pvp", "number"],
];

function ModalArticulo({ inicial, onClose, onGuardado }) {
  const t = useT();
  const [form, setForm] = useState({
    codigo: inicial?.codigo ?? "", descripcion: inicial?.descripcion || "",
    tipo: inicial?.tipo || "", proveedor: inicial?.proveedor || "",
    stock: inicial?.stock ?? "", costo_iva: inicial?.costo_iva ?? "", pvp: inicial?.pvp ?? "",
  });
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);

  const guardar = async () => {
    setGuardando(true);
    setError(null);
    const payload = {
      ...form,
      codigo: Number(form.codigo),
      stock: form.stock === "" ? 0 : Number(form.stock),
      costo_iva: form.costo_iva === "" ? null : Number(form.costo_iva),
      pvp: form.pvp === "" ? null : Number(form.pvp),
    };
    try {
      if (inicial) {
        const { codigo, ...cambios } = payload;
        await api.articuloActualizar(inicial.codigo, cambios);
      } else {
        await api.articuloCrear(payload);
      }
      toast(t(inicial ? "inventario.producto_actualizado" : "inventario.producto_creado"));
      onGuardado();
    } catch (e) {
      setError(e.criollo || t("inventario.form_error"));
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-tinta/40 p-4" onClick={onClose}>
      <div className="max-h-[85vh] w-full max-w-md overflow-y-auto rounded-[var(--radius-card)] border border-linea bg-crema p-6 sombra-alta" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between">
          <h2 className="font-display text-xl font-bold">{t(inicial ? "inventario.form_editar" : "inventario.nuevo_producto")}</h2>
          <button type="button" onClick={onClose} className="text-tinta-suave hover:text-tinta"><X size={20} /></button>
        </div>
        {CAMPOS_ARTICULO.map(([campo, lk, tipo]) => (
          <div key={campo}>
            <label className="mt-3 block text-[0.82rem] font-semibold text-tinta-suave">{t(lk)}</label>
            <input type={tipo} value={form[campo]} disabled={campo === "codigo" && !!inicial}
              onChange={(e) => setForm({ ...form, [campo]: e.target.value })}
              autoFocus={campo === "codigo"}
              className="mt-1 w-full rounded-xl border border-linea bg-papel px-3.5 py-2.5 text-[0.9rem] outline-none focus:border-tinta/40 disabled:opacity-60" />
          </div>
        ))}
        {error && <p className="mt-2 text-[0.82rem] text-rojo-hondo">{error}</p>}
        <div className="mt-5 flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-full border border-linea px-4 py-2 text-[0.85rem] font-semibold text-tinta-suave">
            {t("inventario.form_cancelar")}
          </button>
          <button type="button" onClick={guardar} disabled={!form.codigo || !form.descripcion.trim() || guardando}
            className="rounded-full bg-violeta px-4 py-2 text-[0.85rem] font-semibold text-crema disabled:opacity-50">
            {t("inventario.form_guardar")}
          </button>
        </div>
      </div>
    </div>
  );
}

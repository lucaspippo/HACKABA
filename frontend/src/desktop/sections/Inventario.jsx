import { useEffect, useState } from "react";
import { Sparkles, X, Pencil, ArrowRight } from "lucide-react";
import { toast } from "../../lib/toastStore";
import AngelaMark from "../../components/AngelaMark";
import { useVista, vistaStore } from "../../lib/vistaStore";
import { useFoco, focoStore } from "../../lib/focoStore";
import { contarACorregir } from "../../lib/alertas";
import { peso, num } from "../../lib/format";
import { api } from "../../lib/api";
import { authStore } from "../../lib/auth";
import { useT } from "../../lib/i18n";
import Panorama from "./InventarioPanorama";
import Margenes from "./Margenes";
import Reponer from "./Reponer";

// P16: the "balanzas" subtab died — a scale product is just a product
// (priced differently): it lives as the "By kg" filter of the full catalog.
const SUBTABS = [
  { id: "panorama", lk: "inventario.tab_panorama" },
  { id: "reponer", lk: "inventario.tab_reponer" },
  { id: "margenes", lk: "inventario.tab_margenes" },
];
const GRUPOS = ["fantasmas", "negativos", "sin_pvp", "balanza", "costo_viejo"];

const ESTADO_CAL = {
  ok: { lk: "inventario.estado_ok", cls: "bg-salvia/15 text-salvia" },
  fantasma: { lk: "inventario.estado_fantasma", cls: "bg-rojo/12 text-rojo" },
  negativo: { lk: "inventario.estado_negativo", cls: "bg-rojo/12 text-rojo" },
  sin_precio: { lk: "inventario.estado_sin_precio", cls: "bg-oro/20 text-oro-tinta" },
  balanza: { lk: "inventario.estado_balanza", cls: "bg-oro/20 text-oro-tinta" },
  costo_viejo: { lk: "inventario.estado_costo_viejo", cls: "bg-oro/20 text-oro-tinta" },
};

export default function Inventario({ data, highlight, onPreguntar, onNavegar }) {
  const t = useT();
  const [sub, setSub] = useState("panorama");
  const [detalle, setDetalle] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);
  const vista = useVista();
  const foco = useFoco();
  const nCorregir = contarACorregir(data);

  const tabs = [...SUBTABS, ...(vista.pestanas || []).map((p) => ({ id: p.id, label: p.nombre, custom: p }))];
  const irABalanzas = () => onNavegar?.("productos", "balanza");

  useEffect(() => {
    if (!highlight) return;
    if (highlight === "foco") setSub("foco");
    else if (highlight === "margenes") setSub("margenes");
    else if (highlight === "reponer") setSub("reponer");
    else if (highlight === "plata" || highlight === "briefing" || highlight === "mapa" || GRUPOS.includes(highlight)) setSub("panorama");
    else if (highlight === "balanzas") irABalanzas();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [highlight]);

  const pestActiva = (vista.pestanas || []).find((p) => p.id === sub);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-3xl font-bold">{t("inventario.titulo")}</h1>
        <p className="mt-1 max-w-2xl text-[0.95rem] leading-snug text-tinta-suave">
          {t("inventario.subtitulo")}
        </p>
      </header>

      <PisoNav t={t} onNavegar={onNavegar} nCorregir={nCorregir} />

      {!vista.balanzaEsquemaOk && <BalanzaPropuesta onVer={irABalanzas} />}

      <div className="flex flex-wrap gap-2 border-b border-linea">
        {tabs.map((tb) => (
          <button
            key={tb.id}
            onClick={() => setSub(tb.id)}
            className={`-mb-px flex items-center gap-1.5 border-b-2 px-1 py-2.5 text-[0.92rem] font-semibold transition-colors ${
              sub === tb.id ? "border-tinta text-tinta" : "border-transparent text-tinta-suave hover:text-tinta"
            }`}
          >
            {tb.lk ? t(tb.lk) : tb.label}
            {tb.custom && (
              <X size={13} onClick={(e) => { e.stopPropagation(); vistaStore.quitarPestana(tb.id); if (sub === tb.id) setSub("panorama"); }}
                 className="opacity-50 hover:opacity-100" />
            )}
          </button>
        ))}
      </div>

      {sub === "foco" && <FocoView foco={foco} onSelect={setDetalle} onPreguntar={onPreguntar} onSalir={() => { focoStore.clear(); setSub("panorama"); }} />}
      {sub === "panorama" && (
        <Panorama
          key={reloadKey}
          data={data}
          onSelect={setDetalle}
          onNavegar={onNavegar}
          onTab={setSub}
          onPreguntar={onPreguntar}
        />
      )}
      {sub === "margenes" && (
        <div data-nav-id="margenes">
          <Margenes onPreguntar={onPreguntar} onNavegar={onNavegar} />
        </div>
      )}
      {sub === "reponer" && (
        <div data-nav-id="reponer">
          <Reponer onPreguntar={onPreguntar} onNavegar={onNavegar} />
        </div>
      )}
      {pestActiva && <PestanaCustom pestana={pestActiva} onSelect={setDetalle} />}

      {detalle && (
        <ProductoDetalle p={detalle} onClose={() => setDetalle(null)} onPreguntar={onPreguntar}
          onGuardado={() => { setDetalle(null); setReloadKey((k) => k + 1); }}
          onNavegar={onNavegar} />
      )}
    </div>
  );
}

function PisoNav({ t, onNavegar, nCorregir }) {
  if (!onNavegar) return null;
  const chips = [
    { id: "productos", label: t("nav.productos") },
    authStore.tiene("saneamiento") && {
      id: "saneamiento", label: t("nav.saneamiento"), badge: nCorregir,
    },
    authStore.tiene("deposito") && { id: "deposito", label: t("nav.deposito") },
    { id: "ordenes_compra", label: t("nav.ordenes_compra") },
  ].filter(Boolean);
  return (
    <nav aria-label={t("inventario.piso_aria")} className="flex flex-wrap items-center gap-2">
      <span className="text-[0.82rem] text-tinta-suave">{t("inventario.piso_trabajar")}</span>
      {chips.map((c) => (
        <button
          key={c.id}
          type="button"
          onClick={() => onNavegar(c.id)}
          className="inline-flex items-center gap-1.5 rounded-full border border-linea bg-crema px-3 py-1.5 text-[0.8rem] font-semibold text-tinta hover:border-tinta/30"
        >
          {c.label}
          {c.badge > 0 && (
            <span className="grid h-4 min-w-4 place-items-center rounded-full bg-oro px-1 text-[0.68rem] font-bold text-crema">
              {num(c.badge)}
            </span>
          )}
        </button>
      ))}
    </nav>
  );
}

function BalanzaPropuesta({ onVer }) {
  const t = useT();
  const [n, setN] = useState(null);
  useEffect(() => { api.balanzas().then((d) => setN(d.total)).catch(() => {}); }, []);
  if (!n) return null;
  return (
    <div className="flex items-start gap-3 rounded-[var(--radius-card)] border border-oro/30 bg-oro/[0.06] p-5">
      <AngelaMark size={34} />
      <div className="flex-1">
        <p className="text-[0.98rem] leading-snug text-tinta">
          {t("inventario.balanza_prop_1")} <b>{t("inventario.balanza_prop_n", { n: num(n) })}</b>{t("inventario.balanza_prop_2")}
        </p>
        <div className="mt-3 flex gap-2">
          <button onClick={() => { vistaStore.aplicar({ balanzaEsquemaOk: true }); onVer(); }}
            className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-[0.88rem] font-semibold text-crema">
            {t("inventario.balanza_prop_si")}
          </button>
          <button onClick={() => vistaStore.aplicar({ balanzaEsquemaOk: true })}
            className="rounded-full border border-linea px-4 py-2 text-[0.88rem] font-semibold text-tinta-suave">
            {t("inventario.balanza_prop_no")}
          </button>
        </div>
      </div>
    </div>
  );
}

function FocoView({ foco, onSelect, onPreguntar, onSalir }) {
  const t = useT();
  const [items, setItems] = useState(null);
  useEffect(() => { api.articulos().then((d) => setItems(d.items)).catch(() => {}); }, []);
  if (!foco?.codigos?.length) {
    return <p className="text-[0.9rem] text-tinta-suave">{t("inventario.foco_vacio")} <button onClick={onSalir} className="font-semibold text-tinta">{t("inventario.foco_volver")}</button>.</p>;
  }
  if (!items) return <p className="text-[0.9rem] text-tinta-suave">{t("inventario.cargando")}</p>;
  const set = new Set(foco.codigos);
  const filt = items.filter((p) => set.has(p.codigo));
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3 rounded-[var(--radius-card)] border border-rojo/25 bg-rojo/[0.04] p-4">
        <AngelaMark size={28} />
        <p className="flex-1 text-[0.92rem] text-tinta"><b>{num(filt.length)}</b> {t("inventario.foco_senalados")} {foco.titulo}</p>
        <button onClick={() => onPreguntar?.(`¿cómo corrijo ${foco.titulo.toLowerCase()}?`)} className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-3.5 py-1.5 text-[0.88rem] font-semibold text-crema">
          <Sparkles size={14} /> {t("inventario.arreglar_angela")}
        </button>
        <button onClick={onSalir} className="rounded-full border border-linea px-3.5 py-1.5 text-[0.88rem] font-semibold text-tinta-suave hover:text-tinta">{t("inventario.salir")}</button>
      </div>
      <div className="overflow-x-auto rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
        <table className="w-full text-[0.88rem]">
          <thead>
            <tr className="border-b border-linea text-left text-tinta-suave">
              <th className="px-4 py-2.5 font-semibold">{t("inventario.col_producto")}</th>
              <th className="px-4 py-2.5 text-right font-semibold">{t("inventario.col_stock")}</th>
              <th className="px-4 py-2.5 text-right font-semibold">{t("inventario.col_costo")}</th>
              <th className="px-4 py-2.5 text-right font-semibold">{t("inventario.col_pvp")}</th>
              <th className="px-4 py-2.5 text-right font-semibold">{t("inventario.plata_parada")}</th>
            </tr>
          </thead>
          <tbody>
            {filt.map((p) => (
              <tr key={p.codigo} onClick={() => onSelect(p)} className="cursor-pointer border-b border-linea/60 bg-rojo/[0.025] last:border-0 hover:bg-rojo/[0.05]">
                <td className="px-4 py-2 text-tinta">{p.descripcion}</td>
                <td className="plata px-4 py-2 text-right">{num(Math.round(p.stock || 0))}</td>
                <td className="plata px-4 py-2 text-right text-tinta-suave">{p.costo_iva ? peso(p.costo_iva) : "—"}</td>
                <td className="plata px-4 py-2 text-right text-tinta-suave">{p.pvp ? peso(p.pvp) : "—"}</td>
                <td className="plata px-4 py-2 text-right font-medium text-hielo">{p.inmovilizado ? peso(p.inmovilizado) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PestanaCustom({ pestana, onSelect }) {
  const t = useT();
  const [items, setItems] = useState(null);
  useEffect(() => { api.articulos().then((d) => setItems(d.items)).catch(() => {}); }, []);
  if (!items) return <p className="text-[0.9rem] text-tinta-suave">{t("inventario.cargando")}</p>;
  const filt = pestana.filtro === "balanza"
    ? items.filter((p) => p.estado_calidad === "balanza")
    : items.filter((p) => p.estado_calidad === pestana.filtro);
  return (
    <div className="space-y-3">
      <p className="text-[0.9rem] text-tinta-suave">
        {t("inventario.pestana_custom_1")} <b>{num(filt.length)}</b> {t("inventario.pestana_custom_2")}
      </p>
      <div className="overflow-x-auto rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
        <table className="w-full text-[0.88rem]">
          <thead>
            <tr className="border-b border-linea text-left text-tinta-suave">
              <th className="px-4 py-2.5 font-semibold">{t("inventario.col_producto")}</th>
              <th className="px-4 py-2.5 text-right font-semibold">{t("inventario.col_stock")}</th>
              <th className="px-4 py-2.5 text-right font-semibold">{t("inventario.plata_parada")}</th>
            </tr>
          </thead>
          <tbody>
            {filt.slice(0, 100).map((p) => (
              <tr key={p.codigo} onClick={() => onSelect(p)} className="cursor-pointer border-b border-linea/60 last:border-0 hover:bg-papel-hondo/40">
                <td className="px-4 py-2 text-tinta">{p.descripcion}</td>
                <td className="plata px-4 py-2 text-right">{num(Math.round(p.stock || 0))}</td>
                <td className="plata px-4 py-2 text-right font-medium text-hielo">{p.inmovilizado ? peso(p.inmovilizado) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ProductoDetalle({ p, onClose, onPreguntar, onGuardado, onNavegar }) {
  const t = useT();
  const [editando, setEditando] = useState(false);
  const e = ESTADO_CAL[p.estado_calidad] || ESTADO_CAL.ok;

  if (editando) {
    return <ModalArticulo inicial={p} onClose={() => setEditando(false)} onGuardado={onGuardado} />;
  }

  const err = p.estado_calidad && p.estado_calidad !== "ok" ? p.estado_calidad : null;

  return (
    <div className="fixed inset-0 z-40 grid place-items-center bg-tinta/40 p-4" onClick={onClose}>
      <div className="w-full max-w-md rounded-[var(--radius-card)] border border-linea bg-crema p-6 sombra-alta" onClick={(ev) => ev.stopPropagation()}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="font-display text-[1.2rem] font-bold leading-tight">{p.descripcion || p.name}</p>
            <p className="text-[0.88rem] text-tinta-suave">{t("inventario.det_codigo", { codigo: p.codigo })}</p>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            {onGuardado && (
              <button onClick={() => setEditando(true)} className="text-tinta-suave hover:text-tinta"><Pencil size={18} /></button>
            )}
            <button onClick={onClose} className="text-tinta-suave hover:text-tinta"><X size={20} /></button>
          </div>
        </div>
        {p.estado_calidad && (
          <span className={`mt-2 inline-block rounded-full px-2.5 py-0.5 text-[0.88rem] font-semibold ${e.cls}`}>{t(e.lk)}</span>
        )}
        <div className="mt-4 grid grid-cols-2 gap-3">
          <Dato label={t("inventario.col_stock")} valor={`${num(p.stock)}${p.unidad_pricing === "kg" ? " kg" : ""}`} alerta={p.stock < 0} />
          <Dato
            label={p.source === "odoo" ? `${t("inventario.col_costo_iva")} · ${t("inventario.col_costo_odoo")}` : t("inventario.col_costo_iva")}
            valor={p.costo_iva ? peso(p.costo_iva) : "—"}
          />
          <Dato label={t("inventario.det_precio_venta")} valor={p.pvp ? peso(p.pvp) : t("inventario.det_sin_cargar")} alerta={!p.pvp} />
          <Dato label={t("inventario.plata_parada")} valor={p.inmovilizado ? peso(p.inmovilizado) : "—"} />
          {(Number(p.incoming_qty) || 0) !== 0 && (
            <Dato label={t("inventario.det_en_camino")} valor={num(p.incoming_qty)} />
          )}
          {(Number(p.outgoing_qty) || 0) !== 0 && (
            <Dato label={t("inventario.det_reservado")} valor={num(p.outgoing_qty)} />
          )}
          {p.unidades != null && (
            <>
              <Dato label={t("inventario.det_piezas")} valor={num(p.unidades)} />
              <Dato label={t("inventario.det_peso_pieza")} valor={`${num(p.peso_por_unidad)} kg`} />
              {p.precio_por_unidad != null && (
                <Dato label={t("inventario.det_precio_pieza")} valor={peso(p.precio_por_unidad)} />
              )}
            </>
          )}
        </div>
        <div className="mt-5 flex flex-wrap gap-2">
          <button
            onClick={() => { onClose(); onPreguntar?.(t("inventario.det_preguntar_q", { nombre: p.descripcion || p.name, codigo: p.codigo })); }}
            className="inline-flex items-center gap-2 rounded-full bg-violeta px-4 py-2 text-[0.88rem] font-semibold text-crema"
          >
            <AngelaMark size={18} /> {t("inventario.det_preguntar")}
          </button>
          {onNavegar && (
            <button
              onClick={() => { onClose(); onNavegar("productos", `q:${p.codigo}`); }}
              className="inline-flex items-center gap-1.5 rounded-full border border-linea px-4 py-2 text-[0.88rem] font-semibold text-tinta"
            >
              {t("inventario.acc_ver_catalogo")} <ArrowRight size={13} />
            </button>
          )}
          {err && onNavegar && authStore.tiene("saneamiento") && (
            <button
              onClick={() => { onClose(); onNavegar("saneamiento", err); }}
              className="inline-flex items-center gap-1.5 rounded-full border border-linea px-4 py-2 text-[0.88rem] font-semibold text-tinta-suave"
            >
              {t("inventario.acc_ver_saneamiento")}
            </button>
          )}
        </div>
      </div>
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
      <div className="max-h-[85vh] w-full max-w-md overflow-y-auto rounded-[var(--radius-card)] border border-linea bg-crema p-6 sombra-alta" onClick={(ev) => ev.stopPropagation()}>
        <div className="flex items-start justify-between">
          <h2 className="font-display text-xl font-bold">{t(inicial ? "inventario.form_editar" : "inventario.nuevo_producto")}</h2>
          <button onClick={onClose} className="text-tinta-suave hover:text-tinta"><X size={20} /></button>
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
          <button onClick={onClose} className="rounded-full border border-linea px-4 py-2 text-[0.85rem] font-semibold text-tinta-suave">
            {t("inventario.form_cancelar")}
          </button>
          <button onClick={guardar} disabled={!form.codigo || !form.descripcion.trim() || guardando}
            className="rounded-full bg-violeta px-4 py-2 text-[0.85rem] font-semibold text-crema disabled:opacity-50">
            {t("inventario.form_guardar")}
          </button>
        </div>
      </div>
    </div>
  );
}

function Dato({ label, valor, alerta }) {
  return (
    <div className="rounded-xl border border-linea bg-papel p-3">
      <p className="text-[0.88rem] font-semibold uppercase tracking-wide text-tinta-suave">{label}</p>
      <p className={`plata mt-0.5 text-[1.05rem] font-medium ${alerta ? "text-rojo" : "text-tinta"}`}>{valor}</p>
    </div>
  );
}

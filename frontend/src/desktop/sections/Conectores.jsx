import { useEffect, useState } from "react";
import { FileSpreadsheet, LineChart, Waypoints, Link2, ChevronDown } from "lucide-react";
import AngelaSays from "../../components/AngelaSays";
import Cargando from "../../components/Cargando";
import { api } from "../../lib/api";
import { useT } from "../../lib/i18n";

// Plan 11 · una sola página para TODO sistema externo que hable con PolPilot.
// Hoy: CSV (manual) y BCRA (macro) ya activos, Odoo interactivo (conectás vos
// tu cuenta), MCP como slot pendiente para cuando Faro/Tango lo expongan. A
// medida que se sumen conectores nuevos, entran acá — un solo lugar, no uno
// por sistema desperdigado en otras pantallas.
const ICONOS = { csv: FileSpreadsheet, bcra: LineChart, odoo: Link2, mcp: Waypoints };

export default function Conectores({ onNavigate }) {
  const t = useT();
  const [lista, setLista] = useState(null); // null=cargando, false=error

  useEffect(() => {
    api.conectores().then((r) => setLista(r.conectores)).catch(() => setLista(false));
  }, []);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-2xl font-bold">{t("conectores.titulo")}</h1>
        <p className="mt-1 text-[0.9rem] text-tinta-suave">{t("conectores.subtitulo")}</p>
      </header>

      <AngelaSays>{t("conectores.angela")}</AngelaSays>

      {lista === null && <Cargando />}
      {lista === false && <p className="text-[0.9rem] text-rojo">{t("conectores.error")}</p>}

      {lista && (
        <div className="space-y-4">
          {lista.map((c) => (
            c.nombre === "odoo"
              ? <PanelOdoo key={c.nombre} estado={c.estado} onNavigate={onNavigate} />
              : <TarjetaConector key={c.nombre} nombre={c.nombre} estado={c.estado} />
          ))}
        </div>
      )}
    </div>
  );
}

// Conectores sin panel propio todavía: sólo el estado, a la espera de que les
// toque su turno de volverse interactivos (como Odoo hoy).
function TarjetaConector({ nombre, estado }) {
  const t = useT();
  const Icon = ICONOS[nombre] || Waypoints;
  const activo = estado === "activo";
  return (
    <div className="flex items-center gap-3 rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
      <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-full ${activo ? "bg-salvia/12 text-salvia" : "bg-papel-hondo text-tinta-suave"}`}>
        <Icon size={17} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="font-display text-[1.02rem] font-bold leading-tight">{t(`conectores.${nombre}_nombre`)}</p>
        <p className="text-[0.82rem] text-tinta-suave">{t(`conectores.${nombre}_desc`)}</p>
      </div>
      <span className={`shrink-0 rounded-full px-3 py-1 text-[0.76rem] font-semibold ${
        activo ? "bg-salvia/12 text-salvia" : "bg-papel-hondo text-tinta-suave"}`}>
        {t(activo ? "conectores.estado_activo" : "conectores.estado_pendiente")}
      </span>
    </div>
  );
}

// CONECTOR ODOO (Plan 11). Sólo lectura por ahora: trae contactos-cliente
// (res.partner) y catálogo de productos con stock (product.template) de la
// cuenta Odoo propia del dueño, para previsualizarlos. Integrarlos al
// catálogo/cuentas reales de PolPilot es trabajo futuro — ver core/conectores.py.
function PanelOdoo({ estado, onNavigate }) {
  const t = useT();
  const [abierto, setAbierto] = useState(estado === "activo");
  const [cfg, setCfg] = useState(null);
  const [form, setForm] = useState({ url: "", database: "", username: "", api_key: "" });
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("contactos");

  const cargar = () => api.odooConfig().then(setCfg).catch(() => setCfg(false));
  useEffect(() => { cargar(); }, []);

  const conectar = async (e) => {
    e.preventDefault();
    setGuardando(true);
    setError(null);
    try {
      await api.odooConfigGuardar(form);
      setForm({ url: "", database: "", username: "", api_key: "" });
      await cargar();
    } catch (err) {
      setError(err.status === 400 ? t("odoo.error_guardar") : t("odoo.error_generico"));
    } finally {
      setGuardando(false);
    }
  };

  const desconectar = async () => {
    try { await api.odooConfigBorrar(); } catch { /* best-effort */ }
    await cargar();
  };

  return (
    <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
      <button onClick={() => setAbierto((v) => !v)} className="flex w-full items-center gap-3 text-left">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-violeta/10 text-violeta">
          <Link2 size={17} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block font-display text-[1.02rem] font-bold leading-tight">{t("odoo.titulo")}</span>
          <span className="block text-[0.82rem] text-tinta-suave">{t("odoo.subtitulo")}</span>
        </span>
        <ChevronDown size={16} className={`shrink-0 text-tinta-suave transition-transform ${abierto ? "rotate-180" : ""}`} />
      </button>

      {abierto && cfg && (
        <div className="mt-3.5 space-y-3 border-t border-linea pt-3.5">
          {cfg.conectado ? (
            <>
              <p className="text-[0.85rem] text-tinta">
                {t("odoo.conectado_como", { url: cfg.url, database: cfg.database, username: cfg.username })}
              </p>
              <div className="flex items-center gap-1 border-b border-linea">
                <button onClick={() => setTab("contactos")}
                  className={`px-3 py-1.5 text-[0.82rem] font-semibold border-b-2 -mb-px ${
                    tab === "contactos" ? "border-violeta text-violeta" : "border-transparent text-tinta-suave hover:text-tinta"}`}>
                  {t("odoo.tab_contactos")}
                </button>
                <button onClick={() => setTab("productos")}
                  className={`px-3 py-1.5 text-[0.82rem] font-semibold border-b-2 -mb-px ${
                    tab === "productos" ? "border-violeta text-violeta" : "border-transparent text-tinta-suave hover:text-tinta"}`}>
                  {t("odoo.tab_productos")}
                </button>
                <button onClick={() => setTab("proveedores")}
                  className={`px-3 py-1.5 text-[0.82rem] font-semibold border-b-2 -mb-px ${
                    tab === "proveedores" ? "border-violeta text-violeta" : "border-transparent text-tinta-suave hover:text-tinta"}`}>
                  {t("odoo.tab_proveedores")}
                </button>
                <button onClick={() => setTab("compras")}
                  className={`px-3 py-1.5 text-[0.82rem] font-semibold border-b-2 -mb-px ${
                    tab === "compras" ? "border-violeta text-violeta" : "border-transparent text-tinta-suave hover:text-tinta"}`}>
                  {t("odoo.tab_compras")}
                </button>
                <button onClick={() => setTab("ventas")}
                  className={`px-3 py-1.5 text-[0.82rem] font-semibold border-b-2 -mb-px ${
                    tab === "ventas" ? "border-violeta text-violeta" : "border-transparent text-tinta-suave hover:text-tinta"}`}>
                  {t("odoo.tab_ventas")}
                </button>
              </div>
              {tab === "contactos" && <OdooTabContactos t={t} onNavigate={onNavigate} />}
              {tab === "productos" && <OdooTabProductos t={t} onNavigate={onNavigate} />}
              {tab === "proveedores" && <OdooTabProveedores t={t} onNavigate={onNavigate} />}
              {tab === "compras" && <OdooTabCompras t={t} onNavigate={onNavigate} />}
              {tab === "ventas" && <OdooTabVentas t={t} onNavigate={onNavigate} />}
              <button onClick={desconectar}
                className="rounded-full border border-linea px-3.5 py-1.5 text-[0.8rem] font-semibold
                           text-tinta-suave hover:text-tinta">
                {t("odoo.desconectar")}
              </button>
            </>
          ) : (
            <form onSubmit={conectar} className="space-y-2.5">
              <p className="text-[0.85rem] text-tinta-suave">{t("odoo.no_conectado")}</p>
              <Campo label={t("odoo.campo_url")} placeholder="https://mi-empresa.odoo.com"
                value={form.url} onChange={(v) => setForm((f) => ({ ...f, url: v }))} />
              <Campo label={t("odoo.campo_db")} value={form.database}
                onChange={(v) => setForm((f) => ({ ...f, database: v }))} />
              <Campo label={t("odoo.campo_usuario")} value={form.username}
                onChange={(v) => setForm((f) => ({ ...f, username: v }))} />
              <Campo label={t("odoo.campo_api_key")} type="password" value={form.api_key}
                onChange={(v) => setForm((f) => ({ ...f, api_key: v }))} />
              {error && <p className="text-[0.8rem] text-rojo">{error}</p>}
              <button type="submit" disabled={guardando}
                className="rounded-full border border-violeta bg-violeta px-3.5 py-1.5 text-[0.8rem]
                           font-semibold text-crema disabled:opacity-50">
                {guardando ? t("odoo.conectando") : t("odoo.conectar")}
              </button>
            </form>
          )}
          <p className="text-[0.78rem] leading-snug text-tinta-suave">{t("odoo.nota")}</p>
        </div>
      )}
    </div>
  );
}

// Pestaña Contactos: mismo comportamiento que la versión original de PanelOdoo,
// ahora aislado para convivir con la pestaña Productos.
function OdooTabContactos({ t, onNavigate }) {
  const [sync, setSync] = useState(null);
  const [sincronizando, setSincronizando] = useState(false);
  const [error, setError] = useState(null);
  const [ingesta, setIngesta] = useState(null);
  const [ingestando, setIngestando] = useState(false);
  const [errorIngesta, setErrorIngesta] = useState(null);

  const sincronizar = async () => {
    setSincronizando(true);
    setError(null);
    try {
      setSync(await api.odooSync());
    } catch {
      setError(t("odoo.error_generico"));
    } finally {
      setSincronizando(false);
    }
  };

  const ingestar = async () => {
    setIngestando(true);
    setErrorIngesta(null);
    try {
      setIngesta(await api.odooIngestContactos());
    } catch {
      setErrorIngesta(t("odoo.error_generico"));
    } finally {
      setIngestando(false);
    }
  };

  return (
    <div className="space-y-3 pt-1">
      <div className="flex flex-wrap items-center gap-2">
        <button onClick={sincronizar} disabled={sincronizando}
          className="rounded-full border border-violeta bg-violeta px-3.5 py-1.5 text-[0.8rem]
                     font-semibold text-crema disabled:opacity-50">
          {sincronizando ? t("odoo.sincronizando") : t("odoo.sincronizar")}
        </button>
        <button onClick={ingestar} disabled={ingestando}
          className="rounded-full border border-violeta px-3.5 py-1.5 text-[0.8rem]
                     font-semibold text-violeta disabled:opacity-50">
          {ingestando ? t("odoo.ingestando_contactos") : t("odoo.ingestar_contactos")}
        </button>
      </div>
      {error && <p className="text-[0.8rem] text-rojo">{error}</p>}
      {errorIngesta && <p className="text-[0.8rem] text-rojo">{errorIngesta}</p>}
      {ingesta && (
        <p className="text-[0.82rem] text-tinta-suave">
          {ingesta.actualizados > 0 || ingesta.nuevos_para_revisar > 0
            ? t("odoo.ingesta_contactos_resultado", { actualizados: ingesta.actualizados, nuevos: ingesta.nuevos_para_revisar })
            : t("odoo.ingesta_contactos_sin_novedades")}
          {ingesta.batch_id && (
            <> · <button type="button" onClick={() => onNavigate?.("saneamiento", "revision")}
              className="font-semibold text-violeta underline">{t("odoo.ver_en_staging")}</button></>
          )}
        </p>
      )}
      {sync && (
        <p className="text-[0.82rem] text-tinta-suave">
          {sync.total > 0 ? t("odoo.sync_resultado", { n: sync.total }) : t("odoo.sync_vacio")}
        </p>
      )}
      {sync?.total > 0 && (
        <ul className="max-h-48 space-y-1 overflow-y-auto rounded-xl border border-linea/60
                       bg-papel-hondo/30 p-2 text-[0.8rem]">
          {sync.clientes.map((c) => (
            <li key={c.id} className="text-tinta">
              {c.nombre}{c.localidad && <span className="text-tinta-suave"> · {c.localidad}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// Pestaña Productos: catálogo con stock (product.template.qty_available).
// Mismo patrón que Contactos — sólo lectura, preview.
function OdooTabProductos({ t, onNavigate }) {
  const [sync, setSync] = useState(null);
  const [sincronizando, setSincronizando] = useState(false);
  const [error, setError] = useState(null);
  const [ingesta, setIngesta] = useState(null);
  const [ingestando, setIngestando] = useState(false);
  const [errorIngesta, setErrorIngesta] = useState(null);

  const sincronizar = async () => {
    setSincronizando(true);
    setError(null);
    try {
      setSync(await api.odooSyncProductos());
    } catch {
      setError(t("odoo.error_generico"));
    } finally {
      setSincronizando(false);
    }
  };

  const ingestar = async () => {
    setIngestando(true);
    setErrorIngesta(null);
    try {
      setIngesta(await api.odooIngestProductos());
    } catch {
      setErrorIngesta(t("odoo.error_generico"));
    } finally {
      setIngestando(false);
    }
  };

  return (
    <div className="space-y-3 pt-1">
      <div className="flex flex-wrap items-center gap-2">
        <button onClick={sincronizar} disabled={sincronizando}
          className="rounded-full border border-violeta bg-violeta px-3.5 py-1.5 text-[0.8rem]
                     font-semibold text-crema disabled:opacity-50">
          {sincronizando ? t("odoo.sincronizando_productos") : t("odoo.traer_productos")}
        </button>
        <button onClick={ingestar} disabled={ingestando}
          className="rounded-full border border-violeta px-3.5 py-1.5 text-[0.8rem]
                     font-semibold text-violeta disabled:opacity-50">
          {ingestando ? t("odoo.ingestando_productos") : t("odoo.ingestar_productos")}
        </button>
      </div>
      {error && <p className="text-[0.8rem] text-rojo">{error}</p>}
      {errorIngesta && <p className="text-[0.8rem] text-rojo">{errorIngesta}</p>}
      {ingesta && (
        <p className="text-[0.82rem] text-tinta-suave">
          {ingesta.actualizados > 0 || ingesta.nuevos_para_revisar > 0
            ? t("odoo.ingesta_productos_resultado", { actualizados: ingesta.actualizados, nuevos: ingesta.nuevos_para_revisar })
            : t("odoo.ingesta_productos_sin_novedades")}
          {ingesta.batch_id && (
            <> · <button type="button" onClick={() => onNavigate?.("saneamiento", "revision")}
              className="font-semibold text-violeta underline">{t("odoo.ver_en_staging")}</button></>
          )}
        </p>
      )}
      {sync && (
        <p className="text-[0.82rem] text-tinta-suave">
          {sync.total > 0 ? t("odoo.sync_productos_resultado", { n: sync.total }) : t("odoo.sync_productos_vacio")}
        </p>
      )}
      {sync?.total > 0 && (
        <ul className="max-h-48 space-y-1 overflow-y-auto rounded-xl border border-linea/60
                       bg-papel-hondo/30 p-2 text-[0.8rem]">
          {sync.productos.map((p) => (
            <li key={p.id} className="flex items-center justify-between gap-2 text-tinta">
              <span className="min-w-0 truncate">
                {p.codigo && <span className="text-tinta-suave">{p.codigo} · </span>}
                {p.nombre}
                {p.categoria && <span className="text-tinta-suave"> · {p.categoria}</span>}
              </span>
              <span className={`shrink-0 font-semibold ${p.stock > 0 ? "text-tinta" : "text-rojo"}`}>
                {t("odoo.stock_unidades", { n: p.stock })}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// Pestaña Proveedores: contactos-proveedor (supplier_rank > 0), la
// contraparte de Contactos del lado compras. Mismo patrón: sólo lectura, preview.
function OdooTabProveedores({ t, onNavigate }) {
  const [sync, setSync] = useState(null);
  const [sincronizando, setSincronizando] = useState(false);
  const [error, setError] = useState(null);
  const [ingesta, setIngesta] = useState(null);
  const [ingestando, setIngestando] = useState(false);
  const [errorIngesta, setErrorIngesta] = useState(null);

  const sincronizar = async () => {
    setSincronizando(true);
    setError(null);
    try {
      setSync(await api.odooSyncProveedores());
    } catch {
      setError(t("odoo.error_generico"));
    } finally {
      setSincronizando(false);
    }
  };

  const ingestar = async () => {
    setIngestando(true);
    setErrorIngesta(null);
    try {
      setIngesta(await api.odooIngestProveedores());
    } catch {
      setErrorIngesta(t("odoo.error_generico"));
    } finally {
      setIngestando(false);
    }
  };

  return (
    <div className="space-y-3 pt-1">
      <div className="flex flex-wrap items-center gap-2">
        <button onClick={sincronizar} disabled={sincronizando}
          className="rounded-full border border-violeta bg-violeta px-3.5 py-1.5 text-[0.8rem]
                     font-semibold text-crema disabled:opacity-50">
          {sincronizando ? t("odoo.sincronizando_proveedores") : t("odoo.traer_proveedores")}
        </button>
        <button onClick={ingestar} disabled={ingestando}
          className="rounded-full border border-violeta px-3.5 py-1.5 text-[0.8rem]
                     font-semibold text-violeta disabled:opacity-50">
          {ingestando ? t("odoo.ingestando_proveedores") : t("odoo.ingestar_proveedores")}
        </button>
      </div>
      {error && <p className="text-[0.8rem] text-rojo">{error}</p>}
      {errorIngesta && <p className="text-[0.8rem] text-rojo">{errorIngesta}</p>}
      {ingesta && (
        <p className="text-[0.82rem] text-tinta-suave">
          {ingesta.actualizados > 0 || ingesta.nuevos_para_revisar > 0
            ? t("odoo.ingesta_proveedores_resultado", { actualizados: ingesta.actualizados, nuevos: ingesta.nuevos_para_revisar })
            : t("odoo.ingesta_proveedores_sin_novedades")}
          {ingesta.batch_id && (
            <> · <button type="button" onClick={() => onNavigate?.("saneamiento", "revision")}
              className="font-semibold text-violeta underline">{t("odoo.ver_en_staging")}</button></>
          )}
        </p>
      )}
      {sync && (
        <p className="text-[0.82rem] text-tinta-suave">
          {sync.total > 0 ? t("odoo.sync_proveedores_resultado", { n: sync.total }) : t("odoo.sync_proveedores_vacio")}
        </p>
      )}
      {sync?.total > 0 && (
        <ul className="max-h-48 space-y-1 overflow-y-auto rounded-xl border border-linea/60
                       bg-papel-hondo/30 p-2 text-[0.8rem]">
          {sync.proveedores.map((p) => (
            <li key={p.id} className="text-tinta">
              {p.nombre}{p.localidad && <span className="text-tinta-suave"> · {p.localidad}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// Pestaña Compras: órdenes de compra (purchase.order) con sus líneas, la
// contraparte de Productos del lado compras. Mismo patrón: sólo lectura, preview.
function OdooTabCompras({ t, onNavigate }) {
  const [sync, setSync] = useState(null);
  const [sincronizando, setSincronizando] = useState(false);
  const [error, setError] = useState(null);
  const [ingesta, setIngesta] = useState(null);
  const [ingestando, setIngestando] = useState(false);
  const [errorIngesta, setErrorIngesta] = useState(null);

  const sincronizar = async () => {
    setSincronizando(true);
    setError(null);
    try {
      setSync(await api.odooSyncOrdenesCompra());
    } catch {
      setError(t("odoo.error_generico"));
    } finally {
      setSincronizando(false);
    }
  };

  const ingestar = async () => {
    setIngestando(true);
    setErrorIngesta(null);
    try {
      setIngesta(await api.odooIngestOrdenesCompra());
    } catch {
      setErrorIngesta(t("odoo.error_generico"));
    } finally {
      setIngestando(false);
    }
  };

  return (
    <div className="space-y-3 pt-1">
      <div className="flex flex-wrap items-center gap-2">
        <button onClick={sincronizar} disabled={sincronizando}
          className="rounded-full border border-violeta bg-violeta px-3.5 py-1.5 text-[0.8rem]
                     font-semibold text-crema disabled:opacity-50">
          {sincronizando ? t("odoo.sincronizando_compras") : t("odoo.traer_compras")}
        </button>
        <button onClick={ingestar} disabled={ingestando}
          className="rounded-full border border-violeta px-3.5 py-1.5 text-[0.8rem]
                     font-semibold text-violeta disabled:opacity-50">
          {ingestando ? t("odoo.ingestando_compras") : t("odoo.ingestar_compras")}
        </button>
      </div>
      {error && <p className="text-[0.8rem] text-rojo">{error}</p>}
      {errorIngesta && <p className="text-[0.8rem] text-rojo">{errorIngesta}</p>}
      {ingesta && (
        <p className="text-[0.82rem] text-tinta-suave">
          {ingesta.actualizados > 0 || ingesta.nuevos_para_revisar > 0
            ? t("odoo.ingesta_compras_resultado", { actualizados: ingesta.actualizados, nuevos: ingesta.nuevos_para_revisar })
            : t("odoo.ingesta_compras_sin_novedades")}
          {ingesta.batch_id && (
            <> · <button type="button" onClick={() => onNavigate?.("saneamiento", "revision")}
              className="font-semibold text-violeta underline">{t("odoo.ver_en_staging")}</button></>
          )}
        </p>
      )}
      {sync && (
        <p className="text-[0.82rem] text-tinta-suave">
          {sync.total > 0 ? t("odoo.sync_compras_resultado", { n: sync.total }) : t("odoo.sync_compras_vacio")}
        </p>
      )}
      {sync?.total > 0 && (
        <ul className="max-h-56 space-y-2 overflow-y-auto rounded-xl border border-linea/60
                       bg-papel-hondo/30 p-2 text-[0.8rem]">
          {sync.ordenes.map((o) => (
            <li key={o.id} className="rounded-lg border border-linea/50 bg-papel/60 p-2">
              <div className="flex items-center justify-between gap-2">
                <span className="min-w-0 truncate font-semibold text-tinta">
                  {o.numero} <span className="font-normal text-tinta-suave">· {o.proveedor}</span>
                </span>
                <span className="shrink-0 rounded-full bg-papel-hondo px-2 py-0.5 text-[0.72rem]
                                 font-semibold text-tinta-suave">
                  {t(`odoo.estado_compra_${o.estado}`)}
                </span>
              </div>
              <ul className="mt-1 space-y-0.5 pl-1 text-tinta-suave">
                {o.items.map((it, i) => (
                  <li key={i}>{it.producto} · {it.cantidad}</li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function OdooTabVentas({ t, onNavigate }) {
  const [sync, setSync] = useState(null);
  const [sincronizando, setSincronizando] = useState(false);
  const [error, setError] = useState(null);
  const [ingesta, setIngesta] = useState(null);
  const [ingestando, setIngestando] = useState(false);
  const [errorIngesta, setErrorIngesta] = useState(null);

  const sincronizar = async () => {
    setSincronizando(true);
    setError(null);
    try {
      setSync(await api.odooSyncVentas());
    } catch {
      setError(t("odoo.error_generico"));
    } finally {
      setSincronizando(false);
    }
  };

  const ingestar = async () => {
    setIngestando(true);
    setErrorIngesta(null);
    try {
      setIngesta(await api.odooIngestVentas());
    } catch {
      setErrorIngesta(t("odoo.error_generico"));
    } finally {
      setIngestando(false);
    }
  };

  return (
    <div className="space-y-3 pt-1">
      <div className="flex flex-wrap items-center gap-2">
        <button onClick={sincronizar} disabled={sincronizando}
          className="rounded-full border border-violeta bg-violeta px-3.5 py-1.5 text-[0.8rem]
                     font-semibold text-crema disabled:opacity-50">
          {sincronizando ? t("odoo.sincronizando_ventas") : t("odoo.traer_ventas")}
        </button>
        <button onClick={ingestar} disabled={ingestando}
          className="rounded-full border border-violeta px-3.5 py-1.5 text-[0.8rem]
                     font-semibold text-violeta disabled:opacity-50">
          {ingestando ? t("odoo.ingestando_ventas") : t("odoo.ingestar_ventas")}
        </button>
      </div>
      {error && <p className="text-[0.8rem] text-rojo">{error}</p>}
      {errorIngesta && <p className="text-[0.8rem] text-rojo">{errorIngesta}</p>}
      {ingesta && (
        <p className="text-[0.82rem] text-tinta-suave">
          {ingesta.actualizados > 0 || ingesta.nuevos_para_revisar > 0
            ? t("odoo.ingesta_ventas_resultado", { actualizados: ingesta.actualizados, nuevos: ingesta.nuevos_para_revisar })
            : t("odoo.ingesta_ventas_sin_novedades")}
          {ingesta.batch_id && (
            <> · <button type="button" onClick={() => onNavigate?.("saneamiento", "revision")}
              className="font-semibold text-violeta underline">{t("odoo.ver_en_staging")}</button></>
          )}
        </p>
      )}
      {sync && (
        <p className="text-[0.82rem] text-tinta-suave">
          {sync.total > 0 ? t("odoo.sync_ventas_resultado", { n: sync.total }) : t("odoo.sync_ventas_vacio")}
        </p>
      )}
      {sync?.total > 0 && (
        <ul className="max-h-56 space-y-2 overflow-y-auto rounded-xl border border-linea/60
                       bg-papel-hondo/30 p-2 text-[0.8rem]">
          {sync.ordenes.map((o) => (
            <li key={o.id} className="rounded-lg border border-linea/50 bg-papel/60 p-2">
              <div className="flex items-center justify-between gap-2">
                <span className="min-w-0 truncate font-semibold text-tinta">
                  {o.numero} <span className="font-normal text-tinta-suave">· {o.cliente}</span>
                </span>
                <span className="shrink-0 rounded-full bg-papel-hondo px-2 py-0.5 text-[0.72rem]
                                 font-semibold text-tinta-suave">
                  {t(`odoo.estado_venta_${o.estado}`)}
                </span>
              </div>
              <ul className="mt-1 space-y-0.5 pl-1 text-tinta-suave">
                {o.items.map((it, i) => (
                  <li key={it.id || i}>{it.producto} · {it.cantidad}</li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Campo({ label, value, onChange, type = "text", placeholder }) {
  return (
    <label className="block text-[0.8rem]">
      <span className="mb-1 block font-semibold text-tinta-suave">{label}</span>
      <input required type={type} value={value} placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-linea bg-papel px-3 py-1.5 text-[0.85rem]
                   text-tinta outline-none focus:border-violeta" />
    </label>
  );
}

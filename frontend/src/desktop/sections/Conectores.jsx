import { useEffect, useState } from "react";
import {
  FileSpreadsheet, LineChart, Waypoints, Plug, MessageCircle, ArrowRight,
  Users, Package, Truck, ShoppingCart, ShoppingBag, Warehouse, PackagePlus,
  PackageCheck, FileText, Tag,
} from "lucide-react";
import AngelaSays from "../../components/AngelaSays";
import Cargando from "../../components/Cargando";
import { api } from "../../lib/api";
import { useT } from "../../lib/i18n";
import IngestPipeline from "./IngestPipeline";
import {
  ConnectorCard, ConnectorStatusPill, ConnectorField, ConnectorButton,
  ConnectorSyncAction,
} from "./connectorUI";

// Plan 11 · una sola página para TODO sistema externo que hable con PolPilot.
// Hoy: CSV (manual) y BCRA (macro) ya activos, Odoo interactivo (conectás vos
// tu cuenta), WhatsApp (canal de ventas — ver whatsapp_bot.jsx, se configura
// en su propia pantalla), MCP como slot pendiente para cuando Faro/Tango lo
// expongan. A medida que se sumen conectores nuevos, entran acá — un solo
// lugar, no uno por sistema desperdigado en otras pantallas.
const ICONOS = { csv: FileSpreadsheet, bcra: LineChart, odoo: Plug, mcp: Waypoints };

function IngestLinks({ t, onNavigate, batchId, importedTab }) {
  return (
    <>
      {batchId && (
        <> · <button type="button" onClick={() => onNavigate?.("staging")}
          className="font-semibold text-violeta underline">{t("odoo.ver_en_staging")}</button></>
      )}
      {importedTab && (
        <> · <button type="button" onClick={() => onNavigate?.("imported", importedTab)}
          className="font-semibold text-violeta underline">{t("odoo.view_imported")}</button></>
      )}
    </>
  );
}

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
        <div className="mt-3">
          <IngestPipeline current="conectores" onNavigate={onNavigate} />
        </div>
      </header>

      <AngelaSays>{t("conectores.angela")}</AngelaSays>

      {lista === null && <Cargando />}
      {lista === false && <p className="text-[0.9rem] text-rojo-hondo">{t("conectores.error")}</p>}

      {lista && (
        <div className="space-y-4">
          {lista.map((c) => (
            c.nombre === "odoo"
              ? <PanelOdoo key={c.nombre} estado={c.estado} onNavigate={onNavigate} />
              : <TarjetaConector key={c.nombre} nombre={c.nombre} estado={c.estado} />
          ))}
          <TarjetaWhatsApp onNavigate={onNavigate} />
        </div>
      )}
    </div>
  );
}

// Conectores sin panel propio todavía: sólo el estado, a la espera de que les
// toque su turno de volverse interactivos (como Odoo hoy).
function TarjetaConector({ nombre, estado }) {
  const t = useT();
  const activo = estado === "activo";
  return (
    <ConnectorCard
      icon={ICONOS[nombre] || Waypoints}
      tone={activo ? "active" : "neutral"}
      title={t(`conectores.${nombre}_nombre`)}
      subtitle={t(`conectores.${nombre}_desc`)}
      status={
        <ConnectorStatusPill variant={activo ? "activo" : "proximamente"}>
          {t(activo ? "conectores.estado_activo" : "conectores.estado_pendiente")}
        </ConnectorStatusPill>
      }
    />
  );
}

// WhatsApp vive en su propia pantalla (setup + bandeja de conversaciones es
// demasiado para un panel expandible acá) pero es un CONECTOR como cualquier
// otro — tiene que aparecer en esta galería, no escondido en otro menú.
// El ícono es "agent"-tone (violeta) a propósito: este canal ES Ángela
// contestando del otro lado, distinto de Odoo (un caño de datos).
function TarjetaWhatsApp({ onNavigate }) {
  const t = useT();
  const [cfg, setCfg] = useState(null);
  useEffect(() => { api.whatsappBotConfig().then(setCfg).catch(() => setCfg(false)); }, []);
  const activo = !!cfg?.conectado && cfg?.enabled;
  return (
    <button type="button" onClick={() => onNavigate?.("whatsapp_bot")}
      className="card-hover block w-full rounded-[var(--radius-card)] text-left">
      <ConnectorCard
        icon={MessageCircle}
        tone={activo ? "active" : "agent"}
        title={t("conectores.whatsapp_nombre")}
        subtitle={t("conectores.whatsapp_desc")}
        status={
          <>
            {cfg && (
              <ConnectorStatusPill variant={activo ? "activo" : cfg.conectado ? "pausado" : "pendiente"}>
                {t(activo ? "conectores.estado_activo"
                  : cfg.conectado ? "whatsapp_bot.estado_pausado" : "conectores.estado_configurar")}
              </ConnectorStatusPill>
            )}
            <ArrowRight size={15} className="shrink-0 text-tinta-suave" />
          </>
        }
      />
    </button>
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

  const TABS = [
    { id: "contactos", icon: Users },
    { id: "productos", icon: Package },
    { id: "proveedores", icon: Truck },
    { id: "compras", icon: ShoppingCart },
    { id: "ventas", icon: ShoppingBag },
    { id: "deposito", icon: Warehouse },
    { id: "recepciones", icon: PackagePlus },
    { id: "entregas", icon: PackageCheck },
    { id: "facturas", icon: FileText },
    { id: "precios", icon: Tag },
  ];

  return (
    <ConnectorCard
      icon={Plug}
      tone={cfg?.conectado ? "active" : "neutral"}
      title={t("odoo.titulo")}
      subtitle={t("odoo.subtitulo")}
      status={cfg && (
        <ConnectorStatusPill variant={cfg.conectado ? "activo" : "pendiente"}>
          {t(cfg.conectado ? "conectores.estado_activo" : "conectores.estado_configurar")}
        </ConnectorStatusPill>
      )}
      expanded={abierto}
      onToggle={() => setAbierto((v) => !v)}
    >
      {cfg && (cfg.conectado ? (
        <>
          <p className="text-[0.85rem] text-tinta-suave">
            {t("odoo.conectado_como", { url: cfg.url, database: cfg.database, username: cfg.username })}
            {" · "}
            <button type="button" onClick={() => onNavigate?.("imported")}
              className="font-semibold text-tinta underline decoration-linea underline-offset-2 hover:decoration-tinta">
              {t("odoo.view_imported")}
            </button>
          </p>
          <div className="-mx-1 flex items-center gap-1 overflow-x-auto border-b border-linea px-1 pb-px">
            {TABS.map(({ id, icon: TabIcon }) => (
              <button key={id} onClick={() => setTab(id)}
                className={`flex shrink-0 items-center gap-1.5 whitespace-nowrap border-b-2 -mb-px px-2.5 py-2 text-[0.8rem] font-semibold transition-colors ${
                  tab === id ? "border-tinta text-tinta" : "border-transparent text-tinta-suave hover:text-tinta"}`}>
                <TabIcon size={14} />
                {t(`odoo.tab_${id}`)}
              </button>
            ))}
          </div>
          {tab === "contactos" && <OdooTabContactos t={t} onNavigate={onNavigate} />}
          {tab === "productos" && <OdooTabProductos t={t} onNavigate={onNavigate} />}
          {tab === "proveedores" && <OdooTabProveedores t={t} onNavigate={onNavigate} />}
          {tab === "compras" && <OdooTabCompras t={t} onNavigate={onNavigate} />}
          {tab === "ventas" && <OdooTabVentas t={t} onNavigate={onNavigate} />}
          {tab === "deposito" && <OdooTabDeposito t={t} onNavigate={onNavigate} />}
          {tab === "recepciones" && <OdooTabRecepciones t={t} onNavigate={onNavigate} />}
          {tab === "entregas" && <OdooTabEntregas t={t} onNavigate={onNavigate} />}
          {tab === "facturas" && <OdooTabFacturas t={t} onNavigate={onNavigate} />}
          {tab === "precios" && <OdooTabPrecios t={t} />}
          <div className="border-t border-linea pt-3.5">
            <ConnectorButton variant="danger" onClick={desconectar}>{t("odoo.desconectar")}</ConnectorButton>
          </div>
        </>
      ) : (
        <>
          <form onSubmit={conectar} className="space-y-3">
            <p className="text-[0.85rem] text-tinta-suave">{t("odoo.no_conectado")}</p>
            <ConnectorField label={t("odoo.campo_url")} placeholder="https://mi-empresa.odoo.com"
              value={form.url} onChange={(v) => setForm((f) => ({ ...f, url: v }))} />
            <div className="grid gap-3 sm:grid-cols-2">
              <ConnectorField label={t("odoo.campo_db")} placeholder="mi_empresa" value={form.database}
                onChange={(v) => setForm((f) => ({ ...f, database: v }))} />
              <ConnectorField label={t("odoo.campo_usuario")} placeholder="admin@mi-empresa.com" value={form.username}
                onChange={(v) => setForm((f) => ({ ...f, username: v }))} />
            </div>
            <ConnectorField label={t("odoo.campo_api_key")} type="password" value={form.api_key}
              hint={t("odoo.campo_api_key_hint")}
              onChange={(v) => setForm((f) => ({ ...f, api_key: v }))} />
            {error && <p className="text-[0.8rem] text-rojo-hondo">{error}</p>}
            <ConnectorButton type="submit" loading={guardando}>
              {guardando ? t("odoo.conectando") : t("odoo.conectar")}
            </ConnectorButton>
          </form>
        </>
      ))}
      {cfg && <p className="text-[0.78rem] leading-snug text-tinta-suave">{t("odoo.nota")}</p>}
    </ConnectorCard>
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
      <ConnectorSyncAction
        onFetch={sincronizar} fetching={sincronizando}
        fetchLabel={t("odoo.sincronizar")} fetchingLabel={t("odoo.sincronizando")}
        onIngest={ingestar} ingesting={ingestando}
        ingestLabel={t("odoo.ingestar_contactos")} ingestingLabel={t("odoo.ingestando_contactos")}
        error={error} errorIngest={errorIngesta}
      />
      {ingesta && (
        <p className="text-[0.82rem] text-tinta-suave">
          {ingesta.actualizados > 0 || ingesta.nuevos_para_revisar > 0
            ? t("odoo.ingesta_contactos_resultado", { actualizados: ingesta.actualizados, nuevos: ingesta.nuevos_para_revisar })
            : t("odoo.ingesta_contactos_sin_novedades")}
          <IngestLinks t={t} onNavigate={onNavigate} batchId={ingesta.batch_id} />
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
      <ConnectorSyncAction
        onFetch={sincronizar} fetching={sincronizando}
        fetchLabel={t("odoo.traer_productos")} fetchingLabel={t("odoo.sincronizando_productos")}
        onIngest={ingestar} ingesting={ingestando}
        ingestLabel={t("odoo.ingestar_productos")} ingestingLabel={t("odoo.ingestando_productos")}
        error={error} errorIngest={errorIngesta}
      />
      {ingesta && (
        <p className="text-[0.82rem] text-tinta-suave">
          {ingesta.actualizados > 0 || ingesta.nuevos_para_revisar > 0
            ? t("odoo.ingesta_productos_resultado", { actualizados: ingesta.actualizados, nuevos: ingesta.nuevos_para_revisar })
            : t("odoo.ingesta_productos_sin_novedades")}
          <IngestLinks t={t} onNavigate={onNavigate} batchId={ingesta.batch_id} importedTab="products" />
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
                {p.pricing_status === "needs_pricing" && (
                  <span className="text-rojo-hondo"> · {t("odoo.pricing_needs")}</span>
                )}
                {p.pricing_status === "wholesale_only" && (
                  <span className="text-tinta-suave"> · {t("odoo.pricing_wholesale")}</span>
                )}
              </span>
              <span className={`shrink-0 font-semibold ${p.stock > 0 ? "text-tinta" : "text-rojo-hondo"}`}>
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
      <ConnectorSyncAction
        onFetch={sincronizar} fetching={sincronizando}
        fetchLabel={t("odoo.traer_proveedores")} fetchingLabel={t("odoo.sincronizando_proveedores")}
        onIngest={ingestar} ingesting={ingestando}
        ingestLabel={t("odoo.ingestar_proveedores")} ingestingLabel={t("odoo.ingestando_proveedores")}
        error={error} errorIngest={errorIngesta}
      />
      {ingesta && (
        <p className="text-[0.82rem] text-tinta-suave">
          {ingesta.actualizados > 0 || ingesta.nuevos_para_revisar > 0
            ? t("odoo.ingesta_proveedores_resultado", { actualizados: ingesta.actualizados, nuevos: ingesta.nuevos_para_revisar })
            : t("odoo.ingesta_proveedores_sin_novedades")}
          <IngestLinks t={t} onNavigate={onNavigate} batchId={ingesta.batch_id} />
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
      <ConnectorSyncAction
        onFetch={sincronizar} fetching={sincronizando}
        fetchLabel={t("odoo.traer_compras")} fetchingLabel={t("odoo.sincronizando_compras")}
        onIngest={ingestar} ingesting={ingestando}
        ingestLabel={t("odoo.ingestar_compras")} ingestingLabel={t("odoo.ingestando_compras")}
        error={error} errorIngest={errorIngesta}
      />
      {ingesta && (
        <p className="text-[0.82rem] text-tinta-suave">
          {ingesta.actualizados > 0 || ingesta.nuevos_para_revisar > 0
            ? t("odoo.ingesta_compras_resultado", { actualizados: ingesta.actualizados, nuevos: ingesta.nuevos_para_revisar })
            : t("odoo.ingesta_compras_sin_novedades")}
          <IngestLinks t={t} onNavigate={onNavigate} batchId={ingesta.batch_id} />
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
                  {o.currency && o.currency !== (sync.moneda_compania || "ARS") && (
                    <span className="font-normal text-tinta-suave"> · {o.currency}</span>
                  )}
                  {o.open_backorder && (
                    <span className="ml-1 font-normal text-rojo-hondo"> · {t("odoo.backorder_abierto")}</span>
                  )}
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
      <ConnectorSyncAction
        onFetch={sincronizar} fetching={sincronizando}
        fetchLabel={t("odoo.traer_ventas")} fetchingLabel={t("odoo.sincronizando_ventas")}
        onIngest={ingestar} ingesting={ingestando}
        ingestLabel={t("odoo.ingestar_ventas")} ingestingLabel={t("odoo.ingestando_ventas")}
        error={error} errorIngest={errorIngesta}
      />
      {ingesta && (
        <p className="text-[0.82rem] text-tinta-suave">
          {ingesta.actualizados > 0 || ingesta.nuevos_para_revisar > 0
            ? t("odoo.ingesta_ventas_resultado", { actualizados: ingesta.actualizados, nuevos: ingesta.nuevos_para_revisar })
            : t("odoo.ingesta_ventas_sin_novedades")}
          <IngestLinks t={t} onNavigate={onNavigate} batchId={ingesta.batch_id} importedTab="sales" />
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
                  {o.currency && o.currency !== (sync.moneda_compania || "ARS") && (
                    <span className="font-normal text-tinta-suave"> · {o.currency}</span>
                  )}
                  {o.open_backorder && (
                    <span className="ml-1 font-normal text-rojo-hondo"> · {t("odoo.backorder_abierto")}</span>
                  )}
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

function OdooTabDeposito({ t, onNavigate }) {
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
      setSync(await api.odooSyncDeposito());
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
      setIngesta(await api.odooIngestDeposito());
    } catch {
      setErrorIngesta(t("odoo.error_generico"));
    } finally {
      setIngestando(false);
    }
  };

  return (
    <div className="space-y-3 pt-1">
      <ConnectorSyncAction
        onFetch={sincronizar} fetching={sincronizando}
        fetchLabel={t("odoo.traer_deposito")} fetchingLabel={t("odoo.sincronizando_deposito")}
        onIngest={ingestar} ingesting={ingestando}
        ingestLabel={t("odoo.ingestar_deposito")} ingestingLabel={t("odoo.ingestando_deposito")}
        error={error} errorIngest={errorIngesta}
      />
      {ingesta && (
        <p className="text-[0.82rem] text-tinta-suave">
          {ingesta.actualizados > 0 || ingesta.nuevos_para_revisar > 0
            ? t("odoo.ingesta_deposito_resultado", { actualizados: ingesta.actualizados, nuevos: ingesta.nuevos_para_revisar })
            : t("odoo.ingesta_deposito_sin_novedades")}
          <IngestLinks t={t} onNavigate={onNavigate} batchId={ingesta.batch_id} importedTab="movements" />
        </p>
      )}
      {sync && (
        <p className="text-[0.82rem] text-tinta-suave">
          {sync.total > 0 ? t("odoo.sync_deposito_resultado", { n: sync.total }) : t("odoo.sync_deposito_vacio")}
        </p>
      )}
      {sync?.total > 0 && (
        <ul className="max-h-48 space-y-1 overflow-y-auto rounded-xl border border-linea/60
                       bg-papel-hondo/30 p-2 text-[0.8rem]">
          {sync.quants.map((q) => (
            <li key={q.id} className="text-tinta">
              {q.producto}
              {q.ubicacion && <span className="text-tinta-suave"> · {q.ubicacion}</span>}
              <span className="text-tinta-suave"> · {q.cantidad}</span>
              {q.in_date && <span className="text-tinta-suave"> · {q.in_date}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function OdooTabRecepciones({ t, onNavigate }) {
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
      setSync(await api.odooSyncRecepciones());
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
      setIngesta(await api.odooIngestRecepciones());
    } catch {
      setErrorIngesta(t("odoo.error_generico"));
    } finally {
      setIngestando(false);
    }
  };

  return (
    <div className="space-y-3 pt-1">
      <ConnectorSyncAction
        onFetch={sincronizar} fetching={sincronizando}
        fetchLabel={t("odoo.traer_recepciones")} fetchingLabel={t("odoo.sincronizando_recepciones")}
        onIngest={ingestar} ingesting={ingestando}
        ingestLabel={t("odoo.ingestar_recepciones")} ingestingLabel={t("odoo.ingestando_recepciones")}
        error={error} errorIngest={errorIngesta}
      />
      {ingesta && (
        <p className="text-[0.82rem] text-tinta-suave">
          {ingesta.actualizados > 0 || ingesta.nuevos_para_revisar > 0
            ? t("odoo.ingesta_recepciones_resultado", { actualizados: ingesta.actualizados, nuevos: ingesta.nuevos_para_revisar })
            : t("odoo.ingesta_recepciones_sin_novedades")}
          <IngestLinks t={t} onNavigate={onNavigate} batchId={ingesta.batch_id} importedTab="receipts" />
        </p>
      )}
      {sync && (
        <p className="text-[0.82rem] text-tinta-suave">
          {sync.total > 0 ? t("odoo.sync_recepciones_resultado", { n: sync.total }) : t("odoo.sync_recepciones_vacio")}
        </p>
      )}
      {sync?.total > 0 && (
        <ul className="max-h-48 space-y-1 overflow-y-auto rounded-xl border border-linea/60
                       bg-papel-hondo/30 p-2 text-[0.8rem]">
          {sync.recepciones.map((r) => (
            <li key={r.id} className="text-tinta">
              {r.origen} · {r.producto}
              <span className="text-tinta-suave"> · {r.cantidad}</span>
              {r.po_number && <span className="text-tinta-suave"> · {r.po_number}</span>}
              {r.pendiente && <span className="text-rojo-hondo"> · {t("odoo.picking_pendiente")}</span>}
              {r.open_backorder && <span className="text-rojo-hondo"> · {t("odoo.backorder_abierto")}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function OdooTabEntregas({ t, onNavigate }) {
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
      setSync(await api.odooSyncEntregas());
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
      setIngesta(await api.odooIngestEntregas());
    } catch {
      setErrorIngesta(t("odoo.error_generico"));
    } finally {
      setIngestando(false);
    }
  };

  return (
    <div className="space-y-3 pt-1">
      <ConnectorSyncAction
        onFetch={sincronizar} fetching={sincronizando}
        fetchLabel={t("odoo.traer_entregas")} fetchingLabel={t("odoo.sincronizando_entregas")}
        onIngest={ingestar} ingesting={ingestando}
        ingestLabel={t("odoo.ingestar_entregas")} ingestingLabel={t("odoo.ingestando_entregas")}
        error={error} errorIngest={errorIngesta}
      />
      {ingesta && (
        <p className="text-[0.82rem] text-tinta-suave">
          {ingesta.actualizados > 0 || ingesta.nuevos_para_revisar > 0
            ? t("odoo.ingesta_entregas_resultado", { actualizados: ingesta.actualizados, nuevos: ingesta.nuevos_para_revisar })
            : t("odoo.ingesta_entregas_sin_novedades")}
          <IngestLinks t={t} onNavigate={onNavigate} batchId={ingesta.batch_id} importedTab="deliveries" />
        </p>
      )}
      {sync && (
        <p className="text-[0.82rem] text-tinta-suave">
          {sync.total > 0 ? t("odoo.sync_entregas_resultado", { n: sync.total }) : t("odoo.sync_entregas_vacio")}
        </p>
      )}
      {sync?.total > 0 && (
        <ul className="max-h-48 space-y-1 overflow-y-auto rounded-xl border border-linea/60
                       bg-papel-hondo/30 p-2 text-[0.8rem]">
          {sync.entregas.map((r) => (
            <li key={r.id} className="text-tinta">
              {r.origen} · {r.producto}
              <span className="text-tinta-suave"> · {r.cantidad}</span>
              {r.cliente && <span className="text-tinta-suave"> · {r.cliente}</span>}
              {r.pendiente && <span className="text-rojo-hondo"> · {t("odoo.picking_pendiente")}</span>}
              {r.open_backorder && <span className="text-rojo-hondo"> · {t("odoo.backorder_abierto")}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function OdooTabFacturas({ t, onNavigate }) {
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
      setSync(await api.odooSyncFacturas());
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
      setIngesta(await api.odooIngestFacturas());
    } catch {
      setErrorIngesta(t("odoo.error_generico"));
    } finally {
      setIngestando(false);
    }
  };

  const agingKey = (f) => `odoo.aging_${f.aging || "open"}`;

  return (
    <div className="space-y-3 pt-1">
      <ConnectorSyncAction
        onFetch={sincronizar} fetching={sincronizando}
        fetchLabel={t("odoo.traer_facturas")} fetchingLabel={t("odoo.sincronizando_facturas")}
        onIngest={ingestar} ingesting={ingestando}
        ingestLabel={t("odoo.ingestar_facturas")} ingestingLabel={t("odoo.ingestando_facturas")}
        error={error} errorIngest={errorIngesta}
      />
      {ingesta && (
        <p className="text-[0.82rem] text-tinta-suave">
          {ingesta.actualizados > 0 || ingesta.nuevos_para_revisar > 0
            ? t("odoo.ingesta_facturas_resultado", { actualizados: ingesta.actualizados, nuevos: ingesta.nuevos_para_revisar })
            : t("odoo.ingesta_facturas_sin_novedades")}
          <IngestLinks t={t} onNavigate={onNavigate} batchId={ingesta.batch_id} importedTab="invoices" />
        </p>
      )}
      {sync && (
        <p className="text-[0.82rem] text-tinta-suave">
          {sync.total > 0
            ? t("odoo.sync_facturas_resultado", { n: sync.total, as_of: sync.as_of || "" })
            : t("odoo.sync_facturas_vacio")}
        </p>
      )}
      {sync?.total > 0 && (
        <ul className="max-h-56 space-y-1 overflow-y-auto rounded-xl border border-linea/60
                       bg-papel-hondo/30 p-2 text-[0.8rem]">
          {sync.facturas.map((f) => (
            <li key={f.id} className="flex items-center justify-between gap-2 text-tinta">
              <span className="min-w-0 truncate">
                {f.numero} · {f.partner}
                {f.currency && <span className="text-tinta-suave"> · {f.currency}</span>}
              </span>
              <span className={`shrink-0 text-[0.72rem] font-semibold ${
                f.aging === "overdue" ? "text-rojo-hondo" : "text-tinta-suave"}`}>
                {t(agingKey(f))}
                {f.residual != null && f.aging !== "paid" ? ` · ${f.residual}` : ""}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function OdooTabPrecios({ t }) {
  const [listas, setListas] = useState(null);
  const [monedas, setMonedas] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);

  const traer = async () => {
    setCargando(true);
    setError(null);
    try {
      const [pl, fx] = await Promise.all([api.odooSyncListasPrecios(), api.odooSyncMonedas()]);
      setListas(pl);
      setMonedas(fx);
    } catch {
      setError(t("odoo.error_generico"));
    } finally {
      setCargando(false);
    }
  };

  return (
    <div className="space-y-3 pt-1">
      <ConnectorButton onClick={traer} loading={cargando}>
        {cargando ? t("odoo.sincronizando_precios") : t("odoo.traer_precios")}
      </ConnectorButton>
      {error && <p className="text-[0.8rem] text-rojo-hondo">{error}</p>}
      {monedas && (
        <p className="text-[0.82rem] text-tinta-suave">
          {t("odoo.sync_monedas_resultado", {
            moneda: monedas.moneda_compania, n: monedas.total,
          })}
        </p>
      )}
      {monedas?.tipos_cambio?.length > 0 && (
        <ul className="max-h-32 space-y-0.5 overflow-y-auto rounded-xl border border-linea/60
                       bg-papel-hondo/30 p-2 text-[0.8rem] text-tinta-suave">
          {monedas.tipos_cambio.map((r) => (
            <li key={`${r.currency}-${r.fecha}`}>
              {r.fecha} · {r.currency} · {r.inverse_company_rate}
            </li>
          ))}
        </ul>
      )}
      {listas && (
        <p className="text-[0.82rem] text-tinta-suave">
          {listas.total > 0
            ? t("odoo.sync_listas_resultado", { n: listas.total })
            : t("odoo.sync_listas_vacio")}
        </p>
      )}
      {listas?.total > 0 && (
        <ul className="max-h-40 space-y-1 overflow-y-auto rounded-xl border border-linea/60
                       bg-papel-hondo/30 p-2 text-[0.8rem]">
          {listas.listas.map((pl) => (
            <li key={pl.id} className="text-tinta">
              {pl.nombre}
              <span className="text-tinta-suave"> · {pl.currency} · {pl.items.length}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}


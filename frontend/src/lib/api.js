// Cliente de la API de PolPilot. En dev, Vite proxea /api -> FastAPI:8000.
import { authStore } from "./auth";
import { t } from "./i18n";
import { ChatStreamError, chatErrorCodeFromStatus } from "./chat/errors";
import { apiUrl } from "./apiUrl";

// El token de sesión viaja en el header Authorization en TODA llamada: el backend
// saca la identidad de ahí (nunca del body). Un solo lugar, sin tocar cada llamada.
function _headers(extra = {}) {
  const token = authStore.getSnapshot()?.token;
  return { ...extra, ...(token ? { Authorization: `Bearer ${token}` } : {}) };
}

// El error viaja con status y un mensaje con la personalidad de la casa (en el
// idioma del usuario), para que las vistas distingan "no tenés este módulo"
// (403) de un error técnico.
function _error(path, res) {
  // Un 401 significa que el token guardado ya no vale (server reiniciado,
  // sesión de otra corrida): se borra acá — único lugar por donde pasan
  // todos — y App cae sola al login en vez de quedar clavada en un error.
  if (res.status === 401) authStore.logout();
  const e = new Error(`${path} → ${res.status}`);
  e.status = res.status;
  e.criollo = res.status === 403
    ? t("api.error_403")
    : res.status === 401
      ? t("api.error_401")
      : t("api.error_generico");
  return e;
}

async function get(path) {
  const res = await fetch(apiUrl(path), { headers: _headers() });
  if (!res.ok) throw _error(path, res);
  return res.json();
}

function qs(params = {}) {
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v != null && v !== "" && v !== "all") u.set(k, String(v));
  }
  const s = u.toString();
  return s ? `?${s}` : "";
}

async function downloadCsv(path, fallbackName) {
  const res = await fetch(apiUrl(path), { headers: _headers() });
  if (!res.ok) throw _error(path, res);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  const disp = res.headers.get("content-disposition") || "";
  const m = disp.match(/filename="?([^"]+)"?/i);
  a.href = url;
  a.download = m?.[1] || fallbackName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

async function post(path, body) {
  const res = await fetch(apiUrl(path), {
    method: "POST",
    headers: _headers({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw _error(path, res);
  return res.json();
}

async function put(path, body) {
  const res = await fetch(apiUrl(path), {
    method: "PUT",
    headers: _headers({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw _error(path, res);
  return res.json();
}

async function del(path) {
  const res = await fetch(apiUrl(path), { method: "DELETE", headers: _headers() });
  if (!res.ok) throw _error(path, res);
  return res.json();
}

export const api = {
  inventario: () => get("/api/inventario"),
  actividad: () => get("/api/actividad"),
  inicio: () => get("/api/inicio"),
  equipoNombres: () => get("/api/equipo/nombres"),
  // P·onboarding — la guía del que recién entró (recortada a sus features).
  onboarding: () => get("/api/onboarding"),
  objetivos: () => get("/api/objetivos"),
  objetivoCrear: (nombre, responsable, fecha, id) =>
    post("/api/objetivos", { nombre, responsable, fecha, id }),
  objetivoEstado: (oid, estado) => post(`/api/objetivos/${oid}/estado`, { estado }),
  verComo: (username) => post("/api/demo/ver-como", { username }),
  // Carga de comprobantes por foto (P10)
  facturaLeer: (imagen, media_type) => post("/api/factura/leer", { imagen, media_type }),
  facturaConfirmar: (extraccion) => post("/api/factura/confirmar", { extraccion }),
  // El segundo sí: faltó mercadería contra la orden y el dueño manda a reclamar.
  remitoReclamar: (proveedor, items, oc) =>
    post("/api/remito/reclamar", { proveedor, items, oc }),
  muestras: () => get("/api/comprobantes/muestras"),
  // LA VOZ DEL PISO. El navegador transcribe (Web Speech) y acá viaja TEXTO:
  // la API de Anthropic no acepta audio ni transcribe.
  vozEscuchar: (texto) => post("/api/voz/escuchar", { texto }),
  vozConfirmar: (tipo, datos, transcripcion) =>
    post("/api/voz/confirmar", { tipo, datos, transcripcion }),
  vozMuestras: () => get("/api/voz/muestras"),
  blob: async (path) => {
    const res = await fetch(apiUrl(path), { headers: _headers() });
    if (!res.ok) throw _error(path, res);
    return res.blob();
  },
  // El PDF de un documento se pide con el documento en el cuerpo (la copia con
  // los cambios del usuario vive en el cliente), así que no alcanza el GET.
  blobPost: async (path, body) => {
    const res = await fetch(apiUrl(path), {
      method: "POST",
      headers: { ..._headers(), "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw _error(path, res);
    return res.blob();
  },
  grupo: (nombre, limit) =>
    get(`/api/grupo/${nombre}${limit ? `?limit=${limit}` : ""}`),
  buscar: (q) => get(`/api/buscar?q=${encodeURIComponent(q)}`),
  buscarGlobal: (q) => get(`/api/buscar-global?q=${encodeURIComponent(q)}`),
  // La ficha de UN producto. En el teléfono no se llega por una lista de 430
  // filas: se llega por una búsqueda, un escaneo o una tarea.
  fichaProducto: (codigo) => get(`/api/ficha/producto/${codigo}`),
  oportunidades: () => get("/api/oportunidades"),
  prioridades: () => get("/api/prioridades"),
  // Closing the loop on a continuous-learning finding (core/patrones.py):
  // the owner's reaction, so the same instance doesn't resurface.
  patronFeedback: (cardId, action, note) =>
    post("/api/patrones/feedback", { card_id: cardId, action, note }),
  patronHistorial: () => get("/api/patrones/historial"),
  // P38·B — el dueño aprueba la orden que Ángela dejó armada (queda en borrador).
  ordenCompraPreparar: (p) => post("/api/orden-compra/preparar", p),
  ordenesPreparadas: () => get("/api/ordenes-preparadas"),
  ordenCompraCrear: (p) => post("/api/ordenes-compra", p),
  ordenCompraEstado: (numero, estado) =>
    post(`/api/ordenes-compra/${encodeURIComponent(numero)}/estado`, { estado }),
  ubicaciones: () => get("/api/ubicaciones"),
  ubicacionCrear: (p) => post("/api/ubicaciones", p),
  ubicacionActualizar: (id, p) => post(`/api/ubicaciones/${encodeURIComponent(id)}/actualizar`, p),
  ubicacionEliminar: (id) => post(`/api/ubicaciones/${encodeURIComponent(id)}/eliminar`, {}),
  proveedores: () => get("/api/proveedores"),
  proveedorCrear: (p) => post("/api/proveedores", p),
  proveedorActualizar: (id, p) => post(`/api/proveedores/${encodeURIComponent(id)}/actualizar`, p),
  proveedorEliminar: (id) => post(`/api/proveedores/${encodeURIComponent(id)}/eliminar`, {}),
  lotes: () => get("/api/lotes"),
  loteCrear: (p) => post("/api/lotes", p),
  loteActualizar: (id, p) => post(`/api/lotes/${encodeURIComponent(id)}/actualizar`, p),
  loteEliminar: (id) => post(`/api/lotes/${encodeURIComponent(id)}/eliminar`, {}),
  articuloCrear: (p) => post("/api/articulos", p),
  articuloActualizar: (codigo, p) => post(`/api/articulos/${codigo}/actualizar`, p),
  articuloEliminar: (codigo) => post(`/api/articulos/${codigo}/eliminar`, {}),
  productos: (p = {}) => get("/api/productos" + qs(p)),
  productosExport: (p = {}) => downloadCsv("/api/productos/export.csv" + qs(p), "productos.csv"),
  sales: (p = {}) => get("/api/sales" + qs(p)),
  salesExport: (p = {}) => downloadCsv("/api/sales/export.csv" + qs(p), "ventas.csv"),
  saleCrear: (p) => post("/api/sales", p),
  saleActualizar: (id, p) => post(`/api/sales/${encodeURIComponent(id)}/actualizar`, p),
  saleEliminar: (id) => post(`/api/sales/${encodeURIComponent(id)}/eliminar`, {}),
  receipts: (p = {}) => get("/api/receipts" + qs(p)),
  receiptsExport: (p = {}) => downloadCsv("/api/receipts/export.csv" + qs(p), "recepciones.csv"),
  receiptCrear: (p) => post("/api/receipts", p),
  receiptActualizar: (id, p) => post(`/api/receipts/${encodeURIComponent(id)}/actualizar`, p),
  receiptEliminar: (id) => post(`/api/receipts/${encodeURIComponent(id)}/eliminar`, {}),
  movimientos: (p = {}) => get("/api/movimientos" + qs(p)),
  movimientosExport: (p = {}) => downloadCsv("/api/movimientos/export.csv" + qs(p), "movimientos.csv"),
  conciliacion: () => get("/api/conciliacion"),
  conciliacionAceptar: (id) => post(`/api/conciliacion/${encodeURIComponent(id)}/aceptar`, {}),
  // P38·C — márgenes por grupo y por producto (mayorista + mostrador)
  margenes: () => get("/api/margenes"),
  margenes_detalle: (grupo) => get(`/api/margenes?grupo=${encodeURIComponent(grupo)}`),
  // P38·E/F — reporte de cierres por local y separación de traslados internos
  cierresLocales: (dias = 7) => get(`/api/cierres-locales?dias=${dias}`),
  // El costo viejo, del lado del que mira ese precio todos los días.
  mostradorCostosViejos: () => get("/api/mostrador/costos-viejos"),
  traslados: () => get("/api/traslados-internos"),
  // P38·H — vencimientos que Ángela gestiona
  vencimientos: (dias = 30) => get(`/api/vencimientos?dias=${dias}`),
  vencimientoGestionar: (body) => post("/api/vencimientos/gestionar", body),
  conocimiento: (params = {}) => {
    const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString();
    return get("/api/conocimiento" + (q ? `?${q}` : ""));
  },
  // Proposals from chat (angela.py: proponer_conocimiento) waiting for
  // someone with that node to approve or reject them before they take effect.
  conocimientoPendientes: (nodo) => get("/api/conocimiento/pendientes" + (nodo ? `?nodo=${encodeURIComponent(nodo)}` : "")),
  conocimientoAprobar: (pid) => post(`/api/conocimiento/${encodeURIComponent(pid)}/aprobar`, {}),
  conocimientoRechazar: (pid) => post(`/api/conocimiento/${encodeURIComponent(pid)}/rechazar`, {}),
  knowledgeDelete: (pid) => del(`/api/conocimiento/${encodeURIComponent(pid)}`),
  knowledgeSetState: (pid, state) => post(`/api/conocimiento/${encodeURIComponent(pid)}/estado`, { estado: state }),
  knowledgeConfirm: (proposal) => post("/api/conocimiento/confirm", proposal),
  analisis: () => get("/api/analisis"),
  // Bloque D — qué reponer primero, ordenado por la plata que cuesta no hacerlo
  reponer: () => get("/api/reponer"),
  // Bloque E — a quién cobrar primero, y en qué anda cada gestión
  // Bloque F — el registro de auditoría legible y la perilla de autonomía.
  // /api/audit (crudo) sigue existiendo para depurar; esto es lo que lee el dueño.
  auditoria: (f = {}) => {
    const qs = new URLSearchParams();
    for (const k of ["clase", "actor", "desde", "hasta", "q", "limite"])
      if (f[k]) qs.set(k, f[k]);
    return get("/api/auditoria" + (qs.toString() ? `?${qs}` : ""));
  },
  auditoriaHilo: (sujeto) => get(`/api/auditoria/hilo?sujeto=${encodeURIComponent(sujeto)}`),
  autonomia: () => get("/api/autonomia"),
  autonomiaSet: (clase, nivel) => post("/api/autonomia", { clase, nivel }),
  // Bot de WhatsApp de cara al cliente (canal de ventas, no el interno de empleados).
  whatsappBotConfig: () => get("/api/whatsapp-bot/config"),
  whatsappBotConfigGuardar: (config) => put("/api/whatsapp-bot/config", config),
  whatsappBotConfigBorrar: () => del("/api/whatsapp-bot/config"),
  whatsappBotConversaciones: () => get("/api/whatsapp-bot/conversaciones"),
  whatsappBotMensajes: (conversationId) =>
    get(`/api/whatsapp-bot/conversaciones/${encodeURIComponent(conversationId)}/mensajes`),
  // Plan 11 · Conectores con sistemas externos.
  conectores: () => get("/api/conectores"),
  odooConfig: () => get("/api/conectores/odoo"),
  odooConfigGuardar: (config) => put("/api/conectores/odoo", config),
  odooConfigBorrar: () => del("/api/conectores/odoo"),
  // DEMO: one click connects the sample transport and runs the first sync.
  odooConectarDemo: () => post("/api/conectores/odoo/conectar-demo", {}),
  odooSync: () => post("/api/conectores/odoo/sync", {}),
  odooIngestContactos: () => post("/api/conectores/odoo/ingest-contactos", {}),
  odooSyncProductos: () => post("/api/conectores/odoo/sync-productos", {}),
  odooIngestProductos: () => post("/api/conectores/odoo/ingest-productos", {}),
  odooSyncProveedores: () => post("/api/conectores/odoo/sync-proveedores", {}),
  odooIngestProveedores: () => post("/api/conectores/odoo/ingest-proveedores", {}),
  odooSyncOrdenesCompra: () => post("/api/conectores/odoo/sync-ordenes-compra", {}),
  odooIngestOrdenesCompra: () => post("/api/conectores/odoo/ingest-ordenes-compra", {}),
  odooSyncVentas: () => post("/api/conectores/odoo/sync-ventas", {}),
  odooIngestVentas: () => post("/api/conectores/odoo/ingest-ventas", {}),
  odooSyncDeposito: () => post("/api/conectores/odoo/sync-deposito", {}),
  odooIngestDeposito: () => post("/api/conectores/odoo/ingest-deposito", {}),
  odooSyncRecepciones: () => post("/api/conectores/odoo/sync-recepciones", {}),
  odooIngestRecepciones: () => post("/api/conectores/odoo/ingest-recepciones", {}),
  odooSyncEntregas: () => post("/api/conectores/odoo/sync-entregas", {}),
  odooIngestEntregas: () => post("/api/conectores/odoo/ingest-entregas", {}),
  odooSyncFacturas: () => post("/api/conectores/odoo/sync-facturas", {}),
  odooIngestFacturas: () => post("/api/conectores/odoo/ingest-facturas", {}),
  odooSyncPagos: () => post("/api/conectores/odoo/sync-pagos", {}),
  odooIngestPagos: () => post("/api/conectores/odoo/ingest-pagos", {}),
  odooSyncListasPrecios: () => post("/api/conectores/odoo/sync-listas-precios", {}),
  odooSyncMonedas: () => post("/api/conectores/odoo/sync-monedas", {}),
  cobranza: () => get("/api/cobranza"),
  cobranzaPropuesta: (id) => get(`/api/cobranza/${id}/propuesta`),
  cobranzaRegistrar: (cliente_id, estado, extra = {}) =>
    post("/api/cobranza/registrar", { cliente_id, estado, ...extra }),
  // EL CEREBRO — entidades del negocio y sus cruces reales (vista nueva del
  // mapa). Aditivo: el mapa de árbol no lo consume.
  grafo: () => get("/api/grafo"),
  // THE OPERATION MAP — the physical chain (origin → warehouse → destination)
  // plus the context layer no ERP captures. Additive: neither the sources
  // tree nor the brain consume these.
  mapaOperacion: () => get("/api/mapa-operacion"),
  mapaOperacionNodo: (nid) =>
    get(`/api/mapa-operacion/nodo/${encodeURIComponent(nid)}`),
  fase: () => get("/api/fase"),
  articulos: () => get("/api/articulos"),
  imported: () => get("/api/imported"),
  inventarioTop: (n = 10) => get(`/api/inventario/top?n=${n}`),
  inventarioViz: () => get("/api/inventario/viz"),
  inventarioBurn: (codigo) => get(`/api/inventario/burn/${codigo}`),
  calidad: () => get("/api/calidad"),
  anomalias: () => get("/api/anomalias"),
  anomaliasAplicar: (tipo, accion, params = {}) => post("/api/anomalias/aplicar", { tipo, accion, params }),
  balanzas: () => get("/api/balanzas"),
  documento: (tipo) => get(`/api/documentos/${tipo}`),
  // P39 · lo que el piso reporta (y lo que el dueño hace con eso)
  piso: {
    reportar: (tipo, datos, destinatario) =>
      post("/api/piso/reporte", { tipo, datos, destinatario }),
    // A quién PROPONE Ángela mandarlo. Se consulta antes de mandar para poder
    // preguntar "esto lo ve Celeste, ¿lo mando?" — nunca se manda solo.
    destinatario: (tipo) => get(`/api/piso/destinatario?tipo=${encodeURIComponent(tipo)}`),
    // Los avisos que deja ESTE oficio, como botones. El servidor los resuelve
    // desde el rol de quien pregunta: el cliente no elige su propia lista.
    avisosOficio: () => get("/api/piso/avisos-oficio"),
    // Lo que mandé, lo que me mandaron, y los hallazgos que se apoyan en algo
    // que yo dije. La mitad del circuito que faltaba.
    mios: () => get("/api/piso/mios"),

    visto: (rid) => post(`/api/piso/reportes/${rid}/visto`, {}),
    reportes: (tipo, estado) => get(`/api/piso/reportes${tipo || estado
      ? `?${[tipo && `tipo=${tipo}`, estado && `estado=${estado}`].filter(Boolean).join("&")}` : ""}`),
    resolver: (rid, nota = "") => post(`/api/piso/reportes/${rid}/resolver`, { nota }),
    propuestas: () => get("/api/piso/propuestas"),
    // La foto de la prueba. Va como <img src>, que no puede mandar headers, así
    // que el token viaja en la query — el endpoint ya lo acepta por ahí, y lo
    // recorta igual: sólo el dueño y quien la sacó.
    pruebaUrl: (rid) => apiUrl(`/api/piso/reportes/${rid}/prueba?token=${
      encodeURIComponent(authStore.getSnapshot()?.token || "")}`),
  },
  // PDF real (P17): manda el draft EDITADO (la única copia con los cambios
  // del usuario vive en el docStore) y vuelve el binario para descargar.
  documentoPdf: async (documento) => {
    const res = await fetch(apiUrl("/api/documentos/pdf"), {
      method: "POST",
      headers: _headers({ "Content-Type": "application/json" }),
      body: JSON.stringify({ documento }),
    });
    if (!res.ok) throw _error("/api/documentos/pdf", res);
    return res.blob();
  },
  documentosListado: () => get("/api/documentos/listado"),
  carpetaPedidos: () => get("/api/carpeta"),
  carpeta: (numero) => get(`/api/carpeta/${encodeURIComponent(numero)}`),
  carpetaDocumento: (numero, docId) =>
    get(`/api/carpeta/${encodeURIComponent(numero)}/${encodeURIComponent(docId)}`),
  cuentas: () => get("/api/cuentas"),
  cuentaCobro: (id, monto) => post(`/api/cuentas/${id}/cobro`, { monto }),
  // C2 · la parada enriquecida: quién está parado frente a quién.
  parada: (cliente) => get(`/api/parada?cliente=${encodeURIComponent(cliente)}`),
  paradasProximas: (transporte) =>
    get("/api/parada/proximas" + (transporte ? `?transporte=${encodeURIComponent(transporte)}` : "")),
  cuentaRecordatorio: (id) => get(`/api/cuentas/${id}/recordatorio`),
  // P24·D6 — reglas de aviso del usuario (recordatorios condicionales)
  recordatorios: () => get("/api/recordatorios"),
  // P41·4 — el dueño asigna una tarea a alguien; queda PERSISTIDA y la
  // persona la ve en su vista de trabajo y la marca hecha desde ahí.
  recordatorioCrear: (texto, para) => post("/api/recordatorios", { texto, para }),
  equipoActividad: () => get("/api/equipo/actividad"),
  recordatorioCompletar: (rid) => post(`/api/recordatorios/${rid}/completar`, {}),
  evolucion: () => get("/api/evolucion"),
  forecast: () => get("/api/forecast"),
  pagos: () => get("/api/pagos"),
  macro: () => get("/api/macro"),
  deposito: (dias = 15) => get(`/api/deposito?dias=${dias}`),
  ventas: () => get("/api/ventas"),
  ventasValidacion: () => get("/api/ventas/validacion"),
  ventasValidar: (esperado, confirmar = false) => post("/api/ventas/validacion", { esperado, confirmar }),
  ventasDryrun: (csv) => post("/api/ventas/dryrun", { csv }),
  cajaEstado: () => get("/api/caja"),
  cajaMovimiento: (tipo, medio, monto, detalle = "") => post("/api/caja/movimiento", { tipo, medio, monto, detalle }),
  cajaCerrar: (declarado = null) => post("/api/caja/cerrar", { declarado }),
  syncDelta: (formato = "generico") => get(`/api/sync/delta?formato=${formato}`),
  versiones: () => get("/api/versiones"),
  saneamientoProponer: (cat) => get(`/api/saneamiento/proponer/${cat}`),
  saneamientoAplicar: (cat, actor = "dueño") => post(`/api/saneamiento/aplicar/${cat}`, { actor }),
  saneamientoRevertir: (vid, actor = "dueño") => post(`/api/saneamiento/revertir/${vid}`, { actor }),
  contextoListar: () => get("/api/contexto"),
  contextoAgregar: (nombre, tipo, texto) =>
    post("/api/contexto", { nombre, tipo, texto }),
  importPreview: (csv, destino, usuario) =>
    post("/api/import/preview", { csv, destino, usuario }),
  cargarOtro: (nombre, descripcion, usuario) =>
    post("/api/cargar/otro", { nombre, descripcion, usuario }),
  stagingListar: () => get("/api/staging"),
  stagingCrear: (nombre, csv) => post("/api/staging", { nombre, csv }),
  stagingResolver: (id, obs_id, accion, params = {}) => post(`/api/staging/${id}/resolver`, { obs_id, accion, params }),
  stagingPreview: (id) => get(`/api/staging/${id}/preview`),
  stagingIntegrar: (id) => post(`/api/staging/${id}/integrar`, {}),
  stagingDescartar: (id) => post(`/api/staging/${id}/descartar`, {}),
  stagingRevertirNormalizacion: (id) => post(`/api/staging/${id}/normalizacion/revertir`, {}),
  memoria: (usuario) => get(`/api/memoria/${encodeURIComponent(usuario)}`),
  // P19·C — dato de las cards a pedido (se recalcula en cada carga)
  widgetPlataParada: (dias = 120) => get(`/api/widget-datos/plata-parada?dias=${dias}`),
  // P21 — widget generativo: la consulta validada se re-ejecuta en el server
  consultaSerie: (consulta) => post("/api/consulta-serie", { consulta }),
  // P19·A — preferencias de vista (server = fuente de verdad; el token decide el usuario)
  preferencias: () => get("/api/preferencias"),
  preferenciaSet: (clave, valor) => post("/api/preferencias", { clave, valor }),
  preferenciaBorrar: async (clave) => {
    const res = await fetch(apiUrl(`/api/preferencias/${encodeURIComponent(clave)}`), {
      method: "DELETE", headers: _headers(),
    });
    if (!res.ok) throw _error("/api/preferencias", res);
    return res.json();
  },
  perfil: (usuario) => get(`/api/perfil/${encodeURIComponent(usuario)}`),
  perfilDescripcion: (usuario, token, texto) =>
    post(`/api/perfil/${encodeURIComponent(usuario)}/descripcion`, { token, texto }),
  perfilFoto: (usuario, token, imagen) =>
    post(`/api/perfil/${encodeURIComponent(usuario)}/foto`, { token, imagen }),
  solicitar: (token, modulos, motivo = "") => post("/api/solicitudes", { token, modulos, motivo }),
  solicitudes: (token, estado) =>
    get(`/api/solicitudes?token=${encodeURIComponent(token)}${estado ? `&estado=${estado}` : ""}`),
  solicitudResolver: (sid, token, aprobar, motivo = "") =>
    post(`/api/solicitudes/${sid}/resolver`, { token, aprobar, motivo }),
  adminMatriz: (token) => get(`/api/admin/matriz?token=${encodeURIComponent(token)}`),
  adminFeature: (token, usuario, modulo, habilitar) =>
    post("/api/admin/feature", { token, usuario, modulo, habilitar }),
  notificaciones: (token) => get(`/api/notificaciones?token=${encodeURIComponent(token)}`),
  notificacionLeida: (nid, token) =>
    post(`/api/notificaciones/${nid}/leida?token=${encodeURIComponent(token)}`, {}),
  notificacionAvisar: (para, titulo, cuerpo = "") =>
    post("/api/notificaciones/avisar", { para, titulo, cuerpo }),
  health: () => get("/api/health"),
  // Streaming (NDJSON): returns the raw Response so the assistant-ui runtime
  // can read the body as it arrives. The non-streaming /api/angela endpoint
  // still exists server-side (WhatsApp and backend tests use it) but nothing
  // in the frontend calls it anymore — this is the only client-side entry point.
  chatStream: async (mensaje, historial = [], extra = {}, { signal } = {}) => {
    let res;
    try {
      res = await fetch(apiUrl("/api/angela/stream"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: mensaje, history: historial, ...extra }),
        signal,
      });
    } catch (e) {
      // An aborted fetch is a cancellation, not a failure.
      if (signal?.aborted) throw new ChatStreamError("aborted");
      throw new ChatStreamError("network", String(e?.message || e));
    }
    if (!res.ok) {
      throw new ChatStreamError(
        chatErrorCodeFromStatus(res.status),
        `angela/stream → ${res.status}`,
        res.status,
      );
    }
    if (!res.body) throw new ChatStreamError("stream", "response has no body");
    return res;
  },
};

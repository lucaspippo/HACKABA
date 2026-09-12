import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";
import { queryClient } from "./client";
import { keys } from "./keys";

const inventarioStock = [keys.inventario(), keys.productos(), keys.articulos(), keys.inicio(), keys.paged()];
const knowledge = [keys.conocimiento(), keys.conocimientoPendientes()];
const odoo = [keys.conectores(), keys.odooConfig(), keys.inventario(), keys.productos(), keys.staging()];
const piso = [keys.piso.all()];

export const MUTATIONS = {
  objetivoCrear: { mutationFn: api.objetivoCrear, invalidate: [keys.objetivos(), keys.objetivosMedidos(), keys.inicio()] },
  objetivoEstado: { mutationFn: api.objetivoEstado, invalidate: [keys.objetivos(), keys.objetivosMedidos(), keys.inicio()] },
  verComo: { mutationFn: api.verComo, invalidate: [keys.all()] },
  facturaLeer: { mutationFn: api.facturaLeer, invalidate: [] },
  facturaConfirmar: { mutationFn: api.facturaConfirmar, invalidate: [...inventarioStock, keys.sales(), keys.receipts(), keys.imported()] },
  remitoReclamar: { mutationFn: api.remitoReclamar, invalidate: [keys.receipts(), keys.inicio()] },
  vozEscuchar: { mutationFn: api.vozEscuchar, invalidate: [] },
  vozConfirmar: { mutationFn: api.vozConfirmar, invalidate: [keys.all()] },
  patronFeedback: { mutationFn: api.patronFeedback, invalidate: [keys.prioridades(), keys.patronHistorial()] },
  ordenCompraPreparar: { mutationFn: api.ordenCompraPreparar, invalidate: [keys.ordenesPreparadas(), keys.reponer(), keys.oportunidades()] },
  ordenCompraCrear: { mutationFn: api.ordenCompraCrear, invalidate: [keys.ordenesPreparadas(), keys.reponer(), keys.oportunidades()] },
  ordenCompraEstado: { mutationFn: api.ordenCompraEstado, invalidate: [keys.ordenesPreparadas(), keys.reponer()] },
  ubicacionCrear: { mutationFn: api.ubicacionCrear, invalidate: [keys.ubicaciones()] },
  ubicacionActualizar: { mutationFn: api.ubicacionActualizar, invalidate: [keys.ubicaciones()] },
  ubicacionEliminar: { mutationFn: api.ubicacionEliminar, invalidate: [keys.ubicaciones()] },
  proveedorCrear: { mutationFn: api.proveedorCrear, invalidate: [keys.proveedores()] },
  proveedorActualizar: { mutationFn: api.proveedorActualizar, invalidate: [keys.proveedores()] },
  proveedorEliminar: { mutationFn: api.proveedorEliminar, invalidate: [keys.proveedores()] },
  loteCrear: { mutationFn: api.loteCrear, invalidate: [keys.lotes(), keys.inventario(), keys.vencimientos()] },
  loteActualizar: { mutationFn: api.loteActualizar, invalidate: [keys.lotes(), keys.inventario(), keys.vencimientos()] },
  loteEliminar: { mutationFn: api.loteEliminar, invalidate: [keys.lotes(), keys.inventario(), keys.vencimientos()] },
  articuloCrear: { mutationFn: api.articuloCrear, invalidate: inventarioStock },
  articuloActualizar: { mutationFn: api.articuloActualizar, invalidate: inventarioStock },
  articuloEliminar: { mutationFn: api.articuloEliminar, invalidate: inventarioStock },
  saleCrear: { mutationFn: api.saleCrear, invalidate: [keys.sales(), keys.ventas(), ...inventarioStock] },
  saleActualizar: { mutationFn: api.saleActualizar, invalidate: [keys.sales(), keys.ventas(), ...inventarioStock] },
  saleEliminar: { mutationFn: api.saleEliminar, invalidate: [keys.sales(), keys.ventas(), ...inventarioStock] },
  receiptCrear: { mutationFn: api.receiptCrear, invalidate: [keys.receipts(), keys.deposito(), ...inventarioStock] },
  receiptActualizar: { mutationFn: api.receiptActualizar, invalidate: [keys.receipts(), keys.deposito(), ...inventarioStock] },
  receiptEliminar: { mutationFn: api.receiptEliminar, invalidate: [keys.receipts(), keys.deposito(), ...inventarioStock] },
  conciliacionAceptar: { mutationFn: api.conciliacionAceptar, invalidate: [keys.conciliacion(), keys.caja()] },
  vencimientoGestionar: { mutationFn: api.vencimientoGestionar, invalidate: [keys.vencimientos(), keys.deposito()] },
  conocimientoAprobar: { mutationFn: api.conocimientoAprobar, invalidate: knowledge },
  conocimientoRechazar: { mutationFn: api.conocimientoRechazar, invalidate: knowledge },
  knowledgeDelete: { mutationFn: api.knowledgeDelete, invalidate: knowledge },
  knowledgeSetState: { mutationFn: api.knowledgeSetState, invalidate: knowledge },
  knowledgeConfirm: { mutationFn: api.knowledgeConfirm, invalidate: knowledge },
  rulesConfirm: { mutationFn: api.rulesConfirm, invalidate: knowledge },
  conocimientoCrear: { mutationFn: api.conocimientoCrear, invalidate: knowledge },
  conocimientoEditar: { mutationFn: api.conocimientoEditar, invalidate: knowledge },
  conocimientoArchivar: { mutationFn: api.conocimientoArchivar, invalidate: knowledge },
  conocimientoReemplazar: { mutationFn: api.conocimientoReemplazar, invalidate: knowledge },
  conocimientoReconfirmar: { mutationFn: api.conocimientoReconfirmar, invalidate: knowledge },
  anomaliasAplicar: { mutationFn: api.anomaliasAplicar, invalidate: [keys.anomalias(), keys.calidad(), keys.inventario()] },
  autonomiaSet: { mutationFn: api.autonomiaSet, invalidate: [keys.autonomia()] },
  whatsappBotConfigGuardar: { mutationFn: api.whatsappBotConfigGuardar, invalidate: [keys.whatsappBotConfig()] },
  whatsappBotConfigBorrar: { mutationFn: api.whatsappBotConfigBorrar, invalidate: [keys.whatsappBotConfig()] },
  odooConfigGuardar: { mutationFn: api.odooConfigGuardar, invalidate: odoo },
  odooConfigBorrar: { mutationFn: api.odooConfigBorrar, invalidate: odoo },
  odooConectarDemo: { mutationFn: api.odooConectarDemo, invalidate: odoo },
  odooSync: { mutationFn: api.odooSync, invalidate: odoo },
  odooIngestContactos: { mutationFn: api.odooIngestContactos, invalidate: odoo },
  odooSyncProductos: { mutationFn: api.odooSyncProductos, invalidate: odoo },
  odooIngestProductos: { mutationFn: api.odooIngestProductos, invalidate: odoo },
  odooSyncProveedores: { mutationFn: api.odooSyncProveedores, invalidate: odoo },
  odooIngestProveedores: { mutationFn: api.odooIngestProveedores, invalidate: odoo },
  odooSyncOrdenesCompra: { mutationFn: api.odooSyncOrdenesCompra, invalidate: odoo },
  odooIngestOrdenesCompra: { mutationFn: api.odooIngestOrdenesCompra, invalidate: odoo },
  odooSyncVentas: { mutationFn: api.odooSyncVentas, invalidate: odoo },
  odooIngestVentas: { mutationFn: api.odooIngestVentas, invalidate: odoo },
  odooSyncDeposito: { mutationFn: api.odooSyncDeposito, invalidate: odoo },
  odooIngestDeposito: { mutationFn: api.odooIngestDeposito, invalidate: odoo },
  odooSyncRecepciones: { mutationFn: api.odooSyncRecepciones, invalidate: odoo },
  odooIngestRecepciones: { mutationFn: api.odooIngestRecepciones, invalidate: odoo },
  odooSyncEntregas: { mutationFn: api.odooSyncEntregas, invalidate: odoo },
  odooIngestEntregas: { mutationFn: api.odooIngestEntregas, invalidate: odoo },
  odooSyncFacturas: { mutationFn: api.odooSyncFacturas, invalidate: odoo },
  odooIngestFacturas: { mutationFn: api.odooIngestFacturas, invalidate: odoo },
  odooSyncPagos: { mutationFn: api.odooSyncPagos, invalidate: odoo },
  odooIngestPagos: { mutationFn: api.odooIngestPagos, invalidate: odoo },
  odooSyncListasPrecios: { mutationFn: api.odooSyncListasPrecios, invalidate: odoo },
  odooSyncMonedas: { mutationFn: api.odooSyncMonedas, invalidate: odoo },
  cobranzaRegistrar: { mutationFn: api.cobranzaRegistrar, invalidate: [keys.cobranza(), keys.cuentas()] },
  cajaMovimiento: { mutationFn: api.cajaMovimiento, invalidate: [keys.caja(), keys.cierresLocales(), keys.inicio()] },
  cajaCerrar: { mutationFn: api.cajaCerrar, invalidate: [keys.caja(), keys.cierresLocales(), keys.inicio()] },
  saneamientoAplicar: { mutationFn: api.saneamientoAplicar, invalidate: [keys.calidad(), keys.anomalias(), keys.inventario(), keys.syncDelta(), keys.staging(), keys.inicio()] },
  saneamientoRevertir: { mutationFn: api.saneamientoRevertir, invalidate: [keys.calidad(), keys.anomalias(), keys.inventario(), keys.syncDelta(), keys.staging(), keys.inicio()] },
  contextoAgregar: { mutationFn: api.contextoAgregar, invalidate: [keys.contexto()] },
  importPreview: { mutationFn: api.importPreview, invalidate: [] },
  cargarOtro: { mutationFn: api.cargarOtro, invalidate: [keys.staging()] },
  stagingCrear: { mutationFn: api.stagingCrear, invalidate: [keys.staging()] },
  stagingResolver: { mutationFn: api.stagingResolver, invalidate: [keys.staging()] },
  stagingIntegrar: { mutationFn: api.stagingIntegrar, invalidate: [keys.staging(), keys.inventario(), keys.inicio()] },
  stagingDescartar: { mutationFn: api.stagingDescartar, invalidate: [keys.staging()] },
  stagingRevertirNormalizacion: { mutationFn: api.stagingRevertirNormalizacion, invalidate: [keys.staging()] },
  preferenciaSet: { mutationFn: api.preferenciaSet, invalidate: [keys.preferencias()] },
  preferenciaBorrar: { mutationFn: api.preferenciaBorrar, invalidate: [keys.preferencias()] },
  perfilDescripcion: { mutationFn: api.perfilDescripcion, invalidate: [keys.perfil(), keys.perfiles()] },
  perfilFoto: { mutationFn: api.perfilFoto, invalidate: [keys.perfil(), keys.perfiles()] },
  perfilIdioma: { mutationFn: api.perfilIdioma, invalidate: [keys.perfil()] },
  solicitar: { mutationFn: api.solicitar, invalidate: [keys.solicitudes(), keys.notificaciones()] },
  solicitudResolver: { mutationFn: api.solicitudResolver, invalidate: [keys.solicitudes(), keys.notificaciones(), keys.adminMatriz()] },
  adminFeature: { mutationFn: api.adminFeature, invalidate: [keys.adminMatriz(), keys.notificaciones(), keys.perfiles()] },
  notificacionLeida: { mutationFn: api.notificacionLeida, invalidate: [keys.notificaciones()] },
  notificacionAvisar: { mutationFn: api.notificacionAvisar, invalidate: [keys.notificaciones()] },
  pisoReportar: { mutationFn: api.piso.reportar, invalidate: piso },
  pisoVisto: { mutationFn: api.piso.visto, invalidate: piso },
  pisoResolver: { mutationFn: api.piso.resolver, invalidate: piso },
  recordatorioCrear: { mutationFn: api.recordatorioCrear, invalidate: [keys.recordatorios()] },
  recordatorioCompletar: { mutationFn: api.recordatorioCompletar, invalidate: [keys.recordatorios()] },
  cuentaCobro: { mutationFn: api.cuentaCobro, invalidate: [keys.cuentas(), keys.cobranza()] },
  ventasValidar: { mutationFn: api.ventasValidar, invalidate: [keys.ventasValidacion(), keys.ventas()] },
  ventasDryrun: { mutationFn: api.ventasDryrun, invalidate: [] },
};

export function invalidationKeys(name) {
  const spec = MUTATIONS[name];
  if (!spec) throw new Error(`Unknown mutation: ${name}`);
  return spec.invalidate;
}

function specOf(name) {
  const spec = MUTATIONS[name];
  if (!spec) throw new Error(`Unknown mutation: ${name}`);
  return spec;
}

function callFn(fn, vars) {
  if (vars === undefined) return fn();
  if (Array.isArray(vars)) return fn(...vars);
  return fn(vars);
}

async function invalidateList(qc, list) {
  await Promise.all(list.map((queryKey) => qc.invalidateQueries({ queryKey })));
}

export async function runMutation(name, ...args) {
  const spec = specOf(name);
  const result = await spec.mutationFn(...args);
  await invalidateList(queryClient, spec.invalidate);
  return result;
}

export function useApiMutation(name, options = {}) {
  const spec = specOf(name);
  const qc = useQueryClient();
  const { onSuccess, ...rest } = options;
  return useMutation({
    mutationFn: (vars) => callFn(spec.mutationFn, vars),
    onSuccess: async (data, vars, ctx) => {
      await invalidateList(qc, spec.invalidate);
      await onSuccess?.(data, vars, ctx);
    },
    ...rest,
  });
}

export function invalidateShell() {
  return queryClient.invalidateQueries({ queryKey: keys.all() });
}

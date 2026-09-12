// GENERATED FILE - DO NOT EDIT.
// Source: backend/angela.py (TOOLS)
// Regenerate: py backend/scripts/generate_tool_types.py
//
// Python owns the tool schemas; these types exist so tool-call renderers get
// typed `args` and a schema change fails `npm run typecheck` instead of at
// runtime.

export interface ToolArgs {
  analisis_estacionalidad: Record<string, never>;
  analisis_push_pull: Record<string, never>;
  analisis_rotacion: Record<string, never>;
  aplicar_correccion_custom: {
    categoria: string;
    regla: string;
  };
  aplicar_correccion_en_lote: {
    categoria: string;
  };
  buscar_productos: {
    texto: string;
  };
  cancelar_mensaje: Record<string, never>;
  capital_recuperable: Record<string, never>;
  cerrar_caja: {
    declarado?: number;
  };
  consultar_compras: {
    proveedor?: string;
  };
  consultar_contexto_macro: {
    indicadores?: unknown[];
  };
  consultar_cruces: {
    id?: string;
  };
  consultar_deposito: {
    dias?: number;
    modo: string;
    producto?: string;
  };
  consultar_envios: {
    cliente?: string;
    modo: string;
  };
  consultar_evolucion: Record<string, never>;
  consultar_manual: {
    producto?: string;
    tema: string;
  };
  consultar_pronostico: Record<string, never>;
  consultar_serie: {
    agrupar?: string;
    categoria?: string;
    cliente?: string;
    comparar_categoria?: string;
    comparar_producto?: string;
    composicion?: boolean;
    desde?: string;
    fijar_en?: string;
    fuente: string;
    hasta?: string;
    metrica?: string;
    orden?: string;
    posicion?: string;
    producto?: string;
    tipo?: string;
    titulo?: string;
    top_n?: number;
    universo?: string;
  };
  crear_objetivo: {
    fecha?: string;
    nombre: string;
    responsable?: string;
  };
  crear_pestana: {
    pedido: string;
  };
  crear_recordatorio: {
    condicion?: Record<string, unknown>;
    responsable?: string;
    texto: string;
  };
  crear_widget: {
    datos_fuente: string;
    dias?: number;
    posicion?: string;
    seccion_destino?: string;
    tipo: string;
    titulo?: string;
  };
  cuentas_corrientes: {
    cliente?: string;
  };
  ejecutar_plan: Record<string, never>;
  estado_caja: Record<string, never>;
  generar_documento: {
    asunto?: string;
    destinatario?: string;
    proveedor?: string;
    tipo: string;
  };
  gestionar_modulo: {
    habilitar: boolean;
    modulo: string;
    usuario: string;
  };
  gestionar_widget: {
    que: string;
    tipo?: string;
    titulo: string;
  };
  leer_preferencias: Record<string, never>;
  listar_grupo: {
    grupo: string;
    limit?: number;
  };
  listar_prioridades: Record<string, never>;
  mensaje_cobro: {
    cliente: string;
  };
  mis_recordatorios: Record<string, never>;
  modificar_vista: {
    pedido: string;
  };
  navegar_a: {
    highlight?: string;
    section: string;
  };
  normalizaciones_staging: {
    accion: string;
    batch_id?: string;
  };
  objetivos_negocio: Record<string, never>;
  plata_en: {
    texto: string;
  };
  proponer_conocimiento: {
    ambito?: string;
    entidad?: string;
    nodo: string;
    texto: string;
  };
  proponer_correccion: {
    categoria: string;
  };
  proponer_plan: Record<string, never>;
  recordar: {
    clave: string;
    valor: string;
  };
  recordar_preferencia: {
    clave: string;
    valor: unknown;
  };
  recuperar: Record<string, never>;
  recuperar_contexto_negocio: Record<string, never>;
  reordenar_inicio: {
    orden?: unknown[];
    reset?: boolean;
  };
  resumen_negocio: Record<string, never>;
  revertir_version: {
    version_id: number;
  };
  scoring_credito: {
    cliente: string;
    monto?: number;
  };
  top_inmovilizado: {
    n?: number;
  };
}

export type ToolName = keyof ToolArgs;

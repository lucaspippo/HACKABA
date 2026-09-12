import {
  HandCoins, Moon, Tag, ShoppingCart, Megaphone, CalendarClock, Shield,
  Users, PackagePlus, Landmark, Warehouse, Eye,
} from "lucide-react";

// Closed catalog of verbs on Prioridades. Same keys as core/priorities
// ACTION_BY_ID + opportunity `tipo`. Chip color matches CardNegocio / Oportunidades.
export const ACCION = {
  cobrar: { icon: HandCoins, cls: "bg-rojo/10 text-rojo" },
  liquidar: { icon: Moon, cls: "bg-hielo/15 text-hielo" },
  ajustar_precio: { icon: Tag, cls: "bg-oro/15 text-oro-tinta" },
  comprar: { icon: ShoppingCart, cls: "bg-salvia/12 text-salvia" },
  vender: { icon: Megaphone, cls: "bg-salvia/12 text-salvia" },
  planificar: { icon: CalendarClock, cls: "bg-hielo/15 text-hielo" },
  diversificar: { icon: Shield, cls: "bg-oro/15 text-oro-tinta" },
  reclamar: { icon: Users, cls: "bg-hielo/15 text-hielo" },
  reponer: { icon: PackagePlus, cls: "bg-rojo/10 text-rojo" },
  pagar: { icon: Landmark, cls: "bg-oro/15 text-oro-tinta" },
  deposito: { icon: Warehouse, cls: "bg-oro/15 text-oro-tinta" },
  ver: { icon: Eye, cls: "bg-hielo/15 text-hielo" },
};

// Mirrors backend/core/priorities.py ACTION_BY_ID so chips/filters work
// even if a cached payload is missing `tipo`.
export const ACTION_BY_ID = {
  quiebre_inminente: "reponer",
  quiebre: "reponer",
  concentracion: "diversificar",
  caida_interanual: "diversificar",
  morosos: "cobrar",
  moroso_atraso: "cobrar",
  cobrar_morosos: "cobrar",
  pago_vencido: "pagar",
  pago_semana: "pagar",
  cheques: "ver",
  caja_inusual: "ver",
  dep_vencidos: "deposito",
  dep_porvencer: "deposito",
  dep_discrep: "deposito",
  venc_riesgo: "deposito",
  costo_viejo: "ajustar_precio",
  pico: "planificar",
  pre_pico: "planificar",
};

export function accionDe(item) {
  if (item?.id && ACTION_BY_ID[item.id]) return ACTION_BY_ID[item.id];
  if (item?.tipo && ACCION[item.tipo]) return item.tipo;
  if (item?.piso) return "reclamar";
  return "ver";
}

export function estiloAccion(item) {
  return ACCION[accionDe(item)] || ACCION.ver;
}

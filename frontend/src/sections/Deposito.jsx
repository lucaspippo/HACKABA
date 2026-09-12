import { useState } from "react";
import { keepPreviousData } from "@tanstack/react-query";
import { PackageX, AlertOctagon, Lock, Clock, Scale, MapPin, CalendarX, Check, Camera, Mic } from "lucide-react";
import AngelaSays from "../components/AngelaSays";
import AngelaMark from "../components/AngelaMark";
import FacturaFlow from "../components/FacturaFlow";
import VozAngela from "../components/VozAngela";
import { useApiMutation, useApiQuery } from "../lib/query";
import { toast } from "../lib/toastStore";
import { num, peso, pesoCorto, fecha } from "../lib/format";
import { useT, tDato } from "../lib/i18n";
import { useEmpresa } from "../lib/useEmpresa";

// P38·H — vencimientos que Ángela GESTIONA.
//
// Todos los ERP del rubro tienen alerta de vencimiento y casi nadie la usa,
// porque nadie carga la fecha — y porque "vence en 12 días" no decide nada.
// La pregunta real es otra: al ritmo al que vendés eso, ¿llegás? Ese cruce
// (lote × ritmo real de venta) es lo que se muestra acá, con la plata que
// se va a tirar si no se hace nada y una acción que espera el OK.
function Vencimientos({ onPreguntar }) {
  const t = useT();
  const { data: v, refetch } = useApiQuery("vencimientos", [30]);
  const gestionarMut = useApiMutation("vencimientoGestionar");
  const [hecho, setHecho] = useState(null);      // the persisted decision, from the server
  const [pospuesto, setPospuesto] = useState(false);
  const [trabajando, setTrabajando] = useState(false);

  if (!v || !v.disponible || (!v.lotes_en_riesgo && !(v.gestionados || []).length)) return null;

  // "Aprobar" persists the decision (core/vencimientos.gestionar): a row, an
  // audit event attributed to this person, and the lot leaves the list on
  // reload. It used to set local state and show a toast — nothing behind it.
  const decidir = async (tipo) => {
    const p = v.propuesta;
    if (!p || trabajando) return;
    setTrabajando(true);
    try {
      const r = await gestionarMut.mutateAsync([{
        codigo: p.codigo, lote: p.lote, tipo, cantidad: p.cantidad,
      }]);
      setHecho(r.gestion);
      toast(t("deposito.venc_prop_ok"));
      refetch();
    } catch {
      toast(t("deposito.venc_prop_error"), "error");
    }
    setTrabajando(false);
  };

  return (
    <div className="overflow-hidden rounded-[var(--radius-card)] border border-rojo/25 bg-crema sombra-papel">
      <div className="flex flex-wrap items-center gap-3 border-b border-linea bg-rojo/[0.04] px-4 py-3">
        <CalendarX size={18} className="text-rojo" />
        <div className="min-w-0 flex-1">
          <p className="font-display text-lg font-bold leading-tight">
            {t("deposito.venc_riesgo_titulo", { n: num(v.lotes_en_riesgo) })}
          </p>
          <p className="text-sm text-tinta-suave">{t("deposito.venc_riesgo_sub", { dias: v.ventana_dias })}</p>
        </div>
        <div className="shrink-0 text-right">
          <p className="plata text-xl font-medium text-rojo">{pesoCorto(v.total_en_riesgo)}</p>
          <p className="text-xs text-tinta-suave">{t("deposito.venc_riesgo_plata")}</p>
        </div>
      </div>
      {/* Seis columnas no entran en un celular: la tarjeta tiene
          `overflow-hidden`, así que la tabla quedaba CORTADA (la columna de la
          plata en riesgo, justo la que importa, no se veía). Ahora la tabla
          scrollea DENTRO de su tarjeta y no empuja la página. */}
      <div className="overflow-x-auto">
      <table className="w-full min-w-[34rem] text-sm">
        <thead>
          <tr className="border-b border-linea text-2xs uppercase tracking-wide text-tinta-suave">
            <th className="px-4 py-2 text-left font-semibold">{t("inventario.col_producto")}</th>
            <th className="px-3 py-2 text-right font-semibold">{t("deposito.venc_col_vence")}</th>
            <th className="px-3 py-2 text-right font-semibold">{t("deposito.venc_col_tenes")}</th>
            <th className="px-3 py-2 text-right font-semibold">{t("deposito.venc_col_ritmo")}</th>
            <th className="px-3 py-2 text-right font-semibold">{t("deposito.venc_col_sobra")}</th>
            <th className="px-4 py-2 text-right font-semibold">{t("deposito.venc_col_plata")}</th>
          </tr>
        </thead>
        <tbody>
          {v.items.slice(0, 8).map((i) => (
            <tr key={`${i.codigo}-${i.lote}`} className="border-b border-linea/60 last:border-0">
              <td className="px-4 py-2">
                <p className="font-medium">{i.producto}</p>
                <p className="text-xs text-tinta-suave">{i.lote} · {i.ubicacion}</p>
              </td>
              <td className={`plata px-3 py-2 text-right font-semibold ${i.dias_restantes <= 7 ? "text-rojo" : "text-oro-tinta"}`}>
                {i.dias_restantes === 0 ? t("deposito.venc_hoy") : t("deposito.venc_dias", { n: num(i.dias_restantes) })}
              </td>
              <td className="plata px-3 py-2 text-right">{num(Math.round(i.cantidad))}{i.por_peso ? " kg" : ""}</td>
              <td className="plata px-3 py-2 text-right text-tinta-suave">{t("deposito.venc_por_mes", { n: `${num(Math.round(i.ritmo_mes))}${i.por_peso ? " kg" : ""}` })}</td>
              <td className="plata px-3 py-2 text-right font-semibold text-rojo">{num(Math.round(i.sobrante))}{i.por_peso ? " kg" : ""}</td>
              <td className="plata px-4 py-2 text-right font-medium text-rojo">{peso(i.plata_en_riesgo)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
      {v.propuesta && !pospuesto && (
        <div className="border-t border-linea bg-violeta/[0.04] p-4">
          <div className="flex items-start gap-3">
            <AngelaMark size={30} />
            <div className="min-w-0 flex-1">
              <p className="font-display text-base font-bold leading-tight">{v.propuesta.titulo}</p>
              <p className="mt-0.5 text-sm leading-snug text-tinta">{v.propuesta.detalle}</p>
              {hecho ? (
                <p className="mt-2.5 flex items-center gap-1.5 text-sm font-semibold text-salvia">
                  <Check size={15} /> {t(hecho.tipo === "locales" ? "deposito.venc_hecho_locales" : "deposito.venc_hecho_promocion", { quien: hecho.actor })}
                </p>
              ) : (
                <div className="mt-2.5 flex flex-wrap gap-2">
                  <button onClick={() => decidir(v.propuesta.gestion || "promocion")} disabled={trabajando}
                    className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-sm font-semibold text-crema disabled:opacity-50">
                    <Check size={14} /> {t("cardneg.prop_aprobar")}
                  </button>
                  {v.propuesta.alternativa && (
                    <button onClick={() => decidir(v.propuesta.alternativa.gestion)} disabled={trabajando}
                      className="rounded-full border border-violeta/40 px-4 py-2 text-sm font-semibold text-violeta hover:border-violeta disabled:opacity-50">
                      {v.propuesta.alternativa.label}
                    </button>
                  )}
                  <button onClick={() => setPospuesto(true)}
                    className="rounded-full border border-linea px-4 py-2 text-sm font-semibold text-tinta-suave hover:text-tinta">
                    {t("cardneg.prop_despues")}
                  </button>
                  <button onClick={() => onPreguntar?.(t("deposito.venc_preguntar"))}
                    className="rounded-full border border-linea px-4 py-2 text-sm font-semibold text-tinta-suave hover:text-tinta">
                    {t("deposito.venc_otra_idea")}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      {(v.gestionados || []).length > 0 && (
        <ul className="border-t border-linea px-4 py-2.5 text-xs leading-snug text-tinta-suave">
          {v.gestionados.map((g) => (
            <li key={`${g.codigo}-${g.lote}`} className="flex items-center gap-1.5">
              <Check size={12} className="shrink-0 text-salvia" />
              {t(g.tipo === "locales" ? "deposito.venc_gest_locales" : "deposito.venc_gest_promocion",
                 { producto: g.producto, quien: g.actor, fecha: fecha(g.cuando) })}
            </li>
          ))}
        </ul>
      )}
      <p className="border-t border-linea px-4 py-2.5 text-xs leading-snug text-tinta-suave">
        {t("deposito.venc_nota_captura")}
      </p>
    </div>
  );
}

const AGING_LABEL = {
  "0_90": "deposito.aging_0_90",
  "91_180": "deposito.aging_91_180",
  "181_365": "deposito.aging_181_365",
  "365_plus": "deposito.aging_365",
};
const AGING_COLOR = {
  "0_90": "bg-hielo",
  "91_180": "bg-salvia",
  "181_365": "bg-oro",
  "365_plus": "bg-rojo",
};

function AgingMercaderia({ aging }) {
  const t = useT();
  const buckets = aging || [];
  const totalU = buckets.reduce((s, b) => s + (b.units || 0), 0);
  if (!totalU) return null;
  return (
    <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
      <p className="text-xs font-semibold uppercase tracking-wide text-tinta-suave">{t("deposito.aging_titulo")}</p>
      <p className="mt-0.5 text-sm text-tinta-suave">{t("deposito.aging_sub")}</p>
      <div className="mt-3 flex h-3 overflow-hidden rounded-full">
        {buckets.filter((b) => b.units > 0).map((b) => (
          <div key={b.bucket} className={AGING_COLOR[b.bucket]}
            style={{ width: `${(b.units / totalU) * 100}%` }}
            title={`${t(AGING_LABEL[b.bucket])}: ${num(b.units)}`} />
        ))}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-4">
        {buckets.map((b) => (
          <div key={b.bucket} className="flex items-baseline justify-between gap-2 text-sm">
            <span className="flex items-center gap-1.5 text-tinta-suave">
              <span className={`h-2 w-2 rounded-full ${AGING_COLOR[b.bucket]}`} />
              {t(AGING_LABEL[b.bucket])}
            </span>
            <span className="plata font-medium">{pesoCorto(b.inmovilizado)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Vista del encargado de depósito: lo físico. Los datos WMS del tenant
// (ubicaciones, lotes, vencimientos, discrepancias) + los problemas de
// catálogo que él resuelve en el galpón (fantasma / negativo). El panel
// "FIFO pendiente" sólo existe donde el dato todavía no está (piloto).
export default function Deposito({ data, onPreguntar, onNavegar }) {
  const t = useT();
  // El consejo de Ángela habla de LOS DATOS del tenant: cada tenant usa su
  // propia versión general del texto (P9·C1, M2), sin datos cross-tenant.
  const { esPiloto } = useEmpresa();
  const [grupo, setGrupo] = useState("fantasmas");
  const { data: grupoData, isError: errorCarga } = useApiQuery("grupo", [grupo, 60], {
    placeholderData: keepPreviousData,
  });
  const items = errorCarga ? [] : (grupoData?.items || []);
  const { data: wms, refetch: refetchDeposito } = useApiQuery("deposito");
  const [fotoAbierta, setFotoAbierta] = useState(false);
  const [vozAbierta, setVozAbierta] = useState(false);
  // Vencimientos/discrepancias y datos-a-corregir son dos tareas distintas
  // (qué se vence vs. qué está mal cargado): separadas en pestañas.
  const [tab, setTab] = useState("vencimientos");

  const a = data.alertas;
  const hayWms = wms?.resumen?.hay_datos;
  const tiles = hayWms ? [
    { icon: MapPin, valor: wms.resumen.ubicaciones, lk: "deposito.wms_ubic", color: "text-hielo" },
    { icon: PackageX, valor: wms.resumen.lotes, lk: "deposito.wms_lotes", color: "text-hielo" },
    { icon: Clock, valor: wms.resumen.por_vencer, lk: "deposito.wms_porvencer", color: wms.resumen.por_vencer ? "text-oro-tinta" : "text-tinta-suave" },
    { icon: Clock, valor: wms.resumen.vencidos, lk: "deposito.wms_vencidos", color: wms.resumen.vencidos ? "text-rojo" : "text-tinta-suave" },
    { icon: Scale, valor: wms.resumen.discrepancias, lk: "deposito.wms_discrep", color: wms.resumen.discrepancias ? "text-oro-tinta" : "text-tinta-suave", ir: "conciliacion" },
  ] : [];

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-bold">{t("deposito.titulo")}</h1>
          <p className="mt-1 text-sm text-tinta-suave">{t("deposito.subtitulo")}</p>
        </div>
        {/* La carga por foto vivía sólo en "Cargar datos" y en el chat. Pero el
            remito llega ACÁ: cuando baja el camión, el encargado está en esta
            pantalla, no en Sistema. Mismo componente, misma tubería. */}
        {/* `shrink-0` empujaba estos dos botones fuera de la pantalla en el
            celular (en inglés "Load delivery note by photo" no entra en 375px):
            sin él, la fila envuelve y ninguno queda cortado. */}
        <div className="flex flex-wrap gap-2">
          {/* Las dos formas de cargar con las manos ocupadas: la foto del
              remito y la voz. Ninguna de las dos pasa por el teclado. */}
          <button onClick={() => setVozAbierta(true)}
            className="inline-flex items-center gap-2 rounded-full border border-violeta/40
                       bg-violeta-suave px-4 py-2 text-sm font-semibold text-violeta-hondo
                       hover:bg-violeta/15">
            <Mic size={16} /> {t("deposito.decirle")}
          </button>
          <button onClick={() => setFotoAbierta(true)}
            className="inline-flex items-center gap-2 rounded-full bg-violeta px-4 py-2
                       text-sm font-semibold text-crema hover:bg-violeta-hondo">
            <Camera size={16} /> {t("deposito.cargar_remito")}
          </button>
        </div>
      </header>

      {vozAbierta && (
        <VozAngela rol="deposito" onCerrar={() => setVozAbierta(false)}
          onPreguntar={onPreguntar}
          onListo={() => { refetchDeposito(); }} />
      )}

      {fotoAbierta && (
        <FacturaFlow onCerrar={() => setFotoAbierta(false)}
          onCargado={() => { refetchDeposito(); }}
          onPreguntar={onPreguntar} />
      )}

      <AngelaSays tone="urgente">
        {t(esPiloto ? "deposito.angela" : "deposito.angela_demo")}
      </AngelaSays>

      {/* El estado del galpón según el WMS (solo si el dato existe) */}
      {hayWms && (
        // Son CINCO tiles: en el celular la grilla de 2 columnas dejaba al
        // último ("Diferencias") solo y a media caja, con un hueco al lado —
        // se leía como un error de layout. Ahora el impar ocupa la fila entera:
        // ninguna caja cortada, ningún hueco, y el número sigue siendo lo
        // primero que se ve. De sm en adelante, los cinco en una sola fila.
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {tiles.map((x, i) => {
            const Icon = x.icon;
            const imparFinal = i === tiles.length - 1 && tiles.length % 2 === 1;
            const Tag = x.ir ? "button" : "div";
            return (
              <Tag key={x.lk} type={x.ir ? "button" : undefined}
                onClick={x.ir ? () => onNavegar?.(x.ir) : undefined}
                className={`rounded-[var(--radius-card)] border border-linea bg-crema p-3.5 text-left sombra-papel ${
                  imparFinal ? "col-span-2 sm:col-span-1" : ""} ${x.ir ? "hover:border-violeta/40" : ""}`}>
                <Icon size={15} className={x.color} />
                <p className={`plata mt-1 text-xl font-medium leading-none ${x.color}`}>{num(x.valor)}</p>
                <p className="mt-1 text-xs leading-snug text-tinta-suave">{t(x.lk)}</p>
              </Tag>
            );
          })}
        </div>
      )}

      <div className="flex gap-1.5 border-b border-linea">
        {[["vencimientos", "deposito.tab_vencimientos"], ["corregir", "deposito.tab_corregir"]].map(([id, lk]) => (
          <button key={id} onClick={() => setTab(id)}
            className={`-mb-px border-b-2 px-1 py-2.5 text-sm font-semibold transition-colors ${
              tab === id ? "border-tinta text-tinta" : "border-transparent text-tinta-suave hover:text-tinta"
            }`}>
            {t(lk)}
          </button>
        ))}
      </div>

      {tab === "vencimientos" && <>
      {/* P38·H — el apartado de vencimientos GESTIONADOS: no "vence en 12 días"
          (eso no decide nada) sino "vence en 12 días y NO llegás a venderlo". */}
      <Vencimientos onPreguntar={onPreguntar} />
      <AgingMercaderia aging={wms?.aging || wms?.resumen?.aging} />

      {/* Vencidos + por vencer: mover primero (FIFO con datos reales) */}
      {hayWms && (wms.vencidos?.length > 0 || wms.vencimientos?.length > 0) && (
        <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema">
          <p className="border-b border-linea px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-tinta-suave">{t("deposito.venc_titulo")}</p>
          {[...(wms.vencidos || []), ...(wms.vencimientos || [])].slice(0, 12).map((f, i) => (
            <div key={`${f.codigo}-${f.lote}-${i}`} className="flex items-center justify-between gap-3 border-b border-linea px-4 py-2.5 last:border-0">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{f.producto}</p>
                <p className="text-xs text-tinta-suave">{f.lote} · {f.ubicacion} · {num(f.cantidad)} u.</p>
              </div>
              <span className={`shrink-0 text-sm font-semibold ${f.dias_vencido != null ? "text-rojo" : f.dias_restantes <= 3 ? "text-oro-tinta" : "text-tinta-suave"}`}>
                {f.dias_vencido != null
                  ? t("deposito.venc_vencido", { n: num(f.dias_vencido) })
                  : f.dias_restantes === 0
                  ? t("deposito.venc_hoy")
                  : t("deposito.venc_dias", { n: num(f.dias_restantes) })}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Físico vs sistema: lo que el conteo encontró distinto */}
      {hayWms && wms.discrepancias?.length > 0 && (
        <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema">
          <div className="flex items-center justify-between gap-3 border-b border-linea px-4 py-2.5">
            <p className="text-xs font-semibold uppercase tracking-wide text-tinta-suave">{t("deposito.disc_titulo")}</p>
            {onNavegar && (
              <button type="button" onClick={() => onNavegar("conciliacion")}
                className="text-xs font-semibold text-hielo">{t("nav.conciliacion")}</button>
            )}
          </div>
          {wms.discrepancias.slice(0, 8).map((d) => (
            <div key={d.codigo} className="border-b border-linea last:border-0">
              <button type="button" onClick={() => onNavegar?.("conciliacion")}
                className="flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left hover:bg-papel">
                <p className="min-w-0 flex-1 truncate text-sm font-medium">{d.descripcion}</p>
                <span className="plata shrink-0 text-sm text-tinta-suave">{num(d.stock_contable)} → {num(d.stock_fisico)}</span>
                <span className={`plata shrink-0 text-sm font-semibold ${d.diferencia < 0 ? "text-rojo" : "text-salvia"}`}>
                  {d.diferencia > 0 ? "+" : ""}{num(d.diferencia)}
                </span>
              </button>
              {/* C7 — LA DIFERENCIA LLEGA CON LA EXPLICACIÓN PUESTA.
                  El ERP dice "faltan 6,5"; el equipo ya había dicho por qué, el
                  mismo día y desde dos canales distintos. Sin esto, el que la
                  mira manda a recontar — o ajusta el stock por un faltante que
                  no existe. La nota no decide: es contexto para el que decide,
                  y por eso NO saca la diferencia de la lista. */}
              {d.notas?.length > 0 && (
                <div className="border-t border-linea/60 bg-violeta/[0.04] px-4 py-2.5">
                  <p className="text-2xs font-semibold uppercase tracking-wide text-violeta-hondo">
                    {t("deposito.disc_explica", { n: d.notas.length })}
                  </p>
                  {d.notas.map((n) => (
                    <p key={n.id} className="mt-1 text-xs leading-snug text-tinta-suave">
                      <b className="text-tinta">{n.autor}</b> · {n.fecha} · «{tDato(n.texto, n.texto_en)}»
                    </p>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* FIFO / vencimientos: el placeholder sólo donde el dato NO está (piloto).
          P32·1 — solo cuando la respuesta YA llegó (wms): sin esto flasheaba el
          placeholder mientras cargaba (wms=null → !hayWms=true). */}
      {wms && !hayWms && (
        <div className="rounded-[var(--radius-card)] border border-dashed border-linea bg-papel-hondo/40 p-4">
          <div className="flex items-center gap-2 text-tinta-suave">
            <Lock size={15} />
            <p className="text-sm font-semibold">{t("deposito.fifo_titulo")}</p>
          </div>
          <p className="mt-1.5 text-sm leading-snug text-tinta-suave">
            {t("deposito.fifo_detalle")}
          </p>
        </div>
      )}
      </>}

      {tab === "corregir" && <>
      <div className="grid grid-cols-2 gap-3">
        <button
          onClick={() => setGrupo("fantasmas")}
          className={`rounded-[var(--radius-card)] border p-4 text-left ${grupo === "fantasmas" ? "border-rojo bg-rojo/[0.04]" : "border-linea bg-crema"}`}
        >
          <PackageX size={18} className="text-rojo" />
          <p className="plata mt-1.5 text-2xl font-medium">{num(a.fantasmas.cantidad)}</p>
          <p className="text-sm text-tinta-suave">{t("deposito.fantasmas")}</p>
        </button>
        <button
          onClick={() => setGrupo("negativos")}
          className={`rounded-[var(--radius-card)] border p-4 text-left ${grupo === "negativos" ? "border-rojo bg-rojo/[0.04]" : "border-linea bg-crema"}`}
        >
          <AlertOctagon size={18} className="text-rojo" />
          <p className="plata mt-1.5 text-2xl font-medium">{num(a.negativos.cantidad)}</p>
          <p className="text-sm text-tinta-suave">{t("deposito.negativos")}</p>
        </button>
      </div>

      <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema">
        {errorCarga && (
          <p className="p-4 text-sm text-tinta-suave">{t("deposito.error_carga")}</p>
        )}
        {items.map((p, i) => (
          <div key={`${p.codigo}-${i}`} className="flex items-center justify-between gap-3 border-b border-linea px-4 py-2.5 last:border-0">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{p.descripcion}</p>
              <p className="text-xs text-tinta-suave">{t("deposito.cod", { codigo: p.codigo })}</p>
            </div>
            <span className={`plata shrink-0 text-sm font-medium ${grupo === "negativos" ? "text-rojo" : "text-tinta-suave"}`}>
              {t("deposito.unidades", { n: num(p.stock) })}
            </span>
          </div>
        ))}
      </div>
      </>}
    </div>
  );
}

import { useEffect, useState } from "react";
import { PackageX, AlertOctagon, Lock, Clock, Scale, MapPin, CalendarX, Check, Camera, Mic } from "lucide-react";
import AngelaSays from "../components/AngelaSays";
import AngelaMark from "../components/AngelaMark";
import FacturaFlow from "../components/FacturaFlow";
import VozAngela from "../components/VozAngela";
import { api } from "../lib/api";
import { toast } from "../lib/toastStore";
import { num, peso, pesoCorto, fecha } from "../lib/format";
import { useT } from "../lib/i18n";
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
  const [v, setV] = useState(null);
  const [hecho, setHecho] = useState(false);
  const [pospuesto, setPospuesto] = useState(false);

  useEffect(() => { api.vencimientos(30).then(setV).catch(() => setV(false)); }, []);
  if (!v || !v.disponible || !v.lotes_en_riesgo) return null;

  const aprobar = () => { setHecho(true); toast(t("deposito.venc_prop_ok")); };

  return (
    <div className="overflow-hidden rounded-[var(--radius-card)] border border-rojo/25 bg-crema sombra-papel">
      <div className="flex flex-wrap items-center gap-3 border-b border-linea bg-rojo/[0.04] px-4 py-3">
        <CalendarX size={18} className="text-rojo" />
        <div className="min-w-0 flex-1">
          <p className="font-display text-[1.05rem] font-bold leading-tight">
            {t("deposito.venc_riesgo_titulo", { n: num(v.lotes_en_riesgo) })}
          </p>
          <p className="text-[0.82rem] text-tinta-suave">{t("deposito.venc_riesgo_sub", { dias: v.ventana_dias })}</p>
        </div>
        <div className="shrink-0 text-right">
          <p className="plata text-xl font-medium text-rojo">{pesoCorto(v.total_en_riesgo)}</p>
          <p className="text-[0.7rem] text-tinta-suave">{t("deposito.venc_riesgo_plata")}</p>
        </div>
      </div>
      {/* Seis columnas no entran en un celular: la tarjeta tiene
          `overflow-hidden`, así que la tabla quedaba CORTADA (la columna de la
          plata en riesgo, justo la que importa, no se veía). Ahora la tabla
          scrollea DENTRO de su tarjeta y no empuja la página. */}
      <div className="overflow-x-auto">
      <table className="w-full min-w-[34rem] text-[0.85rem]">
        <thead>
          <tr className="border-b border-linea text-[0.68rem] uppercase tracking-wide text-tinta-suave">
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
                <p className="text-[0.72rem] text-tinta-suave">{i.lote} · {i.ubicacion}</p>
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
              <p className="font-display text-[0.98rem] font-bold leading-tight">{v.propuesta.titulo}</p>
              <p className="mt-0.5 text-[0.86rem] leading-snug text-tinta">{v.propuesta.detalle}</p>
              {hecho ? (
                <p className="mt-2.5 flex items-center gap-1.5 text-[0.85rem] font-semibold text-salvia">
                  <Check size={15} /> {t("deposito.venc_prop_ok")}
                </p>
              ) : (
                <div className="mt-2.5 flex flex-wrap gap-2">
                  <button onClick={aprobar}
                    className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-[0.84rem] font-semibold text-crema">
                    <Check size={14} /> {t("cardneg.prop_aprobar")}
                  </button>
                  <button onClick={() => setPospuesto(true)}
                    className="rounded-full border border-linea px-4 py-2 text-[0.84rem] font-semibold text-tinta-suave hover:text-tinta">
                    {t("cardneg.prop_despues")}
                  </button>
                  <button onClick={() => onPreguntar?.(t("deposito.venc_preguntar"))}
                    className="rounded-full border border-linea px-4 py-2 text-[0.84rem] font-semibold text-tinta-suave hover:text-tinta">
                    {t("deposito.venc_otra_idea")}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      <p className="border-t border-linea px-4 py-2.5 text-[0.76rem] leading-snug text-tinta-suave">
        {t("deposito.venc_nota_captura")}
      </p>
    </div>
  );
}

// Vista del encargado de depósito: lo físico. Los datos WMS del tenant
// (ubicaciones, lotes, vencimientos, discrepancias) + los problemas de
// catálogo que él resuelve en el galpón (fantasma / negativo). El panel
// "FIFO pendiente" sólo existe donde el dato todavía no está (piloto).
export default function Deposito({ data, onPreguntar }) {
  const t = useT();
  // El consejo de Ángela habla de LOS DATOS del tenant: cada tenant usa su
  // propia versión general del texto (P9·C1, M2), sin datos cross-tenant.
  const { esPiloto } = useEmpresa();
  const [grupo, setGrupo] = useState("fantasmas");
  const [items, setItems] = useState([]);
  const [errorCarga, setErrorCarga] = useState(false);
  const [wms, setWms] = useState(null);
  const [fotoAbierta, setFotoAbierta] = useState(false);
  const [vozAbierta, setVozAbierta] = useState(false);

  useEffect(() => {
    setErrorCarga(false);
    // Con .catch y feedback: sin esto, un fallo dejaba la lista vacía y muda (M14).
    api.grupo(grupo, 60)
      .then((r) => setItems(r.items))
      .catch(() => { setItems([]); setErrorCarga(true); });
  }, [grupo]);
  useEffect(() => {
    api.deposito().then(setWms).catch(() => {});
  }, []);

  const a = data.alertas;
  const hayWms = wms?.resumen?.hay_datos;
  const tiles = hayWms ? [
    { icon: MapPin, valor: wms.resumen.ubicaciones, lk: "deposito.wms_ubic", color: "text-hielo" },
    { icon: PackageX, valor: wms.resumen.lotes, lk: "deposito.wms_lotes", color: "text-hielo" },
    { icon: Clock, valor: wms.resumen.por_vencer, lk: "deposito.wms_porvencer", color: wms.resumen.por_vencer ? "text-oro-tinta" : "text-tinta-suave" },
    { icon: Clock, valor: wms.resumen.vencidos, lk: "deposito.wms_vencidos", color: wms.resumen.vencidos ? "text-rojo" : "text-tinta-suave" },
    { icon: Scale, valor: wms.resumen.discrepancias, lk: "deposito.wms_discrep", color: wms.resumen.discrepancias ? "text-oro-tinta" : "text-tinta-suave" },
  ] : [];

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-bold">{t("deposito.titulo")}</h1>
          <p className="mt-1 text-[0.9rem] text-tinta-suave">{t("deposito.subtitulo")}</p>
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
                       bg-violeta-suave px-4 py-2 text-[0.86rem] font-semibold text-violeta-hondo
                       hover:bg-violeta/15">
            <Mic size={16} /> {t("deposito.decirle")}
          </button>
          <button onClick={() => setFotoAbierta(true)}
            className="inline-flex items-center gap-2 rounded-full bg-violeta px-4 py-2
                       text-[0.86rem] font-semibold text-crema hover:bg-violeta-hondo">
            <Camera size={16} /> {t("deposito.cargar_remito")}
          </button>
        </div>
      </header>

      {vozAbierta && (
        <VozAngela rol="deposito" onCerrar={() => setVozAbierta(false)}
          onPreguntar={onPreguntar}
          onListo={() => { api.deposito().then(setWms).catch(() => {}); }} />
      )}

      {fotoAbierta && (
        <FacturaFlow onCerrar={() => setFotoAbierta(false)}
          onCargado={() => { api.deposito().then(setWms).catch(() => {}); }}
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
            return (
              <div key={x.lk}
                className={`rounded-[var(--radius-card)] border border-linea bg-crema p-3.5 sombra-papel ${
                  imparFinal ? "col-span-2 sm:col-span-1" : ""}`}>
                <Icon size={15} className={x.color} />
                <p className={`plata mt-1 text-xl font-medium leading-none ${x.color}`}>{num(x.valor)}</p>
                <p className="mt-1 text-[0.76rem] leading-snug text-tinta-suave">{t(x.lk)}</p>
              </div>
            );
          })}
        </div>
      )}

      {/* P38·H — el apartado de vencimientos GESTIONADOS: no "vence en 12 días"
          (eso no decide nada) sino "vence en 12 días y NO llegás a venderlo". */}
      <Vencimientos onPreguntar={onPreguntar} />

      {/* Vencidos + por vencer: mover primero (FIFO con datos reales) */}
      {hayWms && (wms.vencidos?.length > 0 || wms.vencimientos?.length > 0) && (
        <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema">
          <p className="border-b border-linea px-4 py-2.5 text-[0.78rem] font-semibold uppercase tracking-wide text-tinta-suave">{t("deposito.venc_titulo")}</p>
          {[...(wms.vencidos || []), ...(wms.vencimientos || [])].slice(0, 12).map((f, i) => (
            <div key={`${f.codigo}-${f.lote}-${i}`} className="flex items-center justify-between gap-3 border-b border-linea px-4 py-2.5 last:border-0">
              <div className="min-w-0">
                <p className="truncate text-[0.88rem] font-medium">{f.producto}</p>
                <p className="text-[0.72rem] text-tinta-suave">{f.lote} · {f.ubicacion} · {num(f.cantidad)} u.</p>
              </div>
              <span className={`shrink-0 text-[0.8rem] font-semibold ${f.dias_vencido != null ? "text-rojo" : f.dias_restantes <= 3 ? "text-oro-tinta" : "text-tinta-suave"}`}>
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
          <p className="border-b border-linea px-4 py-2.5 text-[0.78rem] font-semibold uppercase tracking-wide text-tinta-suave">{t("deposito.disc_titulo")}</p>
          {wms.discrepancias.slice(0, 8).map((d) => (
            <div key={d.codigo} className="flex items-center justify-between gap-3 border-b border-linea px-4 py-2.5 last:border-0">
              <p className="min-w-0 flex-1 truncate text-[0.88rem] font-medium">{d.descripcion}</p>
              <span className="plata shrink-0 text-[0.82rem] text-tinta-suave">{num(d.stock_contable)} → {num(d.stock_fisico)}</span>
              <span className={`plata shrink-0 text-[0.84rem] font-semibold ${d.diferencia < 0 ? "text-rojo" : "text-salvia"}`}>
                {d.diferencia > 0 ? "+" : ""}{num(d.diferencia)}
              </span>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <button
          onClick={() => setGrupo("fantasmas")}
          className={`rounded-[var(--radius-card)] border p-4 text-left ${grupo === "fantasmas" ? "border-rojo bg-rojo/[0.04]" : "border-linea bg-crema"}`}
        >
          <PackageX size={18} className="text-rojo" />
          <p className="plata mt-1.5 text-2xl font-medium">{num(a.fantasmas.cantidad)}</p>
          <p className="text-[0.82rem] text-tinta-suave">{t("deposito.fantasmas")}</p>
        </button>
        <button
          onClick={() => setGrupo("negativos")}
          className={`rounded-[var(--radius-card)] border p-4 text-left ${grupo === "negativos" ? "border-rojo bg-rojo/[0.04]" : "border-linea bg-crema"}`}
        >
          <AlertOctagon size={18} className="text-rojo" />
          <p className="plata mt-1.5 text-2xl font-medium">{num(a.negativos.cantidad)}</p>
          <p className="text-[0.82rem] text-tinta-suave">{t("deposito.negativos")}</p>
        </button>
      </div>

      <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema">
        {errorCarga && (
          <p className="p-4 text-[0.88rem] text-tinta-suave">{t("deposito.error_carga")}</p>
        )}
        {items.map((p, i) => (
          <div key={`${p.codigo}-${i}`} className="flex items-center justify-between gap-3 border-b border-linea px-4 py-2.5 last:border-0">
            <div className="min-w-0">
              <p className="truncate text-[0.88rem] font-medium">{p.descripcion}</p>
              <p className="text-[0.72rem] text-tinta-suave">{t("deposito.cod", { codigo: p.codigo })}</p>
            </div>
            <span className={`plata shrink-0 text-[0.86rem] font-medium ${grupo === "negativos" ? "text-rojo" : "text-tinta-suave"}`}>
              {t("deposito.unidades", { n: num(p.stock) })}
            </span>
          </div>
        ))}
      </div>

      {/* FIFO / vencimientos: el placeholder sólo donde el dato NO está (piloto).
          P32·1 — solo cuando la respuesta YA llegó (wms): sin esto flasheaba el
          placeholder mientras cargaba (wms=null → !hayWms=true). */}
      {wms && !hayWms && (
        <div className="rounded-[var(--radius-card)] border border-dashed border-linea bg-papel-hondo/40 p-4">
          <div className="flex items-center gap-2 text-tinta-suave">
            <Lock size={15} />
            <p className="text-[0.9rem] font-semibold">{t("deposito.fifo_titulo")}</p>
          </div>
          <p className="mt-1.5 text-[0.84rem] leading-snug text-tinta-suave">
            {t("deposito.fifo_detalle")}
          </p>
        </div>
      )}
    </div>
  );
}

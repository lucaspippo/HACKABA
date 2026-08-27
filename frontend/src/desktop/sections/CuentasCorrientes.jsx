import { useEffect, useState } from "react";
import { HandCoins, Send, X, Check, FileText, AlertTriangle } from "lucide-react";
import AngelaMark from "../../components/AngelaMark";
import PanelDecision from "../../components/PanelDecision";
import { api } from "../../lib/api";
import Cargando from "../../components/Cargando";
import { peso, pesoCorto, num } from "../../lib/format";
import { useT } from "../../lib/i18n";

// Los KEYS del score vienen del backend; el label vive en el diccionario (lk).
const SCORE = {
  confiable: { lk: "cuentas.score_confiable", cls: "bg-salvia/15 text-salvia" },
  atencion: { lk: "cuentas.score_atencion", cls: "bg-oro/20 text-oro-tinta" },
  riesgoso: { lk: "cuentas.score_riesgoso", cls: "bg-rojo/12 text-rojo" },
};

// Plan 6: cuentas corrientes de clientes deudores, con scoring e IA.
// P44 — drill-through: cualquier pantalla que mencione un cliente (Cobranzas,
// el mapa de negocio) puede mandar acá con highlight=`cliente-${id}` y el
// modal de detalle se abre solo — el scroll/pulse ya lo hacía resaltarPorId
// via data-nav-id; esto agrega la mitad que faltaba (abrir el modal).
export default function CuentasCorrientes({ onPreguntar, highlight }) {
  const t = useT();
  const [clientes, setClientes] = useState(null);
  const [alertas, setAlertas] = useState({ cantidad: 0, impacto_pesos: 0 });
  const [error, setError] = useState(null);
  const [sel, setSel] = useState(null);

  useEffect(() => {
    api.cuentas().then((d) => { setClientes(d.clientes); setAlertas(d.alertas); }).catch(setError);
  }, []);

  useEffect(() => {
    if (!highlight?.startsWith("cliente-") || !clientes) return;
    const id = highlight.slice("cliente-".length);
    const c = clientes.find((x) => String(x.id) === id);
    if (c) setSel(c);
  }, [highlight, clientes]);

  if (!clientes) return <div className="pt-2"><Cargando error={error} /></div>;

  const peor = clientes.find((c) => c.en_mora);

  return (
    <div className="space-y-6">
      <header className="flex items-center gap-2">
        <HandCoins size={24} className="text-tinta-suave" />
        <div>
          <h1 className="font-display text-2xl font-bold leading-none">{t("cuentas.titulo")}</h1>
          <p className="mt-1 text-[0.9rem] text-tinta-suave">{t("cuentas.subtitulo")}</p>
        </div>
      </header>

      {/* Alerta proactiva de Ángela sobre el moroso más urgente */}
      {peor && (
        <div className="flex items-start gap-3 rounded-[var(--radius-card)] border border-rojo/25 bg-rojo/[0.04] p-5">
          <AngelaMark size={34} />
          <div className="flex-1">
            <p className="text-[1rem] leading-snug text-tinta">
              <b>{peor.nombre}</b> {t("cuentas.mora_lleva")} <b>{t("cuentas.mora_dias", { dias: peor.dias_sin_pagar })}</b> {t("cuentas.mora_sin_pagar")} <b className="plata">{peso(peor.saldo)}</b>.
              {peor.atraso_vs_promedio > 0 && <> {t("cuentas.mora_historico", { promedio: peor.promedio_pago_dias })} <b>{t("cuentas.mora_pct_tarde", { pct: peor.atraso_vs_promedio })}</b> {t("cuentas.mora_que_promedio")}</>}
            </p>
            <button onClick={() => setSel(peor)} className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-[0.85rem] font-semibold text-crema">
              <Send size={14} /> {t("cuentas.mandar_recordatorio")}
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Tarjeta label={t("cuentas.total_adeudado")} valor={pesoCorto(clientes.reduce((a, c) => a + c.saldo, 0))} acento />
        <Tarjeta label={t("cuentas.clientes_en_mora")} valor={num(alertas.cantidad)} />
        <Tarjeta label={t("cuentas.en_mora_pesos")} valor={pesoCorto(alertas.impacto_pesos)} />
      </div>

      <div className="space-y-2" data-nav-id="morosos">
        {clientes.map((c) => (
          <button key={c.id} data-nav-id={`cliente-${c.id}`} onClick={() => setSel(c)}
            className={`flex w-full items-center gap-4 rounded-[var(--radius-card)] border bg-crema p-4 text-left sombra-papel transition-colors hover:border-tinta/25 ${c.en_mora ? "border-rojo/30" : "border-linea"}`}>
            <div className="min-w-0 flex-1">
              <p className="font-semibold text-tinta">{c.nombre}</p>
              <p className="text-[0.82rem] text-tinta-suave">
                {c.saldo > 0 ? t("cuentas.fila_estado", { dias: c.dias_sin_pagar, plazo: c.plazo_dias }) : t("cuentas.al_dia")}
              </p>
            </div>
            <span className={`rounded-full px-2.5 py-0.5 text-[0.74rem] font-semibold ${SCORE[c.score].cls}`}>{t(SCORE[c.score].lk)}</span>
            <span className={`plata w-32 text-right text-[1.05rem] font-medium ${c.en_mora ? "text-rojo" : "text-tinta"}`}>{peso(c.saldo)}</span>
          </button>
        ))}
      </div>

      {sel && <DetalleCliente c={sel} onClose={() => setSel(null)} onPreguntar={onPreguntar} />}
    </div>
  );
}

function DetalleCliente({ c, onClose, onPreguntar }) {
  const t = useT();
  const [recordatorio, setRecordatorio] = useState(null);
  // P18·C: WhatsApp no está conectado — acá NO se finge un envío. La acción
  // real es COPIAR el mensaje para mandarlo por donde el dueño hable con el
  // cliente. Cuando el canal exista, este botón pasa a enviar de verdad.
  const [copiado, setCopiado] = useState(false);
  const copiarMensaje = async () => {
    try {
      await navigator.clipboard.writeText(recordatorio.mensaje);
      setCopiado(true);
    } catch {
      setCopiado(true); // el mensaje queda visible igual para copiar a mano
    }
  };

  const proponerRecordatorio = async () => {
    const r = await api.cuentaRecordatorio(c.id);  // vía api → lleva el token en el header
    setRecordatorio(r);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-tinta/40 p-4" onClick={onClose}>
      <div className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-[var(--radius-card)] border border-linea bg-crema p-6 sombra-papel" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between">
          <div>
            <h2 className="font-display text-xl font-bold">{c.nombre}</h2>
            <span className={`mt-1 inline-block rounded-full px-2.5 py-0.5 text-[0.74rem] font-semibold ${SCORE[c.score].cls}`}>{t(SCORE[c.score].lk)}</span>
            {/* P25·B3 — el PORQUÉ del score, de los MISMOS campos que el chip */}
            <p className="mt-1.5 max-w-sm text-[0.8rem] leading-snug text-tinta-suave">
              {c.en_mora
                ? t("cuentas.score_expl_mora", { dias: c.dias_sin_pagar, plazo: c.plazo_dias,
                    atraso: c.atraso_vs_promedio, prom: c.promedio_pago_dias })
                : t("cuentas.score_expl_ok", { prom: c.promedio_pago_dias, plazo: c.plazo_dias })}
            </p>
          </div>
          <button onClick={onClose} className="text-tinta-suave hover:text-tinta"><X size={20} /></button>
        </div>

        <div className="mt-4 grid grid-cols-3 gap-3">
          <Tarjeta label={t("cuentas.saldo")} valor={pesoCorto(c.saldo)} acento={c.en_mora} />
          <Tarjeta label={t("cuentas.dias_sin_pagar")} valor={num(c.dias_sin_pagar)} />
          <Tarjeta label={t("cuentas.disponible")} valor={pesoCorto(c.disponible)} />
        </div>

        <h3 className="mt-5 mb-2 text-[0.78rem] font-semibold uppercase tracking-wide text-tinta-suave">{t("cuentas.movimientos")}</h3>
        <div className="space-y-1.5">
          {c.movimientos?.length ? c.movimientos.map((m, i) => (
            <div key={i} className="flex justify-between border-b border-linea/60 py-1.5 text-[0.86rem]">
              <span className="text-tinta-suave">{m.fecha} · {m.tipo}</span>
              <span className="plata">{peso(m.monto)}</span>
            </div>
          )) : <p className="text-[0.86rem] text-tinta-suave">{t("cuentas.sin_movimientos")}</p>}
        </div>

        {/* Recordatorio de cobro propuesto por Ángela (sale por WhatsApp) —
            patrón de decisión unificado (P14): impacto = el saldo del cliente,
            y su score real como nivel de confianza, sin inventar nada. */}
        {recordatorio && (
          <PanelDecision
            className="mt-4"
            impacto={copiado ? null : c.saldo}
            extra={<span className={`rounded-full px-2.5 py-0.5 text-[0.72rem] font-semibold ${SCORE[c.score].cls}`}>{t(SCORE[c.score].lk)}</span>}
            acciones={copiado ? null : (
              <>
                <button onClick={copiarMensaje} className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-1.5 text-[0.84rem] font-semibold text-crema"><Send size={14} /> {t("cuentas.copiar_mensaje")}</button>
                <button onClick={() => setRecordatorio(null)} className="rounded-full border border-linea px-4 py-1.5 text-[0.84rem] font-semibold text-tinta-suave">{t("cuentas.cancelar")}</button>
              </>
            )}
          >
            <div className="flex items-center gap-2"><AngelaMark size={24} estado={copiado ? "idle" : "esperando"} /><span className="text-[0.78rem] font-semibold uppercase tracking-wide text-tinta-suave">{t("cuentas.mensaje_propuesto")}</span></div>
            <p className="mt-2 rounded-lg bg-papel-hondo/60 p-2.5 text-[0.88rem] italic text-tinta">"{recordatorio.mensaje}"</p>
            {copiado && (
              <p className="mt-2 inline-flex items-center gap-1.5 text-[0.84rem] font-semibold text-salvia"><Check size={15} /> {t("cuentas.mensaje_copiado")}</p>
            )}
          </PanelDecision>
        )}

        <div className="mt-5 flex flex-wrap gap-2 border-t border-linea pt-4">
          {c.saldo > 0 && !recordatorio && (
            <button onClick={proponerRecordatorio} className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-[0.85rem] font-semibold text-crema"><Send size={14} /> {t("cuentas.recordatorio_cobro")}</button>
          )}
          <button onClick={() => { onPreguntar?.(t("cuentas.enviar_estado", { nombre: c.nombre })); onClose(); }} className="inline-flex items-center gap-1.5 rounded-full border border-linea px-4 py-2 text-[0.85rem] font-semibold text-tinta-suave hover:text-tinta"><FileText size={14} /> {t("cuentas.estado_pdf")}</button>
        </div>
      </div>
    </div>
  );
}

function Tarjeta({ label, valor, acento }) {
  return (
    <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
      <p className={`plata text-xl font-medium ${acento ? "text-rojo" : "text-tinta"}`}>{valor}</p>
      <p className="text-[0.78rem] text-tinta-suave">{label}</p>
    </div>
  );
}

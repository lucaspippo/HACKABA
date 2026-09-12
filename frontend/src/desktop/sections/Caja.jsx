import { useState } from "react";
import { Wallet, Plus, Lock, FileDown, TrendingDown, TrendingUp } from "lucide-react";
import AngelaMark from "../../components/AngelaMark";
import { api } from "../../lib/api";
import { toast } from "../../lib/toastStore";
import { peso, pesoCorto, num, fecha } from "../../lib/format";
import { useT } from "../../lib/i18n";
import { useApiMutation, useApiQuery } from "../../lib/query";

// P38·E — el reporte que hoy hace una persona a mano.
//
// El caso real de una distribuidora con bocas propias: una empleada imputa
// TODOS los cierres diarios de cada local a un Excel y arma el comparativo que
// el dueño pide cada 4-5 días. Los cierres YA están cargados: el comparativo
// es una resta. Ángela lo tiene hecho antes de que se lo pidan, y lo deja en
// PDF si el dueño lo quiere mandar.
function ReporteCierres() {
  const t = useT();
  const { data: r } = useApiQuery("cierresLocales", [7]);
  const [bajando, setBajando] = useState(false);

  if (!r) return null;   // sin locales propios (el piloto) la card no existe

  const pdf = async () => {
    setBajando(true);
    try {
      const doc = await api.documento("reporte_cierres");
      const blob = await api.documentoPdf(doc);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `reporte-cierres-${r.desde}_${r.hasta}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast(t("caja.rep_pdf_listo"));
    } catch { toast(t("caja.rep_pdf_error")); }
    setBajando(false);
  };

  const Var = ({ v }) => {
    if (v == null) return <span className="text-tinta-suave">—</span>;
    const Icon = v >= 0 ? TrendingUp : TrendingDown;
    return (
      <span className={`plata inline-flex items-center gap-1 font-semibold ${v >= 0 ? "text-salvia" : "text-rojo"}`}>
        <Icon size={13} />{v > 0 ? "+" : ""}{v}%
      </span>
    );
  };

  return (
    <div className="flex items-start gap-3 rounded-[var(--radius-card)] border border-violeta/15 bg-violeta/[0.04] p-5">
      <AngelaMark size={38} />
      <div className="min-w-0 flex-1">
        <p className="text-base leading-snug text-tinta">
          {t("caja.rep_intro", { dias: r.dias })}{" "}
          {r.mejor && r.peor && r.mejor.local !== r.peor.local && (
            <>{t("caja.rep_mejor", { local: r.mejor.local, pct: `${r.mejor.variacion_pct > 0 ? "+" : ""}${r.mejor.variacion_pct}%` })}{" "}
              {t("caja.rep_peor", { local: r.peor.local, pct: `${r.peor.variacion_pct}%` })}</>
          )}
        </p>
        <div className="mt-3 overflow-hidden rounded-xl border border-linea bg-crema">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-linea text-xs uppercase tracking-wide text-tinta-suave">
                <th className="px-3 py-2 text-left font-semibold">{t("caja.rep_col_local")}</th>
                <th className="px-3 py-2 text-right font-semibold">{t("caja.rep_col_actual")}</th>
                <th className="px-3 py-2 text-right font-semibold">{t("caja.rep_col_previo")}</th>
                <th className="px-3 py-2 text-right font-semibold">{t("caja.rep_col_var")}</th>
              </tr>
            </thead>
            <tbody>
              {r.locales.map((l) => (
                <tr key={l.local} className="border-b border-linea/60 last:border-0">
                  <td className="px-3 py-1.5 font-medium">{l.local}</td>
                  <td className="plata px-3 py-1.5 text-right">{pesoCorto(l.total)}</td>
                  <td className="plata px-3 py-1.5 text-right text-tinta-suave">{pesoCorto(l.total_previo)}</td>
                  <td className="px-3 py-1.5 text-right"><Var v={l.variacion_pct} /></td>
                </tr>
              ))}
              <tr className="bg-papel-hondo/50">
                <td className="px-3 py-1.5 font-semibold">{t("caja.rep_total")}</td>
                <td className="plata px-3 py-1.5 text-right font-semibold">{pesoCorto(r.total)}</td>
                <td className="plata px-3 py-1.5 text-right text-tinta-suave">{pesoCorto(r.total_previo)}</td>
                <td className="px-3 py-1.5 text-right"><Var v={r.variacion_pct} /></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button onClick={pdf} disabled={bajando}
            className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-sm font-semibold text-crema disabled:opacity-50">
            <FileDown size={14} /> {bajando ? t("caja.rep_armando") : t("caja.rep_pdf")}
          </button>
          <span className="text-xs leading-snug text-tinta-suave">{t("caja.rep_nota")}</span>
        </div>
      </div>
    </div>
  );
}

// Los KEYS de medios vienen del backend; acá solo el label key (lk) para traducir al pintar.
const MEDIO_LK = { efectivo: "caja.medio_efectivo", tarjeta: "caja.medio_tarjeta", transferencia: "caja.medio_transferencia", mercadopago: "caja.medio_mercadopago" };

// Plan 7: caja diaria simple. Apertura, movimientos por medio, cierre con diferencia.
export default function Caja() {
  const t = useT();
  const { data: caja } = useApiQuery("caja");
  const cajaMovimiento = useApiMutation("cajaMovimiento");
  const cajaCerrar = useApiMutation("cajaCerrar");
  const [cierre, setCierre] = useState(null);
  const [declarado, setDeclarado] = useState("");
  const [form, setForm] = useState({ tipo: "ingreso", medio: "efectivo", monto: "", detalle: "" });

  const agregar = async () => {
    if (!form.monto) return;
    await cajaMovimiento.mutateAsync([form.tipo, form.medio, Number(form.monto), form.detalle]);
    setForm({ ...form, monto: "", detalle: "" });
  };

  const cerrar = async () => {
    const r = await cajaCerrar.mutateAsync(declarado ? Number(declarado) : null);
    setCierre(r);
  };

  if (caja == null) return <p className="text-sm text-tinta-suave">{t("caja.cargando")}</p>;
  const tot = caja.totales;

  return (
    <div className="space-y-6">
      <header className="flex items-center gap-2">
        <Wallet size={24} className="text-tinta-suave" />
        <div>
          <h1 className="font-display text-2xl font-bold leading-none">{t("caja.titulo")}</h1>
          <p className="mt-1 text-sm text-tinta-suave">{fecha(caja.fecha)} · {caja.abierta ? t("caja.abierta") : t("caja.cerrada")}</p>
        </div>
      </header>

      <ReporteCierres />

      {cierre && (
        <div className="flex items-start gap-3 rounded-[var(--radius-card)] border border-hielo/25 bg-hielo-claro p-5">
          <AngelaMark size={32} />
          <div>
            <p className="text-base text-tinta">{t("caja.cierre_total")} <b className="plata">{peso(cierre.total)}</b>
              {cierre.diferencia ? <> · {t("caja.cierre_diferencia")} <b className="plata text-rojo">{peso(cierre.diferencia)}</b></> : <> · {t("caja.cierre_sin_diferencia")}</>}.</p>
            {cierre.nota_angela && <p className="mt-1 text-sm text-tinta-suave">{cierre.nota_angela}</p>}
          </div>
        </div>
      )}

      {/* Total y por medio */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-5">
        <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel sm:col-span-1">
          <p className="plata text-2xl font-medium text-hielo">{pesoCorto(tot.total)}</p>
          <p className="text-xs text-tinta-suave">{t("caja.en_caja_ahora")}</p>
        </div>
        {caja.medios.map((mdio) => (
          <div key={mdio} className="rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
            <p className="plata text-lg font-medium text-tinta">{pesoCorto(tot.por_medio[mdio] || 0)}</p>
            <p className="text-xs text-tinta-suave">{t(MEDIO_LK[mdio])}</p>
          </div>
        ))}
      </div>

      {/* Cargar movimiento */}
      <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-5 sombra-papel">
        <h2 className="mb-3 font-display text-lg font-bold">{t("caja.cargar_movimiento")}</h2>
        <div className="flex flex-wrap items-end gap-2">
          <select value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })} className="rounded-full border border-linea bg-papel px-3 py-2 text-sm">
            <option value="ingreso">{t("caja.tipo_ingreso")}</option>
            <option value="egreso">{t("caja.tipo_egreso")}</option>
          </select>
          <select value={form.medio} onChange={(e) => setForm({ ...form, medio: e.target.value })} className="rounded-full border border-linea bg-papel px-3 py-2 text-sm">
            {caja.medios.map((mdio) => <option key={mdio} value={mdio}>{t(MEDIO_LK[mdio])}</option>)}
          </select>
          <input type="number" value={form.monto} onChange={(e) => setForm({ ...form, monto: e.target.value })} placeholder={t("caja.ph_monto")} className="w-32 rounded-full border border-linea bg-papel px-3 py-2 text-sm outline-none focus:border-tinta/40" />
          <input value={form.detalle} onChange={(e) => setForm({ ...form, detalle: e.target.value })} placeholder={t("caja.ph_detalle")} className="flex-1 rounded-full border border-linea bg-papel px-3 py-2 text-sm outline-none focus:border-tinta/40" />
          <button onClick={agregar} className="inline-flex items-center gap-1.5 rounded-full bg-tinta px-4 py-2 text-sm font-semibold text-crema"><Plus size={15} /> {t("caja.agregar")}</button>
        </div>
      </div>

      {/* Movimientos del día */}
      <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-5 sombra-papel">
        <h2 className="mb-2 font-display text-lg font-bold">{t("caja.movimientos_dia")}</h2>
        <div className="space-y-1">
          <div className="flex justify-between border-b border-linea/60 py-1.5 text-sm text-tinta-suave">
            <span>{t("caja.saldo_inicial")}</span><span className="plata">{peso(caja.saldo_inicial)}</span>
          </div>
          {caja.movimientos.map((m, i) => (
            <div key={i} className="flex items-center justify-between border-b border-linea/60 py-1.5 text-sm">
              <span className="text-tinta">{m.detalle || m.tipo} <span className="text-tinta-suave">· {t(MEDIO_LK[m.medio])}</span></span>
              <span className={`plata ${m.tipo === "egreso" ? "text-rojo" : "text-salvia"}`}>{m.tipo === "egreso" ? "−" : "+"}{peso(m.monto)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Cerrar caja */}
      <div className="flex flex-wrap items-center gap-2 rounded-[var(--radius-card)] border border-linea bg-papel-hondo/40 p-5">
        <span className="text-sm text-tinta-suave">{t("caja.cerrar_nota")}</span>
        <div className="ml-auto flex items-center gap-2">
          <input type="number" value={declarado} onChange={(e) => setDeclarado(e.target.value)} placeholder={t("caja.ph_declarado")} className="w-48 rounded-full border border-linea bg-crema px-3 py-2 text-sm outline-none focus:border-tinta/40" />
          <button onClick={cerrar} className="inline-flex items-center gap-1.5 rounded-full bg-tinta px-4 py-2 text-sm font-semibold text-crema"><Lock size={14} /> {t("caja.cerrar")}</button>
        </div>
      </div>

      {/* Historial */}
      {caja.historial?.length > 0 && (
        <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-5 sombra-papel">
          <h2 className="mb-2 font-display text-lg font-bold">{t("caja.cierres_anteriores")}</h2>
          <div className="space-y-1">
            {caja.historial.slice().reverse().map((h, i) => (
              <div key={i} className="flex justify-between border-b border-linea/60 py-1.5 text-sm">
                <span className="text-tinta-suave">{fecha(h.fecha)}</span>
                <span className="plata text-tinta">{peso(h.total)}{h.diferencia ? <span className="text-rojo"> ({peso(h.diferencia)})</span> : null}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

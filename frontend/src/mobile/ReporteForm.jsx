import { useEffect, useState } from "react";
import { X, Check, Loader2, Camera, ArrowRight } from "lucide-react";
import AngelaMark from "../components/AngelaMark";
import { CAMPOS_REPORTE } from "../lib/roles";
import { api } from "../lib/api";
import { toast } from "../lib/toastStore";
import { useT } from "../lib/i18n";

// P39·2/3 — el formulario con el que el empleado REPORTA un hecho del piso
// (faltante, conteo, entrega, reposición, pedido). Corto y de una mano: esta
// gente lo completa parada, con el celular.
//
// Lo que reporta NO mueve stock ni ERP — se dice en pantalla, no se sobreentiende.
// Entra al sistema atribuido a la persona, el dueño lo ve en su panel y Ángela
// lo cruza para proponerle una decisión (el reclamo al proveedor, por ejemplo).

// `destinoFijo` — cuando el destinatario NO sale del oficio sino de la ficha de
// quien reporta: la pregunta del que recién entró va a SU referente, y ése es un
// dato de su perfil, no del tipo de aviso. Se sigue mostrando y confirmando
// igual; lo único que cambia es de dónde salió la propuesta.
// `inicial` — valores ya puestos (el producto de la fila que tocó). Es la
// diferencia entre tocar un botón y escribir "JAMON COCIDO GUARANI (HORMA)"
// parado atrás del mostrador.
export default function ReporteForm({ tipo, onCerrar, onListo, destinoFijo, inicial }) {
  const t = useT();
  const campos = CAMPOS_REPORTE[tipo] || [];
  const [valores, setValores] = useState(() => ({
    ...Object.fromEntries(campos.map((c) => [c.id, c.tipo === "opciones" ? c.opciones[0].v : ""])),
    ...(inicial || {}),
  }));
  const [enviando, setEnviando] = useState(false);
  // P·círculo — A QUIÉN LE LLEGA. Nadie en la cámara de frío elige de una lista
  // de catorce nombres: Ángela propone por oficio y la persona confirma con un
  // toque. `null` mientras no contestó el backend; si no contesta, se manda
  // igual (el hecho vale más que el ruteo) y queda en el pozo del dueño.
  const [destino, setDestino] = useState(destinoFijo || null);
  useEffect(() => {
    if (destinoFijo) return;   // ya lo sabemos: no hay a quién preguntarle
    api.piso.destinatario(tipo).then((d) => setDestino(d.sugerido || null)).catch(() => {});
  }, [tipo, destinoFijo]);

  const falta = campos.some((c) => c.requerido && !String(valores[c.id] ?? "").trim());

  const enviar = async () => {
    setEnviando(true);
    try {
      const datos = {};
      for (const c of campos) {
        const v = valores[c.id];
        if (v === "" || v == null) continue;
        datos[c.id] = c.tipo === "numero" ? Number(v) : v;
      }
      await api.piso.reportar(tipo, datos, destino?.username);
      toast(t(`rol.reporte_ok_${tipo}`));
      onListo?.();
      onCerrar();
    } catch {
      toast(t("rol.reporte_error"), "error");
    }
    setEnviando(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-tinta/40 p-0 sm:items-center sm:p-4"
      onClick={onCerrar}>
      <div onClick={(e) => e.stopPropagation()}
        className="max-h-[88vh] w-full max-w-md overflow-y-auto rounded-t-[var(--radius-card)] border border-linea bg-crema p-5 pb-[max(1.25rem,env(safe-area-inset-bottom))] sombra-alta sm:rounded-[var(--radius-card)]">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <AngelaMark size={28} />
            <h2 className="font-display text-lg font-bold leading-tight">{t(`rol.reporte_t_${tipo}`)}</h2>
          </div>
          <button onClick={onCerrar} aria-label={t("common.cerrar")} className="text-tinta-suave hover:text-tinta"><X size={20} /></button>
        </div>
        <p className="mt-1.5 text-sm leading-snug text-tinta-suave">{t(`rol.reporte_sub_${tipo}`)}</p>

        <div className="mt-4 space-y-3">
          {campos.map((c) => (
            <div key={c.id}>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-tinta-suave">
                {t(c.lk)}{c.requerido && <span className="ml-1 text-rojo">*</span>}
              </label>
              {c.tipo === "foto" ? (
                // P41·4 — la prueba de la entrega: cámara del teléfono (capture
                // "environment" abre la trasera directo). Se manda como data-URL
                // y el backend la guarda como archivo.
                <div>
                  <label className="flex min-h-11 cursor-pointer items-center gap-2 rounded-xl border border-dashed border-violeta/40 bg-violeta/[0.04] px-3.5 py-2.5 text-sm font-semibold text-violeta">
                    <Camera size={16} />
                    {valores[c.id] ? t("rol.f_prueba_cambiar") : t("rol.f_prueba_sacar")}
                    <input type="file" accept="image/*" capture="environment" className="hidden"
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (!f) return;
                        if (f.size > 2_000_000) { toast(t("rol.f_prueba_pesada"), "error"); return; }
                        const rd = new FileReader();
                        rd.onload = () => setValores((v) => ({ ...v, [c.id]: rd.result }));
                        rd.readAsDataURL(f);
                      }} />
                  </label>
                  {valores[c.id] && (
                    <div className="mt-2 flex items-center gap-2">
                      <img src={valores[c.id]} alt="" className="h-16 w-16 rounded-lg object-cover" />
                      <button onClick={() => setValores((v) => ({ ...v, [c.id]: "" }))}
                        className="text-xs font-semibold text-tinta-suave hover:text-tinta">
                        {t("rol.f_prueba_quitar")}
                      </button>
                    </div>
                  )}
                </div>
              ) : c.tipo === "opciones" ? (
                <div className="flex flex-wrap gap-1.5">
                  {c.opciones.map((o) => (
                    <button key={o.v} onClick={() => setValores((v) => ({ ...v, [c.id]: o.v }))}
                      className={`min-h-9 rounded-full border px-3 py-1.5 text-sm font-semibold transition-colors ${
                        valores[c.id] === o.v ? "border-tinta bg-tinta text-crema"
                                              : "border-linea text-tinta-suave"}`}>
                      {t(o.lk)}
                    </button>
                  ))}
                </div>
              ) : (
                <input
                  type={c.tipo === "numero" ? "number" : "text"}
                  inputMode={c.tipo === "numero" ? "decimal" : undefined}
                  value={valores[c.id] ?? ""}
                  onChange={(e) => setValores((v) => ({ ...v, [c.id]: e.target.value }))}
                  className="min-h-11 w-full rounded-xl border border-linea bg-papel px-3.5 py-2.5 text-sm outline-none focus:border-tinta/40"
                />
              )}
            </div>
          ))}
        </div>

        {/* Ángela propone, la persona confirma. Nunca automático sin que se
            vea: si se equivoca y nadie lo nota, el aviso se muere en silencio
            y esta persona no vuelve a usar la app. */}
        {destino && (
          <div className="mt-4 rounded-xl border border-violeta/25 bg-violeta/[0.05] px-3.5 py-3">
            <p className="text-sm leading-snug text-tinta">
              {t("rol.reporte_destino", { nombre: destino.nombre })}
            </p>
            <p className="mt-0.5 text-xs text-tinta-suave">{destino.rol}</p>
          </div>
        )}

        <div className="mt-4 flex items-center gap-2">
          <button onClick={enviar} disabled={falta || enviando}
            className="inline-flex min-h-11 items-center gap-1.5 rounded-full bg-violeta px-4 py-2.5 text-sm font-semibold text-crema active:scale-95 disabled:opacity-40">
            {enviando ? <Loader2 size={15} className="animate-spin" /> : <Check size={15} />}
            {destino ? t("rol.reporte_enviar_a", { nombre: destino.nombre })
                     : t("rol.reporte_enviar")}
          </button>
          <button onClick={onCerrar}
            className="min-h-11 rounded-full border border-linea px-4 py-2.5 text-sm font-semibold text-tinta-suave">
            {t("rol.reporte_cancelar")}
          </button>
        </div>
        {/* La regla de la casa, dicha donde se aplica */}
        <p className="mt-3 rounded-xl bg-papel-hondo/60 px-3 py-2 text-xs leading-snug text-tinta-suave">
          {t("rol.reporte_nota")}
        </p>
      </div>
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import { Camera, Image as ImageIcon, UploadCloud, FileText, X, Check, ArrowRight, RotateCcw } from "lucide-react";
import AngelaMark from "./AngelaMark";
import PanelDecision from "./PanelDecision";
import { api } from "../lib/api";
import { angelaBus } from "../lib/angelaBus";
import { peso, fecha as fmtFecha, renderPartes } from "../lib/format";
import { useT } from "../lib/i18n";

// P10 — El flujo entero de "sacale una foto y decile que la cargue":
// elegir/sacar foto (o comprobante de muestra, solo demo) → subiendo → leyendo
// (visión real) → Ángela presenta lo extraído en una card EDITABLE con sus
// cruces → sí explícito → persistencia por los rieles → resultado + sync
// simulado declarado. Compartido por desktop (Cargar datos) y mobile (chat).

const TIPOS_OK = ["image/jpeg", "image/png", "image/webp"];
const MAX_BYTES = 5 * 1024 * 1024; // el copy dice 5 MB y ACÁ se valida de verdad

export default function FacturaFlow({ onCerrar, onCargado, onPreguntar, onAngelaAbrir }) {
  const t = useT();
  const [paso, setPaso] = useState("elegir");  // elegir|leyendo|confirmar|guardando|resultado|rechazo
  const [error, setError] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [lectura, setLectura] = useState(null);   // respuesta de /api/factura/leer
  const [ext, setExt] = useState(null);           // extracción EDITABLE
  const [resultado, setResultado] = useState(null);
  const [muestras, setMuestras] = useState(null); // null=no demo / lista
  const [verMuestras, setVerMuestras] = useState(false);
  // P38·G — el catálogo de pesables, para que la cantidad de un fiambre no sea
  // sólo un número: "36 → ≈5 hormas de 6,7 kg". El chofer y el depósito piensan
  // en piezas; la factura llega en kilos. Se muestran las dos.
  const [pesables, setPesables] = useState({});
  const fileRef = useRef(null);
  const camRef = useRef(null);

  useEffect(() => {
    // Los comprobantes de muestra existen SOLO en el tenant demo (404 en piloto).
    api.muestras().then((r) => setMuestras(r.muestras)).catch(() => setMuestras(null));
    api.articulos().then((r) => {
      const m = {};
      for (const p of r.items || []) {
        if (p.unidad_pricing === "kg" && p.peso_por_unidad) m[p.codigo] = p.peso_por_unidad;
      }
      setPesables(m);
    }).catch(() => {});
    return () => { if (previewUrl) URL.revokeObjectURL(previewUrl); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const procesarBlob = async (blob, mediaType) => {
    setError(null);
    if (!TIPOS_OK.includes(mediaType)) { setError(t("foto.err_tipo")); return; }
    if (blob.size > MAX_BYTES) { setError(t("foto.err_tamano")); return; }
    setPreviewUrl(URL.createObjectURL(blob));
    setPaso("leyendo");
    try {
      const b64 = await new Promise((res, rej) => {
        const r = new FileReader();
        r.onload = () => res(String(r.result).split(",")[1]);
        r.onerror = rej;
        r.readAsDataURL(blob);
      });
      const lec = await api.facturaLeer(b64, mediaType);
      if (lec.rechazo || lec.error) {
        setLectura(lec);
        setPaso("rechazo");
        return;
      }
      setLectura(lec);
      setExt(structuredClone(lec.extraccion));
      setPaso("confirmar");
    } catch {
      setLectura({ mensaje: t("foto.err_red") });
      setPaso("rechazo");
    }
  };

  const tomarArchivo = (f) => { if (f) procesarBlob(f, f.type); };

  const usarMuestra = async (m) => {
    setVerMuestras(false);
    try {
      const blob = await api.blob(m.url);   // misma secuencia visual, mismo pipeline
      await procesarBlob(blob, "image/png");
    } catch { setError(t("foto.err_red")); }
  };

  const confirmar = async () => {
    setPaso("guardando");
    try {
      const r = await api.facturaConfirmar(ext);
      setResultado(r);
      setPaso("resultado");
      if (r.ok) {
        onCargado?.();
        // B1: el análisis proactivo de Ángela entra al chat SIN que nadie
        // pregunte — el momento del producto. El TEXTO se arma acá con t():
        // el backend manda la decisión y los números, el idioma lo pone quien
        // dibuja (antes venía renderizado y salía en español sobre UI inglesa).
        const partes = renderPartes(r.mensaje_angela_partes);
        if (partes.length) {
          angelaBus.push(partes.join(" "));
          onAngelaAbrir?.();
        }
      }
    } catch {
      setError(t("foto.err_red"));
      setPaso("confirmar");
    }
  };

  const reiniciar = () => {
    setPaso("elegir"); setError(null); setLectura(null); setExt(null);
    setResultado(null);
    if (previewUrl) { URL.revokeObjectURL(previewUrl); setPreviewUrl(null); }
  };

  const nItems = ext?.items?.length || 0;
  const dudosos = (ext?.campos_dudosos?.length || 0) + (ext?.campos_ilegibles?.length || 0)
    + (ext?.items || []).filter((i) => i.confianza && i.confianza !== "leido").length;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-tinta/30 p-0 sm:items-center sm:p-6" onClick={onCerrar}>
      <div onClick={(e) => e.stopPropagation()}
        className="flex max-h-[92dvh] w-full max-w-2xl flex-col overflow-hidden rounded-t-[var(--radius-card)] border border-linea bg-papel sombra-alta sm:rounded-[var(--radius-card)]">
        <div className="flex items-center justify-between border-b border-linea bg-crema px-5 py-3">
          <h2 className="flex items-center gap-2 font-display text-[1.05rem] font-bold">
            <Camera size={18} className="text-violeta" /> {t("foto.titulo")}
          </h2>
          <button onClick={onCerrar} className="text-tinta-suave hover:text-tinta"><X size={18} /></button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-5">
          {/* PASO 1: entrada */}
          {paso === "elegir" && (
            <div className="space-y-3">
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => { e.preventDefault(); tomarArchivo(e.dataTransfer.files?.[0]); }}
                className="grid place-items-center rounded-[var(--radius-card)] border-2 border-dashed border-linea p-6 text-center"
              >
                <UploadCloud size={26} className="text-tinta-suave" />
                <p className="mt-2 text-[0.9rem] text-tinta-suave">{t("foto.arrastra")}</p>
                <p className="mt-1 text-[0.76rem] text-tinta-suave">{t("foto.limite")}</p>
              </div>
              <div className="grid gap-2 sm:grid-cols-3">
                <button onClick={() => camRef.current?.click()}
                  className="flex items-center justify-center gap-2 rounded-full bg-violeta px-4 py-2.5 text-[0.88rem] font-semibold text-crema">
                  <Camera size={16} /> {t("foto.sacar")}
                </button>
                <button onClick={() => fileRef.current?.click()}
                  className="flex items-center justify-center gap-2 rounded-full border border-linea bg-crema px-4 py-2.5 text-[0.88rem] font-semibold text-tinta">
                  <ImageIcon size={16} /> {t("foto.galeria")}
                </button>
                {muestras?.length > 0 && (
                  <button onClick={() => setVerMuestras((v) => !v)}
                    className="flex items-center justify-center gap-2 rounded-full border border-hielo/40 bg-hielo/[0.07] px-4 py-2.5 text-[0.88rem] font-semibold text-hielo">
                    <FileText size={16} /> {t("foto.muestra")}
                  </button>
                )}
              </div>
              <input ref={camRef} type="file" accept="image/*" capture="environment" className="hidden"
                onChange={(e) => tomarArchivo(e.target.files?.[0])} />
              <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden"
                onChange={(e) => tomarArchivo(e.target.files?.[0])} />
              {verMuestras && (
                <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema">
                  {muestras.map((m) => (
                    <button key={m.id} onClick={() => usarMuestra(m)}
                      className="block w-full border-b border-linea px-4 py-3 text-left last:border-0 hover:bg-papel-hondo/50">
                      <p className="text-[0.9rem] font-semibold text-tinta">{t(`muestras.${m.id}_t`)}</p>
                      <p className="mt-0.5 text-[0.8rem] leading-snug text-tinta-suave">{t(`muestras.${m.id}_d`)}</p>
                    </button>
                  ))}
                </div>
              )}
              {error && <p className="rounded-xl border border-oro/30 bg-oro/[0.08] px-3.5 py-2 text-[0.86rem] text-tinta">{error}</p>}
            </div>
          )}

          {/* PASO 2: subiendo → leyendo (visión real) */}
          {paso === "leyendo" && (
            <div className="flex flex-col items-center gap-4 py-8">
              {previewUrl && <img src={previewUrl} alt="" className="max-h-56 rounded-xl border border-linea object-contain" />}
              <div className="flex items-center gap-3">
                <AngelaMark size={30} estado="ejecutando" />
                <p className="text-[0.92rem] text-tinta-suave">{t("foto.leyendo")}</p>
              </div>
            </div>
          )}

          {/* Rechazo honesto de una línea (selfie/borrosa/sin visión) */}
          {paso === "rechazo" && (
            <div className="space-y-4 py-4">
              <div className="flex items-start gap-3">
                <AngelaMark size={32} />
                <p className="text-[0.95rem] leading-snug text-tinta">{lectura?.mensaje}</p>
              </div>
              <button onClick={reiniciar} className="inline-flex items-center gap-2 rounded-full border border-linea bg-crema px-4 py-2 text-[0.86rem] font-semibold text-tinta">
                <RotateCcw size={15} /> {t("foto.reintentar")}
              </button>
            </div>
          )}

          {/* PASO 3: Ángela presenta lo extraído — card EDITABLE + cruces */}
          {paso === "confirmar" && ext && (
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <AngelaMark size={32} estado="esperando" />
                <div className="text-[0.95rem] leading-snug text-tinta">
                  <p>{t("foto.angela_leyo", {
                    proveedor: ext.proveedor?.razon_social || "—",
                    tipo: t(`foto.tipo_${ext.tipo_comprobante}`),
                    numero: ext.numero || "s/n",
                    fecha: ext.fecha ? fmtFecha(ext.fecha) : "—",
                    n: nItems,
                    total: ext.total != null ? peso(ext.total) : t("foto.sin_precios"),
                  })}</p>
                  <CruceInfo cruce={lectura?.cruce} tipo={ext.tipo_comprobante} t={t} />
                  {(lectura?.chequeos?.alertas || []).map((a, i) => (
                    <p key={i} className="mt-1.5 rounded-lg border border-oro/40 bg-oro/[0.08] px-2.5 py-1.5 text-[0.86rem]">{a.detalle}</p>
                  ))}
                  {dudosos > 0 && (
                    <p className="mt-1.5 rounded-lg border border-oro/40 bg-oro/[0.08] px-2.5 py-1.5 text-[0.86rem]">
                      {t("foto.dudosos", { n: dudosos })}
                    </p>
                  )}
                </div>
              </div>

              <PanelDecision
                impacto={ext.total}
                acciones={
                  <>
                    <button onClick={confirmar}
                      className="inline-flex items-center gap-2 rounded-full bg-violeta px-5 py-2.5 text-[0.9rem] font-semibold text-crema">
                      <Check size={16} /> {t("foto.confirmar")}
                    </button>
                    <button onClick={reiniciar}
                      className="rounded-full border border-linea bg-crema px-4 py-2.5 text-[0.9rem] font-semibold text-tinta-suave">
                      {t("foto.cancelar")}
                    </button>
                  </>
                }
              >
                <p className="mb-2 text-[0.74rem] font-semibold uppercase tracking-wide text-tinta-suave">{t("foto.editar_hint")}</p>
                <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
                  <CampoEdit label={t("foto.f_proveedor")} valor={ext.proveedor?.razon_social || ""}
                    onChange={(v) => setExt({ ...ext, proveedor: { ...ext.proveedor, razon_social: v } })} ancho="col-span-2" />
                  <CampoEdit label={t("foto.f_numero")} valor={ext.numero || ""}
                    onChange={(v) => setExt({ ...ext, numero: v })} />
                  <CampoEdit label={t("foto.f_fecha")} valor={ext.fecha || ""}
                    onChange={(v) => setExt({ ...ext, fecha: v })} />
                </div>
                {ext.items?.length > 0 && (
                  <div className="mt-3 space-y-1.5">
                    {ext.items.map((it, i) => {
                      // P38·G — si es un pesable del catálogo, la misma cantidad
                      // dicha en piezas: en kilos entra, en piezas se baja.
                      const kgPieza = pesables[it.codigo];
                      const piezas = kgPieza && Number(it.cantidad)
                        ? Math.round(Number(it.cantidad) / kgPieza) : null;
                      return (
                      <div key={i} className={`flex items-center gap-2 rounded-lg px-2 py-1 ${it.confianza && it.confianza !== "leido" ? "bg-oro/[0.1]" : ""}`}>
                        {/* P22·A: en la lista de precios el CÓDIGO es editable
                            (el clásico código pisado se corrige acá mismo) */}
                        {ext.tipo_comprobante === "lista_precios" && (
                          <input value={it.codigo ?? ""} inputMode="numeric" aria-label={t("foto.f_codigo")}
                            onChange={(e) => cambiarItem(setExt, ext, i, "codigo", e.target.value)}
                            className="w-16 rounded-lg border border-linea bg-papel px-2 py-1 text-right text-[0.84rem]" />
                        )}
                        <span className="min-w-0 flex-1 truncate text-[0.84rem]">
                          {it.descripcion}
                          {piezas != null && (
                            <span className="ml-1.5 text-[0.72rem] text-tinta-suave">
                              {t("foto.f_piezas", { n: piezas, kg: kgPieza })}
                            </span>
                          )}
                          {/* El remito trae lote y vencimiento: se muestran acá
                              porque es lo que va a encender la alerta después */}
                          {it.vencimiento && (
                            <span className="ml-1.5 text-[0.72rem] text-tinta-suave">
                              {t("foto.f_lote", { lote: it.lote || "s/l",
                                                  vto: fmtFecha(it.vencimiento) })}
                            </span>
                          )}
                        </span>
                        {ext.tipo_comprobante !== "lista_precios" && (
                          <input value={it.cantidad ?? ""} inputMode="decimal" aria-label={t("foto.f_cant")}
                            onChange={(e) => cambiarItem(setExt, ext, i, "cantidad", e.target.value)}
                            className="w-16 rounded-lg border border-linea bg-papel px-2 py-1 text-right text-[0.84rem]" />
                        )}
                        {(ext.tipo_comprobante === "factura" || ext.tipo_comprobante === "lista_precios") && (
                          <input value={it.precio_unitario ?? ""} inputMode="decimal" aria-label={t("foto.f_precio")}
                            onChange={(e) => cambiarItem(setExt, ext, i, "precio_unitario", e.target.value)}
                            className="w-24 rounded-lg border border-linea bg-papel px-2 py-1 text-right text-[0.84rem]" />
                        )}
                      </div>
                      );
                    })}
                  </div>
                )}
                {ext.total != null && (
                  <div className="mt-3 flex items-center justify-end gap-2">
                    <span className="text-[0.82rem] font-semibold text-tinta-suave">{t("foto.f_total")}</span>
                    <input value={ext.total} inputMode="decimal"
                      onChange={(e) => setExt({ ...ext, total: Number(e.target.value) || 0 })}
                      className="plata w-36 rounded-lg border border-linea bg-papel px-2 py-1 text-right text-[0.9rem] font-medium" />
                  </div>
                )}
                {error && <p className="mt-3 rounded-xl border border-oro/30 bg-oro/[0.08] px-3.5 py-2 text-[0.86rem]">{error}</p>}
              </PanelDecision>
            </div>
          )}

          {paso === "guardando" && (
            <div className="flex items-center justify-center gap-3 py-10">
              <AngelaMark size={30} estado="ejecutando" />
              <p className="text-[0.92rem] text-tinta-suave">{t("foto.guardando")}</p>
            </div>
          )}

          {/* PASO 4: resultado + sync simulado DECLARADO */}
          {paso === "resultado" && resultado && (
            <div className="space-y-4 py-2">
              <div className="flex items-start gap-3">
                {resultado.ok
                  ? <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-salvia text-crema"><Check size={18} /></span>
                  : <AngelaMark size={32} />}
                <div className="text-[0.95rem] leading-snug text-tinta">
                  <ResultadoTexto r={resultado} t={t} />
                </div>
              </div>
              {resultado.ok && resultado.sync && (
                <p className="rounded-xl border border-hielo/30 bg-hielo/[0.06] px-3.5 py-2 text-[0.84rem] text-hielo">
                  {t(`foto.${resultado.sync.k || "sync_simulado"}`)}
                </p>
              )}
              {/* El SEGUNDO sí: faltó mercadería y Ángela propone reclamarla.
                  Propone — no lo dispara. El reclamo entra por el mismo riel
                  que usa el depósito a mano y sale agrupado en Equipo. */}
              {resultado.ok && resultado.reclamo_sugerido && (
                <Reclamo r={resultado.reclamo_sugerido} t={t} />
              )}
              <div className="flex flex-wrap gap-2">
                {resultado.ok && onPreguntar && (
                  <button onClick={() => { onPreguntar(t("foto.pregunta_sugerida")); onCerrar?.(); }}
                    className="inline-flex items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-[0.86rem] font-semibold text-crema">
                    {t("foto.preguntar")} <ArrowRight size={14} />
                  </button>
                )}
                <button onClick={reiniciar} className="rounded-full border border-linea bg-crema px-4 py-2 text-[0.86rem] font-semibold text-tinta-suave">
                  {t("foto.otro")}
                </button>
                <button onClick={onCerrar} className="rounded-full border border-linea bg-crema px-4 py-2 text-[0.86rem] font-semibold text-tinta-suave">
                  {t("foto.cerrar")}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function cambiarItem(setExt, ext, i, campo, valor) {
  const items = ext.items.map((it, j) => (j === i ? { ...it, [campo]: valor === "" ? null : Number(valor) } : it));
  setExt({ ...ext, items });
}

function CampoEdit({ label, valor, onChange, ancho = "" }) {
  return (
    <label className={`block ${ancho}`}>
      <span className="mb-0.5 block text-[0.72rem] font-semibold text-tinta-suave">{label}</span>
      <input value={valor} onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-linea bg-papel px-2 py-1.5 text-[0.86rem]" />
    </label>
  );
}

// Faltó mercadería contra la orden: el reclamo al proveedor, con el monto real
// (cantidad faltante × costo de catálogo — cuenta determinista, no estimada).
function Reclamo({ r, t }) {
  const [estado, setEstado] = useState("propuesto"); // propuesto|enviando|hecho|error
  const [msg, setMsg] = useState(null);

  const reclamar = async () => {
    setEstado("enviando");
    try {
      await api.remitoReclamar(r.proveedor, r.items, r.oc);
      // El texto se compone ACÁ y no se usa el del backend: el idioma del
      // perfil y el del chrome pueden estar desfasados (P31·4) y quedaba un
      // cartel en español sobre una UI en inglés.
      setMsg(t("foto.reclamo_ok", { n: r.items.length, proveedor: r.proveedor }));
      setEstado("hecho");
    } catch {
      setMsg(t("foto.err_red"));
      setEstado("error");
    }
  };

  if (estado === "hecho") {
    return (
      <p className="rounded-xl border border-salvia/30 bg-salvia/[0.07] px-3.5 py-2 text-[0.86rem] text-tinta">
        {msg}
      </p>
    );
  }
  return (
    <div className="rounded-xl border border-oro/30 bg-oro/[0.07] px-3.5 py-3">
      <p className="text-[0.9rem] font-semibold text-tinta">
        {t("foto.reclamo_titulo", { n: r.items.length, proveedor: r.proveedor })}
      </p>
      <ul className="mt-1.5 space-y-0.5">
        {r.items.map((it, i) => (
          <li key={i} className="flex items-baseline gap-2 text-[0.84rem] text-tinta-suave">
            <span className="min-w-0 flex-1 truncate">{it.producto}</span>
            <span className="plata shrink-0">
              {t("foto.reclamo_falta", { falta: it.falta, pedido: it.pedido })}
            </span>
            <span className="plata shrink-0 font-medium text-tinta">{peso(it.monto)}</span>
          </li>
        ))}
      </ul>
      <div className="mt-2.5 flex items-center gap-2">
        <button onClick={reclamar} disabled={estado === "enviando"}
          className="rounded-full bg-tinta px-4 py-1.5 text-[0.84rem] font-semibold text-crema disabled:opacity-50">
          {estado === "enviando" ? t("foto.guardando") : t("foto.reclamar")}
        </button>
        <button onClick={() => { setMsg(t("foto.reclamo_no")); setEstado("hecho"); }}
          className="rounded-full border border-linea bg-crema px-4 py-1.5 text-[0.84rem] font-semibold text-tinta-suave">
          {t("foto.reclamo_dejar")}
        </button>
        {estado === "error" && <span className="text-[0.82rem] text-rojo">{msg}</span>}
      </div>
    </div>
  );
}

// El criterio de Ángela: qué dice el cruce ANTES de confirmar.
function CruceInfo({ cruce, tipo, t }) {
  if (!cruce) return null;
  if (tipo === "remito") {
    if (!cruce.oc_encontrada) return <p className="mt-1.5 text-[0.88rem] text-tinta-suave">{t("foto.remito_sin_oc")}</p>;
    return (
      <div className="mt-1.5 text-[0.9rem]">
        <p>{t("foto.remito_oc", { oc: cruce.oc_encontrada.numero, n: cruce.coincidencias, m: cruce.total_items })}</p>
        {cruce.diferencias.map((d, i) => (
          <p key={i} className="mt-0.5 text-[0.86rem] text-oro-tinta">
            · {d.tipo === "cantidad"
              ? t("foto.dif_cantidad", { producto: d.producto, pedido: d.pedido, recibido: d.recibido })
              : d.tipo === "no_pedido"
                ? t("foto.dif_no_pedido", { producto: d.producto })
                : t("foto.dif_faltante", { producto: d.producto, pedido: d.pedido })}
          </p>
        ))}
        <p className="mt-1 font-semibold">{t("foto.remito_confirmar")}</p>
      </div>
    );
  }
  if (tipo === "factura" && cruce.remito_encontrado) {
    return (
      <p className="mt-1.5 text-[0.9rem]">
        {cruce.diferencias.length === 0
          ? t("foto.factura_cierra")
          : t("foto.factura_difiere", { n: cruce.diferencias.length })}
      </p>
    );
  }
  // P22·A — la lista de precios: el diff con criterio, ANTES del OK
  if (tipo === "lista_precios") {
    return (
      <div className="mt-1.5 text-[0.9rem]">
        <p>{t("foto.lista_resumen", { n: cruce.n, pct: cruce.promedio_pct ?? "—" })}</p>
        {(cruce.dudosos || []).map((d, i) => (
          <p key={i} className="mt-1 rounded-lg border border-oro/40 bg-oro/[0.08] px-2.5 py-1.5 text-[0.86rem]">
            {d.estado === "salto_sospechoso"
              ? t("foto.lista_salto", { producto: d.producto_catalogo, pct: d.pct, mediana: cruce.mediana_pct })
              : t("foto.lista_codigo", {
                  codigo: d.codigo, producto: d.producto_catalogo,
                  dice: d.descripcion_lista,
                  sugerido: d.sugerido ? t("foto.lista_sugerido", { producto: d.sugerido.producto, codigo: d.sugerido.codigo }) : "",
                })}
          </p>
        ))}
        <p className="mt-1.5 font-semibold">
          {t("foto.lista_pregunta", { limpios: cruce.limpios, k: (cruce.dudosos || []).length })}
        </p>
      </div>
    );
  }
  return null;
}

function ResultadoTexto({ r, t }) {
  if (!r.ok) return <p>{r.error}</p>;
  if (r.tipo === "remito") {
    return <p>
      {t("foto.res_remito", { n: r.items_al_stock })}
      {/* los lotes con vencimiento son media noticia: por eso se dicen */}
      {r.lotes_al_deposito > 0 && ` ${t("foto.deposito_lotes", { n: r.lotes_al_deposito })}.`}
      {r.sin_catalogo?.length > 0 && ` ${t("foto.res_sin_catalogo", { lista: r.sin_catalogo.join(", ") })}`}
    </p>;
  }
  if (r.tipo === "factura") {
    return <p>{t("foto.res_factura", { saldo: peso(r.saldo_proveedor), fecha: fmtFecha(r.vencimiento) })}</p>;
  }
  if (r.tipo === "recibo") {
    return <p>{t("foto.res_recibo", { cliente: r.cliente, antes: peso(r.saldo_antes), despues: peso(r.saldo_despues), scoring: r.scoring || "—" })}</p>;
  }
  if (r.tipo === "lista_precios") {
    // el resumen con los $ ya viene compuesto por el backend (mensaje_angela):
    // acá la versión corta con el efecto en cascada
    return <p>{t("foto.res_lista", {
      n: r.items,
      antes: r.margen_antes != null ? `${r.margen_antes}%` : "—",
      despues: r.margen_despues != null ? `${r.margen_despues}%` : "—",
      backup: r.version_backup,
    })}</p>;
  }
  return <p>{t("foto.res_generico")}</p>;
}

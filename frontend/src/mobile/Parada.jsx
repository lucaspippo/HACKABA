import { useEffect, useState } from "react";
import { MapPin, ChevronRight, Loader2, Clock, Sparkles } from "lucide-react";
import { api } from "../lib/api";
import { peso, num } from "../lib/format";
import { useT, useLang } from "../lib/i18n";

// C2 · LA PARADA ENRIQUECIDA — quién está parado frente a quién.
//
// El chofer mira esto parado, al sol, con el motor andando; el preventista lo
// mira entrando al local. Por eso es UNA parada por pantalla y no una lista de
// nueve: la lista no le sirve a ninguno de los dos, la parada de ahora sí.
//
// Tres preguntas, y las tres fuentes ya existían sueltas:
//   ¿debe?  ·  ¿alguien dijo algo?  ·  ¿compra algo de lo que se vence?
//
// Los montos vienen calculados del backend y acá sólo se renderizan
// (PRODUCT.md, The Counting Rule). No hay ningún total en esta pantalla: la
// suma por camión ya existe y es canónica.

function Bloque({ titulo, children, tono = "" }) {
  return (
    <section className="mt-4">
      <h2 className="mb-2 text-2xs font-semibold uppercase tracking-wide text-tinta-suave">{titulo}</h2>
      <div className={`rounded-[var(--radius-card)] border p-4 sombra-papel ${tono || "border-linea bg-crema"}`}>
        {children}
      </div>
    </section>
  );
}

export default function Parada({ transporte, onVolver }) {
  const t = useT();
  const lang = useLang();
  const [paradas, setParadas] = useState(null);
  const [i, setI] = useState(0);
  const [det, setDet] = useState(null);

  useEffect(() => {
    api.paradasProximas(transporte)
      .then((d) => setParadas(d.paradas || []))
      .catch(() => setParadas([]));
  }, [transporte]);

  const actual = paradas?.[i];
  useEffect(() => {
    if (!actual) return;
    setDet(null);
    api.parada(actual.cliente).then(setDet).catch(() => setDet({}));
  }, [actual?.cliente, lang]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!paradas) return <div className="py-10 text-center text-sm text-tinta-suave">
    <Loader2 size={18} className="mx-auto animate-spin" /></div>;

  if (!paradas.length) return (
    <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-6 text-center">
      <p className="text-sm text-tinta-suave">{t("parada.sin_paradas")}</p>
    </div>
  );

  const d = det?.deuda;

  return (
    <div className="pb-2">
      <p className="text-2xs font-semibold uppercase tracking-wide text-tinta-suave">
        {t("parada.contador", { n: i + 1, total: paradas.length })}
      </p>

      {/* La parada: quién y dónde, en el tamaño que se lee de un vistazo */}
      <div className="mt-1 rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
        <p className="font-display text-xl font-bold leading-tight">{actual.cliente}</p>
        <p className="mt-1 flex items-center gap-1.5 text-sm text-tinta-suave">
          <MapPin size={14} className="shrink-0" /> {actual.direccion}
        </p>
        <p className="mt-1 text-xs text-tinta-suave">
          <span className="plata">{actual.pedido}</span> · {actual.dia}
        </p>
      </div>

      {/* 1 · ¿debe? Con los DOS plazos: el del sistema y el de la casa. Sin la
          regla del dueño el número miente dos veces — marca en falso a quien
          tiene permiso, y no marca a quien lo pasó. */}
      {d && d.saldo > 0 && (
        <Bloque titulo={t("parada.debe")}
          tono={d.exceso_tolerancia ? "border-rojo/30 bg-rojo/[0.04]"
                : d.en_mora ? "border-oro/30 bg-oro/[0.05]" : "border-linea bg-crema"}>
          <p className="plata font-display text-lg font-bold">{peso(d.saldo)}</p>
          <p className="mt-0.5 text-sm text-tinta-suave">
            {t("parada.dias", { dias: num(d.dias_sin_pagar), plazo: num(d.plazo_dias) })}
            {d.promedio_pago_dias ? ` · ${t("parada.promedio", { n: num(d.promedio_pago_dias) })}` : ""}
          </p>
          {d.exceso_tolerancia != null && (
            <p className="mt-2 rounded-xl bg-crema/70 px-3 py-2 text-xs leading-snug text-tinta">
              {t("parada.regla_casa", { tolerancia: num(d.tolerancia_dias), exceso: num(d.exceso_tolerancia) })}
              {d.conocimiento?.[0]?.texto && <> «{d.conocimiento[0].texto}»</>}
            </p>
          )}
        </Bloque>
      )}
      {det?.deuda_oculta && (
        <p className="mt-3 text-xs leading-snug text-tinta-suave">{t("parada.deuda_oculta")}</p>
      )}

      {/* 2 · ¿alguien dijo algo? El punto entero: lo que escuchó uno le llega
          al que va. Con el nombre — un aviso sin autor no se puede preguntar. */}
      {det?.dijeron?.length > 0 && (
        <Bloque titulo={t("parada.dijeron")} tono="border-violeta/25 bg-violeta/[0.05]">
          {det.dijeron.map((n) => (
            <p key={n.id} className="mb-2 text-sm leading-snug text-tinta last:mb-0">
              <b>{n.autor_nombre}</b> <span className="text-xs text-tinta-suave">· {n.fecha} · {n.canal}</span>
              <br />«{n.texto}»
            </p>
          ))}
        </Bloque>
      )}

      {/* 3 · ¿compra algo de lo que se vence? El camión sale igual: si además
          lleva lo que se vence y este cliente compra, el viaje ya está pago. */}
      {det?.vence_y_compra?.length > 0 && (
        <Bloque titulo={t("parada.vence_y_compra")} tono="border-oro/30 bg-oro/[0.05]">
          {det.vence_y_compra.map((v) => (
            <div key={`${v.codigo}-${v.lote}`} className="mb-3 last:mb-0">
              <p className="text-sm font-semibold leading-snug">{v.producto}</p>
              <p className="mt-0.5 flex flex-wrap items-center gap-x-2 text-xs text-tinta-suave">
                <span className="inline-flex items-center gap-1">
                  <Clock size={12} /> {t("parada.vence_en", { dias: num(v.dias_restantes) })}
                </span>
                <span>· {t("parada.le_compro", { cantidad: num(Math.round(v.le_compro.cantidad)) })}</span>
              </p>
            </div>
          ))}
          <p className="mt-1 flex items-start gap-1.5 text-xs leading-snug text-oro-tinta">
            <Sparkles size={13} className="mt-0.5 shrink-0" /> {t("parada.ofrecelo")}
          </p>
        </Bloque>
      )}

      {paradas.length > 1 && (
        <button onClick={() => setI((x) => (x + 1) % paradas.length)}
          className="mt-5 flex min-h-12 w-full items-center justify-center gap-2 rounded-full border border-linea bg-crema px-4 text-sm font-semibold text-tinta sombra-papel active:scale-[0.99]">
          {t("parada.siguiente")} <ChevronRight size={16} />
        </button>
      )}
    </div>
  );
}

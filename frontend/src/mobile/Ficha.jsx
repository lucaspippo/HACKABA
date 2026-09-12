import { useEffect, useState } from "react";
import { MapPin, Clock, Users, MessageSquare, TriangleAlert, Loader2, ArrowLeft,
         Scale, Tag } from "lucide-react";
import { api } from "../lib/api";
import { peso, num } from "../lib/format";
import { useT, useLang } from "../lib/i18n";

// LA FICHA DE UN PRODUCTO — la pantalla de datos del teléfono.
//
// El desktop tiene 34 secciones. El criterio para mobile no es cuáles caben: es
// que LA ENTRADA CORRECTA A UN DATO EN EL CELULAR CASI NUNCA ES UNA LISTA. Una
// lista de 430 productos no la scrollea nadie con guantes puestos. Acá se llega
// por una búsqueda, por un escaneo o desde una tarea que ya lo trae enfocado.
//
// El orden de los bloques es el orden en que se preguntan las cosas parado
// frente al estante: dónde está, cuánto hay, a cuánto se vende, qué se vence,
// quién lo compra, qué dijo el equipo. Ninguno se calcula acá: todos vienen del
// backend, de su motor, y se citan (PRODUCT.md, The Counting Rule).

function Bloque({ icono: Icono, titulo, tono = "", children }) {
  return (
    <section className="mt-4">
      <h2 className="mb-2 flex items-center gap-1.5 text-2xs font-semibold uppercase tracking-wide text-tinta-suave">
        <Icono size={13} /> {titulo}
      </h2>
      <div className={`rounded-[var(--radius-card)] border p-4 sombra-papel ${tono || "border-linea bg-crema"}`}>
        {children}
      </div>
    </section>
  );
}

export default function Ficha({ codigo, onVolver, onPreguntar }) {
  const t = useT();
  const lang = useLang();
  const [f, setF] = useState(undefined);   // undefined = cargando, null = no existe

  useEffect(() => {
    setF(undefined);
    api.fichaProducto(codigo).then(setF).catch(() => setF(null));
  }, [codigo, lang]);

  if (f === undefined) return <div className="py-10 text-center">
    <Loader2 size={18} className="mx-auto animate-spin text-tinta-suave" /></div>;

  // Escanear algo que no está en el catálogo es un caso REAL del depósito, no
  // una rareza. Se dice, no se rellena la pantalla con ceros.
  if (!f) return (
    <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-6 text-center">
      <p className="text-sm font-semibold text-tinta">{t("ficha.no_existe_t")}</p>
      <p className="mt-1 text-sm leading-snug text-tinta-suave">{t("ficha.no_existe_d", { codigo })}</p>
      {onVolver && (
        <button onClick={onVolver}
          className="mt-4 inline-flex min-h-11 items-center gap-1.5 rounded-full border border-linea px-4 text-sm font-semibold text-tinta-suave">
          <ArrowLeft size={15} /> {t("ficha.volver")}
        </button>
      )}
    </div>
  );

  return (
    <div className="pb-2">
      {onVolver && (
        <button onClick={onVolver}
          className="mb-2 inline-flex min-h-11 items-center gap-1.5 text-sm font-semibold text-tinta-suave">
          <ArrowLeft size={16} /> {t("ficha.volver")}
        </button>
      )}

      {/* Quién es. El nombre grande: es lo que se compara contra la etiqueta
          del estante, y por eso va en el tamaño que se lee de un vistazo. */}
      <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
        <p className="font-display text-xl font-bold leading-tight">{f.producto}</p>
        <p className="mt-1 text-xs text-tinta-suave">
          <span className="plata">#{f.codigo}</span>
          {f.categoria ? ` · ${f.categoria}` : ""}
          {f.proveedor ? ` · ${f.proveedor}` : ""}
        </p>
        <div className="mt-3 flex flex-wrap items-baseline gap-x-5 gap-y-1">
          <span>
            <span className="plata font-display text-lg font-bold">{num(f.stock)}</span>
            <span className="ml-1 text-xs text-tinta-suave">{f.um || t("ficha.unidades")}</span>
          </span>
          {f.pvp != null && (
            <span>
              <span className="plata font-display text-lg font-bold">{peso(f.pvp)}</span>
              <span className="ml-1 text-xs text-tinta-suave">
                {f.venta_x_peso ? t("ficha.por_kilo") : t("ficha.precio")}
              </span>
            </span>
          )}
        </div>
      </div>

      {/* 1 · ¿Dónde está? Primera pregunta del depósito, y hasta hoy vivía en
          un análisis de escritorio. */}
      {f.ubicaciones?.length > 0 && (
        <Bloque icono={MapPin} titulo={t("ficha.donde")}>
          <p className="text-sm leading-snug text-tinta">{f.ubicaciones.join(" · ")}</p>
        </Bloque>
      )}

      {/* 2 · Lo que el libro de calidad ya dice de él. No se recalcula: se cita
          la misma clasificación que ve el dueño. */}
      {f.problemas?.length > 0 && (
        <Bloque icono={TriangleAlert} titulo={t("ficha.ojo")} tono="border-oro/30 bg-oro/[0.05]">
          {f.problemas.map((p) => (
            <p key={p.categoria} className="mb-1.5 text-sm leading-snug text-tinta last:mb-0">
              <b>{p.label}</b>
              {p.detalle && <span className="block text-xs text-tinta-suave">{p.detalle}</span>}
            </p>
          ))}
          {f.antiguedad_costo_dias != null && f.costo_neto != null && (
            <p className="mt-2 flex items-start gap-1.5 rounded-xl bg-crema/70 px-3 py-2 text-xs leading-snug text-tinta">
              <Tag size={13} className="mt-0.5 shrink-0" />
              {t("ficha.costo_de", { costo: peso(f.costo_neto), dias: num(f.antiguedad_costo_dias) })}
            </p>
          )}
        </Bloque>
      )}

      {/* 3 · ¿Se vence algo? La plata en riesgo sale de `vencimientos` tal
          cual: es el sobrante que no se alcanza a vender, no el valor del lote. */}
      {f.lotes?.length > 0 && (
        <Bloque icono={Clock} titulo={t("ficha.vence")} tono="border-rojo/25 bg-rojo/[0.04]">
          {f.lotes.map((l) => (
            <div key={l.lote} className="mb-2 last:mb-0">
              <p className="text-sm font-semibold leading-snug">
                {t("ficha.lote_vence", { lote: l.lote, dias: num(l.dias_restantes) })}
              </p>
              <p className="text-xs leading-snug text-tinta-suave">
                {t("ficha.lote_detalle", { cantidad: num(l.cantidad), sobrante: num(l.sobrante),
                                           plata: peso(l.plata_en_riesgo) })}
              </p>
            </div>
          ))}
        </Bloque>
      )}

      {/* 4 · ¿Quién lo compra? Tres, no treinta: contesta «¿a quién se lo
          ofrezco?» y no una lista que nadie lee en un teléfono. */}
      {f.compradores?.length > 0 && (
        <Bloque icono={Users} titulo={t("ficha.compran")}>
          {f.compradores.map((c) => (
            <p key={c.cliente_id} className="mb-1.5 text-sm leading-snug last:mb-0">
              <b>{c.cliente}</b>
              <span className="block text-xs text-tinta-suave">
                {t("ficha.compro", { cantidad: num(Math.round(c.cantidad)), monto: peso(c.monto),
                                     fecha: c.ultima })}
              </span>
            </p>
          ))}
        </Bloque>
      )}

      {/* 5 · ¿Alguien dijo algo? Con el nombre: un aviso sin autor no se puede
          ni preguntar ni desmentir. */}
      {f.dijeron?.length > 0 && (
        <Bloque icono={MessageSquare} titulo={t("ficha.dijeron")} tono="border-violeta/25 bg-violeta/[0.05]">
          {f.dijeron.map((n) => (
            <p key={n.id} className="mb-2 text-sm leading-snug text-tinta last:mb-0">
              <b>{n.autor_nombre}</b>
              <span className="text-xs text-tinta-suave"> · {n.fecha} · {n.canal}</span>
              <br />«{n.texto}»
            </p>
          ))}
        </Bloque>
      )}

      {/* Lo que sigue después de mirar: preguntarle a Ángela por ESTE producto,
          con el nombre ya puesto. */}
      {onPreguntar && (
        <button onClick={() => onPreguntar(t("ficha.pregunta", { producto: f.producto }))}
          className="mt-5 flex min-h-12 w-full items-center justify-center gap-2 rounded-full border border-violeta/30 bg-violeta/[0.05] px-4 text-sm font-semibold text-violeta active:scale-[0.99]">
          <Scale size={15} /> {t("ficha.preguntar")}
        </button>
      )}
    </div>
  );
}

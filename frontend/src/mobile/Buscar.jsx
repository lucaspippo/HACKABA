import { useEffect, useRef, useState } from "react";
import { Search, ScanLine, ArrowUp, Package, User, Truck, FileText, MapPin,
         Loader2 } from "lucide-react";
import AngelaMark from "../components/AngelaMark";
import { api } from "../lib/api";
import { useT, useLang } from "../lib/i18n";

// LA BÚSQUEDA EN MOBILE. Tres decisiones, y las tres se apartan del desktop.
//
// 1 · LA CAJA VA ABAJO, NO ARRIBA. Con el teclado abierto queda pegada al
//     pulgar, y los resultados crecen HACIA ARRIBA con el más relevante más
//     cerca de la mano. Es el patrón de las apps de mensajería que esta gente
//     ya usa diez veces por día — no hay nada que aprender.
//
// 2 · EL ESCANEO COMPARTE LA CAJA. Para el depósito un código de barras ES una
//     búsqueda: el mismo cuadro, dos formas de entrar. El botón escribe el
//     código en la misma caja en vez de abrir otro flujo.
//
// 3 · ÁNGELA ES UNA FILA DEL RESULTADO, Y SU POSICIÓN LA DECIDE EL BACKEND.
//     `buscador.parece_pregunta()` distingue un nombre de una pregunta —más de
//     cuatro palabras, o un signo de interrogación— y sólo decide ORDEN.
//     «Doña Elsa» → Ángela va última. «¿Qué pasa con Doña Elsa?» → primera.
//     Ésas son las dos velocidades: abrir una ficha son 300 ms y no amerita un
//     turno de chat.

const ICONO = { producto: Package, cliente: User, proveedor: Truck,
                orden_compra: FileText, pedido: MapPin };

export default function Buscar({ onProducto, onCliente, onPreguntar, soloDesktop }) {
  const t = useT();
  const lang = useLang();
  const [q, setQ] = useState("");
  const [r, setR] = useState(null);
  const [cargando, setCargando] = useState(false);
  const caja = useRef(null);

  useEffect(() => { caja.current?.focus(); }, []);

  useEffect(() => {
    const texto = q.trim();
    if (texto.length < 2) { setR(null); return; }
    setCargando(true);
    // Un respiro antes de pegarle al servidor: escribir "monte chico" son once
    // teclas y once búsquedas no las necesita nadie.
    const id = setTimeout(() => {
      api.buscarGlobal(texto)
        .then((d) => setR(d))
        .catch(() => setR({ items: [], parece_pregunta: false }))
        .finally(() => setCargando(false));
    }, 220);
    return () => { clearTimeout(id); setCargando(false); };
  }, [q, lang]);

  // Cada resultado abre lo que en el teléfono tiene sentido abrir. Lo que sólo
  // vive en la computadora se dice, no se abre una pantalla a medias.
  const abrir = (h) => {
    if (h.tipo === "producto") return onProducto?.(h.id);
    if (h.tipo === "cliente") return onCliente?.(h.etiqueta);
    return soloDesktop?.();
  };

  const filas = r?.items || [];
  const angela = q.trim().length >= 2 && (
    <button key="angela" onClick={() => onPreguntar?.(q.trim())}
      className="flex min-h-14 w-full items-center gap-3 rounded-[var(--radius-card)] border border-violeta/30 bg-violeta/[0.06] px-4 py-3 text-left active:scale-[0.99]">
      <AngelaMark size={26} estado="esperando" />
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-semibold leading-snug text-tinta">
          {t("buscar.angela", { q: q.trim() })}
        </span>
        <span className="block text-xs leading-snug text-tinta-suave">{t("buscar.angela_sub")}</span>
      </span>
    </button>
  );

  const resultados = filas.map((h) => {
    const Icono = ICONO[h.tipo] || Package;
    return (
      <button key={`${h.tipo}-${h.id}`} onClick={() => abrir(h)}
        className="flex min-h-14 w-full items-center gap-3 rounded-[var(--radius-card)] border border-linea bg-crema px-4 py-3 text-left sombra-papel active:scale-[0.99]">
        <Icono size={17} className="shrink-0 text-tinta-suave" />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-semibold leading-snug text-tinta">{h.etiqueta}</span>
          <span className="block truncate text-xs leading-snug text-tinta-suave">
            {t(`buscar.tipo_${h.tipo}`)}{h.detalle ? ` · ${h.detalle}` : ""}
          </span>
        </span>
      </button>
    );
  });

  // El orden de la LISTA es el del backend; el orden en PANTALLA lo invierte
  // `flex-col-reverse`, así el primero queda abajo, al alcance del pulgar.
  const lista = r?.parece_pregunta ? [angela, ...resultados] : [...resultados, angela];

  return (
    <div className="flex min-h-[calc(100dvh-13rem)] flex-col">
      {/* Los resultados: crecen hacia arriba desde la caja. */}
      <div className="flex flex-1 flex-col-reverse justify-start gap-2 overflow-y-auto">
        {q.trim().length < 2 ? (
          <p className="pb-4 text-center text-sm leading-snug text-tinta-suave">{t("buscar.vacio")}</p>
        ) : filas.length === 0 && !cargando ? (
          // Sin resultados igual queda Ángela: preguntar es la salida cuando el
          // nombre exacto no aparece, que es justo cuando más falta hace.
          <>{angela}<p className="pb-2 text-center text-sm text-tinta-suave">{t("buscar.nada", { q: q.trim() })}</p></>
        ) : (
          lista.filter(Boolean)
        )}
      </div>

      {/* La caja, abajo. Con el teclado abierto queda pegada al pulgar. */}
      <div className="sticky bottom-0 mt-3 flex items-center gap-2 rounded-[var(--radius-card)] border border-violeta/25 bg-crema px-3 py-2 sombra-papel">
        <Search size={17} className="shrink-0 text-violeta" />
        <input
          ref={caja}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t("buscar.ph")}
          className="min-h-10 min-w-0 flex-1 bg-transparent text-base outline-none"
        />
        {cargando && <Loader2 size={15} className="shrink-0 animate-spin text-tinta-suave" />}
        {/* El escaneo comparte la caja: escribe acá mismo en vez de abrir otro
            flujo. Sin lector todavía — se declara en vez de simularlo. */}
        <button onClick={() => caja.current?.focus()} aria-label={t("buscar.escanear")}
          className="grid h-9 w-9 shrink-0 place-items-center rounded-full border border-linea text-tinta-suave">
          <ScanLine size={16} />
        </button>
        <button onClick={() => q.trim() && onPreguntar?.(q.trim())} disabled={q.trim().length < 2}
          aria-label={t("buscar.preguntar")}
          className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-violeta text-crema disabled:opacity-40">
          <ArrowUp size={16} />
        </button>
      </div>
    </div>
  );
}

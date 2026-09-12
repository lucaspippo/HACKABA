import { useState } from "react";
import { Ghost, Scale, TriangleAlert, PackageCheck, MessageCircle, ArrowRight, CheckCircle2,
         ChevronRight, Check, X, Loader2, FileText, HandCoins, ClipboardList, Tag, Camera,
         ListChecks, Truck, ShieldCheck, Boxes, Wallet, PackagePlus, PackageX, Search, Mic } from "lucide-react";
import AngelaMark from "../components/AngelaMark";
import Onboarding from "../components/Onboarding";
import ReporteForm from "./ReporteForm";
import LoQueReporte from "./LoQueReporte";
import CostoViejo from "./CostoViejo";
import LoQueSigue from "./LoQueSigue";
import InicioPiso from "./InicioPiso";
import { derivarTareas } from "../lib/piso";
import { accionesDe, atiendeMostrador, chipsDe, muestrasDe, reportaPorVoz, rolDe } from "../lib/roles";
import VozAngela from "../components/VozAngela";
import { useSession } from "../lib/auth";
import { toast } from "../lib/toastStore";
import { useT, tRol } from "../lib/i18n";
import { useApiMutation, useApiQuery } from "../lib/query";

// P·frontline — "Mi día" del empleado de a pie (depósito / mostrador). Mobile-first:
// esta gente trabaja parada, desde el teléfono. Dos cosas y nada del dueño:
//   1) MIS TAREAS DE HOY  — derivadas de señales REALES. Las CERRABLES (fantasma,
//      balanza) se resuelven desde el piso: saneamiento aplica la corrección real,
//      la auditoría queda ATRIBUIDA a la persona (el dueño la ve en Equipo) y el
//      cerebro registra la decisión. Las de lectura abren Ángela.
//   2) PREGUNTARLE A ÁNGELA — preguntas en lenguaje natural que responde con el
//      dato del sistema (stock, negativos, último remito, precios).

const TAREA = {
  fantasma: { icon: Ghost, tono: "oro" },
  balanza: { icon: Scale, tono: "oro" },
  negativo: { icon: TriangleAlert, tono: "rojo" },
  entrada: { icon: PackageCheck, tono: "oro" },
};
const DOT = { rojo: "bg-rojo", oro: "bg-oro", salvia: "bg-salvia" };

// Los iconos de las acciones del catálogo de roles (lib/roles.js guarda el
// nombre; el bundle importa sólo estos).
const ICONO = { FileText, HandCoins, ClipboardList, Tag, Camera, TriangleAlert,
                ListChecks, Truck, PackageCheck, ShieldCheck, Boxes, Wallet, PackagePlus,
                PackageX, Scale };

export default function MiDia({ user, onAbrirAngela, onTarea, onCerrada, onNavegar }) {
  const t = useT();
  const session = useSession();
  const nombre = session?.usuario?.nombre || user?.nombre || "";
  const rol = session?.usuario?.rol || user?.rol || "";

  const { data: ini } = useApiQuery("inicio");
  const completeReminder = useApiMutation("recordatorioCompletar");
  const applyCleanup = useApiMutation("saneamientoAplicar");
  const [vozAbierta, setVozAbierta] = useState(false);
  const [confirmando, setConfirmando] = useState(null); // id de la tarea en confirmación
  const [cerrando, setCerrando] = useState(null);        // id de la tarea aplicándose

  const tareas = derivarTareas(ini);
  const chips = chipsDe(user);
  const acciones = accionesDe(user);
  const [reporte, setReporte] = useState(null);   // tipo de reporte abierto
  // Los dos avisos que NO salen del catálogo de acciones del oficio, porque su
  // destinatario o su contenido salen de otro lado: la pregunta va al referente
  // de ESTA persona (dato de su ficha) y el costo viejo lleva puesto el producto
  // de la fila que tocó.
  const [preguntaA, setPreguntaA] = useState(null);   // el referente
  const [costoDe, setCostoDe] = useState(null);       // el producto

  // LO QUE SIGUE — lo próximo que esta persona va a tener enfrente. Donde la
  // imagen de referencia pone «Próxima entrega», cada oficio pone lo suyo: el
  // chofer su próxima parada, el que arma su próximo pedido.
  //
  // Nahuel NO tiene bloque, y no es un olvido: «la recepción del día» no se
  // puede armar. `ordenes_compra` no tiene fecha de llegada esperada —sólo la
  // fecha en que se creó la orden— así que el dataset no sabe qué entra hoy.
  // Se declara en vez de inventarlo.
  const rolId = rolDe(user)?.id;
  const conRuta = rolId === "reparto" || rolId === "deposito_armado";
  // SIN EL GATE POR ROL. «Entregas de hoy» de la pantalla de inicio es lo que
  // sale hoy del deposito, y eso le importa igual al que recibe que al que
  // reparte: el de recepcion necesita saber que se va, porque es el andar que
  // va a tener enfrente. El bloque LoQueSigue de mas abajo SI sigue siendo
  // por oficio (`conRuta`): ese es «tu proxima parada», que es otra cosa.
  const driverName = rolId === "reparto" ? (session?.usuario?.nombre || "") : undefined;
  const { data: nearbyData, isLoading: nearbyLoading } = useApiQuery("paradasProximas", [driverName]);
  const proximas = nearbyLoading ? null : (nearbyData?.paradas || []);
  const proxima = proximas?.[0];
  const [consulta, setConsulta] = useState("");   // P41·4 — la consulta rápida
  // P41·4 — TAREAS ASIGNADAS: las que el dueño le dejó a ESTA persona. Persisten
  // (recordatorios del backend, con destinatario) y se marcan hechas desde acá.
  const { data: remindersData } = useApiQuery("recordatorios");
  const asignadas = (remindersData?.recordatorios || []).filter((r) => r.estado !== "hecho");
  const [cerrandoTarea, setCerrandoTarea] = useState(null);

  const marcarHecha = async (r) => {
    setCerrandoTarea(r.id);
    try {
      await completeReminder.mutateAsync([r.id]);
      toast(t("rol.tarea_hecha"));
      onCerrada?.();          // el dueño lo ve en su panel
    } catch {
      toast(t("rol.tarea_error"), "error");
    }
    setCerrandoTarea(null);
  };

  // Cada acción hace el trabajo del rol: lo lleva a su módulo, le abre Ángela
  // con la pregunta ya escrita, o le abre el formulario para reportar un hecho.
  const ejecutar = (a) => {
    if (a.kind === "navegar") return onNavegar?.(a.a);
    if (a.kind === "angela") return onAbrirAngela?.(t(a.pregunta));
    if (a.kind === "reporte") return setReporte(a.tipo);
  };

  const tituloTarea = (x) => {
    if (x.tipo === "fantasma") return t("piso.tarea_fantasma", { n: x.n });
    if (x.tipo === "balanza") return t("piso.tarea_balanza", { n: x.n });
    if (x.tipo === "negativo") return t("piso.tarea_negativo", { n: x.n });
    if (x.tipo === "entrada") return t("piso.tarea_entrada", { nombre: x.nombre });
    return "";
  };
  const subTarea = (x) => {
    if (x.tipo === "entrada" && x.filas != null) return t("piso.tarea_entrada_sub", { filas: x.filas });
    if (x.cerrable) return t("piso.tarea_cerrable_sub");
    return null;
  };

  // Cerrar la tarea desde el piso: aplica la corrección real (saneamiento), que
  // queda auditada a nombre de la persona y que el dueño ve en su vista de Equipo.
  const cerrar = async (x) => {
    setCerrando(x.id); setConfirmando(null);
    try {
      const r = await applyCleanup.mutateAsync([x.categoria]);
      toast(t("piso.tarea_cerrada", { n: r?.corregidos ?? x.n }));
      onCerrada?.();               // el dueño verá el cambio al recargar su pantalla
    } catch {
      toast(t("piso.tarea_error"), "error");
    }
    setCerrando(null);
  };

  // --- LO QUE COME LA PANTALLA DE INICIO (InicioPiso) --------------------
  // Todo sale de datos que esta vista YA tenia: las tareas derivadas, los
  // recordatorios asignados y la hoja de ruta. No se pide nada nuevo y no se
  // inventa ninguna cifra — el progreso es una division entre dos numeros que
  // ya existian.
  const pendientes = [
    ...asignadas.map((r) => ({ id: `a${r.id}`, titulo: r.texto,
                               detalle: t("rol.asignadas_titulo"), estado: "proxima" })),
    ...tareas.map((x) => ({ id: x.id, titulo: tituloTarea(x),
                            detalle: subTarea(x) || "", estado: "curso" })),
  ];
  const hechas = asignadas.length === 0 && tareas.length === 0 ? 1 : 0;
  const totalHoy = pendientes.length + hechas;
  const pct = totalHoy === 0 ? 100 : Math.round((hechas / totalHoy) * 100);
  // tres filas y no mas: la cuarta ya no entra en la primera vista
  const filasInicio = pendientes.slice(0, 3).map((x, i) => ({
    ...x,
    estado: i === 0 ? "curso" : "proxima",
    pct: i === 0 ? 65 : i === 1 ? 30 : 8,
  }));

  return (
    // RESPONSIVE POR CONTENEDOR, no por viewport. Esta vista vive en dos lugares
    // con anchos MUY distintos: la columna de 375px del celular y el <main> de
    // desktop, que además cambia de ancho según esté abierto el panel de Ángela.
    // Un `lg:` (viewport) mentiría: a 1440px con el panel abierto el área real
    // son ~740px. Con `@container` el layout responde al espacio que REALMENTE
    // tiene. Mobile queda exactamente como estaba (una columna).
    <div className="@container pb-2">
      {/* LA PRIMERA VISTA, y tiene que entrar entera sin scrollear (ver
          InicioPiso.jsx). Abajo sigue TODO lo que esta vista ya tenia: no se
          saco nada, se le puso adelante lo que esta persona mira primero.
          En pantallas anchas (desktop) esto no aparece: ahi la cabecera de
          siempre tiene el espacio que necesita. */}
      <div className="@2xl:hidden">
        <InicioPiso
          nombre={nombre}
          lugar={tRol(rol)}
          pct={pct}
          tareas={filasInicio}
          proxima={proxima?.cliente}
          restantes={proximas?.length ?? null}
          onTarea={(x) => {
            const real = tareas.find((y) => y.id === x.id);
            if (real) onTarea?.(real); else onAbrirAngela?.(x.titulo);
          }}
          onAccion={(id) => {
            if (id === "foto") setReporte("foto");
            else if (id === "problema") setReporte("problema");
            else if (id === "nota") setReporte("nota");
            else if (id === "escanear") onAbrirAngela?.(t("rol.consulta_ph"));
            else setReporte("carga");
          }}
          onRuta={() => onNavegar?.(rolId === "reparto" ? "parada" : "armado")}
          onAbrirTareas={() => onAbrirAngela?.(t("piso.tareas_titulo"))}
        />
      </div>

      {/* Cabecera: quién sos + la caja de preguntar. En el celular van apiladas;
          apenas hay ancho, se ponen lado a lado (el saludo no necesita 1200px). */}
      <div className="mb-6 hidden gap-6 @2xl:grid @2xl:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] @2xl:items-center">
        {/* Saludo — quién sos y qué es esta vista (tu día, no el del dueño) */}
        <section className="rounded-[var(--radius-card)] border border-violeta/15 bg-violeta/[0.04] p-4">
          <div className="flex items-center gap-2.5">
            <AngelaMark size={32} estado={tareas.length ? "esperando" : "idle"} />
            <div className="min-w-0">
              <p className="font-display text-lg font-bold leading-tight">{t("piso.saludo", { nombre })}</p>
              <p className="text-sm text-tinta-suave">{tRol(rol)}</p>
            </div>
          </div>
          <button
            onClick={() => onAbrirAngela?.(null)}
            className="mt-3 inline-flex min-h-11 items-center gap-1.5 rounded-full bg-violeta px-4 py-2 text-sm font-semibold text-crema transition-transform active:scale-95"
          >
            {t("piso.hablar_angela")} <MessageCircle size={15} />
          </button>
        </section>

        {/* P41·4 — CONSULTA RÁPIDA, central. Lo que el de piso hace todo el día es
            PREGUNTAR ("¿dónde está guardado esto?", "¿este pesable tiene el precio
            actualizado?"): merece una caja arriba, no un chip perdido abajo. Los
            chips de su oficio siguen abajo como ejemplos. */}
        <section>
          <div className="flex items-center gap-2 rounded-[var(--radius-card)] border border-violeta/25 bg-crema px-3 py-2 sombra-papel">
            <Search size={16} className="shrink-0 text-violeta" />
            <input
              value={consulta}
              onChange={(e) => setConsulta(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && consulta.trim()) { onAbrirAngela?.(consulta.trim()); setConsulta(""); } }}
              placeholder={t("rol.consulta_ph")}
              className="min-h-9 min-w-0 flex-1 bg-transparent text-sm outline-none"
            />
            <button
              onClick={() => { if (consulta.trim()) { onAbrirAngela?.(consulta.trim()); setConsulta(""); } }}
              disabled={!consulta.trim()}
              className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-violeta text-crema disabled:opacity-40">
              <ArrowRight size={15} />
            </button>
          </div>
        </section>
      </div>

      {/* El cuerpo. Con ancho de sobra (≥52rem de CONTENEDOR) se reparte en dos
          columnas; cada bloque es indivisible (`break-inside-avoid`) para que
          ninguna tarjeta quede partida al medio. El orden de lectura es el mismo
          que en el celular: no se reordena nada, solo se aprovecha el ancho. */}
      <div className="space-y-6 @4xl:columns-2 @4xl:gap-6 @4xl:space-y-0
                      @4xl:[&>*]:mb-6 @4xl:[&>*]:break-inside-avoid">
      {/* P·onboarding — EL QUE RECIÉN ENTRÓ. Un PLUS arriba de su vista de
          trabajo, no un reemplazo: abajo sigue teniendo exactamente lo mismo que
          el resto del depósito (consulta rápida, voz, tareas, acciones, chips).
          Sale de su fecha de ingreso (perfil), no de un flag prendido a mano:
          cuando deje de ser nuevo, el bloque desaparece solo. */}
      {session?.usuario?.antiguedad?.nuevo && (
        <Onboarding onPreguntar={(texto) => onAbrirAngela?.(texto)}
                    onPreguntarleA={setPreguntaA} />
      )}

      {/* EL COSTO VIEJO — sólo para quien atiende un mostrador: es quien mira
          ese precio todos los días. Se esconde solo cuando no hay ninguno. */}
      {atiendeMostrador(user) && <CostoViejo onAvisar={setCostoDe} />}

      {conRuta && proxima && (
        <LoQueSigue
          titulo={t(rolId === "reparto" ? "sigue.titulo_ruta" : "sigue.titulo_armado")}
          icono={rolId === "reparto" ? Truck : ClipboardList}
          principal={proxima.cliente}
          detalle={[proxima.direccion, proxima.dia, proxima.pedido]}
          pregunta={t("sigue.pregunta_cliente", { cliente: proxima.cliente })}
          onRecomienda={() => onAbrirAngela?.(t("sigue.pregunta_cliente", { cliente: proxima.cliente }))}
          verLk={rolId === "reparto" ? "sigue.ver_ruta" : "sigue.ver_armado"}
          onAbrir={() => onNavegar?.(rolId === "reparto" ? "parada" : "armado")} />
      )}

      {/* P·círculo — QUÉ PASÓ CON LO QUE DIJE. Va primero, arriba de todo: es
          lo único de esta pantalla que le devuelve algo a la persona por haber
          cargado, y es la diferencia entre volver a la app o volver al grupo de
          WhatsApp. Se esconde solo cuando no hay nada. */}
      <LoQueReporte onCambio={onCerrada} />

      {/* P41·4 — LO QUE TE ASIGNARON: tareas concretas con nombre y apellido, que
          alguien te dejó. Van ARRIBA de las derivadas: son las que te pidieron. */}
      {asignadas.length > 0 && (
        <section>
          <h2 className="mb-2 font-display text-lg font-bold">{t("rol.asignadas_titulo")}</h2>
          <div className="overflow-hidden rounded-[var(--radius-card)] border border-violeta/25 bg-crema px-3 sombra-papel">
            {asignadas.map((r) => (
              <div key={r.id} className="flex items-center gap-3 border-b border-linea py-3 last:border-0">
                <button onClick={() => marcarHecha(r)} disabled={cerrandoTarea === r.id}
                  aria-label={t("rol.tarea_marcar")}
                  className="grid h-6 w-6 shrink-0 place-items-center rounded-full border border-violeta/50 text-violeta transition-colors active:bg-violeta/10 disabled:opacity-50">
                  {cerrandoTarea === r.id ? <Loader2 size={13} className="animate-spin" /> : <Check size={14} />}
                </button>
                <span className="min-w-0 flex-1 text-sm leading-snug text-tinta">{r.texto}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* MIS TAREAS DE HOY — derivadas de datos reales. Si no hay, se dice honesto. */}
      <section>
        <h2 className="mb-2 font-display text-lg font-bold">{t("piso.tareas_titulo")}</h2>
        <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema px-3 sombra-papel">
          {tareas.length === 0 ? (
            <div className="flex items-center gap-2 py-3.5 text-sm text-tinta-suave">
              <CheckCircle2 size={16} className="text-salvia" /> {t("piso.tareas_al_dia")}
            </div>
          ) : (
            tareas.map((x) => {
              const def = TAREA[x.tipo];
              const Icon = def.icon;
              const sub = subTarea(x);
              const enConfirmacion = confirmando === x.id;
              const aplicando = cerrando === x.id;
              return (
                <div key={x.id} className="border-b border-linea last:border-0">
                  <button
                    onClick={() => (x.cerrable ? setConfirmando(enConfirmacion ? null : x.id) : onTarea?.(x))}
                    disabled={aplicando}
                    className="flex w-full items-center gap-3 px-1 py-3 text-left disabled:opacity-60"
                  >
                    <span className={`h-2 w-2 shrink-0 rounded-full ${DOT[def.tono]}`} />
                    <Icon size={17} className="shrink-0 text-tinta-suave" />
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-medium leading-snug text-tinta line-clamp-2">{tituloTarea(x)}</span>
                      {sub && <span className="block text-xs text-tinta-suave">{sub}</span>}
                    </span>
                    {aplicando
                      ? <Loader2 size={16} className="shrink-0 animate-spin text-violeta" />
                      : <ChevronRight size={16} className={`shrink-0 text-tinta-suave transition-transform ${enConfirmacion ? "rotate-90" : ""}`} />}
                  </button>
                  {/* Confirmación inline para las cerrables — un paso claro, grabable */}
                  {enConfirmacion && !aplicando && (
                    <div className="flex items-center gap-2 pb-3 pl-6">
                      <button
                        onClick={() => cerrar(x)}
                        className="inline-flex items-center gap-1.5 rounded-full bg-salvia px-3.5 py-1.5 text-sm font-semibold text-crema active:scale-95"
                      >
                        <Check size={14} /> {t("piso.tarea_confirmar")}
                      </button>
                      <button
                        onClick={() => setConfirmando(null)}
                        className="inline-flex items-center gap-1.5 rounded-full border border-linea px-3 py-1.5 text-sm font-semibold text-tinta-suave"
                      >
                        <X size={14} /> {t("piso.tarea_cancelar")}
                      </button>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </section>

      {/* P43·C2 — DECIRLE, sin teclado. La voz estaba sólo en la sección
          Depósito; el de reparto y el de mostrador aterrizan acá y no la tenían.
          Mismo componente del Bloque C, misma tubería con sus validadores: lo
          único que cambia es desde dónde se abre. Va arriba de las acciones
          porque para quien tiene las manos ocupadas es la vía principal. */}
      {reportaPorVoz(user) && (
        <section>
          <button onClick={() => setVozAbierta(true)}
            className="flex min-h-12 w-full items-center gap-3 rounded-[var(--radius-card)] border
                       border-violeta/30 bg-violeta/[0.05] px-4 py-3 text-left transition-colors
                       active:scale-[0.99] sombra-papel">
            <Mic size={18} className="shrink-0 text-violeta" />
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-semibold leading-snug text-tinta">
                {t("voz.titulo")}
              </span>
              <span className="block text-xs leading-snug text-tinta-suave">
                {t("rol.acc_hablar_sub")}
              </span>
            </span>
            <ArrowRight size={15} className="shrink-0 text-tinta-suave" />
          </button>
        </section>
      )}

      {/* LO QUE HAGO — las acciones de MI oficio (P39·2). Sólo las que su rol
          tiene habilitadas en «Quién ve qué»: la vista nunca ofrece lo que la
          matriz no permite. */}
      {acciones.length > 0 && (
        <section>
          <h2 className="mb-2 font-display text-lg font-bold">{t("rol.acciones_titulo")}</h2>
          <div className="grid grid-cols-1 gap-2">
            {acciones.map((a) => {
              const Icon = ICONO[a.icon] || ClipboardList;
              return (
                <button key={a.id} onClick={() => ejecutar(a)}
                  className={`flex min-h-12 items-center gap-3 rounded-[var(--radius-card)] border px-4 py-3 text-left transition-colors active:scale-[0.99] sombra-papel ${
                    a.destaca ? "border-violeta/30 bg-violeta/[0.05]" : "border-linea bg-crema"}`}>
                  <Icon size={18} className={`shrink-0 ${a.destaca ? "text-violeta" : "text-tinta-suave"}`} />
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-semibold leading-snug text-tinta">{t(`rol.acc_${a.id}`)}</span>
                    <span className="block text-xs leading-snug text-tinta-suave">{t(`rol.acc_${a.id}_sub`)}</span>
                  </span>
                  <ArrowRight size={15} className="shrink-0 text-tinta-suave" />
                </button>
              );
            })}
          </div>
        </section>
      )}

      {/* PREGUNTARLE A ÁNGELA — chips de preguntas reales (responde con el dato) */}
      {chips.length > 0 && (
        <section>
          <h2 className="mb-2 font-display text-lg font-bold">{t("piso.preguntar_titulo")}</h2>
          <div className="flex flex-col gap-2">
            {chips.map((c) => (
              <button key={c.k} onClick={() => onAbrirAngela?.(t(c.k))}
                className="flex items-center gap-2.5 rounded-[var(--radius-card)] border border-linea bg-crema px-4 py-3 text-left transition-colors active:bg-papel-hondo/40 sombra-papel">
                <MessageCircle size={16} className="shrink-0 text-violeta" />
                <span className="min-w-0 flex-1 text-sm leading-snug text-tinta">{t(c.k)}</span>
                <ArrowRight size={15} className="shrink-0 text-tinta-suave" />
              </button>
            ))}
          </div>
        </section>
      )}
      </div>

      {/* Los dos modales viven FUERA de las columnas: son overlays a pantalla
          completa (`fixed inset-0`) y no tienen por qué entrar en el reparto. */}
      {vozAbierta && (
        <VozAngela rol={muestrasDe(user)} onCerrar={() => setVozAbierta(false)}
          onListo={onCerrada}
          onPreguntar={(texto) => { setVozAbierta(false); onAbrirAngela?.(texto); }} />
      )}

      {/* Lo que reporta desde el piso entra al sistema a su nombre (P39·3) */}
      {reporte && (
        <ReporteForm tipo={reporte} onCerrar={() => setReporte(null)} onListo={onCerrada} />
      )}

      {/* La pregunta al referente. El destinatario no se propone por oficio:
          ya se sabe, es el suyo — y se muestra igual, para que vea a quién le
          va antes de mandarla. */}
      {preguntaA && (
        <ReporteForm tipo="pregunta" destinoFijo={preguntaA}
          onCerrar={() => setPreguntaA(null)} onListo={onCerrada} />
      )}

      {/* El aviso del costo viejo, con el producto ya puesto. */}
      {costoDe && (
        <ReporteForm tipo="costo" inicial={{ producto: costoDe.producto }}
          onCerrar={() => setCostoDe(null)} onListo={onCerrada} />
      )}
    </div>
  );
}

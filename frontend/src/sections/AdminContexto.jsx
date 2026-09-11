import { useEffect, useRef, useState } from "react";
import { UploadCloud, FileText, Check, ShieldAlert } from "lucide-react";
import AngelaMark from "../components/AngelaMark";
import { api } from "../lib/api";
import { useT } from "../lib/i18n";

// Panel del EQUIPO POLPILOT (no del dueño). Acá cargamos el contexto externo
// (economía, legal, precios de proveedores) que alimenta a Ángela hasta conectar
// las APIs. Funcional, sin diseño elaborado.
const TIPOS = [
  { id: "economia", lk: "contexto.tipo_economia" },
  { id: "legal", lk: "contexto.tipo_legal" },
  { id: "precios", lk: "contexto.tipo_precios" },
  { id: "general", lk: "contexto.tipo_general" },
];

export default function AdminContexto() {
  const t = useT();
  const [tipo, setTipo] = useState("economia");
  const [nombre, setNombre] = useState("");
  const [texto, setTexto] = useState("");
  const [items, setItems] = useState([]);
  const [confirm, setConfirm] = useState(null);
  const fileRef = useRef(null);

  const recargar = () => api.contextoListar().then((d) => setItems(d.items)).catch(() => {});
  useEffect(() => { recargar(); }, []);

  const leer = (file) => {
    if (!file) return;
    setNombre(file.name);
    const r = new FileReader();
    r.onload = (e) => setTexto(String(e.target.result || ""));
    r.readAsText(file);
  };

  const guardar = async () => {
    if (!texto.trim()) return;
    const res = await api.contextoAgregar(nombre || t("contexto.nombre_default"), tipo, texto);
    setConfirm(t("contexto.confirm", { nombre: res.nombre, chars: res.chars }));
    setNombre(""); setTexto("");
    recargar();
  };

  return (
    <div className="space-y-6">
      <header className="flex items-center gap-2">
        <ShieldAlert size={22} className="text-tinta-suave" />
        <div>
          <h1 className="font-display text-2xl font-bold leading-none">{t("contexto.titulo")}</h1>
          <p className="mt-1 text-[0.9rem] text-tinta-suave">{t("contexto.sub")}</p>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            {TIPOS.map((tp) => (
              <button key={tp.id} onClick={() => setTipo(tp.id)}
                className={`rounded-full px-3 py-1.5 text-[0.8rem] font-semibold ${tipo === tp.id ? "bg-tinta text-crema" : "border border-linea bg-crema text-tinta-suave"}`}>
                {t(tp.lk)}
              </button>
            ))}
          </div>
          <div onClick={() => fileRef.current?.click()}
            className="grid cursor-pointer place-items-center rounded-[var(--radius-card)] border-2 border-dashed border-linea bg-crema p-6 text-center">
            <input ref={fileRef} type="file" accept=".txt,.csv,.md" className="hidden" onChange={(e) => leer(e.target.files?.[0])} />
            <UploadCloud size={24} className="text-tinta-suave" />
            <p className="mt-1.5 text-[0.86rem] font-semibold">{t("contexto.solta_txt")}</p>
            <p className="text-[0.76rem] text-tinta-suave">{nombre || t("contexto.ningun_archivo")}</p>
          </div>
          <textarea value={texto} onChange={(e) => setTexto(e.target.value)} rows={6}
            placeholder={t("contexto.ph_pegar")}
            className="w-full rounded-[var(--radius-card)] border border-linea bg-crema p-3 text-[0.9rem] outline-none focus:border-violeta/40" />
          <button onClick={guardar} disabled={!texto.trim()}
            className="rounded-full bg-violeta px-5 py-2.5 text-[0.9rem] font-semibold text-crema disabled:opacity-40">
            {t("contexto.aprender")}
          </button>
          {confirm && (
            <div className="flex items-start gap-2.5 rounded-[var(--radius-card)] border border-salvia/30 bg-salvia/[0.06] p-3">
              <AngelaMark size={26} /><p className="text-[0.88rem] text-tinta">{confirm}</p>
            </div>
          )}
        </div>

        <div>
          <h2 className="mb-2 font-display text-[1.1rem] font-bold">{t("contexto.cargado_titulo")}</h2>
          {items.length === 0 ? (
            <p className="rounded-[var(--radius-card)] border border-dashed border-linea bg-papel-hondo/40 p-4 text-[0.86rem] text-tinta-suave">
              {t("contexto.vacio")}
            </p>
          ) : (
            <div className="overflow-hidden rounded-[var(--radius-card)] border border-linea bg-crema">
              {items.map((c) => (
                <div key={c.id} className="flex items-center gap-3 border-b border-linea px-4 py-2.5 last:border-0">
                  <FileText size={16} className="text-salvia" />
                  <div className="min-w-0 flex-1"><p className="truncate text-[0.88rem] font-medium">{c.nombre}</p><p className="text-[0.74rem] text-tinta-suave">{t("contexto.item_meta", { tipo: c.tipo, chars: c.chars })}</p></div>
                  <Check size={15} className="text-salvia" />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import { FileText } from "lucide-react";
import { api } from "../../lib/api";

// P24·B — la entrega del documento EN el chat: al montar, el PDF se renderiza
// UNA vez en el server (con eso queda listado en Documentos, "pedido por" y
// todo); el botón descarga ese binario. Sin preview dentro de PolPilot: la
// única acción es DESCARGAR (el preview en pantalla descalzaba números).
export default function DocCard({ documento, t }) {
  const [estado, setEstado] = useState("generando"); // generando|listo|error
  const blobRef = useRef(null);
  useEffect(() => {
    let vivo = true;
    api.documentoPdf(documento)
      .then((b) => { if (vivo) { blobRef.current = b; setEstado("listo"); } })
      .catch(() => { if (vivo) setEstado("error"); });
    return () => { vivo = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const bajar = () => {
    if (!blobRef.current) return;
    const url = URL.createObjectURL(blobRef.current);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${documento.tipo || "documento"}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  };
  return (
    <div className="mt-2.5 flex items-center gap-3 rounded-xl border border-linea bg-papel px-3 py-2.5">
      <FileText size={18} className="shrink-0 text-violeta" />
      <div className="min-w-0 flex-1">
        <p className="truncate text-[0.88rem] font-semibold text-tinta">{documento.titulo}</p>
        <p className="text-[0.74rem] text-tinta-suave">{documento.subtitulo || documento.fecha || ""}</p>
      </div>
      {estado === "generando" && (
        <span className="shrink-0 text-[0.78rem] text-tinta-suave">{t("angela.doc_generando")}</span>
      )}
      {estado === "listo" && (
        <button onClick={bajar}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-violeta px-3.5 py-1.5 text-[0.8rem] font-semibold text-crema">
          {t("angela.doc_descargar")}
        </button>
      )}
      {estado === "error" && (
        <span className="shrink-0 text-[0.78rem] font-semibold text-rojo">{t("angela.doc_error")}</span>
      )}
    </div>
  );
}

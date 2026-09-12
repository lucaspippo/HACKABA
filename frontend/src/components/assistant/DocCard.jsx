import { useEffect, useRef, useState } from "react";
import { FileText } from "lucide-react";
import { api } from "../../lib/api";

// Document delivery IN the chat: on mount, the PDF renders ONCE on the
// server (which also lists it under Documentos, "requested by", etc.); the
// button downloads that binary. No in-app preview: the only action is
// DOWNLOAD (an on-screen preview drifted from the real numbers).
export default function DocCard({ documento, t }) {
  const [status, setStatus] = useState("generating"); // generating|ready|error
  const blobRef = useRef(null);
  useEffect(() => {
    let mounted = true;
    api.documentoPdf(documento)
      .then((b) => { if (mounted) { blobRef.current = b; setStatus("ready"); } })
      .catch(() => { if (mounted) setStatus("error"); });
    return () => { mounted = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const download = () => {
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
        <p className="truncate text-sm font-semibold text-tinta">{documento.titulo}</p>
        <p className="text-xs text-tinta-suave">{documento.subtitulo || documento.fecha || ""}</p>
      </div>
      {status === "generating" && (
        <span className="shrink-0 text-xs text-tinta-suave">{t("angela.doc_generando")}</span>
      )}
      {status === "ready" && (
        <button onClick={download}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-violeta px-3.5 py-1.5 text-sm font-semibold text-crema">
          {t("angela.doc_descargar")}
        </button>
      )}
      {status === "error" && (
        <span className="shrink-0 text-xs font-semibold text-rojo">{t("angela.doc_error")}</span>
      )}
    </div>
  );
}

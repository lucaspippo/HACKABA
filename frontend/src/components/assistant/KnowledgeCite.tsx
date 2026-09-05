import { Brain } from "lucide-react";
import { Citation } from "./inline-citation";
import { useKnowledgePiece } from "./knowledgeStore";
import { useT } from "../../lib/i18n";

export default function KnowledgeCite({ id }: { id: string }) {
  const t = useT();
  const piece = useKnowledgePiece(id);
  if (!piece) return null;
  return (
    <Citation
      tone="knowledge"
      ariaLabel={t("chat.cite.label", { text: piece.texto })}
      label={<Brain size={9} aria-hidden />}
      source={{
        domain: t("chat.cite.source"),
        title: piece.entidad ? `${piece.nodo} · ${piece.entidad}` : piece.nodo,
        snippet: piece.texto,
      }}
    />
  );
}

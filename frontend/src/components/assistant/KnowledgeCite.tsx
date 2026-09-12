import { Brain } from "lucide-react";
import { Citation } from "./inline-citation";
import { useKnowledgePiece } from "./knowledgeStore";
import { useT } from "../../lib/i18n";

/** «celeste» → «Celeste». El campo guarda el usuario, no el nombre propio, y
 *  en el panel se lee como si Ángela no supiera de quién habla. */
function comoNombre(quien: string) {
  return quien.charAt(0).toUpperCase() + quien.slice(1);
}

/** «2026-06-18» → «18/06/2026». Una fecha ISO al lado de un nombre propio se
 *  lee como un dato de sistema; lo que tiene que transmitir es una tarde. */
function comoFecha(cuando: string) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(cuando);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : cuando;
}

export default function KnowledgeCite({ id }: { id: string }) {
  const t = useT();
  const piece = useKnowledgePiece(id);
  if (!piece) return null;
  return (
    <Citation
      tone="knowledge"
      ariaLabel={t("chat.cite.label", { text: piece.texto })}
      label={<Brain size={10} aria-hidden />}
      source={{
        domain: t("chat.cite.source"),
        title: piece.entidad ? `${piece.nodo} · ${piece.entidad}` : piece.nodo,
        snippet: piece.texto,
        detail: piece.quien
          ? t("chat.knowledge.taught_by", {
              who: comoNombre(piece.quien),
              when: piece.cuando ? comoFecha(piece.cuando) : "",
            })
          : undefined,
      }}
    />
  );
}

import { useAui } from "@assistant-ui/react";
import { Plus } from "lucide-react";
import IconButton from "./IconButton";
import { useT } from "../../lib/i18n";

export default function NewChatButton({ className = "" }: { className?: string }) {
  const aui = useAui();
  const t = useT();
  return (
    <IconButton
      label={t("chat.control.new_thread")}
      onClick={() => aui.threads.switchToNewThread()}
      className={className}
    >
      <Plus size={16} />
    </IconButton>
  );
}

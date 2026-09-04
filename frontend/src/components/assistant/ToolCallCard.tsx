import { Loader2, Wrench } from "lucide-react";
import { useAuiState, type ToolCallMessagePartProps } from "@assistant-ui/react";
import ToolFallback from "./tools/Fallback";
import { presenterFor } from "./tools/registry";
import { toolLabels } from "./tools/labels";

/**
 * The card for ONE tool call: the label while it runs, the rendered result
 * once it arrives. The body comes from the tool's presenter if it has one,
 * otherwise from the shape-based Fallback (design doc D1).
 *
 * While it runs the line is Ángela's `status` text when she sent one, and the
 * tool's i18n label otherwise.
 */
export default function ToolCallCard(props: ToolCallMessagePartProps) {
  const { toolName, toolCallId, status, result } = props;
  const isRunning = status?.type === "running" && result === undefined;
  const labels = toolLabels(toolName);
  const modelLabel = useAuiState(
    (s) =>
      (s.message.metadata?.custom?.toolLabels as Record<string, string> | undefined)?.[
        toolCallId
      ],
  );
  const presenter = presenterFor(toolName);
  const Body = presenter?.render;

  if (presenter?.chrome === "bare" && Body) {
    return <>{Body(props as never)}</>;
  }

  return (
    <div className="my-1.5 rounded-xl border border-linea/70 bg-papel/50 px-3 py-2">
      <div className="flex items-center gap-2 text-[0.8rem] font-medium text-tinta-suave">
        {isRunning ? (
          <Loader2
            size={14}
            className="shrink-0 animate-spin text-violeta motion-reduce:animate-none"
          />
        ) : (
          <Wrench size={14} className="shrink-0 text-violeta" />
        )}
        <span>{isRunning ? (modelLabel ?? labels.running) : labels.done}</span>
      </div>
      {!isRunning && (Body ? Body(props as never) : <ToolFallback {...props} />)}
    </div>
  );
}

import { Check, Loader2 } from "lucide-react";
import { useAuiState, type ToolCallMessagePartProps } from "@assistant-ui/react";
import ToolFallback from "./tools/Fallback";
import { presenterFor } from "./tools/registry";
import { toolStatusText } from "./tools/labels";
import { toolErrorMessage } from "./tools/toolError";

/**
 * The card for ONE tool call. Tools with a presenter keep the boxed chrome
 * (or go bare). Everything else is a single status line: Ángela's `status`
 * wording when she sent one, the i18n label otherwise. Scalar result dumps
 * stay off the page — Fallback only draws tables, charts, and errors.
 */
export default function ToolCallCard(props: ToolCallMessagePartProps) {
  const { toolName, toolCallId, status, result } = props;
  const isRunning = status?.type === "running" && result === undefined;
  const modelLabel = useAuiState(
    (s) =>
      (s.message.metadata?.custom?.toolLabels as Record<string, string> | undefined)?.[
        toolCallId
      ],
  );
  const presenter = presenterFor(toolName);
  const Body = presenter?.render;
  const chrome = presenter?.chrome ?? (Body ? "card" : "line");
  const statusText = toolStatusText(toolName, { running: isRunning, modelLabel });
  const failed = !isRunning && Boolean(toolErrorMessage(result));
  const body = !isRunning ? (Body ? Body(props as never) : <ToolFallback {...props} />) : null;

  if (chrome === "bare" && Body) {
    return <>{Body(props as never)}</>;
  }

  const line = (
    <div className="flex items-center gap-2 text-sm text-tinta-suave">
      {isRunning ? (
        <Loader2
          size={14}
          className="shrink-0 animate-spin text-violeta motion-reduce:animate-none"
        />
      ) : (
        <Check
          size={14}
          className={failed ? "shrink-0 text-rojo-hondo" : "shrink-0 text-violeta"}
        />
      )}
      <span className={failed ? "text-rojo-hondo" : undefined}>{statusText}</span>
    </div>
  );

  if (chrome === "line") {
    return (
      <div className="my-1">
        {line}
        {body}
      </div>
    );
  }

  return (
    <div className="my-1.5 rounded-xl border border-linea/70 bg-papel/50 px-3 py-2">
      <div className="font-medium">{line}</div>
      {body}
    </div>
  );
}

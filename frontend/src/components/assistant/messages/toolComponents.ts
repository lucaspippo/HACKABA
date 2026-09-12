import ToolCallCard from "../ToolCallCard";
import { toolComponentsByName } from "../tools/registry";

// proponer_conocimiento renders as a MemoryChips pill in MessageExtras, so the
// raw tool call draws nothing. propose_rule keeps its status line (the
// default chrome) and adds the same chip from the tool result — do not
// suppress it here. A presentation choice for one tool belongs in the
// by_name map, never in a branch.
const SUPPRESSED = { proponer_conocimiento: () => null };

export const TOOL_COMPONENTS = {
  Fallback: ToolCallCard,
  by_name: { ...SUPPRESSED, ...toolComponentsByName() },
};

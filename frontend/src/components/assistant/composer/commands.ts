import { AlertTriangle, Boxes, MessageSquarePlus, Target, Users, Wallet } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type SlashCommandAction = "new_thread";

export type SlashCommand = {
  id: string;
  nameKey: string;
  descriptionKey: string;
  icon: LucideIcon;
  feature?: string;
  // Sent verbatim to Angela, in Spanish: the engine reads Spanish, while the
  // name and description the user sees are translated. Same split as the
  // suggestion chips in ChatPanel.
  prompt?: string;
  action?: SlashCommandAction;
};

export const SLASH_COMMANDS: readonly SlashCommand[] = [
  {
    id: "priorities",
    nameKey: "chat.command.priorities.name",
    descriptionKey: "chat.command.priorities.description",
    icon: Target,
    prompt: "¿Cuáles son mis prioridades de hoy?",
  },
  {
    id: "cash",
    nameKey: "chat.command.cash.name",
    descriptionKey: "chat.command.cash.description",
    icon: Wallet,
    feature: "caja",
    prompt: "¿Cómo viene la caja?",
  },
  {
    id: "overdue",
    nameKey: "chat.command.overdue.name",
    descriptionKey: "chat.command.overdue.description",
    icon: Users,
    feature: "cuentas",
    prompt: "¿Quiénes son mis clientes en mora y cuánto me deben?",
  },
  {
    id: "stock",
    nameKey: "chat.command.stock.name",
    descriptionKey: "chat.command.stock.description",
    icon: Boxes,
    feature: "inventario",
    prompt: "¿Dónde está el mayor riesgo de mi inventario?",
  },
  {
    id: "data_health",
    nameKey: "chat.command.data_health.name",
    descriptionKey: "chat.command.data_health.description",
    icon: AlertTriangle,
    feature: "saneamiento",
    prompt: "¿Qué datos tengo para corregir?",
  },
  {
    id: "new_thread",
    nameKey: "chat.command.new_thread.name",
    descriptionKey: "chat.command.new_thread.description",
    icon: MessageSquarePlus,
    action: "new_thread",
  },
];

export function availableCommands(
  hasFeature: (feature: string) => boolean,
  commands: readonly SlashCommand[] = SLASH_COMMANDS,
): SlashCommand[] {
  return commands.filter((command) => !command.feature || hasFeature(command.feature));
}

/** The query after "/", or null when the text is not a lone slash command. */
export function slashQuery(text: string): string | null {
  const match = /^\/([\p{L}\d_-]*)$/u.exec(text);
  return match ? (match[1] ?? "").toLowerCase() : null;
}

export function matchCommands(
  text: string,
  commands: readonly SlashCommand[],
  nameOf: (command: SlashCommand) => string,
): SlashCommand[] {
  const query = slashQuery(text);
  if (query === null) return [];
  return commands.filter((command) => nameOf(command).toLowerCase().startsWith(query));
}

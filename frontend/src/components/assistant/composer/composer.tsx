import { useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import { ComposerPrimitive, useAui, useAuiState } from "@assistant-ui/react";
import {
  ComposerActions,
  ComposerAttachButton,
  ComposerAttachmentChip,
  ComposerAttachments,
  ComposerBar,
  ComposerCommandItem,
  ComposerContext,
  ComposerMenu,
  ComposerPersonItem,
  ComposerSend,
  ComposerToolbar,
  ComposerVoice,
  ComposerVoiceButton,
} from "@/components/composer";
import type { ComposerAttachment } from "@/components/composer";
import { useT } from "../../../lib/i18n";
import { authStore } from "../../../lib/auth";
import { equipoReal } from "../../../lib/equipoReal";
import { SLASH_COMMANDS, availableCommands, matchCommands } from "./commands";
import type { SlashCommand } from "./commands";
import { applyMention, matchMentions } from "./mentions";
import type { Mentionable } from "./mentions";
import { latestUsage } from "./tokenUsage";
import { clearDraft, readDraft, writeDraft } from "./draft";
import type { Draft } from "./draft";
import DraftBanner from "./DraftBanner";

const DRAFT_DEBOUNCE_MS = 400;

function useTeam(): Mentionable[] {
  const [team, setTeam] = useState<Mentionable[]>([]);
  useEffect(() => {
    let live = true;
    equipoReal()
      .then((people: { nombre?: string; rol?: string }[]) => {
        if (!live) return;
        setTeam(
          people
            .filter((p) => p.nombre)
            .map((p) => ({ name: p.nombre as string, role: p.rol ?? "" })),
        );
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, []);
  return team;
}

function attachmentView(attachment: {
  name: string;
  status?: { type?: string };
  contentType?: string;
}): ComposerAttachment {
  const status = attachment.status?.type;
  return {
    name: attachment.name,
    meta: attachment.contentType ?? "",
    state: status === "complete" ? "done" : status === "incomplete" ? "error" : "uploading",
    kind: "text",
  };
}

export default function Composer({ leading }: { leading?: ReactNode }) {
  const t = useT();
  const aui = useAui();
  const text = useAuiState((s) => s.composer.text);
  const isRunning = useAuiState((s) => s.thread.isRunning);
  const canSend = useAuiState((s) => s.composer.canSend);
  const dictation = useAuiState((s) => s.composer.dictation);
  const canDictate = useAuiState((s) => s.thread.capabilities.dictation);
  const canAttach = useAuiState((s) => s.thread.capabilities.attachments);
  const attachments = useAuiState((s) => s.composer.attachments);
  const messages = useAuiState((s) => s.thread.messages);
  const threadId = useAuiState((s) => s.threadListItem.id) ?? "new";

  const team = useTeam();
  const commands = useMemo(() => availableCommands((f) => authStore.tiene(f), SLASH_COMMANDS), []);
  const nameOf = (command: SlashCommand) => t(command.nameKey);

  const commandMatches = matchCommands(text, commands, nameOf);
  const mentionMatches = matchMentions(text, team);
  const [highlight, setHighlight] = useState(0);
  const menuOpen = commandMatches.length > 0 || mentionMatches.length > 0;
  const options = commandMatches.length > 0 ? commandMatches.length : mentionMatches.length;

  useEffect(() => setHighlight(0), [text]);

  const usage = useMemo(() => latestUsage(messages as never), [messages]);

  const [draft, setDraft] = useState<Draft | null>(null);
  const [draftDismissed, setDraftDismissed] = useState(false);
  const draftTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    setDraftDismissed(false);
    setDraft(readDraft(threadId, window.localStorage));
  }, [threadId]);

  useEffect(() => {
    clearTimeout(draftTimer.current);
    draftTimer.current = setTimeout(
      () => writeDraft(threadId, text, window.localStorage),
      DRAFT_DEBOUNCE_MS,
    );
    return () => clearTimeout(draftTimer.current);
  }, [threadId, text]);

  const runCommand = (command: SlashCommand) => {
    aui.composer.setText("");
    if (command.action === "new_thread") aui.threads.switchToNewThread();
    else if (command.prompt) aui.thread.append(command.prompt);
  };

  const pickMention = (person: Mentionable) => {
    aui.composer.setText(applyMention(text, person.name));
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (!menuOpen) return;
    if (event.key === "Escape") {
      event.stopPropagation();
      aui.composer.setText("");
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const step = event.key === "ArrowDown" ? 1 : -1;
      setHighlight((h) => (h + step + options) % options);
      return;
    }
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (commandMatches.length > 0) runCommand(commandMatches[highlight]!);
      else pickMention(mentionMatches[highlight]!);
    }
  };

  const showDraft = draft !== null && !draftDismissed && !text.trim();
  const isDictating = dictation !== undefined;

  return (
    <div className="relative w-full">
      {showDraft && (
        <DraftBanner
          savedAt={draft.savedAt}
          preview={draft.text}
          onRestore={() => {
            aui.composer.setText(draft.text);
            clearDraft(threadId, window.localStorage);
            setDraftDismissed(true);
          }}
          onDiscard={() => {
            clearDraft(threadId, window.localStorage);
            setDraftDismissed(true);
          }}
        />
      )}

      <ComposerMenu open={menuOpen} align="start">
        {commandMatches.map((command, i) => (
          <ComposerCommandItem
            key={command.id}
            command={{
              name: nameOf(command),
              description: t(command.descriptionKey),
              icon: command.icon,
            }}
            active={i === highlight}
            onMouseEnter={() => setHighlight(i)}
            onClick={() => runCommand(command)}
          />
        ))}
        {commandMatches.length === 0 &&
          mentionMatches.map((person, i) => (
            <ComposerPersonItem
              key={person.name}
              person={{ name: person.name, role: person.role as "agent" | "human" }}
              active={i === highlight}
              onMouseEnter={() => setHighlight(i)}
              onClick={() => pickMention(person)}
            />
          ))}
      </ComposerMenu>

      <ComposerPrimitive.Root asChild>
        <ComposerBar>
          {attachments.length > 0 && (
            <ComposerAttachments>
              {attachments.map((attachment) => (
                <ComposerAttachmentChip
                  key={attachment.id}
                  attachment={attachmentView(attachment as never)}
                  removeLabel={(name) => t("chat.composer.remove", { name })}
                  onRemove={() => aui.composer.attachment({ id: attachment.id }).remove()}
                />
              ))}
            </ComposerAttachments>
          )}

          {isDictating ? (
            <ComposerVoice
              recording={dictation.status.type === "running"}
              seconds={0}
              transcribingLabel={t("chat.composer.transcribing")}
            />
          ) : (
            <ComposerPrimitive.Input
              rows={1}
              onKeyDown={onKeyDown}
              placeholder={isRunning ? t("angela.ph_trabajando") : t("angela.ph_input")}
              className="min-h-11 w-full resize-none bg-transparent px-3 py-2.5 text-[0.95rem] leading-snug caret-violeta outline-none placeholder:text-tinta-suave/70"
            />
          )}

          <ComposerToolbar>
            <ComposerActions>
              {leading}
              {canAttach && (
                <ComposerPrimitive.AddAttachment asChild>
                  <ComposerAttachButton label={t("chat.composer.attach")} />
                </ComposerPrimitive.AddAttachment>
              )}
            </ComposerActions>
            <ComposerActions>
              {usage && (
                <ComposerContext
                  usage={usage}
                  labels={{
                    title: t("chat.context.title"),
                    system: t("chat.context.system"),
                    tools: t("chat.context.tools"),
                    messages: t("chat.context.messages"),
                    total: t("chat.context.total"),
                    trigger: t("chat.context.trigger"),
                  }}
                />
              )}
              {canDictate && (
                <ComposerVoiceButton
                  active={isDictating}
                  startLabel={t("chat.composer.voice_start")}
                  stopLabel={t("chat.composer.voice_stop")}
                  onClick={() =>
                    isDictating ? aui.composer.stopDictation() : aui.composer.startDictation()
                  }
                />
              )}
              <ComposerSend
                streaming={isRunning}
                idle={canSend}
                sendLabel={t("chat.composer.send")}
                stopLabel={t("chat.composer.stop")}
                onClick={() => (isRunning ? aui.composer.cancel() : aui.composer.send())}
              />
            </ComposerActions>
          </ComposerToolbar>
        </ComposerBar>
      </ComposerPrimitive.Root>
    </div>
  );
}

import { useMemo } from "react";
import { useAuiState } from "@assistant-ui/react";

export type VisibleThread = {
  remoteId: string;
  title: string;
  lastMessageAt: Date;
};

export type DayLabels = {
  today: string;
  yesterday: string;
  older: string;
};

export type ThreadGroup = {
  label: string;
  items: VisibleThread[];
};

function isSameDay(a: Date, b: Date) {
  return a.toDateString() === b.toDateString();
}

export function groupByDay(
  threads: readonly VisibleThread[],
  labels: DayLabels,
  now: Date = new Date(),
): ThreadGroup[] {
  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  const groups: ThreadGroup[] = [
    { label: labels.today, items: [] },
    { label: labels.yesterday, items: [] },
    { label: labels.older, items: [] },
  ];
  for (const thread of threads) {
    if (isSameDay(thread.lastMessageAt, now)) groups[0]!.items.push(thread);
    else if (isSameDay(thread.lastMessageAt, yesterday)) groups[1]!.items.push(thread);
    else groups[2]!.items.push(thread);
  }
  return groups.filter((group) => group.items.length > 0);
}

// The thread list the runtime already maintains, persisted in localStorage by
// chatRuntimeProvider.
export function useVisibleThreads(untitled: string): VisibleThread[] {
  const threadItems = useAuiState((s) => s.threads.threadItems);
  return useMemo(
    () =>
      threadItems
        .filter((t) => t.remoteId && t.status === "regular")
        .map((t) => ({
          remoteId: t.remoteId as string,
          title: t.title?.trim() || untitled,
          lastMessageAt: t.lastMessageAt ?? new Date(),
        }))
        .sort((a, b) => b.lastMessageAt.getTime() - a.lastMessageAt.getTime()),
    [threadItems, untitled],
  );
}

export function useActiveThreadTitle(fallback = "Ángela") {
  return useAuiState((s) => s.threadListItem.title)?.trim() || fallback;
}

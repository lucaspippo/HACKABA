import { describe, expect, it } from "vitest";
import { groupByDay } from "./threads";
import type { VisibleThread } from "./threads";

const LABELS = { today: "Hoy", yesterday: "Ayer", older: "Anteriores" };
const NOW = new Date("2026-07-07T15:00:00");

function thread(iso: string, title = "t"): VisibleThread {
  return { remoteId: iso, title, lastMessageAt: new Date(iso) };
}

describe("groupByDay", () => {
  it("puts the same calendar day under today, whatever the hour", () => {
    const groups = groupByDay([thread("2026-07-07T01:00:00")], LABELS, NOW);
    expect(groups).toHaveLength(1);
    expect(groups[0]!.label).toBe("Hoy");
  });

  it("separates yesterday from earlier", () => {
    const groups = groupByDay(
      [thread("2026-07-06T10:00:00"), thread("2026-07-01T10:00:00")],
      LABELS,
      NOW,
    );
    expect(groups.map((g) => g.label)).toEqual(["Ayer", "Anteriores"]);
  });

  it("omits empty groups rather than rendering bare headings", () => {
    const groups = groupByDay([thread("2026-07-01T10:00:00")], LABELS, NOW);
    expect(groups).toHaveLength(1);
    expect(groups[0]!.label).toBe("Anteriores");
  });

  it("crosses a month boundary correctly", () => {
    const groups = groupByDay([thread("2026-06-30T23:30:00")], LABELS, new Date("2026-07-01T09:00:00"));
    expect(groups[0]!.label).toBe("Ayer");
  });

  it("returns nothing for no threads", () => {
    expect(groupByDay([], LABELS, NOW)).toEqual([]);
  });
});

import { useState } from "react";
import type { ToolCallMessagePartProps } from "@assistant-ui/react";
import ToolFallback from "./Fallback";
import { TOOL_PRESENTERS, presenterFor } from "./registry";
import { toolLabels } from "./labels";
import fixtures from "./fixtures.generated.json";

/**
 * Every tool presenter, rendered from a saved tool result. No API, no key, no
 * model call — so a layout change is a page reload instead of a chat turn,
 * and the states most likely to be broken (`ok:false`, an empty series, a
 * tool with no presenter at all) are reachable at all.
 *
 * Presenters are pure functions of (args, result) by contract, so calling
 * them directly is faithful. What this does NOT cover: the tool card's chrome
 * and its running state, which need the assistant-ui runtime.
 *
 * Regenerate the fixtures from real tool results:
 *   py backend/scripts/generate_tool_fixtures.py
 */

type Fixture = { toolName: string; args: Record<string, unknown>; result: unknown };

const FIXTURES = fixtures as Record<string, Fixture>;

/** The props a presenter sees. `status` is settled: a fixture is a finished call. */
function propsFor(fixture: Fixture, id: string): ToolCallMessagePartProps {
  return {
    toolName: fixture.toolName,
    toolCallId: `showcase-${id}`,
    args: fixture.args,
    argsText: JSON.stringify(fixture.args),
    result: fixture.result,
    status: { type: "complete" },
  } as unknown as ToolCallMessagePartProps;
}

function Panel({ id, fixture }: { id: string; fixture: Fixture }) {
  const [showJson, setShowJson] = useState(false);
  const presenter = presenterFor(fixture.toolName);
  const props = propsFor(fixture, id);
  const body = presenter?.render
    ? presenter.render(props as never)
    : <ToolFallback {...props} />;

  return (
    <section className="rounded-xl border border-linea/70 bg-papel/50 p-4">
      <header className="mb-3 flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2 className="text-base font-medium text-tinta">{id}</h2>
        <code className="rounded bg-papel-hondo px-1.5 py-0.5 text-xs text-tinta-suave">
          {fixture.toolName}
        </code>
        <span className="text-xs text-tinta-suave">
          {presenter ? "presenter" : "Fallback"} · {toolLabels(fixture.toolName).done}
        </span>
        <button
          onClick={() => setShowJson((v) => !v)}
          className="ml-auto rounded border border-linea/70 px-2 py-0.5 text-xs text-tinta-suave hover:text-tinta"
        >
          {showJson ? "ocultar JSON" : "ver JSON"}
        </button>
      </header>

      <div className="rounded-lg bg-papel p-3">{body}</div>

      {showJson && (
        <pre className="mt-3 max-h-80 overflow-auto rounded-lg bg-papel-hondo p-3 text-xs leading-relaxed text-tinta-suave">
          {JSON.stringify({ args: fixture.args, result: fixture.result }, null, 2)}
        </pre>
      )}
    </section>
  );
}

export default function Showcase() {
  const entries = Object.entries(FIXTURES);
  const covered = new Set(entries.map(([, f]) => f.toolName));
  const uncovered = Object.keys(TOOL_PRESENTERS).filter((name) => !covered.has(name));

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="text-2xl font-medium text-tinta">Tool presenters</h1>
      <p className="mt-1 max-w-2xl text-sm text-tinta-suave">
        {entries.length} saved tool results, rendered with no backend and no API key.
        A presenter is an override; anything without one falls through to the
        shape-based Fallback.
      </p>

      {uncovered.length > 0 && (
        <p className="mt-3 rounded-lg border border-oro/40 bg-oro/10 px-3 py-2 text-sm text-oro-tinta">
          No fixture yet for: <b>{uncovered.join(", ")}</b>
        </p>
      )}

      <div className="mt-6 flex flex-col gap-5">
        {entries.map(([id, fixture]) => (
          <Panel key={id} id={id} fixture={fixture} />
        ))}
      </div>
    </div>
  );
}

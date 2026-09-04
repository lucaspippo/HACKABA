import { describe, expect, it, vi } from "vitest";
import { ChatStreamError } from "./errors";
import { createChatModelAdapter, type FetchStream } from "./adapter";

/** A Response whose body streams the given chunks verbatim. */
function responseOf(chunks: string[]): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
  return new Response(body, { status: 200 });
}

function adapterOver(chunks: string[]) {
  return createChatModelAdapter({ fetchStream: async () => responseOf(chunks) });
}

const userMessage = {
  role: "user" as const,
  content: [{ type: "text" as const, text: "¿cuánta plata tengo parada?" }],
};

async function runAll(chunks: string[]) {
  const adapter = adapterOver(chunks);
  const results = [];
  for await (const r of adapter.run({
    messages: [userMessage],
    abortSignal: new AbortController().signal,
  } as never)) {
    results.push(r);
  }
  return results;
}

describe("text deltas", () => {
  it("appends deltas into a single text part", async () => {
    const results = await runAll([
      '{"type":"text","delta":"Tenés "}\n',
      '{"type":"text","delta":"$4.2M "}\n',
      '{"type":"text","delta":"parados."}\n',
      '{"type":"done","result":{"mode":"claude","tools_used":[],"actions":[]}}\n',
    ]);
    const final = results.at(-1)!;
    expect(final.content).toEqual([
      { type: "text", text: "Tenés $4.2M parados." },
    ]);
  });

  it("survives a chunk boundary splitting a line mid-JSON", async () => {
    const results = await runAll([
      '{"type":"text","delta":"Ten',
      'és $4.2M"}\n{"type":"done","result":{"mode":"claude","tools_used":[],"actions":[]}}\n',
    ]);
    expect(results.at(-1)!.content).toEqual([
      { type: "text", text: "Tenés $4.2M" },
    ]);
  });

  it("starts a new text part after a tool call", async () => {
    const results = await runAll([
      '{"type":"text","delta":"Voy a mirar."}\n',
      '{"type":"tool_call","id":"t1","name":"plata_en","input":{}}\n',
      '{"type":"tool_result","id":"t1","result":{"total":42}}\n',
      '{"type":"text","delta":"Listo."}\n',
      '{"type":"done","result":{"mode":"claude","tools_used":["plata_en"],"actions":[]}}\n',
    ]);
    const content = results.at(-1)!.content!;
    expect(content.map((p) => p.type)).toEqual(["text", "tool-call", "text"]);
    expect((content[0] as { text: string }).text).toBe("Voy a mirar.");
    expect((content[2] as { text: string }).text).toBe("Listo.");
  });
});

describe("tool calls", () => {
  it("attaches the result to the matching tool-call part", async () => {
    const results = await runAll([
      '{"type":"tool_call","id":"t1","name":"plata_en","input":{"categoria":"lacteos"}}\n',
      '{"type":"tool_result","id":"t1","result":{"total":42}}\n',
      '{"type":"done","result":{"mode":"claude","tools_used":["plata_en"],"actions":[]}}\n',
    ]);
    const part = results.at(-1)!.content![0] as {
      type: string; toolName: string; args: unknown; result: unknown;
    };
    expect(part.type).toBe("tool-call");
    expect(part.toolName).toBe("plata_en");
    expect(part.args).toEqual({ categoria: "lacteos" });
    expect(part.result).toEqual({ total: 42 });
  });

  it("keeps a call's status line in metadata, keyed by call id", async () => {
    const results = await runAll([
      '{"type":"tool_call","id":"t1","name":"plata_en","input":{},"label":"mirando la caja"}\n',
      '{"type":"tool_result","id":"t1","result":{"total":42}}\n',
      '{"type":"done","result":{"mode":"claude","tools_used":["plata_en"],"actions":[]}}\n',
    ]);
    const last = results.at(-1)!;
    expect(last.metadata!.custom!.toolLabels).toEqual({ t1: "mirando la caja" });
    expect((last.content![0] as { args: unknown }).args).toEqual({});
  });

  it("omits toolLabels entirely when no call sent a status line", async () => {
    const results = await runAll([
      '{"type":"tool_call","id":"t1","name":"plata_en","input":{}}\n',
      '{"type":"tool_result","id":"t1","result":{"total":42}}\n',
      '{"type":"done","result":{"mode":"claude","tools_used":["plata_en"],"actions":[]}}\n',
    ]);
    expect(results.at(-1)!.metadata!.custom!.toolLabels).toBeUndefined();
  });
});

describe("notices", () => {
  it("renders the cap notice with no text events at all", async () => {
    const results = await runAll([
      '{"type":"notice","kind":"cap"}\n',
      '{"type":"done","result":{"mode":"cap","tools_used":[],"actions":[]}}\n',
    ]);
    const final = results.at(-1)!;
    expect(final.metadata?.custom?.notices).toEqual([{ kind: "cap" }]);
  });
});

describe("errors", () => {
  it("throws a ChatStreamError on an error event instead of faking a message", async () => {
    await expect(
      runAll([
        '{"type":"error","code":"model_failed","retryable":true}\n',
      ]),
    ).rejects.toBeInstanceOf(ChatStreamError);
  });

  it("keeps the server-supplied code", async () => {
    await expect(
      runAll(['{"type":"error","code":"rate_limit","retryable":true}\n']),
    ).rejects.toMatchObject({ code: "rate_limit" });
  });

  it("returns quietly when aborted rather than surfacing an error", async () => {
    const controller = new AbortController();
    const adapter = createChatModelAdapter({
      fetchStream: async () => {
        controller.abort();
        throw new ChatStreamError("aborted");
      },
    });
    const results = [];
    for await (const r of adapter.run({
      messages: [userMessage],
      abortSignal: controller.signal,
    } as never)) {
      results.push(r);
    }
    expect(results).toEqual([]);
  });

  it("ignores an unparseable line rather than dying", async () => {
    const results = await runAll([
      "not json at all\n",
      '{"type":"text","delta":"ok"}\n',
      '{"type":"done","result":{"mode":"claude","tools_used":[],"actions":[]}}\n',
    ]);
    expect(results.at(-1)!.content).toEqual([{ type: "text", text: "ok" }]);
  });
});

describe("defensive fallback", () => {
  it("synthesizes a text part when a run produces no parts but an answer", async () => {
    const results = await runAll([
      '{"type":"done","result":{"mode":"cap","tools_used":[],"actions":[],"answer":"Sin contenido."}}\n',
    ]);
    expect(results.at(-1)!.content).toEqual([
      { type: "text", text: "Sin contenido." },
    ]);
  });
});

describe("request shape", () => {
  it("sends the newest message separately from the history", async () => {
    const fetchStream = vi.fn<FetchStream>(async () =>
      responseOf(['{"type":"done","result":{"mode":"claude","tools_used":[],"actions":[]}}\n']),
    );
    const adapter = createChatModelAdapter({ fetchStream });
    for await (const _ of adapter.run({
      messages: [
        { role: "user", content: [{ type: "text", text: "hola" }] },
        { role: "assistant", content: [{ type: "text", text: "buenas" }] },
        { role: "user", content: [{ type: "text", text: "¿y la caja?" }] },
      ],
      abortSignal: new AbortController().signal,
    } as never)) { /* drain */ }

    expect(fetchStream).toHaveBeenCalledOnce();
    const [message, history] = fetchStream.mock.calls[0]!;
    expect(message).toBe("¿y la caja?");
    expect(history).toEqual([
      { role: "user", content: "hola" },
      { role: "assistant", content: "buenas" },
    ]);
  });
});

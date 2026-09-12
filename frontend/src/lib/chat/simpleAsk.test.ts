import { describe, expect, it } from "vitest";
import { ChatStreamError } from "./errors";
import { askAngela } from "./simpleAsk";

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

function askOver(chunks: string[], onDelta?: (s: string) => void) {
  return askAngela("¿tenemos aceite?", {
    fetchStream: async () => responseOf(chunks),
    onDelta,
  });
}

describe("askAngela", () => {
  it("resolves the full text once the stream ends", async () => {
    const text = await askOver([
      '{"type":"text","delta":"Sí, "}\n',
      '{"type":"text","delta":"quedan 12 unidades."}\n',
      '{"type":"done","result":{"mode":"claude","tools_used":[],"actions":[]}}\n',
    ]);
    expect(text).toBe("Sí, quedan 12 unidades.");
  });

  it("reports the running partial via onDelta", async () => {
    const partials: string[] = [];
    await askOver([
      '{"type":"text","delta":"Sí, "}\n',
      '{"type":"text","delta":"quedan 12."}\n',
      '{"type":"done","result":{"mode":"claude","tools_used":[],"actions":[]}}\n',
    ], (s) => partials.push(s));
    expect(partials).toEqual(["Sí, ", "Sí, quedan 12."]);
  });

  it("throws a ChatStreamError on a server error event", async () => {
    await expect(askOver([
      '{"type":"error","code":"model_unavailable","retryable":false}\n',
    ])).rejects.toBeInstanceOf(ChatStreamError);
  });

  it("splits a chunk boundary that lands mid-line", async () => {
    const text = await askOver([
      '{"type":"text","del',
      'ta":"reconstituido"}\n{"type":"done","result":{"mode":"claude","tools_used":[],"actions":[]}}\n',
    ]);
    expect(text).toBe("reconstituido");
  });
});

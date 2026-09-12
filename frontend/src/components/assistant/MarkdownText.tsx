import { MarkdownTextPrimitive } from "@assistant-ui/react-markdown";
import remarkGfm from "remark-gfm";
import KnowledgeCite from "./KnowledgeCite";
import { citedId } from "./knowledgeStore";

const components = {
  p: (props: object) => <p className="mb-2 last:mb-0" {...props} />,
  strong: (props: object) => <strong className="font-semibold text-tinta" {...props} />,
  em: (props: object) => <em className="italic" {...props} />,
  ol: (props: object) => <ol className="mb-2 list-decimal space-y-1 pl-5 last:mb-0" {...props} />,
  ul: (props: object) => <ul className="mb-2 list-disc space-y-1 pl-5 last:mb-0" {...props} />,
  li: (props: object) => <li className="leading-snug" {...props} />,
  // Angela marks a rule she took from the business's memory as
  // [·](memoria:<id>). Rendering it through the link slot keeps it out of the
  // markdown pipeline: worst case it degrades to an inert link, never a
  // broken marker in the middle of a sentence.
  a: ({ href, ...props }: { href?: string } & object) => {
    const cited = citedId(href);
    if (cited) return <KnowledgeCite id={cited} />;
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="font-medium text-violeta underline underline-offset-2"
        {...props}
      />
    );
  },
  h1: (props: object) => <h3 className="mb-1.5 font-display text-base font-bold" {...props} />,
  h2: (props: object) => <h3 className="mb-1.5 font-display text-base font-bold" {...props} />,
  h3: (props: object) => <h4 className="mb-1.5 font-display text-base font-bold" {...props} />,
  h4: (props: object) => <h4 className="mb-1.5 font-display text-sm font-bold" {...props} />,
  blockquote: (props: object) => (
    <blockquote className="mb-2 border-l-2 border-linea pl-3 text-tinta-suave last:mb-0" {...props} />
  ),
  hr: (props: object) => <hr className="my-3 border-linea" {...props} />,
  code: (props: object) => (
    <code className="rounded bg-papel px-1 py-0.5 font-mono text-[0.85em]" {...props} />
  ),
  pre: (props: object) => (
    <pre className="mb-2 overflow-x-auto rounded-xl bg-papel p-3 text-sm last:mb-0" {...props} />
  ),
  table: (props: object) => (
    <div className="mb-2 overflow-x-auto last:mb-0">
      <table className="w-full border-collapse text-sm" {...props} />
    </div>
  ),
  th: (props: object) => (
    <th className="border-b border-linea px-2 py-1 text-left font-semibold" {...props} />
  ),
  td: (props: object) => <td className="border-b border-linea px-2 py-1" {...props} />,
};

export default function MarkdownText() {
  return <MarkdownTextPrimitive remarkPlugins={[remarkGfm]} components={components} />;
}

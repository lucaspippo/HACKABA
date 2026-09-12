import { createContext, useContext, type ReactNode } from "react";

type OpenKnowledge = (id: string, query: string) => void;

const KnowledgeOpenContext = createContext<OpenKnowledge>(() => {});

/** Lets a citation chip open the memory panel of the ChatPanel it lives in. */
export function KnowledgeOpenProvider({
  onOpen,
  children,
}: {
  onOpen: OpenKnowledge;
  children: ReactNode;
}) {
  return (
    <KnowledgeOpenContext.Provider value={onOpen}>
      {children}
    </KnowledgeOpenContext.Provider>
  );
}

export function useOpenKnowledge(): OpenKnowledge {
  return useContext(KnowledgeOpenContext);
}

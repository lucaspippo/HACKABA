import { useQuery } from "@tanstack/react-query";
import { queries } from "./queries";

export { queryClient } from "./client";
export { keys } from "./keys";
export { queries } from "./queries";
export { MUTATIONS, invalidationKeys, runMutation, useApiMutation, invalidateShell } from "./mutations";

export function useApiQuery(name, args = [], options = {}) {
  const spec = queries[name];
  if (!spec) throw new Error(`Unknown query: ${name}`);
  const list = Array.isArray(args) ? args : [args];
  return useQuery({ ...spec(...list), ...options });
}

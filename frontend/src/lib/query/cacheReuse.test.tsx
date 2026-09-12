// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../api";
import { queries } from "./queries";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("query cache reuse", () => {
  it("does not refetch inventario when remounting against the same client", async () => {
    const inventario = vi.spyOn(api, "inventario").mockResolvedValue({ meta: { cached: true } });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: Infinity } },
    });
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );

    const first = renderHook(() => useQuery(queries.inventario()), { wrapper });
    await waitFor(() => expect(first.result.current.isSuccess).toBe(true));
    expect(first.result.current.data).toEqual({ meta: { cached: true } });
    first.unmount();

    const second = renderHook(() => useQuery(queries.inventario()), { wrapper });
    await waitFor(() => expect(second.result.current.isSuccess).toBe(true));
    expect(second.result.current.data).toEqual({ meta: { cached: true } });
    expect(inventario).toHaveBeenCalledTimes(1);
    second.unmount();
  });
});

import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Instancias: piloto (API 8000, front 5173) y demo (API 8001, front 5174).
// El front del demo se levanta con: POLPILOT_API_PORT=8001 npm run dev -- --port 5174
const apiPort = process.env.POLPILOT_API_PORT || "8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    port: 5173,
    // Proxy a la API de FastAPI durante desarrollo.
    // 127.0.0.1 y NO "localhost": en Windows, "localhost" resuelve primero a
    // ::1 y —con uvicorn escuchando en IPv4— cada request se come ~2 s de
    // timeout antes de reintentar. Medido acá: 2.04 s contra 0.007 s. Es sólo
    // el proxy de desarrollo (en producción el backend sirve el front: no hay
    // proxy ni segundo origen), pero hacía que el demo local pareciera lento.
    proxy: {
      "/api": `http://127.0.0.1:${apiPort}`,
    },
  },
  build: {
    rollupOptions: {
      output: {
        // One 2.9 MB file carried React Flow, force-graph, recharts and
        // assistant-ui into every first load, even a Home that uses none of
        // them. Three named chunks: the graph engines (~600 KB, only the map
        // and the brain), the chat runtime, and the charts. Splitting alone
        // does not defer them — the sections that import them are lazy now
        // (DesktopApp.jsx), so a chunk is fetched the first time its screen
        // opens. The chat chunk is the exception: ChatRuntimeProvider wraps
        // the whole app, so it still loads eagerly, just as its own file.
        manualChunks(id) {
          if (!id.includes("node_modules")) return undefined;
          if (/[\\/]node_modules[\\/](@xyflow|react-force-graph-2d|force-graph|d3-force-3d|kapsule)[\\/]/.test(id)) return "grafo";
          if (/[\\/]node_modules[\\/]@assistant-ui[\\/]/.test(id)) return "chat";
          if (/[\\/]node_modules[\\/](recharts|victory-vendor)[\\/]/.test(id)) return "graficos";
          return undefined;
        },
      },
    },
  },
  test: {
    // DOM suites opt in per file with `// @vitest-environment jsdom`.
    environment: "node",
    // Testing Library registers its auto-cleanup only when afterEach is global.
    globals: true,
    include: ["src/**/*.test.{ts,tsx}"],
    setupFiles: ["./src/test-setup.ts"],
  },
});

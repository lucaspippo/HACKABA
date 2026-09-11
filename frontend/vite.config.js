import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Instancias: piloto (API 8000, front 5173) y demo (API 8001, front 5174).
// El front del demo se levanta con: POLPILOT_API_PORT=8001 npm run dev -- --port 5174
const apiPort = process.env.POLPILOT_API_PORT || "8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
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
});

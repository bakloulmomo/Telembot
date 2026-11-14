import { fileURLToPath, URL } from "node:url";
import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      // un solo file per il microfono, condiviso con la pagina /test del backend
      "@voice": fileURLToPath(new URL("../backend/app/static/voice.js", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    fs: { allow: [".."] },
    proxy: {
      "/api": { target: BACKEND, changeOrigin: true },
      "/files": { target: BACKEND, changeOrigin: true },
    },
  },
});

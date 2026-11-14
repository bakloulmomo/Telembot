import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// The backend (backend/) runs on http://localhost:8000: /api and /files are proxied to it.
const BACKEND = process.env.BACKEND_URL || 'http://localhost:8000'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      // one microphone module, shared with the backend test page /test
      '@voice': fileURLToPath(new URL('../backend/app/static/voice.js', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    fs: { allow: ['..'] },
    proxy: {
      '/api': { target: BACKEND, changeOrigin: true },
      '/files': { target: BACKEND, changeOrigin: true },
    },
  },
})

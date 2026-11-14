import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// The backend (team-13/backend) runs on http://localhost:8000.
// /api and /files are proxied: the app always uses the real backend.
export default defineConfig({
  plugins: [vue()],
  resolve: {
    // the microphone module, shared with the backend test page /test
    alias: { '@voice': fileURLToPath(new URL('../backend/app/static/voice.js', import.meta.url)) },
  },
  server: {
    port: 5173,
    open: true,
    fs: { allow: ['..'] },
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/files': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})

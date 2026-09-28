import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// En desarrollo, /api se redirige al backend FastAPI local.
// En producción (Docker) lo hace Nginx (ver nginx.conf).
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      // Igual que el nginx.conf del repo: /api/v1/animals -> http://localhost:8000/v1/animals
      '/api': {
        target: process.env.VITE_BACKEND_URL || 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})

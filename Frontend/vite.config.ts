import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

const API_TARGET = process.env.VITE_API_URL ?? 'http://5.39.250.179:8000'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: API_TARGET.replace(/\/$/, ''),
        changeOrigin: true,
        ws: true, // WebSocket для /api/rooms/{id}/chat и /api/rooms/{id}/graph
      },
    },
  },
})

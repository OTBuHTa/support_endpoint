import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        operator: 'index.html',
        portal: 'portal.html',
      },
    },
  },
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8100' },
  },
})

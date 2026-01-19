import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/upload': {
        target: 'http://0.0.0.0:80',
        changeOrigin: true
      },
      '/chat': {
        target: 'http://0.0.0.0:80',
        changeOrigin: true
      }
    }
  }
})

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/analyze': 'http://127.0.0.1:5000',
      // Fix: Use regex to match /screen and /screen/* but NOT /screener
      '^/screen($|/)': 'http://127.0.0.1:5000',
      '/journal': 'http://127.0.0.1:5000',
      '/download': 'http://127.0.0.1:5000',
      '/dashboard': 'http://127.0.0.1:5000',
      '/feedback': 'http://127.0.0.1:5000',
      '/static': 'http://127.0.0.1:5000',
      '/health': 'http://127.0.0.1:5000',
      '/backtest': 'http://127.0.0.1:5000',
    }
  },
  build: {
    // Default output directory is 'dist', which is required for Dockerfile COPY
    // outDir: '../webapp/static/react_build',
    emptyOutDir: true
  }
})

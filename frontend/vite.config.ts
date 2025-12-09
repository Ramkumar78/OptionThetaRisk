import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/analyze': 'http://127.0.0.1:5000',
      '/screen': 'http://127.0.0.1:5000',
      '/journal': 'http://127.0.0.1:5000',
      '/download': 'http://127.0.0.1:5000',
      '/dashboard': 'http://127.0.0.1:5000',
      '/feedback': 'http://127.0.0.1:5000'
    }
  }
})

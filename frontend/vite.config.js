import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Port is pinned and strict: the backend allowlists http://localhost:5173 for CORS,
// so failing loudly beats silently serving on 5174 and hitting opaque CORS errors.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    strictPort: true,
  },
})

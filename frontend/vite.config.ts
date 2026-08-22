import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // pinned (not the 5173 default) to avoid colliding with other local
  // projects (e.g. an unrelated one already running in this user's IDE)
  server: { port: 5175, strictPort: true },
})

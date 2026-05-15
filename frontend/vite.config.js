import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Bind all interfaces so http://127.0.0.1:5174 works (Stripe success_url often uses 127.0.0.1;
    // default Vite can listen on IPv6 ::1 only, which causes ERR_CONNECTION_REFUSED on 127.0.0.1).
    host: true,
    port: 5174,
    strictPort: true,
  },
  build: {
    sourcemap: false,
  },
})

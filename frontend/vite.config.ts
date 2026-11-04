import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // Bez przeskakiwania na inny port: backend dopuszcza w CORS tylko http://localhost:5173,
    // więc zajęty port ma dać czytelny błąd, a nie stronę, która nie może połączyć się z API.
    strictPort: true,
  },
})

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0', // Allows external Docker network traffic
    port: 5173,
    watch: {
      usePolling: true, // Guarantees live hot-reloading inside Linux Docker containers
    },
  },
});
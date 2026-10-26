import { defineConfig } from 'vite';

export default defineConfig({
  base: process.env.MAHJONG_BASE || './',
  worker: { format: 'es' },
  build: { target: 'es2022' },
  server: { port: 5173, strictPort: true },
  preview: { port: 4173, strictPort: true },
});

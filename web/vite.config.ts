import { defineConfig } from 'vite';

export default defineConfig({
  base: process.env.MAHJONG_BASE || './',
  // We already ship the pinned runtime in public/ort; avoid bundling a second WASM copy.
  resolve: { conditions: ['onnxruntime-web-use-extern-wasm', 'module', 'browser', 'development|production'] },
  worker: { format: 'es' },
  build: { target: 'es2022' },
  server: { port: 5173, strictPort: true },
  preview: { port: 4173, strictPort: true },
});

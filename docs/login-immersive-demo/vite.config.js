import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig(({ mode }) => ({
  base: '/_login/',
  plugins: [tailwindcss()],
  publicDir: false,
  build: mode === 'release' ? {
    outDir: '../../server-reference/public/login-ui',
    emptyOutDir: true,
    rollupOptions: { output: { entryFileNames: 'login.js' } },
  } : {},
  server: { host: '127.0.0.1', port: 8772, strictPort: true },
  preview: { host: '127.0.0.1', port: 8772, strictPort: true },
}));

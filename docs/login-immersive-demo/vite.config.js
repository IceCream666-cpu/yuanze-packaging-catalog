import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  base: '/_login/',
  plugins: [tailwindcss()],
  publicDir: '../../server-reference/public/brand',
  server: { host: '127.0.0.1', port: 8772, strictPort: true },
  preview: { host: '127.0.0.1', port: 8772, strictPort: true },
});

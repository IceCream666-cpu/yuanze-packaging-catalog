import {defineConfig} from 'vite';
import {FEATURED_SIZES} from './src/media-policy.js';
export default defineConfig(({mode}) => ({
  base: mode === 'showroom' ? '/showroom/' : './',
  server: {host: '127.0.0.1', port: 8784, strictPort: true},
  preview: {host: '127.0.0.1', port: 8784, strictPort: true},
  ...(mode === 'showroom' ? {
    publicDir: false,
    plugins: [{name: 'showroom-title', transformIndexHtml: html => html.replace(' · 动效预览', '').replace('</head>', `<link rel="preload" as="image" type="image/webp" href="/showroom/assets/featured/poster-012-1024.webp" imagesrcset="/showroom/assets/featured/poster-012-640.webp 640w, /showroom/assets/featured/poster-012-1024.webp 1024w" imagesizes="${FEATURED_SIZES}" fetchpriority="high"></head>`)}],
    build: {
      outDir: 'release', copyPublicDir: false, cssCodeSplit: false,
      rollupOptions: {output: {entryFileNames: 'preview.js', assetFileNames: 'preview.[ext]', inlineDynamicImports: true}},
    },
  } : {}),
}));

import {defineConfig} from 'vite';
export default defineConfig(({mode}) => ({
  base: mode === 'showroom' ? '/showroom/' : './',
  server: {host: '127.0.0.1', port: 8784, strictPort: true},
  preview: {host: '127.0.0.1', port: 8784, strictPort: true},
  ...(mode === 'showroom' ? {
    publicDir: false,
    plugins: [{name: 'showroom-title', transformIndexHtml: html => html.replace(' · 动效预览', '').replace('</head>', '<link rel="preload" as="image" type="image/webp" href="/showroom/assets/featured/poster-012-640.webp" media="(max-width: 640px)" fetchpriority="high"><link rel="preload" as="image" type="image/webp" href="/showroom/assets/featured/poster-012-1024.webp" media="(min-width: 641px)" fetchpriority="high"></head>')}],
    build: {
      outDir: 'release', copyPublicDir: false, cssCodeSplit: false,
      rollupOptions: {output: {entryFileNames: 'preview.js', assetFileNames: 'preview.[ext]', inlineDynamicImports: true}},
    },
  } : {}),
}));

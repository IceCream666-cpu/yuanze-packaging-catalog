import {defineConfig} from 'vite';
export default defineConfig(({mode}) => ({
  base: mode === 'showroom' ? '/showroom/' : './',
  server: {host: '127.0.0.1', port: 8784, strictPort: true},
  preview: {host: '127.0.0.1', port: 8784, strictPort: true},
  ...(mode === 'showroom' ? {
    publicDir: false,
    plugins: [{name: 'showroom-title', transformIndexHtml: html => html.replace(' · 动效预览', '').replace('</head>', '<link rel="preload" as="image" type="image/webp" href="/showroom/assets/featured/poster-012-640.webp" fetchpriority="high"></head>')}],
    build: {
      outDir: 'release', copyPublicDir: false, cssCodeSplit: true, manifest: true,
      rollupOptions: {output: {
        entryFileNames: 'preview.js',
        chunkFileNames: 'assets/packaging/[name]-[hash].js',
        assetFileNames: asset => (asset.names || [asset.name]).includes('index.css')
          ? 'preview.css' : 'assets/packaging/[name]-[hash][extname]',
      }},
    },
  } : {}),
}));

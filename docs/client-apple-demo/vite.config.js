import { defineConfig } from 'vite';
export default defineConfig(({mode})=>({
 base:mode==='showroom'?'/showroom/':'/',
 server:{host:'127.0.0.1',port:8773,strictPort:true},
 preview:{host:'127.0.0.1',port:8773,strictPort:true},
 ...(mode==='showroom'?{build:{
  outDir:'release',copyPublicDir:false,cssCodeSplit:false,
  rollupOptions:{output:{entryFileNames:'preview.js',assetFileNames:'preview.[ext]',inlineDynamicImports:true}}
 }}:{})
}));

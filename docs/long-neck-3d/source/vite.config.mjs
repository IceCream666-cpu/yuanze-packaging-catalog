import { fileURLToPath } from 'node:url';
const here=fileURLToPath(new URL('.',import.meta.url));
export default {resolve:{alias:{three:here+'../../client-motion-demo/src/structure/vendor/three.module.js'}},build:{outDir:here+'../build',emptyOutDir:true,lib:{entry:here+'viewer.js',name:'LiaoseViewer',formats:['iife'],fileName:()=> 'viewer.js'},minify:true}};

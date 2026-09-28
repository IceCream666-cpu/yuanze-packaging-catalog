import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {pathToFileURL,fileURLToPath} from 'node:url';
export async function evaluateLogin(context) {
  if (!vm.SourceTextModule) throw Error('Run with --experimental-vm-modules');
  Object.assign(context,{AbortController,DOMException,setTimeout,clearTimeout});
  const modules=new Map(),root=fileURLToPath(new URL('../../server-reference/public',import.meta.url));
  const entry=pathToFileURL(path.join(root,'login.js')).href;
  function load(url){if(modules.has(url))return modules.get(url);const file=fileURLToPath(url);if(!file.startsWith(root+path.sep))throw Error('Unexpected module path');const value=new vm.SourceTextModule(fs.readFileSync(file,'utf8'),{context,identifier:url});modules.set(url,value);return value;}
  const module=load(entry);await module.link((specifier,owner)=>load(new URL(specifier,owner.identifier).href));await module.evaluate();
}

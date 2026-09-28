// Evaluate the actual browser module graph inside jsdom. Run Node with
// --experimental-vm-modules; no production imports are removed or stubbed.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {pathToFileURL, fileURLToPath} = require('node:url');

async function evaluateBrowserModule(dom, filename, suffix = '') {
  if (!vm.SourceTextModule) throw new Error('Run Node with --experimental-vm-modules');
  const context = dom.getInternalVMContext();
  const modules = new Map();
  const entry = pathToFileURL(path.resolve(filename)).href;
  const root = path.dirname(fileURLToPath(entry)) + path.sep;
  function load(identifier) {
    if (modules.has(identifier)) return modules.get(identifier);
    const file = fileURLToPath(identifier);
    if (!file.startsWith(root)) throw new Error('Module outside browser source directory');
    const source = fs.readFileSync(file, 'utf8') + (identifier === entry ? suffix : '');
    const module = new vm.SourceTextModule(source, {context, identifier});
    modules.set(identifier, module);
    return module;
  }
  const module = load(entry);
  await module.link((specifier, referencing) => load(new URL(specifier, referencing.identifier).href));
  await module.evaluate();
  return module;
}

module.exports = {evaluateBrowserModule};

import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const root = fileURLToPath(new URL('../../', import.meta.url));
const suites = [
  ['--experimental-vm-modules', 'tests/frontend/catalog-editor-tests.cjs'],
  ['--experimental-vm-modules', 'tests/frontend/admin-workspace-tests.cjs'],
  ['--experimental-vm-modules', 'tests/frontend/client-ui-tests.cjs'],
  ['--experimental-vm-modules', 'tests/frontend/client-tools-tests.cjs'],
  ['--experimental-vm-modules', 'tests/frontend/i18n-tests.cjs'],
  ['--test', 'tests/frontend/mobile-company-preview-tests.cjs'],
  ['--experimental-vm-modules', 'tests/frontend/frontend-fault-tests.mjs'],
  ['--experimental-vm-modules', 'tests/frontend/product-groups-tests.cjs'],
  ['tests/frontend/http-client-tests.mjs'],
  ['--test', 'tests/frontend/catalog-taxonomy-tests.mjs', 'site/test-workflow.mjs'],
];
for (const args of suites) {
  const result = spawnSync(process.execPath, args, {cwd: root, stdio: 'inherit'});
  if (result.error) console.error(result.error);
  if (result.status !== 0) process.exit(result.status ?? 1);
}

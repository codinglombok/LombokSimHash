// Post-build: rename CommonJS output to .cjs so Node treats it as CJS
// inside a `"type": "module"` package. Safe because the emitted bundle
// (dist/cjs/index.js) has no relative imports.
import { renameSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const cjsDir = join(root, 'dist', 'cjs');

for (const name of ['index.js', 'index.d.ts']) {
  const from = join(cjsDir, name);
  if (!existsSync(from)) continue;
  const to = join(cjsDir, name.replace(/\.js$/, '.cjs').replace(/\.d\.ts$/, '.d.cts'));
  renameSync(from, to);
  console.log(`postbuild: ${name} -> ${to.slice(root.length + 1)}`);
}

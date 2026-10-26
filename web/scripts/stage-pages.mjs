import { cpSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../../', import.meta.url));
const dist = path.join(root, 'web/dist');
const docs = path.join(root, 'docs');
// Only these generated paths are owned here; hand-written docs remain untouched.
const owned = ['assets', 'runtime', 'ort', 'models', 'licenses', 'index.html', 'training.json', 'THIRD_PARTY_NOTICES.txt'];
const files = readdirSync(dist);
if (files.some(name => !owned.includes(name))) throw new Error('Unexpected dist entry; review Pages staging paths');
if (!readFileSync(path.join(dist, 'index.html'), 'utf8').includes('/play_mahjong/assets/')) {
  throw new Error('Build with MAHJONG_BASE=/play_mahjong/ before staging');
}
mkdirSync(docs, { recursive: true });
for (const name of owned) {
  if (!files.includes(name)) throw new Error(`Missing release asset: ${name}`);
}
for (const name of owned) {
  const target = path.join(docs, name);
  if (existsSync(target)) rmSync(target, { recursive: true });
  cpSync(path.join(dist, name), target, { recursive: true });
}
writeFileSync(path.join(docs, '.nojekyll'), '');
console.log('Staged static site in docs/. GitHub Pages source: main /docs.');

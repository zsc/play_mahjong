import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync, mkdirSync, copyFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../../', import.meta.url));
const web = path.join(root, 'web');
copyFileSync(path.join(root, 'THIRD_PARTY_NOTICES.md'), path.join(web, 'public/THIRD_PARTY_NOTICES.txt'));
execFileSync('sh', [path.join(root, 'scripts/build_web_engine.sh')], { cwd: root, stdio: 'inherit' });
const loader = path.join(web, 'public/runtime/engine.js');
let code = readFileSync(loader, 'utf8');
// These two checked adaptations turn the pinned compiler's loader into an
// awaitable module and resolve its wasm relative to itself inside a Worker.
if (!code.includes('(js=>') || !code.includes('"src": "engine.assets"')) {
  throw new Error('WASM loader format changed; review the pinned compiler adapter');
}
code = code.replace('(js=>', 'export const ready = (js=>')
  .replace('"src": "engine.assets"', '"src": new URL("./engine.assets", import.meta.url).href');
writeFileSync(loader, code);
const manifest = JSON.parse(readFileSync(path.join(root, 'training/exports/human-candidate-20261026.manifest.json')));
const model = path.join(web, 'assets/candidate.onnx');
const hash = createHash('sha256').update(readFileSync(model)).digest('hex');
if (hash !== manifest.files.onnx.sha256) throw new Error('Candidate ONNX checksum mismatch');
const models = path.join(web, 'public/models');
mkdirSync(models, { recursive: true });
copyFileSync(model, path.join(models, 'candidate.onnx'));
manifest.files.onnx.path = 'candidate.onnx';
writeFileSync(path.join(models, 'candidate.manifest.json'), JSON.stringify(manifest, null, 2));
const ortDir = path.join(web, 'public/ort');
mkdirSync(ortDir, { recursive: true });
for (const name of ['ort-wasm-simd-threaded.wasm', 'ort-wasm-simd-threaded.mjs']) {
  copyFileSync(path.join(web, 'node_modules/onnxruntime-web/dist', name), path.join(ortDir, name));
}
const evidence = JSON.parse(readFileSync(path.join(root, 'benchmarks/human-candidate-holdout.json')));
const timings = JSON.parse(readFileSync(path.join(root, 'benchmarks/ppo-batch-v2-training.json')));
const stats = { selection: evidence.selection, comparisons: evidence.comparisons,
  evaluations: evidence.reports, training: { games: timings.games, samples: timings.samples,
    history: timings.history }, modelCard: '训练模型 + 策略辅助 · 并非模型独立决策',
  sofy: JSON.parse(readFileSync(path.join(root, 'benchmarks/sofy-ppo-summary.json'))),
  arena: JSON.parse(readFileSync(path.join(root, 'benchmarks/arena-primary.json'))) };
writeFileSync(path.join(web, 'public/training.json'), JSON.stringify(stats));
console.log('Prepared OCaml WASM, verified candidate ONNX and real evaluation records.');

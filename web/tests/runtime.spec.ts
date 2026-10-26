import { test, expect } from '@playwright/test';
import { readFileSync, writeFileSync } from 'node:fs';
test('native trace, features, PyTorch and browser WASM parity', async ({ page }) => {
  // Keep numerical checks on a same-origin harness without Vite's HMR client:
  // dependency discovery in a test Worker must not reload the awaiting page.
  await page.route('**/parity-harness', route => route.fulfill({
    contentType: 'text/html', body: '<!doctype html><title>Native/WASM parity</title>',
  }));
  await page.goto('/parity-harness');
  const traces = JSON.parse(readFileSync('tests/fixtures/native.json', 'utf8'));
  const result = await page.evaluate(traces => new Promise<any>((resolve, reject) => {
    const worker = new Worker('/tests/parity.worker.ts', { type: 'module' });
    worker.onmessage = ({ data }) => { worker.terminate(); resolve(data); };
    worker.onerror = e => { worker.terminate(); reject(e.message); };
    worker.postMessage({ base: location.origin + '/', traces });
  }), traces);
  expect(result.error).toBeUndefined(); expect(result.passed).toBe(true);
  writeFileSync('../benchmarks/browser-wasm-parity.json', JSON.stringify(result, null, 2) + '\n');
});

test('game Worker rejects stale/illegal actions, hides draws, and replays terminal scores', async ({ page }) => {
  await page.goto('/');
  const result = await page.evaluate(() => new Promise<any>((resolve, reject) => {
    const worker = new Worker('/src/game.worker.ts', { type: 'module' });
    let id = 0;
    const pending = new Map<number, { resolve: (v: any) => void; reject: (v: any) => void }>();
    worker.onmessage = ({ data }) => { const p = pending.get(data.id)!; pending.delete(data.id); data.error ? p.reject(new Error(data.error)) : p.resolve(data.result); };
    worker.onerror = e => reject(e.message);
    const rpc = (type: string, data: any = {}) => new Promise<any>((resolve, reject) => { pending.set(++id, { resolve, reject }); worker.postMessage({ id, type, data: { generation: 1, ...data } }); });
    (async () => {
      try {
        await rpc('load', { base: location.origin + '/' });
        let state = await rpc('start', { seed: 16000100, seat: 0, mode: 'human' });
        const revision = state.observation.revision;
        const errors = [];
        for (const action of [{ action: 999, revision }, { action: state.observation.legal_action_ids[0], revision: revision - 1 }]) {
          try { await rpc('act', action); throw new Error('accepted invalid action'); } catch (e) { errors.push(String(e)); }
        }
        if (errors.some(x => x.includes('accepted invalid'))) throw new Error('invalid action accepted');
        state = await rpc('start', { seed: 16000100, seat: 0, mode: 'watch' });
        let steps = 0, hiddenDrawChecks = 0;
        while (!state.ended && steps++ < 2000) {
          state = await rpc('tick');
          if (state.actor !== state.seat) {
            if (state.observation.drawn !== null || state.observation.legal_actions.length) throw new Error('UI leaks opponent draw/actions');
            hiddenDrawChecks++;
          }
        }
        if (!state.ended) throw new Error('watch did not finish');
        const replay = await rpc('export');
        state = await rpc('start', { replay });
        for (let i = 0; i < replay.actions.length; i++) state = await rpc('tick');
        if (!state.ended || JSON.stringify(state.observation.phase.outcome) !== JSON.stringify(replay.outcome)) throw new Error('replay mismatch');
        resolve({ steps, hiddenDrawChecks, errors, ended: state.ended });
      } catch (e) { reject(String(e)); } finally { worker.terminate(); }
    })();
  }));
  expect(result.ended).toBe(true); expect(result.hiddenDrawChecks).toBeGreaterThan(0); expect(result.errors).toHaveLength(2);
});

test('incompatible manifest and missing model fail explicitly', async ({ page }) => {
  await page.goto('/');
  const result = await page.evaluate(async () => {
    const { validateManifest } = await import('/src/runtime.ts');
    const manifest = await (await fetch('/models/candidate.manifest.json')).json();
    manifest.contract.feature_size = 770;
    try { validateManifest(manifest); return 'accepted'; } catch (e) { return String(e); }
  });
  expect(result).toContain('模型契约不兼容');
  await page.route('**/models/candidate.onnx', route => route.fulfill({ status: 404, body: 'not found' }));
  await page.reload();
  await expect(page.locator('#error')).toContainText('模型下载失败 (404)');
});

test('production subpath loads without WebGPU and fits a phone viewport', async ({ page }) => {
  test.skip(!process.env.STATIC_TEST_URL, 'Set STATIC_TEST_URL to a running static build');
  await page.addInitScript(() => Object.defineProperty(navigator, 'gpu', { value: undefined }));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(process.env.STATIC_TEST_URL!);
  await expect(page.locator('#engine-status')).toContainText('WASM · 本机推理');
  await expect(page.locator('#error')).toBeHidden();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  expect(await page.locator('.hand button').count()).toBeGreaterThan(0);
});

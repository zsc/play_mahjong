import { BrowserPolicy, call, loadEngine } from '../src/runtime';
import { encodeObservation } from '../src/features';
onmessage = async ({ data }) => {
  try {
    await loadEngine(data.base);
    const policy = new BrowserPolicy();
    await policy.load(data.base);
    const equal = (a: unknown, b: unknown, label: string) => {
      if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error(label + ': values differ');
    };
    let decisions = 0, samples = 0, maxLogits = 0, maxValue = 0, maxFeatures = 0;
    for (const trace of data.traces) {
      const game = call({ op: 'new', seed: trace.seed, round_wind: 'F1' }).handle;
      for (const row of trace.rows) {
        const { actor, observation } = call({ op: 'observe', game, seat: row.actor });
        equal(actor, row.actor, 'actor'); equal(observation, row.observation, 'observation');
        const features = encodeObservation(observation);
        features.forEach((x, i) => maxFeatures = Math.max(maxFeatures, Math.abs(x - row.features[i])));
        if (row.logits) {
          const result = await policy.infer(observation);
          equal(result.allowed, row.allowed, 'guard'); equal(result.action, row.action, 'model action');
          result.logits.forEach((x, i) => maxLogits = Math.max(maxLogits, Math.abs(x - row.logits[i])));
          maxValue = Math.max(maxValue, Math.abs(result.value - row.value)); samples++;
        }
        equal(call({ op: 'step', game, seat: actor, action_id: row.action }), row.result, 'transition');
        decisions++;
      }
      call({ op: 'validate', game });
      equal(call({ op: 'observe', game, seat: 0 }).observation, trace.final, 'terminal');
      call({ op: 'close', game });
    }
    if (maxFeatures > 1e-7 || maxLogits > 1e-4 || maxValue > 1e-4 || samples === 0) throw new Error(JSON.stringify({ maxFeatures, maxLogits, maxValue, samples }));
    postMessage({ passed: true, games: data.traces.length, decisions, samples, maxFeatures, maxLogits, maxValue, backend: 'ORT WASM single thread', webgpu: false });
  } catch (e) { postMessage({ error: (e as Error).stack }); }
};

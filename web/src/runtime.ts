import * as ort from 'onnxruntime-web/wasm';
import { ACTION_COUNT, encodeObservation, guardedDiscards } from './features';
import type { Observation } from './types';

type EngineResponse = { ok: boolean; error?: string; [key: string]: any };
declare global { var mahjongCall: (request: string) => string; }
export type Manifest = { model_id: string; format_version: number; is_smoke: boolean; is_random: boolean;
  contract: Record<string, unknown>; deployment: { discard_guard: string; scaffold_variant: string };
  files: { onnx: { path: string; sha256: string }; checkpoint: { sha256: string } };
  io: { inputs: { name: string; dtype: string; shape: unknown[] }[]; outputs: { name: string }[] } };

export async function getJson(url: URL) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`资源加载失败 (${response.status})：${url.pathname}`);
  return response.json();
}
export function call(request: Record<string, unknown>): EngineResponse {
  const response = JSON.parse(globalThis.mahjongCall(JSON.stringify(request))) as EngineResponse;
  if (!response.ok) throw new Error(response.error || '规则引擎拒绝了操作。');
  return response;
}
export async function loadEngine(base: string) {
  const url = new URL('runtime/engine.js', base).href;
  const module = await import(/* @vite-ignore */ url);
  await module.ready;
  if (typeof globalThis.mahjongCall !== 'function') throw new Error('规则引擎未能初始化，请使用支持 WebAssembly GC 的现代浏览器。');
}
export function validateManifest(m: Manifest) {
  const expected = { ruleset_id: 'mcr-wmo2006-stage1', observation_version: 1,
    feature_encoding_version: 6, action_catalog_version: 1, feature_size: 771, action_count: 122,
    discard_guard: 'teacher-optimal', scaffold_variant: 'qualified-tenpai' };
  if (m.format_version !== 1 || m.is_random || m.is_smoke) throw new Error('模型不是已验收的人测权重。');
  for (const [key, value] of Object.entries(expected)) if (m.contract[key] !== value) throw new Error(`模型契约不兼容：${key}`);
  if (m.deployment.discard_guard !== 'teacher-optimal' || m.deployment.scaffold_variant !== 'qualified-tenpai') throw new Error('模型部署配置不匹配。');
  if (JSON.stringify(m.io.inputs.map(i => [i.name, i.dtype, i.shape])) !== JSON.stringify([
    ['features', 'float32', ['batch', 771]], ['mask', 'bool', ['batch', 122]],
  ]) || m.io.outputs.map(i => i.name).join(',') !== 'logits,value') throw new Error('模型输入输出契约不兼容。');
}
export class BrowserPolicy {
  session!: ort.InferenceSession;
  manifest!: Manifest;
  async load(base: string) {
    this.manifest = await getJson(new URL('models/candidate.manifest.json', base));
    validateManifest(this.manifest);
    const response = await fetch(new URL('models/candidate.onnx', base));
    if (!response.ok) throw new Error(`模型下载失败 (${response.status})，请重新加载。`);
    const bytes = await response.arrayBuffer();
    const digest = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(x => x.toString(16).padStart(2, '0')).join('');
    if (digest !== this.manifest.files.onnx.sha256) throw new Error('模型校验失败，请清除缓存后重试。');
    ort.env.wasm.numThreads = 1;
    ort.env.wasm.proxy = false;
    ort.env.wasm.wasmPaths = new URL('ort/', base).href;
    this.session = await ort.InferenceSession.create(bytes, { executionProviders: ['wasm'], graphOptimizationLevel: 'all' });
    if (this.session.inputNames.join(',') !== 'features,mask' || this.session.outputNames.join(',') !== 'logits,value') throw new Error('ONNX 模型名称契约不匹配。');
  }
  async infer(observation: Observation) {
    const allowed = guardedDiscards(observation);
    const mask = new Uint8Array(ACTION_COUNT);
    allowed.forEach(a => { mask[a] = 1; });
    const features = encodeObservation(observation);
    const output = await this.session.run({ features: new ort.Tensor('float32', features, [1, 771]), mask: new ort.Tensor('bool', mask, [1, 122]) });
    const logits = Array.from(output.logits.data as Float32Array);
    const value = Number(output.value.data[0]);
    if (!Number.isFinite(value) || allowed.some(a => !Number.isFinite(logits[a]))) throw new Error('模型推理返回了无效数值。');
    const action = allowed.reduce((best, a) => logits[a] > logits[best] ? a : best, allowed[0]);
    const max = logits[action];
    const total = allowed.reduce((sum, a) => sum + Math.exp(logits[a] - max), 0);
    return { action, value, logits, features: Array.from(features), allowed,
      actions: allowed.map(id => ({ id, probability: Math.exp(logits[id] - max) / total })).sort((a, b) => b.probability - a.probability) };
  }
}
